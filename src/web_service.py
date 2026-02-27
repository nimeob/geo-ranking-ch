#!/usr/bin/env python3
"""Minimaler HTTP-Webservice für ECS (stdlib only).

Endpoints:
- GET /health
- GET /version
- GET /api/v1/dictionaries
- GET /api/v1/dictionaries/<domain>
- POST /analyze {"query": "...", "intelligence_mode": "basic|extended|risk"}
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from src.address_intel import AddressIntelError, build_report
from src.gwr_codes import DWST, GENH, GKAT, GKLAS, GSTAT, GWAERZH, GWAERZW
from src.personalized_scoring import compute_two_stage_scores

SUPPORTED_INTELLIGENCE_MODES = {"basic", "extended", "risk"}
_BEARER_AUTH_RE = re.compile(r"^\s*Bearer\s+([^\s]+)\s*$", re.IGNORECASE)
_TOP_LEVEL_STATUS_KEYS = {
    "confidence",
    "sources",
    "source_classification",
    "source_attribution",
    "executive_summary",
    "personalization_status",
}
_ENTITY_KEYS = ("query", "matched_address", "ids", "coordinates", "administrative")
_SOURCE_GROUP_MODULE_MAP = {
    "match": ("match",),
    "building_energy": ("building", "energy"),
    "postal_consistency": ("cross_source",),
    "elevation_context": ("cross_source",),
    "intelligence": ("intelligence",),
}
_RESPONSE_MODES = {"compact", "verbose"}

_PREFERENCE_ENUMS = {
    "lifestyle_density": {"rural", "suburban", "urban"},
    "noise_tolerance": {"low", "medium", "high"},
    "nightlife_preference": {"avoid", "neutral", "prefer"},
    "school_proximity": {"avoid", "neutral", "prefer"},
    "family_friendly_focus": {"low", "medium", "high"},
    "commute_priority": {"car", "pt", "bike", "mixed"},
}
_DEFAULT_PREFERENCES = {
    "lifestyle_density": "suburban",
    "noise_tolerance": "medium",
    "nightlife_preference": "neutral",
    "school_proximity": "neutral",
    "family_friendly_focus": "medium",
    "commute_priority": "mixed",
    "weights": {},
}

_DICTIONARY_CACHE_CONTROL = "public, max-age=86400, stale-while-revalidate=3600"
_DICTIONARY_GLOBAL_VERSION = os.getenv("DICTIONARY_VERSION", "2026-02-27")
_DICTIONARY_DOMAIN_VERSIONS = {
    "building": "gwr-building-v1",
    "heating": "gwr-heating-v1",
}
_DICTIONARY_DOMAIN_TABLES: dict[str, dict[str, dict[int, str]]] = {
    "building": {
        "gklas": GKLAS,
        "gkat": GKAT,
        "gstat": GSTAT,
        "dwst": DWST,
    },
    "heating": {
        "gwaerzh": GWAERZH,
        "gwaerzw": GWAERZW,
        "genh": GENH,
    },
}


def _normalize_dictionary_table(table: dict[int, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key in sorted(table):
        normalized[str(int(key))] = str(table[key])
    return normalized


def _stable_etag(payload: dict[str, Any], *, prefix: str) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()[:16]
    return f'"{prefix}-{digest}"'


def _normalize_etag_for_compare(tag: Any) -> str:
    value = str(tag).strip()
    if value.lower().startswith("w/"):
        value = value[2:].strip()
    return value


def _if_none_match_matches(header_value: Any, current_etag: str) -> bool:
    if not header_value:
        return False

    normalized_current = _normalize_etag_for_compare(current_etag)
    for raw_part in str(header_value).split(","):
        candidate = raw_part.strip()
        if not candidate:
            continue
        if candidate == "*":
            return True
        if _normalize_etag_for_compare(candidate) == normalized_current:
            return True
    return False


def _build_dictionary_payloads() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    domains: dict[str, dict[str, Any]] = {}
    domain_payloads: dict[str, dict[str, Any]] = {}

    for domain_name in sorted(_DICTIONARY_DOMAIN_TABLES):
        domain_version = _DICTIONARY_DOMAIN_VERSIONS[domain_name]
        tables = {
            table_name: _normalize_dictionary_table(table)
            for table_name, table in _DICTIONARY_DOMAIN_TABLES[domain_name].items()
        }
        domain_payload: dict[str, Any] = {
            "domain": domain_name,
            "version": domain_version,
            "tables": tables,
        }
        domain_payload["etag"] = _stable_etag(
            {
                "domain": domain_name,
                "version": domain_version,
                "tables": tables,
            },
            prefix=f"dict-{domain_name}",
        )
        domain_payloads[domain_name] = domain_payload

        domains[domain_name] = {
            "version": domain_version,
            "etag": domain_payload["etag"],
            "path": f"/api/v1/dictionaries/{domain_name}",
        }

    index_payload = {
        "version": _DICTIONARY_GLOBAL_VERSION,
        "domains": domains,
    }
    index_payload["etag"] = _stable_etag(
        {
            "version": _DICTIONARY_GLOBAL_VERSION,
            "domains": domains,
        },
        prefix="dict-index",
    )

    return index_payload, domain_payloads


_DICTIONARY_INDEX_PAYLOAD, _DICTIONARY_DOMAIN_PAYLOADS = _build_dictionary_payloads()


def _dictionary_status_payload() -> dict[str, Any]:
    """Liefert den additiven Dictionary-Envelope für Analyze-Responses."""
    return {
        "version": _DICTIONARY_INDEX_PAYLOAD.get("version"),
        "etag": _DICTIONARY_INDEX_PAYLOAD.get("etag"),
        "domains": deepcopy(_DICTIONARY_INDEX_PAYLOAD.get("domains") or {}),
    }


def _is_status_like_key(key: str) -> bool:
    normalized = key.strip().lower()
    if normalized in {"status", "source_health", "source_meta"}:
        return True
    if normalized.startswith("status_") or normalized.endswith("_status"):
        return True
    return False


def _strip_status_fields(payload: Any) -> Any:
    """Entfernt status-artige Schlüssel rekursiv aus Daten-Payloads."""
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            if _is_status_like_key(str(key)):
                continue
            out[key] = _strip_status_fields(value)
        return out
    if isinstance(payload, list):
        return [_strip_status_fields(item) for item in payload]
    return payload


def _build_status_block(report: dict[str, Any]) -> dict[str, Any]:
    quality: dict[str, Any] = {}
    confidence = report.get("confidence")
    executive_summary = report.get("executive_summary")
    if confidence is not None:
        quality["confidence"] = deepcopy(confidence)
    if executive_summary is not None:
        quality["executive_summary"] = deepcopy(executive_summary)

    source_health = deepcopy(report.get("sources") or {})

    source_meta: dict[str, Any] = {}
    source_classification = report.get("source_classification")
    source_attribution = report.get("source_attribution")
    field_provenance = report.get("field_provenance")
    if source_classification:
        source_meta["source_classification"] = deepcopy(source_classification)
    if source_attribution:
        source_meta["source_attribution"] = deepcopy(source_attribution)
    if field_provenance:
        source_meta["field_provenance"] = deepcopy(field_provenance)

    status_block = {
        "quality": quality,
        "source_health": source_health,
        "source_meta": source_meta,
        "dictionary": _dictionary_status_payload(),
    }

    personalization_status = report.get("personalization_status")
    if isinstance(personalization_status, dict):
        status_block["personalization"] = deepcopy(personalization_status)

    return status_block


def _module_ref(module_key: str) -> str:
    return f"#/result/data/modules/{module_key}"


def _compact_projection_for_group(
    group_name: str,
    module_keys: list[str],
    modules: dict[str, Any],
) -> dict[str, Any]:
    refs = [_module_ref(key) for key in module_keys]
    if not refs:
        return {}

    projection: dict[str, Any] = {}
    if len(refs) == 1:
        projection["module_ref"] = refs[0]
    else:
        projection["module_refs"] = refs

    # Kleiner Kompatibilitäts-/Convenience-Slice für Integratoren:
    # by_source bleibt nutzbar, ohne komplette Module erneut zu serialisieren.
    if len(module_keys) == 1:
        module_key = module_keys[0]
        module_payload = modules.get(module_key)

        if group_name == "match" and isinstance(module_payload, dict):
            selected_score = module_payload.get("selected_score")
            candidate_count = module_payload.get("candidate_count")
            if selected_score is not None:
                projection["selected_score"] = deepcopy(selected_score)
            if candidate_count is not None:
                projection["candidate_count"] = deepcopy(candidate_count)

        if group_name == "intelligence" and isinstance(module_payload, dict):
            tenants_businesses = module_payload.get("tenants_businesses")
            if isinstance(tenants_businesses, dict):
                entities = tenants_businesses.get("entities")
                if isinstance(entities, list):
                    compact_entities = [
                        {"name": entry.get("name")}
                        for entry in entities
                        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
                    ]
                    if compact_entities:
                        projection["tenants_businesses"] = {"entities": compact_entities}

    return projection


def _build_by_source_payload(
    modules: dict[str, Any],
    *,
    source_attribution: dict[str, Any],
    source_health: dict[str, Any],
    response_mode: str,
) -> dict[str, dict[str, Any]]:
    by_source: dict[str, dict[str, Any]] = {}

    def ensure_source(name: str) -> dict[str, Any]:
        return by_source.setdefault(name, {"source": name, "data": {}})

    for group_name, group_sources in source_attribution.items():
        module_keys = [key for key in _SOURCE_GROUP_MODULE_MAP.get(group_name, (group_name,)) if key in modules]
        if not module_keys:
            continue

        if response_mode == "verbose":
            grouped_data = {key: deepcopy(modules[key]) for key in module_keys}
            if len(grouped_data) == 1:
                group_value: Any = next(iter(grouped_data.values()))
            else:
                group_value = grouped_data
        else:
            group_value = _compact_projection_for_group(group_name, module_keys, modules)
            if not group_value:
                continue

        if not isinstance(group_sources, list):
            continue
        for source_name in group_sources:
            if not isinstance(source_name, str) or not source_name.strip():
                continue
            entry = ensure_source(source_name)
            entry["data"][group_name] = deepcopy(group_value)

    for source_name in source_health.keys():
        if isinstance(source_name, str) and source_name.strip():
            ensure_source(source_name)

    return by_source


def _normalize_code_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            return None
        if float(value).is_integer():
            return str(int(value))
        return str(value)

    as_text = str(value).strip()
    return as_text or None


def _normalize_code_mapping(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in payload.items():
        normalized_value = _normalize_code_scalar(value)
        if normalized_value is None:
            continue
        normalized[str(key)] = normalized_value
    return normalized


def _to_code_first_modules(modules: dict[str, Any]) -> dict[str, Any]:
    projected = deepcopy(modules)

    building = projected.get("building")
    if isinstance(building, dict):
        building.pop("decoded", None)
        normalized_building_codes = _normalize_code_mapping(building.get("codes"))
        if normalized_building_codes:
            building["codes"] = normalized_building_codes
        else:
            building.pop("codes", None)

    energy = projected.get("energy")
    if isinstance(energy, dict):
        raw_codes = energy.pop("raw_codes", None)
        existing_codes = _normalize_code_mapping(energy.get("codes"))
        raw_codes_normalized = _normalize_code_mapping(raw_codes)
        merged_codes = {**existing_codes, **raw_codes_normalized}
        if merged_codes:
            energy["codes"] = merged_codes
        else:
            energy.pop("codes", None)
        energy.pop("decoded_summary", None)

    return projected


def _grouped_api_result(
    report: dict[str, Any],
    *,
    response_mode: str = "compact",
    include_legacy_labels: bool = False,
) -> dict[str, Any]:
    normalized_response_mode = response_mode if response_mode in _RESPONSE_MODES else "compact"

    status = _build_status_block(report)

    cleaned = _strip_status_fields(deepcopy(report))
    if not isinstance(cleaned, dict):
        cleaned = {}
    for key in _TOP_LEVEL_STATUS_KEYS:
        cleaned.pop(key, None)

    entity: dict[str, Any] = {}
    for key in _ENTITY_KEYS:
        if key in cleaned:
            entity[key] = cleaned.pop(key)

    modules = cleaned if include_legacy_labels else _to_code_first_modules(cleaned)

    source_meta = status.get("source_meta")
    source_attribution = source_meta.get("source_attribution") if isinstance(source_meta, dict) else {}
    if not isinstance(source_attribution, dict):
        source_attribution = {}

    source_health = status.get("source_health")
    if not isinstance(source_health, dict):
        source_health = {}

    return {
        "status": status,
        "data": {
            "entity": entity,
            "modules": modules,
            "by_source": _build_by_source_payload(
                modules,
                source_attribution=source_attribution,
                source_health=source_health,
                response_mode=normalized_response_mode,
            ),
        },
    }


def _as_positive_finite_number(value: Any, field_name: str) -> float:
    """Validiert numerische Inputs robust für API/ENV-Werte."""
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number > 0") from exc

    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{field_name} must be a finite number > 0")
    return parsed


def _extract_bearer_token(auth_header: Any) -> str:
    """Extrahiert Bearer-Token robust aus Authorization-Headern.

    - akzeptiert `Bearer` case-insensitive
    - toleriert führende/trailing Whitespaces und mehrere Leerzeichen nach dem Scheme
    - erlaubt nur genau ein nicht-leeres Token-Segment
    """
    match = _BEARER_AUTH_RE.match(str(auth_header))
    if not match:
        return ""
    return match.group(1)


def _sanitize_request_id_candidate(candidate: Any) -> str:
    """Normalisiert Request-ID-Header robust für Echo/Response-Header."""
    value = str(candidate).strip()
    if not value:
        return ""
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return ""
    if any(ch.isspace() for ch in value):
        return ""
    if any(ch in ",;" for ch in value):
        return ""
    if len(value) > 128:
        return ""
    if not value.isascii():
        return ""
    return value


def _extract_request_options(data: dict[str, Any]) -> dict[str, Any]:
    """Liest den optionalen options-Envelope robust und rückwärtskompatibel.

    Policy:
    - fehlt `options`, bleibt das Laufzeitverhalten unverändert
    - `options` muss ein JSON-Objekt sein (sonst 400 bad_request)
    - unbekannte optionale Keys sind additive No-Op-Felder (Forward-Compatibility)
    """
    raw_options = data.get("options")
    if raw_options is None:
        return {}
    if not isinstance(raw_options, dict):
        raise ValueError("options must be an object when provided")
    return raw_options


def _extract_response_mode(options: dict[str, Any]) -> str:
    """Liest den optionalen Response-Modus (compact|verbose)."""
    raw_mode = options.get("response_mode", "compact")
    if not isinstance(raw_mode, str):
        raise ValueError("options.response_mode must be a string when provided")

    mode = raw_mode.strip().lower() or "compact"
    if mode not in _RESPONSE_MODES:
        raise ValueError("options.response_mode must be one of ['compact', 'verbose']")
    return mode


def _extract_include_legacy_labels(options: dict[str, Any]) -> bool:
    """Liest den optionalen Legacy-Label-Modus für Migrationspfade.

    Default ist code-first (`False`). Wird das Flag explizit gesetzt,
    muss es ein boolescher Wert sein.
    """
    raw_value = options.get("include_labels", False)
    if isinstance(raw_value, bool):
        return raw_value
    raise ValueError("options.include_labels must be a boolean when provided")


def _as_unit_interval_number(value: Any, field_name: str) -> float:
    """Validiert und normalisiert Präferenzgewichte robust auf den Bereich 0..1."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number between 0 and 1")

    as_float = float(value)
    if not math.isfinite(as_float):
        raise ValueError(f"{field_name} must be a finite number between 0 and 1")
    if not (0 <= as_float <= 1):
        raise ValueError(f"{field_name} must be between 0 and 1")
    return as_float


