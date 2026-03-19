from __future__ import annotations

from typing import Any


def source_catalog_view(
    source_status: dict[str, dict[str, Any]],
    *,
    source_catalog: dict[str, dict[str, Any]],
    source_policy_rank: dict[str, int],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name, meta in source_catalog.items():
        state = source_status.get(name, {})
        authority = str(meta.get("authority") or "unknown")
        out[name] = {
            "tier": meta.get("tier"),
            "authority": authority,
            "policy_rank": source_policy_rank.get(authority, source_policy_rank["unknown"]),
            "purpose": meta.get("purpose"),
            "status": state.get("status", "not_used"),
            "optional": state.get("optional", meta.get("tier") != "core"),
        }
    return out


def get_nested(data: dict[str, Any], dotted_path: str) -> Any:
    cur: Any = data
    for part in dotted_path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def build_field_provenance(
    report: dict[str, Any],
    *,
    source_catalog: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    mapping = {
        "ids.egid": ["geoadmin_gwr"],
        "ids.egrid": ["geoadmin_gwr"],
        "administrative.gemeinde": ["geoadmin_gwr", "swissboundaries_identify"],
        "administrative.kanton": ["geoadmin_gwr", "swissboundaries_identify"],
        "cross_source.plz_layer.plz": ["plz_layer_identify"],
        "cross_source.admin_boundary.gemeinde": ["swissboundaries_identify"],
        "cross_source.elevation.height_m": ["swisstopo_height"],
        "building.codes": ["geoadmin_gwr"],
        "building.decoded": ["geoadmin_gwr", "gwr_codes"],
        "energy.raw_codes": ["geoadmin_gwr"],
        "energy.heating_layer": ["bfs_heating_layer"],
        "cross_source.osm_reverse": ["osm_reverse"],
        "intelligence.tenants_businesses.entities": ["osm_poi_overpass"],
        "intelligence.incidents_timeline.events": ["google_news_rss"],
        "intelligence.environment_noise_risk.score": ["osm_poi_overpass"],
        "intelligence.consistency_checks": ["geoadmin_gwr", "geoadmin_address", "google_news_rss"],
        "intelligence.executive_risk_summary": ["geoadmin_gwr", "osm_poi_overpass", "google_news_rss"],
        "suitability_light.score": ["swisstopo_height", "plz_layer_identify", "swissboundaries_identify", "geoadmin_gwr", "osm_reverse"],
        "suitability_light.traffic_light": ["swisstopo_height", "plz_layer_identify", "swissboundaries_identify", "geoadmin_gwr", "osm_reverse"],
    }
    out: dict[str, dict[str, Any]] = {}
    for field_path, source_names in mapping.items():
        value = get_nested(report, field_path)
        out[field_path] = {
            "sources": source_names,
            "primary_source": source_names[0],
            "present": value is not None and value != "" and value != [],
            "authority": source_catalog.get(source_names[0], {}).get("authority"),
        }
    return out


def build_executive_summary(report: dict[str, Any]) -> dict[str, Any]:
    conf = report.get("confidence") or {}
    ambiguity = conf.get("ambiguity") or {}
    warnings = list(conf.get("warnings") or [])
    needs_review = conf.get("level") == "low" or ambiguity.get("level") in {"medium", "high"}
    verdict = "review" if needs_review else "ok"

    return {
        "verdict": verdict,
        "needs_review": needs_review,
        "headline": (
            "Treffer wirkt stabil" if not needs_review else "Treffer prüfen (Ambiguität oder geringe Confidence)"
        ),
        "ambiguity_level": ambiguity.get("level", "none"),
        "ambiguity_gap": ambiguity.get("score_gap_to_next"),
        "warnings": warnings,
    }
