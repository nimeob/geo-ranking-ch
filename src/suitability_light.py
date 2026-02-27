from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _as_finite_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _score_topography(elevation_m: Optional[float]) -> Tuple[float, str, bool]:
    if elevation_m is None:
        return 50.0, "Keine belastbare Höhenlage vorhanden (neutral angesetzt).", True
    if elevation_m < 250:
        return 56.0, "Tieflage; mögliche Zusatzrisiken (z. B. lokale Hochwasser-/Grundwasser-Themen).", False
    if elevation_m <= 950:
        return 82.0, "Moderate Höhenlage; typischerweise gute Ausgangslage für Standardbauvorhaben.", False
    if elevation_m <= 1400:
        return 64.0, "Erhöhte Lage; potenziell anspruchsvollere Randbedingungen (Klima/Erschliessung).", False
    return 42.0, "Alpine Höhenlage; erhöhte technische/operative Komplexität wahrscheinlich.", False


def _score_access(has_road_access: bool, has_plz: bool, has_admin_boundary: bool) -> Tuple[float, str, bool]:
    coverage = int(bool(has_plz)) + int(bool(has_admin_boundary))
    if has_road_access and coverage == 2:
        return 84.0, "Straßenbezug + administrative Verortung vollständig vorhanden.", False
    if has_road_access and coverage >= 1:
        return 76.0, "Straßenbezug vorhanden, administrative Verortung teilweise gesichert.", False
    if coverage == 2:
        return 60.0, "Administrative Verortung vorhanden, aber kein belastbarer Straßenbezug.", True
    if coverage == 1:
        return 52.0, "Nur teilweise Verortung; Erschliessung unklar.", True
    return 40.0, "Weder Straßenbezug noch stabile Verortung verfügbar.", True


def _score_building_state(building_status: Optional[str]) -> Tuple[float, str, bool]:
    status = (building_status or "").strip()
    if not status:
        return 50.0, "Kein Gebäudestatus verfügbar (neutral angesetzt).", True

    lowered = status.lower()
    if "bestehend" in lowered or "in betrieb" in lowered:
        return 74.0, f"Gebäudestatus '{status}' spricht für grundsätzlich belastbaren Bestand.", False
    if "im bau" in lowered:
        return 58.0, f"Gebäudestatus '{status}' deutet auf Übergangsphase mit Unsicherheiten.", False
    if "geplant" in lowered:
        return 44.0, f"Gebäudestatus '{status}' weist auf frühe Planungsphase hin.", False
    if "abbruch" in lowered or "ruine" in lowered:
        return 24.0, f"Gebäudestatus '{status}' signalisiert hohe Umsetzungsrisiken.", False
    return 54.0, f"Gebäudestatus '{status}' ist nicht eindeutig modelliert (konservativ bewertet).", True


def _score_data_quality(confidence_score: Optional[float]) -> Tuple[float, str, bool]:
    if confidence_score is None:
        return 50.0, "Keine Confidence verfügbar; Datenqualität neutral angesetzt.", True

    score = _clamp(confidence_score)
    if score >= 82:
        reason = "Hohe Match-/Quellen-Confidence stabilisiert die Light-Heuristik."
    elif score >= 62:
        reason = "Mittlere Confidence; Ergebnis nutzbar, aber mit Review-Bedarf."
    else:
        reason = "Niedrige Confidence; deutliche Unsicherheiten in den Eingangsdaten."
    return score, reason, False


def _traffic_light(score: float) -> str:
    if score >= 72:
        return "green"
    if score >= 52:
        return "yellow"
    return "red"