def _extract_preferences(data: dict[str, Any]) -> dict[str, Any]:
    """Validiert optionale Präferenzprofile für personalisierte Auswertung.

    Policy:
    - fehlt `preferences`, werden explizite Defaults verwendet
    - `preferences` muss ein JSON-Objekt sein (sonst 400 bad_request)
    - nur bekannte Preference-Dimensionen sind erlaubt
    - `weights` ist optional und auf bekannte Keys mit Werten im Bereich 0..1 begrenzt
    """
    raw_preferences = data.get("preferences")
    effective = deepcopy(_DEFAULT_PREFERENCES)

    if raw_preferences is None:
        return effective
    if not isinstance(raw_preferences, dict):
        raise ValueError("preferences must be an object when provided")

    allowed_keys = set(_PREFERENCE_ENUMS) | {"weights"}
    unknown_keys = set(raw_preferences) - allowed_keys
    if unknown_keys:
        raise ValueError(f"preferences contains unknown keys: {sorted(unknown_keys)}")

    for field_name, allowed_values in _PREFERENCE_ENUMS.items():
        if field_name not in raw_preferences:
            continue
        normalized = str(raw_preferences.get(field_name, "")).strip().lower()
        if normalized not in allowed_values:
            raise ValueError(
                f"preferences.{field_name} must be one of {sorted(allowed_values)}"
            )
        effective[field_name] = normalized

    raw_weights = raw_preferences.get("weights")
    if raw_weights is None:
        return effective
    if not isinstance(raw_weights, dict):
        raise ValueError("preferences.weights must be an object")

    unknown_weights = set(raw_weights) - set(_PREFERENCE_ENUMS)
    if unknown_weights:
        raise ValueError(
            "preferences.weights contains unknown keys: "
            f"{sorted(unknown_weights)}"
        )

    normalized_weights: dict[str, float] = {}
    for key, value in raw_weights.items():
        normalized_weights[key] = _as_unit_interval_number(
            value,
            f"preferences.weights.{key}",
        )

    effective["weights"] = normalized_weights
    return effective


