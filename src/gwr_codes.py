"""
GWR (Eidg. Gebäude- und Wohnungsregister) Code-Tabellen
Quelle: BFS Merkmalskatalog v4.2 + GeoAdmin-Webviewer
Letzte Aktualisierung: 2026-02-24

Legende:
  ✓ = verifiziert (GeoAdmin-Webviewer / housing-stat.ch GWR-Auszug)
  ~ = aus Merkmalskatalog abgeleitet, plausibel
  ? = unsicher
"""

# ---------------------------------------------------------------------------
# GKLAS - Gebäudeklasse
# ---------------------------------------------------------------------------
GKLAS = {
    1110: "Gebäude mit einer Wohnung",
    1121: "Gebäude mit zwei Wohnungen",
    1122: "Gebäude mit drei oder mehr Wohnungen",
    1130: "Wohngebäude für Gemeinschaften",
    1211: "Hotelgebäude",
    1212: "Andere Hotelgebäude (Hospize, Herbergen)",
    1220: "Industrie- und Gewerbegebäude",
    1230: "Büro- und Verwaltungsgebäude",  # ~
    1231: "Bürogebäude",
    1241: "Gross- und Detailhandelsgebäude",
    1251: "Restaurants und Bars",
    1261: "Kulturgebäude",
    1262: "Museen und Bibliotheken",
    1263: "Schul- und Hochschulgebäude",
    1264: "Spital- und Heimgebäude",
    1265: "Sportgebäude",
    1271: "Landwirtschaftliche Betriebsgebäude",
    1272: "Gebäude der Forstwirtschaft",
    1273: "Gartenbaugebäude",
    1274: "Andere landwirtschaftliche Gebäude",
    1275: "Tierhaltungsgebäude",
    1276: "Lagergebäude",
    1277: "Gebäude für den Pflanzenbau",
    1278: "Fahrzeugunterkünfte",
}

# ---------------------------------------------------------------------------
# GKAT - Gebäudekategorie
# ---------------------------------------------------------------------------
GKAT = {
    1010: "Gebäude mit ausschliesslicher Wohnnutzung",
    1020: "Gebäude mit Wohnnutzung und anderen Nutzungen",
    1030: "Gebäude ohne Wohnnutzung mit Übernachtungsmöglichkeit",
    1040: "Gebäude mit teilweiser Wohnnutzung",         # ~
    1060: "Gebäude mit ausschliesslich betrieblicher Nutzung",
    1080: "Sonstige Gebäude (nicht bewohnt)",
}

# ---------------------------------------------------------------------------
# GSTAT - Gebäudestatus
# ---------------------------------------------------------------------------
GSTAT = {
    1001: "Projektiert",
    1002: "Bewilligt",
    1003: "Im Bau",
    1004: "Bestehend",
    1005: "Nicht nutzbar",
    1007: "Abgebrochen",
    1008: "Nicht realisiert",
    1009: "Unbekannt",
}

# ---------------------------------------------------------------------------
# GWAERZH - Wärmeerzeuger Heizung
# Quelle: GWR Merkmalskatalog 4.2 (housing-stat.ch/de/help/42.html, Wayback 2024)
# ---------------------------------------------------------------------------
GWAERZH = {
    7400: "Kein Wärmeerzeuger",
    7410: "Wärmepumpe für ein Gebäude",
    7411: "Wärmepumpe für mehrere Gebäude",
    7420: "Thermische Solaranlage für ein Gebäude",
    7421: "Thermische Solaranlage für mehrere Gebäude",
    7430: "Heizkessel (generisch) für ein Gebäude",
    7431: "Heizkessel (generisch) für mehrere Gebäude",
    7432: "Heizkessel nicht kondensierend für ein Gebäude",
    7433: "Heizkessel nicht kondensierend für mehrere Gebäude",
    7434: "Heizkessel kondensierend für ein Gebäude",
    7435: "Heizkessel kondensierend für mehrere Gebäude",
    7436: "Ofen",
    7440: "Wärmekraftkopplungsanlage für ein Gebäude",
    7441: "Wärmekraftkopplungsanlage für mehrere Gebäude",
    7450: "Elektrospeicher-Zentralheizung für ein Gebäude",
    7451: "Elektrospeicher-Zentralheizung für mehrere Gebäude",
    7452: "Elektro direkt",
    7460: "Wärmetauscher (inkl. Fernwärme) für ein Gebäude",
    7461: "Wärmetauscher (inkl. Fernwärme) für mehrere Gebäude",
    7499: "Andere",
}

# ---------------------------------------------------------------------------
# GWAERZW - Wärmeerzeuger Warmwasser (gleiche Struktur, eigene Codes)
# ---------------------------------------------------------------------------
GWAERZW = {
    7600: "Kein Wärmeerzeuger",
    7610: "Wärmepumpe für ein Gebäude",
    7611: "Wärmepumpe für mehrere Gebäude",
    7620: "Thermische Solaranlage für ein Gebäude",
    7621: "Thermische Solaranlage für mehrere Gebäude",
    7630: "Heizkessel (generisch) für ein Gebäude",
    7631: "Heizkessel (generisch) für mehrere Gebäude",
    7632: "Heizkessel nicht kondensierend für ein Gebäude",
    7633: "Heizkessel nicht kondensierend für mehrere Gebäude",
    7634: "Heizkessel kondensierend für ein Gebäude",
    7635: "Heizkessel kondensierend für mehrere Gebäude",
    7636: "Durchlauferhitzer",
    7640: "Wärmekraftkopplungsanlage für ein Gebäude",
    7641: "Wärmekraftkopplungsanlage für mehrere Gebäude",
    7650: "Elektroboiler für ein Gebäude",
    7651: "Elektroboiler für mehrere Gebäude",
    7652: "Elektro direkt",
    7660: "Wärmetauscher (inkl. Fernwärme) für ein Gebäude",
    7661: "Wärmetauscher (inkl. Fernwärme) für mehrere Gebäude",
    7699: "Andere",
}