def evaluate_suitability_light(
    *,
    elevation_m: Any,
    has_road_access: bool,
    confidence_score: Any,
    building_status: Optional[str],
    has_plz: bool,
    has_admin_boundary: bool,
) -> Dict[str, Any]:
    """Deterministische Bau-Eignung light Heuristik (BL-20.5.b).

    Wichtig: Das Ergebnis ist ein indikatives Vorprüfungs-Signal und ersetzt
    keine baurechtliche, geotechnische oder statische Fachbeurteilung.
    """

    elevation = _as_finite_float(elevation_m)
    confidence = _as_finite_float(confidence_score)

    topography_score, topography_reason, topo_limited = _score_topography(elevation)
    access_score, access_reason, access_limited = _score_access(bool(has_road_access), bool(has_plz), bool(has_admin_boundary))
    building_score, building_reason, building_limited = _score_building_state(building_status)
    quality_score, quality_reason, quality_limited = _score_data_quality(confidence)

    weights = {
        "topography": 0.34,
        "access": 0.29,
        "building_state": 0.17,
        "data_quality": 0.20,
    }

    factors: List[Dict[str, Any]] = [
        {
            "key": "topography",
            "label": "Topografie/Höhenlage (Proxy)",
            "raw_value": elevation,
            "score": round(topography_score, 1),
            "weight": weights["topography"],
            "contribution": round(topography_score * weights["topography"], 2),
            "reason": topography_reason,
            "limited": topo_limited,
        },
        {
            "key": "access",
            "label": "Zugang/Erschliessung (Proxy)",
            "raw_value": {
                "road_access": bool(has_road_access),
                "plz": bool(has_plz),
                "admin_boundary": bool(has_admin_boundary),
            },
            "score": round(access_score, 1),
            "weight": weights["access"],
            "contribution": round(access_score * weights["access"], 2),
            "reason": access_reason,
            "limited": access_limited,
        },
        {
            "key": "building_state",
            "label": "Gebäudestatus (GWR-Proxy)",
            "raw_value": building_status,
            "score": round(building_score, 1),
            "weight": weights["building_state"],
            "contribution": round(building_score * weights["building_state"], 2),
            "reason": building_reason,
            "limited": building_limited,
        },
        {
            "key": "data_quality",
            "label": "Datenqualität/Confidence",
            "raw_value": confidence,
            "score": round(quality_score, 1),
            "weight": weights["data_quality"],
            "contribution": round(quality_score * weights["data_quality"], 2),
            "reason": quality_reason,
            "limited": quality_limited,
        },
    ]

    base_score = sum(float(row["contribution"]) for row in factors)

    uncertainty_reasons: List[str] = []
    uncertainty_score = 6.0
    if topo_limited:
        uncertainty_score += 18.0
        uncertainty_reasons.append("Topografie nur über Höhen-Proxy modelliert (keine Hangneigung).")
    if access_limited:
        uncertainty_score += 16.0
        uncertainty_reasons.append("Erschliessung nicht vollständig belegt (Straßen-/Verortungslücke).")
    if building_limited:
        uncertainty_score += 10.0
        uncertainty_reasons.append("Gebäudestatus fehlt oder ist nicht eindeutig modelliert.")
    if quality_limited:
        uncertainty_score += 12.0
        uncertainty_reasons.append("Confidence fehlt; Datenqualität nur neutral angesetzt.")
    elif confidence is not None and confidence < 62:
        uncertainty_score += 10.0
        uncertainty_reasons.append("Niedrige Match-/Quellen-Confidence reduziert Aussagekraft.")

    uncertainty_score = _clamp(uncertainty_score)
    penalty = uncertainty_score * 0.18
    final_score = _clamp(base_score - penalty)

    traffic_light = _traffic_light(final_score)
    if traffic_light == "green":
        classification = "geeignet"
    elif traffic_light == "yellow":
        classification = "bedingt geeignet"
    else:
        classification = "kritisch"

    uncertainty_level = "low" if uncertainty_score < 25 else ("medium" if uncertainty_score < 55 else "high")

    limitations = [
        "Heuristik ersetzt keine baurechtliche Bewilligungsprüfung.",
        "Keine geotechnischen Messdaten (Boden, Altlasten, Tragfähigkeit) enthalten.",
        "Keine statische, brandschutztechnische oder nutzungsspezifische Fachplanung enthalten.",
    ]
    if uncertainty_reasons:
        limitations.extend(uncertainty_reasons)

    base_score_value = round(base_score, 2)

    return {
        "status": "ok" if uncertainty_level != "high" else "partial",
        "heuristic_version": "bl-20.5.b-v1",
        "score": int(round(final_score)),
        "traffic_light": traffic_light,
        "classification": classification,
        "base_score": base_score_value,
        # BL-20.4.d.wp2: Contract-Feld bereits ausliefern;
        # echte Präferenz-Reweighting-Integration folgt in späterem Work-Package.
        "personalized_score": base_score_value,
        "uncertainty": {
            "score": int(round(uncertainty_score)),
            "level": uncertainty_level,
            "penalty": round(penalty, 2),
            "reasons": uncertainty_reasons,
        },
        "factors": factors,
        "limitations": limitations,
        "next_steps": [
            "Bei kritischem/gelbem Ergebnis: Hangneigung, Zufahrt und Bauzonenregime fachlich nachprüfen.",
            "Vor Projektentscheid: lokale Vorschriften, Erschliessung und Bodengutachten verbindlich prüfen.",
        ],
    }