def _derive_personalization_status(
    *,
    preferences_supplied: bool,
    fallback_applied: bool,
    signal_strength: float,
) -> dict[str, Any]:
    if not preferences_supplied:
        state = "deactivated"
        source = "base_score_default"
    elif fallback_applied or signal_strength <= 0:
        state = "partial"
        source = "base_score_fallback"
    else:
        state = "active"
        source = "personalized_reweighting"

    return {
        "state": state,
        "source": source,
        "fallback_applied": fallback_applied,
        "signal_strength": round(signal_strength, 4),
    }


def _apply_personalized_suitability_scores(
    report: dict[str, Any],
    preferences: dict[str, Any] | None,
    *,
    preferences_supplied: bool = False,
) -> None:
    """Integriert zweistufiges Scoring deterministisch in den Analyze-Report."""
    suitability = report.get("suitability_light")
    if not isinstance(suitability, dict):
        return

    raw_factors = suitability.get("factors")
    if not isinstance(raw_factors, list) or not raw_factors:
        return

    factors: list[dict[str, Any]] = []
    for row in raw_factors:
        if not isinstance(row, dict):
            continue
        key = row.get("key")
        if not isinstance(key, str) or not key.strip():
            continue
        factors.append(
            {
                "key": key,
                "score": row.get("score"),
                "weight": row.get("weight"),
            }
        )

    if not factors:
        return

    two_stage = compute_two_stage_scores(factors, preferences=preferences)
    fallback_applied = bool(two_stage.get("fallback_applied"))
    signal_strength = float(two_stage.get("signal_strength", 0.0))

    base_score = suitability.get("base_score")
    if not isinstance(base_score, (int, float)) or not math.isfinite(float(base_score)):
        base_score = float(two_stage.get("base_score", 0.0))
        suitability["base_score"] = round(base_score, 4)
    else:
        base_score = float(base_score)

    personalized_score = float(two_stage.get("personalized_score", base_score))
    if fallback_applied:
        personalized_score = base_score

    personalization_status = _derive_personalization_status(
        preferences_supplied=preferences_supplied,
        fallback_applied=fallback_applied,
        signal_strength=signal_strength,
    )

    suitability["personalized_score"] = round(personalized_score, 4)
    suitability["personalization"] = {
        **personalization_status,
        "weights": deepcopy(two_stage.get("weights") or {}),
    }
    report["personalization_status"] = deepcopy(personalization_status)

    summary_compact = report.get("summary_compact")
    if not isinstance(summary_compact, dict):
        return

    compact_suitability = summary_compact.get("suitability_light")
    if not isinstance(compact_suitability, dict):
        return

    compact_suitability["base_score"] = round(base_score, 4)
    compact_suitability["personalized_score"] = round(personalized_score, 4)
    compact_suitability["personalization"] = deepcopy(suitability["personalization"])