# Kombinierter Lookup (für Fälle wo GWAERZH/W zusammen verwendet wird)
GWAERZ = {**GWAERZH, **GWAERZW}

# ---------------------------------------------------------------------------
# GENH / GENW - Energie-/Wärmequelle (Heizung und Warmwasser)
# Quelle: GWR Merkmalskatalog 4.2 (offiziell, vollständig)
# Hinweis: Beschreibt die PRIMÄRENERGIE, nicht die Hilfsenergie
#          (z.B. bei Wärmepumpe: GENH = Luft/Erdwärme, nicht Strom)
# ---------------------------------------------------------------------------
GENH = {
    7500: "Keine",
    7501: "Luft",                           # Primärenergie für Luftwärmepumpen
    7510: "Erdwärme (generisch)",
    7511: "Erdwärmesonde",
    7512: "Erdregister",
    7513: "Wasser (Grundwasser, Oberflächenwasser, Abwasser)",
    7520: "Gas",
    7530: "Heizöl",
    7540: "Holz (generisch)",
    7541: "Holz (Stückholz)",
    7542: "Holz (Pellets)",
    7543: "Holz (Schnitzel)",
    7550: "Abwärme (innerhalb des Gebäudes)",
    7560: "Elektrizität",
    7570: "Sonne (thermisch)",
    7580: "Fernwärme (generisch)",
    7581: "Fernwärme (Hochtemperatur)",
    7582: "Fernwärme (Niedertemperatur)",
    7598: "Unbestimmt",
    7599: "Andere",
}

# ---------------------------------------------------------------------------
# DWST - Wohnungsstatus
# ---------------------------------------------------------------------------
DWST = {
    3001: "Projektiert",
    3002: "Bewilligt",
    3003: "Im Bau",
    3004: "Bestehend",
    3005: "Nicht nutzbar",
    3007: "Abgebrochen",
    3008: "Nicht realisiert",
    3009: "Unbekannt",
}

# ---------------------------------------------------------------------------
# WAZIM - Zimmeranzahl (für Infos)
# ---------------------------------------------------------------------------
# Numerisch, kein Lookup nötig

# ---------------------------------------------------------------------------
# Lookup-Funktion
# ---------------------------------------------------------------------------
def decode(code, table, fallback=True):
    """Dekodiert einen GWR-Code.
    
    Args:
        code: numerischer Code (int oder str)
        table: eine der Code-Tabellen (GKAT, GSTAT, GWAERZ, GENH, ...)
        fallback: wenn True, gibt 'Code <code>' zurück wenn nicht gefunden
    
    Returns:
        str: Klartext oder None/Fallback
    """
    if code is None:
        return None
    try:
        code = int(code)
    except (ValueError, TypeError):
        return str(code)
    result = table.get(code)
    if result is None and fallback:
        return f"Code {code}"
    return result


# ---------------------------------------------------------------------------
# Convenience: vollständige Gebäude-Zusammenfassung
# ---------------------------------------------------------------------------
def summarize_building(attrs: dict) -> dict:
    """Erstellt eine lesbare Zusammenfassung aus GWR-Rohdaten (JSON/dict)."""
    def d(key, table):
        return decode(attrs.get(key), table)

    heizung = []
    for i in (1, 2):
        gen = attrs.get(f'gwaerzh{i}')
        ene = attrs.get(f'genh{i}')
        if gen and gen not in (7400, '7400', None):
            gen_txt = decode(gen, GWAERZ)
            ene_txt = decode(ene, GENH) if ene and ene not in (7500, '7500') else None
            heizung.append(f"{gen_txt}" + (f" ({ene_txt})" if ene_txt else ""))

    warmwasser = []
    for i in (1, 2):
        gen = attrs.get(f'gwaerzw{i}')
        ene = attrs.get(f'genw{i}')
        if gen and gen not in (7600, '7600', None):
            gen_txt = decode(gen, GWAERZ)
            ene_txt = decode(ene, GENH) if ene and ene not in (7500, '7500') else None
            warmwasser.append(f"{gen_txt}" + (f" ({ene_txt})" if ene_txt else ""))

    return {
        "status": d('gstat', GSTAT),
        "kategorie": d('gkat', GKAT),
        "klasse": d('gklas', GKLAS),
        "baujahr": attrs.get('gbauj'),
        "stockwerke": attrs.get('gastw'),
        "grundflaeche_m2": attrs.get('garea'),
        "heizung": heizung or None,
        "warmwasser": warmwasser or None,
    }


if __name__ == "__main__":
    # Selbsttest
    print("GSTAT 1004:", decode(1004, GSTAT))
    print("GWAERZ 7430:", decode(7430, GWAERZ))
    print("GENH 7520:", decode(7520, GENH))
    print("GENH 7530:", decode(7530, GENH))
    print("GKAT 1040:", decode(1040, GKAT))
