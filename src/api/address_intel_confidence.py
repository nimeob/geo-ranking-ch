from __future__ import annotations

from typing import Any, Callable, Protocol, Sequence


class CandidateLike(Protocol):
    feature_id: str
    pre_score: float
    total_score: float | None
    pre_reasons: list[str]
    detail_reasons: list[str]
    gwr_attrs: dict[str, Any]
    address_attrs: dict[str, Any]


class SourceRegistryLike(Protocol):
    def required_success_ratio(self, required_names: Sequence[str]) -> float:
        ...


def assess_ambiguity(
    selected: CandidateLike,
    candidates: Sequence[CandidateLike],
) -> dict[str, Any]:
    warnings: list[str] = []
    level = "none"
    score_gap = None

    if len(candidates) > 1:
        others = [c for c in candidates if c.feature_id != selected.feature_id]
        if others:
            best_other = max(others, key=lambda c: c.total_score if c.total_score else c.pre_score)
            best_other_score = best_other.total_score if best_other.total_score else best_other.pre_score
            score_gap = round((selected.total_score or selected.pre_score) - best_other_score, 2)
            if score_gap < 5:
                level = "high"
                warnings.append("Sehr geringe Distanz zum nächstbesten Kandidaten")
            elif score_gap < 12:
                level = "medium"
                warnings.append("Mehrere Kandidaten mit ähnlichem Score")

    mismatch_hits = 0
    for reason in selected.pre_reasons + selected.detail_reasons:
        lowered = reason.lower()
        if "weicht ab" in lowered or "nicht" in lowered or "fehlt" in lowered:
            mismatch_hits += 1

    if mismatch_hits >= 3:
        if level == "none":
            level = "medium"
        warnings.append("Mehrere Matching-Indizien sind inkonsistent")

    return {
        "level": level,
        "score_gap_to_next": score_gap,
        "warnings": warnings,
    }