class Handler(BaseHTTPRequestHandler):
    server_version = "geo-ranking-ch/0.1"

    def _normalized_path(self) -> str:
        """Normalisiert den Request-Pfad für robustes Routing.

        - ignoriert Query/Fragment-Komponenten
        - behandelt optionale trailing Slashes auf bekannten Endpunkten tolerant
        - kollabiert doppelte Slash-Segmente (`//`) auf einen Slash
        """
        path = urlsplit(self.path).path or "/"
        path = re.sub(r"/{2,}", "/", path)
        if path != "/":
            path = path.rstrip("/") or "/"
        return path

    def _request_id(self) -> str:
        """Liefert eine korrelierbare Request-ID (Header oder Fallback)."""
        header_candidates = (
            self.headers.get("X-Request-Id", ""),
            self.headers.get("X_Request_Id", ""),
            self.headers.get("Request-Id", ""),
            self.headers.get("Request_Id", ""),
            self.headers.get("X-Correlation-Id", ""),
            self.headers.get("X_Correlation_Id", ""),
            self.headers.get("Correlation-Id", ""),
            self.headers.get("Correlation_Id", ""),
        )
        for candidate in header_candidates:
            request_id = _sanitize_request_id_candidate(candidate)
            if request_id:
                return request_id
        return f"req-{uuid.uuid4().hex[:16]}"

    def _send_json(
        self,
        payload: dict[str, Any],
        status: int = 200,
        *,
        request_id: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if request_id:
            self.send_header("X-Request-Id", request_id)
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_not_modified(
        self,
        *,
        request_id: str,
        etag: str,
        cache_control: str = _DICTIONARY_CACHE_CONTROL,
    ) -> None:
        self.send_response(HTTPStatus.NOT_MODIFIED)
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", cache_control)
        if request_id:
            self.send_header("X-Request-Id", request_id)
        self.end_headers()

    def _send_dictionary_payload(
        self,
        payload: dict[str, Any],
        *,
        request_id: str,
    ) -> None:
        etag = str(payload.get("etag", "")).strip()
        if etag and _if_none_match_matches(self.headers.get("If-None-Match"), etag):
            self._send_not_modified(request_id=request_id, etag=etag)
            return

        extra_headers: dict[str, str] = {"Cache-Control": _DICTIONARY_CACHE_CONTROL}
        if etag:
            extra_headers["ETag"] = etag

        self._send_json(
            payload,
            request_id=request_id,
            extra_headers=extra_headers,
        )

    def do_GET(self) -> None:  # noqa: N802
        request_id = self._request_id()
        request_path = self._normalized_path()

        if request_path == "/health":
            self._send_json(
                {
                    "ok": True,
                    "service": "geo-ranking-ch",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                },
                request_id=request_id,
            )
            return
        if request_path == "/version":
            self._send_json(
                {
                    "service": "geo-ranking-ch",
                    "version": os.getenv("APP_VERSION", "dev"),
                    "commit": os.getenv("GIT_SHA", "unknown"),
                    "request_id": request_id,
                },
                request_id=request_id,
            )
            return
        if request_path == "/api/v1/dictionaries":
            self._send_dictionary_payload(
                deepcopy(_DICTIONARY_INDEX_PAYLOAD),
                request_id=request_id,
            )
            return
        if request_path.startswith("/api/v1/dictionaries/"):
            domain_name = request_path.rsplit("/", 1)[-1].strip().lower()
            domain_payload = _DICTIONARY_DOMAIN_PAYLOADS.get(domain_name)
            if domain_payload is None:
                self._send_json(
                    {
                        "ok": False,
                        "error": "not_found",
                        "message": f"unknown dictionary domain: {domain_name}",
                        "request_id": request_id,
                    },
                    status=HTTPStatus.NOT_FOUND,
                    request_id=request_id,
                )
                return
            self._send_dictionary_payload(
                deepcopy(domain_payload),
                request_id=request_id,
            )
            return
        self._send_json(
            {"ok": False, "error": "not_found", "request_id": request_id},
            status=HTTPStatus.NOT_FOUND,
            request_id=request_id,
        )

    def do_POST(self) -> None:  # noqa: N802
        request_id = self._request_id()
        request_path = self._normalized_path()

        if request_path != "/analyze":
            self._send_json(
                {"ok": False, "error": "not_found", "request_id": request_id},
                status=HTTPStatus.NOT_FOUND,
                request_id=request_id,
            )
            return

        required_token = os.getenv("API_AUTH_TOKEN", "").strip()
        if required_token:
            provided_token = _extract_bearer_token(self.headers.get("Authorization", ""))
            if provided_token != required_token:
                self._send_json(
                    {"ok": False, "error": "unauthorized", "request_id": request_id},
                    status=HTTPStatus.UNAUTHORIZED,
                    request_id=request_id,
                )
                return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("empty body")
            raw = self.rfile.read(length)
            try:
                decoded_body = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("body must be valid utf-8 json") from exc

            data = json.loads(decoded_body)
            if not isinstance(data, dict):
                raise ValueError("json body must be an object")

            query = str(data.get("query", "")).strip()
            if not query:
                raise ValueError("query is required")

            mode = str(data.get("intelligence_mode", "basic")).strip() or "basic"
            mode = mode.lower()
            if mode not in SUPPORTED_INTELLIGENCE_MODES:
                raise ValueError(
                    f"intelligence_mode must be one of {sorted(SUPPORTED_INTELLIGENCE_MODES)}"
                )

            # Forward-Compatibility: optionaler, additiver Namespace für spätere
            # Request-Erweiterungen (z. B. Deep-Mode) ohne Breaking Changes.
            request_options = _extract_request_options(data)
            response_mode = _extract_response_mode(request_options)
            include_legacy_labels = _extract_include_legacy_labels(request_options)

            # Optionales Preference-Profil für BL-20.4-Personalisierung.
            # Bei fehlendem Profil greifen explizite Defaults (Fallback-kompatibel).
            preferences_supplied = "preferences" in data and data.get("preferences") is not None
            preferences_profile = _extract_preferences(data)

            if os.getenv("ENABLE_E2E_FAULT_INJECTION", "0") == "1":
                if query == "__timeout__":
                    raise TimeoutError("forced timeout for e2e")
                if query == "__internal__":
                    raise RuntimeError("forced internal error for e2e")
                if query == "__address_intel__":
                    raise AddressIntelError("forced address intel error for e2e")
                if query == "__ok__":
                    stub_report = {
                        "query": query,
                        "matched_address": query,
                        "ids": {},
                        "coordinates": {},
                        "administrative": {},
                        "match": {"mode": "e2e_stub"},
                        "building": {
                            "codes": {"gstat": 1004, "gkat": 1020},
                            "decoded": {
                                "status": "Bestehend",
                                "kategorie": "Wohngebäude",
                            },
                        },
                        "energy": {
                            "raw_codes": {"gwaerzh1": 7410, "genh1": 7501},
                            "decoded_summary": {"heizung": ["Wärmepumpe (Luft)"]},
                        },
                        "suitability_light": {
                            "status": "ok",
                            "heuristic_version": "e2e-stub-v1",
                            "score": 80,
                            "traffic_light": "green",
                            "classification": "geeignet",
                            "base_score": 80.1,
                            "personalized_score": 80.1,
                            "factors": [
                                {"key": "topography", "score": 82.0, "weight": 0.34},
                                {"key": "access", "score": 76.0, "weight": 0.29},
                                {"key": "building_state", "score": 74.0, "weight": 0.17},
                                {"key": "data_quality", "score": 88.0, "weight": 0.20},
                            ],
                        },
                        "summary_compact": {
                            "suitability_light": {
                                "status": "ok",
                                "score": 80,
                                "traffic_light": "green",
                                "classification": "geeignet",
                                "base_score": 80.1,
                                "personalized_score": 80.1,
                            }
                        },
                        "sources": {"e2e_fault_injection": {"status": "ok"}},
                        "source_classification": {
                            "e2e_fault_injection": {
                                "source": "e2e_fault_injection",
                                "authority": "internal",
                                "present": True,
                            }
                        },
                        "source_attribution": {"match": ["e2e_fault_injection"]},
                        "confidence": {"score": 100, "max": 100, "level": "high"},
                    }
                    _apply_personalized_suitability_scores(
                        stub_report,
                        preferences_profile,
                        preferences_supplied=preferences_supplied,
                    )
                    self._send_json(
                        {
                            "ok": True,
                            "result": _grouped_api_result(
                                stub_report,
                                response_mode=response_mode,
                                include_legacy_labels=include_legacy_labels,
                            ),
                            "request_id": request_id,
                        },
                        request_id=request_id,
                    )
                    return

            default_timeout = _as_positive_finite_number(
                os.getenv("ANALYZE_DEFAULT_TIMEOUT_SECONDS", "15"),
                "ANALYZE_DEFAULT_TIMEOUT_SECONDS",
            )
            max_timeout = _as_positive_finite_number(
                os.getenv("ANALYZE_MAX_TIMEOUT_SECONDS", "45"),
                "ANALYZE_MAX_TIMEOUT_SECONDS",
            )
            req_timeout_raw = data.get("timeout_seconds", default_timeout)
            timeout = _as_positive_finite_number(req_timeout_raw, "timeout_seconds")
            timeout = min(timeout, max_timeout)

            report = build_report(
                query,
                include_osm=True,
                candidate_limit=8,
                candidate_preview=3,
                timeout=timeout,
                retries=2,
                backoff_seconds=0.6,
                intelligence_mode=mode,
            )
            _apply_personalized_suitability_scores(
                report,
                preferences_profile,
                preferences_supplied=preferences_supplied,
            )
            self._send_json(
                {
                    "ok": True,
                    "result": _grouped_api_result(
                        report,
                        response_mode=response_mode,
                        include_legacy_labels=include_legacy_labels,
                    ),
                    "request_id": request_id,
                },
                request_id=request_id,
            )
        except TimeoutError as e:
            self._send_json(
                {
                    "ok": False,
                    "error": "timeout",
                    "message": str(e),
                    "request_id": request_id,
                },
                status=HTTPStatus.GATEWAY_TIMEOUT,
                request_id=request_id,
            )
        except AddressIntelError as e:
            self._send_json(
                {
                    "ok": False,
                    "error": "address_intel",
                    "message": str(e),
                    "request_id": request_id,
                },
                status=422,
                request_id=request_id,
            )
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_request",
                    "message": str(e),
                    "request_id": request_id,
                },
                status=400,
                request_id=request_id,
            )
        except Exception as e:  # pragma: no cover
            self._send_json(
                {
                    "ok": False,
                    "error": "internal",
                    "message": str(e),
                    "request_id": request_id,
                },
                status=500,
                request_id=request_id,
            )


def _resolve_port() -> int:
    """Liest die Service-Port-Konfiguration robust aus ENV.

    Kompatibilität: `PORT` bleibt primär, `WEB_PORT` dient als Fallback
    (z. B. für lokale Wrapper/Runner).
    """

    port_raw = os.getenv("PORT")
    if port_raw is None or not str(port_raw).strip():
        port_raw = os.getenv("WEB_PORT", "8080")
    return int(str(port_raw).strip())


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = _resolve_port()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"geo-ranking-ch web service listening on {host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
