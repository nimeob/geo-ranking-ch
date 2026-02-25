"""
geo_utils.py — Schweizer Geodaten-Utilities (swisstopo / GeoAdmin API)

Verwendung in anderen Skills:
    import sys; sys.path.insert(0, '/data/.openclaw/workspace')
    from geo_utils import geocode_ch, elevation_at, wgs84_to_lv95, location_info, building_info

Kein API-Key nötig. Nur CH-Daten (Schweiz + Liechtenstein).
"""

import json
import math
import re
import urllib.request
import urllib.parse
from typing import Optional

GEOADMIN_BASE  = "https://api3.geo.admin.ch/rest/services"
REFRAME_BASE   = "https://geodesy.geo.admin.ch/reframe"
HEADERS        = {"User-Agent": "openclaw-geo-utils/1.0", "Accept": "application/json"}


# ── HTTP-Helfer ────────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _post(url: str, data: bytes, content_type: str = "application/x-www-form-urlencoded", timeout: int = 10) -> list | dict:
    req = urllib.request.Request(url, data=data, headers={**HEADERS, "Content-Type": content_type})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ── Koordinaten-Umrechnung ────────────────────────────────────────────────────

def wgs84_to_lv95(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 (lat, lon) → LV95 (easting, northing).
    
    Returns: (easting, northing) in LV95 / EPSG:2056
    """
    url = f"{REFRAME_BASE}/wgs84tolv95?easting={lon}&northing={lat}&format=json"
    d = _get(url)
    return float(d["easting"]), float(d["northing"])


def lv95_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """LV95 (easting, northing) → WGS84 (lat, lon).
    
    Returns: (lat, lon)
    """
    url = f"{REFRAME_BASE}/lv95towgs84?easting={easting}&northing={northing}&format=json"
    d = _get(url)
    return float(d["northing"]), float(d["easting"])


# ── Höhe / Elevation ──────────────────────────────────────────────────────────

def elevation_at(lat: float, lon: float) -> Optional[float]:
    """Höhe über Meer an einem WGS84-Punkt (swisstopo DHM25/SRTM kombiniert).
    
    Returns: Höhe in Metern (ü.M.), oder None wenn außerhalb CH.
    """
    e, n = wgs84_to_lv95(lat, lon)
    url = f"{GEOADMIN_BASE}/height?easting={e}&northing={n}&sr=2056"
    try:
        d = _get(url)
        h = d.get("height")
        return float(h) if h not in (None, "None") else None
    except Exception:
        return None


def elevation_profile(
    waypoints: list[tuple[float, float]],
    nb_points: int = 100,
) -> list[dict]:
    """Höhenprofil entlang einer Route (WGS84-Punkte).

    Args:
        waypoints: Liste von (lat, lon)-Tupeln (mindestens 2)
        nb_points: Anzahl interpolierter Punkte im Profil (max 5000)

    Returns: Liste von Dicts mit keys: dist_m, alt_m, lat, lon
    """
    if len(waypoints) < 2:
        raise ValueError("Mindestens 2 Punkte erforderlich")

    lv_coords = [wgs84_to_lv95(lat, lon) for lat, lon in waypoints]
    geom = {"type": "LineString", "coordinates": [[e, n] for e, n in lv_coords]}
    geom_json = json.dumps(geom)

    url = f"{GEOADMIN_BASE}/profile.json?sr=2056&nb_points={nb_points}"
    data = urllib.parse.urlencode({"geom": geom_json}).encode()
    pts = _post(url, data)

    result = []
    for p in pts:
        e, n = p["easting"], p["northing"]
        lat, lon = lv95_to_wgs84(e, n)
        result.append({
            "dist_m": round(p["dist"], 1),
            "alt_m":  round(p["alts"].get("COMB", p["alts"].get("DTM25", 0)), 1),
            "lat": round(lat, 6),
            "lon": round(lon, 6),
        })
    return result


# ── Geocoding ─────────────────────────────────────────────────────────────────

def geocode_ch(
    query: str,
    origins: str = "address,gg25,gazetteer",
    limit: int = 5,
) -> list[dict]:
    """Schweizer Adressen, Orte und Features geocodieren (GeoAdmin SearchServer).

    Args:
        query:   Suchbegriff (Adresse, Ortsname, Gipfel, …)
        origins: Kommagetrennte Quellen:
                   address   – Adressen (GWR)
                   gg25      – Gemeinden/Kantone
                   gazetteer – Berge, Seen, Quartiere, ÖV-Haltestellen, …
                   parcel    – Grundstücke (Parzellen)
        limit:   Max. Ergebnisse

    Returns: Liste von Dicts mit keys: label, lat, lon, easting, northing,
             origin, detail, zip_code, city
    """
    params = urllib.parse.urlencode({
        "searchText": query,
        "type": "locations",
        "origins": origins,
        "sr": "2056",
        "limit": limit,
        "lang": "de",
    })
    url = f"{GEOADMIN_BASE}/api/SearchServer?{params}"
    d = _get(url)

    results = []
    for r in d.get("results", [])[:limit]:
        a = r.get("attrs", {})
        # LV95 vom SearchServer: x=northing, y=easting (vertauscht!)
        lv_e = a.get("y") or a.get("lon")
        lv_n = a.get("x") or a.get("lat")
        lat, lon = (None, None)
        if lv_e and lv_n:
            try:
                lat, lon = lv95_to_wgs84(float(lv_e), float(lv_n))
            except Exception:
                pass

        # Label bereinigen (HTML-Tags entfernen)
        label = a.get("label", "")
        label = re.sub(r"<[^>]+>", "", label).strip()

        results.append({
            "label":    label,
            "lat":      round(lat, 7) if lat else None,
            "lon":      round(lon, 7) if lon else None,
            "easting":  float(lv_e) if lv_e else None,
            "northing": float(lv_n) if lv_n else None,
            "origin":   a.get("origin"),
            "detail":   a.get("detail", ""),
            "zip_code": a.get("postalcode") or a.get("zscode"),
            "city":     a.get("city"),
            "egid":     a.get("egid"),
            "feature_id": a.get("featureId"),
        })
    return results


# ── Standort-Info ─────────────────────────────────────────────────────────────

def location_info(lat: float, lon: float) -> dict:
    """Gemeinde, Kanton und Koordinaten für einen WGS84-Punkt ermitteln.

    Returns: Dict mit keys: gemeinde, kanton, kanton_kz, gde_nr,
             easting, northing, elevation_m
    """
    e, n = wgs84_to_lv95(lat, lon)

    # Margin für mapExtent (~500m)
    margin = 500
    map_extent = f"{e-margin},{n-margin},{e+margin},{n+margin}"

    url = (
        f"{GEOADMIN_BASE}/api/MapServer/identify"
        f"?geometry={e},{n}&geometryType=esriGeometryPoint"
        f"&imageDisplay=500,500,96"
        f"&mapExtent={map_extent}"
        f"&tolerance=5"
        f"&layers=all:ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill,"
        f"ch.swisstopo.swissboundaries3d-kanton-flaeche.fill"
        f"&sr=2056&lang=de&returnGeometry=false&f=json"
    )
    d = _get(url)
    results = d.get("results", [])

    gemeinde = kanton = kanton_kz = None
    gde_nr = None

    for r in results:
        attrs = r.get("attributes", {})
        layer = r.get("layerBodId", "")
        is_current = attrs.get("is_current_jahr", True)  # Kanton-Layer hat kein is_current_jahr
        if "gemeinde" in layer:
            if attrs.get("is_current_jahr") and gemeinde is None:
                gemeinde  = attrs.get("gemname")
                kanton_kz = attrs.get("kanton")
                gde_nr    = attrs.get("gde_nr")
        elif "kanton" in layer and kanton is None:
            kanton = attrs.get("name") or attrs.get("ak")

    # Höhe
    elev = elevation_at(lat, lon)

    return {
        "gemeinde":    gemeinde,
        "kanton":      kanton,
        "kanton_kz":   kanton_kz,
        "gde_nr":      gde_nr,
        "easting":     round(e, 2),
        "northing":    round(n, 2),
        "elevation_m": elev,
    }


# ── GWR-Code-Tabellen ─────────────────────────────────────────────────────────

_GKAT = {
    1010: "Einfamilienhaus", 1020: "EFH + Nebengebäude", 1021: "EFH + Wohngebäude",
    1025: "Mehrfamilienhaus", 1030: "Wohngebäude", 1040: "Gebäude m. teilw. Wohnnutzung",
    1060: "Gebäude o. Wohnnutzung", 1080: "Sonderbau",
}
_GSTAT = {
    1001: "Geplant", 1002: "Im Bau", 1003: "Bestehend (kein Wohnen)",
    1004: "Bestehend", 1005: "Nicht nutzbar", 1007: "Abgebrochen", 1008: "Im Abbruch",
}
_GWAERZ = {
    7400: "Wärmepumpe", 7410: "WP Luft/Wasser", 7420: "WP Sole/Wasser",
    7421: "WP Sole/Wasser (Grundwasser)", 7430: "WP Wasser/Wasser",
    7431: "WP Wasser/Wasser (Grundwasser)", 7440: "WP Abwasser", 7460: "WP andere",
    7470: "Solaranlage thermisch", 7480: "Solaranlage kombiniert",
    7490: "Solaranlage PV",
    7500: "Heizkessel", 7510: "HK + Wärmerückgewinnung", 7520: "Heizkessel Biogas",
    7530: "Wärme-Kraft-Kopplung", 7540: "Cheminée/Kamin", 7550: "Kachelofen",
    7560: "Elektr. Speicherheizung", 7570: "Elektro-Direktheizung",
    7580: "Fernwärme-Übergabestation", 7590: "Wärmekopplung Abwasser",
    7600: "Andere", 7610: "Holzschnitzelheizung", 7620: "Pelletsheizung",
    7630: "Holzschnitzelheizung", 7640: "Elektro-Boiler",
    7650: "Elektro-Durchlauferhitzer", 7651: "Elektro-Warmwasserbereiter",
    7660: "Wärmepumpenboiler",
}
_GENH = {
    7500: "Gas", 7501: "Biogas", 7510: "Flüssiggas", 7511: "Heizöl", 7512: "Kohle/Koks",
    7520: "Holz (Pellets)", 7521: "Holz (Stückholz)", 7522: "Holz (Schnitzel)",
    7530: "Elektrizität", 7540: "Sonne", 7550: "Fernwärme",
    7560: "Wasser", 7570: "Erde/Geothermie", 7580: "Luft", 7590: "Abwasser",
    7600: "Andere",
}
_WSTWK = {
    3101: "Atelier/Studio", 3102: "Wohnung", 3103: "Wohnheim", 3104: "Wohnküche",
}
_WSTAT = {
    3001: "Geplant", 3002: "Im Bau", 3003: "Bestehend (alt)", 3004: "Bestehend",
    3005: "Nicht nutzbar", 3007: "Abgebrochen", 3008: "Im Abbruch",
}


def _gwr_code(table: dict, code) -> str:
    if code is None:
        return "–"
    try:
        c = int(code)
        return table.get(c, f"Code {c}")
    except (ValueError, TypeError):
        return str(code)


# ── Gebäude-Info (Adressregister + GWR) ──────────────────────────────────────

def building_info(address: str) -> Optional[dict]:
    """Gebäude- und Wohnungsdaten aus dem amtlichen Adressregister + GWR.

    Sucht die Adresse, holt dann per featureId die Daten aus:
      - ch.swisstopo.amtliches-gebaeudeadressverzeichnis
      - ch.bfs.gebaeude_wohnungs_register

    Args:
        address: Schweizer Adresse als Freitext, z.B. "Espenmoosstrasse 18 9008 St. Gallen"

    Returns: Dict mit Gebäude- und Wohnungsdaten, oder None wenn nicht gefunden.
    """
    hits = geocode_ch(address, origins="address", limit=1)
    if not hits:
        return None

    h = hits[0]
    feature_id = h.get("feature_id")
    if not feature_id:
        return None

    result = {
        "address":    h["label"],
        "lat":        h["lat"],
        "lon":        h["lon"],
        "easting":    h["easting"],
        "northing":   h["northing"],
        "feature_id": feature_id,
    }

    # Amtliches Adressregister
    try:
        url = f"{GEOADMIN_BASE}/ech/MapServer/ch.swisstopo.amtliches-gebaeudeadressverzeichnis/{feature_id}?lang=de&sr=4326"
        d = _get(url)
        a = d.get("feature", d).get("attributes", {})
        result.update({
            "egid":           a.get("bdg_egid"),
            "egaid":          a.get("adr_egaid"),
            "street_id":      a.get("str_esid"),
            "building_cat":   a.get("bdg_category"),
            "addr_official":  a.get("adr_official"),
            "addr_modified":  a.get("adr_modified"),
        })
    except Exception:
        pass

    # GWR (Gebäude- und Wohnungsregister)
    try:
        url = f"{GEOADMIN_BASE}/ech/MapServer/ch.bfs.gebaeude_wohnungs_register/{feature_id}?lang=de&sr=4326"
        d = _get(url)
        g = d.get("feature", d).get("attributes", {})

        # Wohnungen entschlüsseln (Arrays im GWR)
        eids   = g.get("ewid", []) or []
        typen  = g.get("wstwk", []) or []
        stats  = g.get("wstat", []) or []
        flaechen = g.get("warea", []) or []
        zimmer   = g.get("wazim", []) or []
        baujahre = g.get("wbauj", []) or []

        wohnungen = []
        for i in range(len(eids)):
            wohnungen.append({
                "ewid":    eids[i] if i < len(eids) else None,
                "typ":     _gwr_code(_WSTWK, typen[i] if i < len(typen) else None),
                "status":  _gwr_code(_WSTAT, stats[i] if i < len(stats) else None),
                "flaeche_m2": flaechen[i] if i < len(flaechen) else None,
                "zimmer":     zimmer[i]   if i < len(zimmer)   else None,
                "baujahr":    baujahre[i] if i < len(baujahre) else None,
            })

        result.update({
            "egrid":        g.get("egrid"),
            "parzelle":     g.get("lparz"),
            "grundbuchkreis": g.get("lgbkr"),
            "gebaeudename":  g.get("gbez"),
            "gebaeudenr":    g.get("gebnr"),
            "baujahr":       g.get("gbauj"),
            "grundflaeche_m2": g.get("garea"),
            "stockwerke":    g.get("gastw"),
            "anzahl_wohnungen": g.get("ganzwhg"),
            "status":        _gwr_code(_GSTAT, g.get("gstat")),
            "kategorie":     _gwr_code(_GKAT,  g.get("gkat")),
            "heizung": {
                "primaer":  {
                    "geraet":   _gwr_code(_GWAERZ, g.get("gwaerzh1")),
                    "energie":  _gwr_code(_GENH,   g.get("genh1")),
                    "stand":    g.get("gwaerdath1"),
                },
                "sekundaer": {
                    "geraet":   _gwr_code(_GWAERZ, g.get("gwaerzh2")),
                    "energie":  _gwr_code(_GENH,   g.get("genh2")),
                    "stand":    g.get("gwaerdath2"),
                } if g.get("gwaerzh2") else None,
            },
            "warmwasser": {
                "primaer": {
                    "geraet":  _gwr_code(_GWAERZ, g.get("gwaerzw1")),
                    "energie": _gwr_code(_GENH,   g.get("genw1")),
                },
                "sekundaer": {
                    "geraet":  _gwr_code(_GWAERZ, g.get("gwaerzw2")),
                    "energie": _gwr_code(_GENH,   g.get("genw2")),
                } if g.get("gwaerzw2") else None,
            },
            "wohnungen": wohnungen,
        })
    except Exception:
        pass

    return result


# ── Haversine (lokal, kein API) ───────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Luftlinie in km zwischen zwei WGS84-Punkten."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ── CLI (direkte Verwendung) ──────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="swisstopo Geodaten-Utilities")
    sub = parser.add_subparsers(dest="cmd")

    p_elev = sub.add_parser("elevation", help="Höhe an einem Punkt")
    p_elev.add_argument("lat", type=float)
    p_elev.add_argument("lon", type=float)

    p_profile = sub.add_parser("profile", help="Höhenprofil zwischen zwei Punkten")
    p_profile.add_argument("lat1", type=float)
    p_profile.add_argument("lon1", type=float)
    p_profile.add_argument("lat2", type=float)
    p_profile.add_argument("lon2", type=float)
    p_profile.add_argument("--points", type=int, default=10)

    p_geo = sub.add_parser("geocode", help="Adresse / Ort suchen")
    p_geo.add_argument("query", nargs="+")
    p_geo.add_argument("--origins", default="address,gg25,gazetteer")

    p_loc = sub.add_parser("locate", help="Gemeinde + Kanton für Koordinate")
    p_loc.add_argument("lat", type=float)
    p_loc.add_argument("lon", type=float)

    p_conv = sub.add_parser("convert", help="WGS84 → LV95")
    p_conv.add_argument("lat", type=float)
    p_conv.add_argument("lon", type=float)

    p_bld = sub.add_parser("building", help="Gebäude-/GWR-Daten zu einer Adresse")
    p_bld.add_argument("address", nargs="+", help="Schweizer Adresse")

    args = parser.parse_args()

    if args.cmd == "elevation":
        h = elevation_at(args.lat, args.lon)
        print(f"📐 Höhe: {h} m ü.M." if h else "❌ Keine Daten (außerhalb CH?)")

    elif args.cmd == "profile":
        pts = elevation_profile([(args.lat1, args.lon1), (args.lat2, args.lon2)], args.points)
        alts = [p["alt_m"] for p in pts]
        print(f"📊 Höhenprofil ({len(pts)} Punkte):")
        print(f"   Start:  {pts[0]['alt_m']} m  |  Ende: {pts[-1]['alt_m']} m")
        print(f"   Min:    {min(alts)} m  |  Max:  {max(alts)} m")
        print(f"   Anstieg: +{sum(max(0, b-a) for a,b in zip(alts,alts[1:])):.0f} m  "
              f"Abstieg: -{sum(max(0, a-b) for a,b in zip(alts,alts[1:])):.0f} m")
        print(f"   Distanz: {pts[-1]['dist_m']/1000:.2f} km")
        for p in pts:
            print(f"   {p['dist_m']:>7.0f} m → {p['alt_m']:>6.1f} m  ({p['lat']}, {p['lon']})")

    elif args.cmd == "geocode":
        q = " ".join(args.query)
        results = geocode_ch(q, origins=args.origins)
        print(f"🔍 \"{q}\" → {len(results)} Treffer\n")
        for r in results:
            coord = f"{r['lat']}, {r['lon']}" if r['lat'] else "?"
            print(f"  📍 {r['label']}")
            print(f"     WGS84: {coord}  |  LV95: E={r['easting']:.0f} N={r['northing']:.0f}")
            print(f"     origin: {r['origin']}  detail: {r['detail']}")

    elif args.cmd == "locate":
        info = location_info(args.lat, args.lon)
        print(f"📍 {args.lat}, {args.lon}")
        print(f"   Gemeinde:  {info['gemeinde']} (Nr. {info['gde_nr']})")
        print(f"   Kanton:    {info['kanton']} ({info['kanton_kz']})")
        print(f"   LV95:      E={info['easting']:.0f}  N={info['northing']:.0f}")
        print(f"   Höhe:      {info['elevation_m']} m ü.M.")

    elif args.cmd == "convert":
        e, n = wgs84_to_lv95(args.lat, args.lon)
        print(f"WGS84:  {args.lat}, {args.lon}")
        print(f"LV95:   E={e:.3f}  N={n:.3f}")

    elif args.cmd == "building":
        addr = " ".join(args.address)
        b = building_info(addr)
        if not b:
            print(f"❌ Adresse nicht gefunden: {addr}")
        else:
            print(f"🏢 {b['address']}")
            print(f"   📍 WGS84: {b['lat']}, {b['lon']}")
            print(f"   📐 LV95:  E={b['easting']:.0f}  N={b['northing']:.0f}")
            if b.get("gebaeudename"):
                print(f"   📛 Name:  {b['gebaeudename']}")
            print(f"   🆔 EGID:  {b.get('egid', '–')}  |  EGRID: {b.get('egrid', '–')}")
            print(f"   📋 Parzelle: {b.get('parzelle', '–')}  (GBKreis {b.get('grundbuchkreis', '–')})")
            print(f"   📊 Status: {b.get('status', '–')}  |  Kategorie: {b.get('kategorie', '–')}")
            if b.get("baujahr"):
                print(f"   🗓  Baujahr: {b['baujahr']}  |  Fläche: {b.get('grundflaeche_m2', '–')} m²  |  Stockwerke: {b.get('stockwerke', '–')}")
            hz = b.get("heizung", {})
            if hz:
                p = hz.get("primaer", {})
                s = hz.get("sekundaer")
                print(f"   🔥 Heizung:  {p.get('geraet')} / {p.get('energie')}  (Stand: {p.get('stand', '–')})")
                if s:
                    print(f"              + {s.get('geraet')} / {s.get('energie')}  (Stand: {s.get('stand', '–')})")
            ww = b.get("warmwasser", {})
            if ww:
                p = ww.get("primaer", {})
                print(f"   🚿 Warmwasser: {p.get('geraet')} / {p.get('energie')}")
            wohnungen = b.get("wohnungen", [])
            if wohnungen:
                print(f"   🏠 Wohnungen ({len(wohnungen)}):")
                for w in wohnungen:
                    zi = f"{w['zimmer']} Zi" if w.get("zimmer") else ""
                    fl = f"{w['flaeche_m2']} m²" if w.get("flaeche_m2") else ""
                    bj = f"Bj. {w['baujahr']}" if w.get("baujahr") else ""
                    info_parts = [x for x in [zi, fl, bj] if x]
                    print(f"      Whg {w['ewid']}: {w['typ']} — {', '.join(info_parts)}")

    else:
        parser.print_help()