def compute_confidence(
    *,
    selected: CandidateLike,
    candidates: Sequence[CandidateLike],
    sources: SourceRegistryLike,
    heating_layer: dict[str, Any],
    plz_layer: dict[str, Any],
    admin_boundary: dict[str, Any],
    osm: dict[str, Any],
    normalize_text_fn: Callable[[str | None], str],
    clamp_fn: Callable[[float, float, float], float],
    required_sources: Sequence[str],
) -> dict[str, Any]:
    gwr = selected.gwr_attrs
    addr = selected.address_attrs

    notes: list[str] = []
    explanations: list[dict[str, Any]] = []

    # 1) Match-Qualität (0-40)
    match_component = clamp_fn(selected.total_score or selected.pre_score, 0, 120) / 120 * 40
    notes.append(f"Match-Komponente: {match_component:.1f}/40")
    explanations.append(
        {
            "factor": "match_quality",
            "impact": round(match_component, 1),
            "text": "Adress-Matching aus Such- und Detailscore",
        }
    )

    # 2) Datenvollständigkeit (0-30)
    completeness = 0.0
    if selected.feature_id:
        completeness += 4
    if gwr.get("egid"):
        completeness += 9
    if gwr.get("egrid"):
        completeness += 5
    if gwr.get("esid") or gwr.get("edid") or addr.get("adr_egaid"):
        completeness += 4
    if gwr.get("gstat"):
        completeness += 3
    if gwr.get("gbauj"):
        completeness += 2
    if gwr.get("garea"):
        completeness += 1.5
    if gwr.get("gastw"):
        completeness += 1.5
    if gwr.get("ganzwhg") is not None:
        completeness += 1.0
    completeness = clamp_fn(completeness, 0, 30)
    notes.append(f"Vollständigkeit: {completeness:.1f}/30")
    explanations.append(
        {
            "factor": "data_completeness",
            "impact": round(completeness, 1),
            "text": "Verfügbarkeit von IDs, Status und Basis-Gebäudeattributen",
        }
    )

    # 3) Quellen-/Konsistenzscore (0-20)
    consistency = 0.0
    gwr_plz = str(gwr.get("plz_plz6") or "")[:4]
    gwr_city = normalize_text_fn(gwr.get("dplzname") or gwr.get("ggdename") or "")

    plz_layer_plz = str(plz_layer.get("plz") or "")[:4]
    plz_layer_city = normalize_text_fn(plz_layer.get("langtext") or "")

    if gwr_plz and plz_layer_plz:
        if gwr_plz == plz_layer_plz:
            consistency += 6
            notes.append("PLZ-Konsistenz: GWR ↔ PLZ-Layer passt")
        else:
            consistency -= 3
            notes.append("PLZ-Konsistenz: Abweichung GWR ↔ PLZ-Layer")

    if gwr_city and plz_layer_city:
        if gwr_city in plz_layer_city or plz_layer_city in gwr_city:
            consistency += 4
            notes.append("Ortskonsistenz: GWR ↔ PLZ-Layer passt")
        else:
            consistency -= 2
            notes.append("Ortskonsistenz: Abweichung GWR ↔ PLZ-Layer")

    boundary_city = normalize_text_fn(admin_boundary.get("gemname") or "")
    boundary_kanton = normalize_text_fn(admin_boundary.get("kanton") or "")
    gwr_kanton = normalize_text_fn(gwr.get("gdekt") or "")
    if boundary_city and gwr_city:
        if boundary_city in gwr_city or gwr_city in boundary_city:
            consistency += 3
            notes.append("Ortskonsistenz: GWR ↔ SwissBoundaries passt")
        else:
            consistency -= 2
            notes.append("Ortskonsistenz: Abweichung GWR ↔ SwissBoundaries")
    if boundary_kanton and gwr_kanton:
        if boundary_kanton == gwr_kanton:
            consistency += 2
            notes.append("Kantonskonsistenz: GWR ↔ SwissBoundaries passt")
        else:
            consistency -= 2
            notes.append("Kantonskonsistenz: Abweichung GWR ↔ SwissBoundaries")

    osm_addr = (osm.get("address") or {}) if isinstance(osm, dict) else {}
    osm_postcode = str(osm_addr.get("postcode") or "")[:4]
    osm_city = normalize_text_fn(osm_addr.get("city") or osm_addr.get("town") or osm_addr.get("village") or "")

    if gwr_plz and osm_postcode:
        if gwr_plz == osm_postcode:
            consistency += 2.5
            notes.append("PLZ-Konsistenz: GWR ↔ OSM passt")
        else:
            consistency -= 1.5
            notes.append("PLZ-Konsistenz: GWR ↔ OSM abweichend")

    if gwr_city and osm_city:
        if gwr_city in osm_city or osm_city in gwr_city:
            consistency += 1.5
            notes.append("Ortskonsistenz: GWR ↔ OSM passt")
        else:
            consistency -= 1
            notes.append("Ortskonsistenz: GWR ↔ OSM abweichend")

    if heating_layer.get("genh1_de"):
        consistency += 1.5
        notes.append("Energie-Layer liefert Klartextwerte")

    consistency = clamp_fn(consistency, 0, 20)
    explanations.append(
        {
            "factor": "cross_source_consistency",
            "impact": round(consistency, 1),
            "text": "Übereinstimmung zwischen GWR, PLZ-Layer, SwissBoundaries und optional OSM",
        }
    )

    # 4) Verfügbarkeit Pflichtquellen (0-10)
    source_ratio = sources.required_success_ratio(required_sources)
    source_component = source_ratio * 10
    explanations.append(
        {
            "factor": "required_source_health",
            "impact": round(source_component, 1),
            "text": "Verfügbarkeit der Pflichtquellen (Search, GWR, Adressregister)",
        }
    )

    mismatch_penalty = 0.0
    if any("Strasse nicht ausreichend enthalten" in r for r in selected.pre_reasons):
        mismatch_penalty += 8.0
    if any("GWR-Strasse weicht ab" in r for r in selected.detail_reasons):
        mismatch_penalty += 14.0
    if any("Hausnummer abweichend" in r for r in selected.detail_reasons):
        mismatch_penalty += 4.0

    ambiguity = assess_ambiguity(
        selected,
        candidates,
    )
    ambiguity_penalty = 0.0
    if ambiguity["level"] == "high":
        ambiguity_penalty = 10.0
    elif ambiguity["level"] == "medium":
        ambiguity_penalty = 4.0

    if mismatch_penalty:
        notes.append(f"Mismatch-Penalty: -{mismatch_penalty:.1f} (Adressabweichung)")
    if ambiguity_penalty:
        notes.append(f"Ambiguitäts-Penalty: -{ambiguity_penalty:.1f}")

    score_raw = (
        match_component
        + completeness
        + consistency
        + source_component
        - mismatch_penalty
        - ambiguity_penalty
    )
    score = int(round(clamp_fn(score_raw, 0, 100)))
    level = "high" if score >= 82 else ("medium" if score >= 62 else "low")

    warnings = list(ambiguity.get("warnings") or [])
    if score < 60:
        warnings.append("Niedrige Gesamt-Confidence: manuelle Prüfung empfohlen")

    return {
        "score": score,
        "max": 100,
        "level": level,
        "components": {
            "match_quality": round(match_component, 1),
            "data_completeness": round(completeness, 1),
            "cross_source_consistency": round(consistency, 1),
            "required_source_health": round(source_component, 1),
            "mismatch_penalty": round(mismatch_penalty, 1),
            "ambiguity_penalty": round(ambiguity_penalty, 1),
        },
        "notes": notes,
        "explanations": explanations,
        "ambiguity": ambiguity,
        "warnings": warnings,
    }
