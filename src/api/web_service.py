#!/usr/bin/env python3
"""Minimaler HTTP-Webservice für ECS (stdlib only).

Endpoints:
- GET /gui
- GET /health
- GET /version
- GET /api/v1/dictionaries
- GET /api/v1/dictionaries/<domain>
- GET /analyze/jobs/<job_id>
- GET /analyze/results/<result_id>
- GET /debug/trace?request_id=<id> (dev-only)
- POST /analyze {"query": "...", "intelligence_mode": "basic|extended|risk"}
- POST /analyze/jobs/<job_id>/cancel
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import ssl
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen

from src.api.address_intel import AddressIntelError, build_report
from src.api.async_jobs import AsyncJobStore
from src.api.async_worker_runtime import AsyncJobRuntime
from src.api.debug_trace import (
    build_trace_timeline,
    normalize_lookback_seconds,
    normalize_max_events,
    normalize_request_id,
)
from src.shared.gui_mvp import render_gui_mvp_html
from src.shared.structured_logging import build_event, emit_event
from src.gwr_codes import DWST, GENH, GKAT, GKLAS, GSTAT, GWAERZH, GWAERZW
from src.api.personalized_scoring import compute_two_stage_scores

SUPPORTED_INTELLIGENCE_MODES = {"basic", "extended", "risk"}
_BEARER_AUTH_RE = re.compile(r"^\s*Bearer\s+([^\s]+)\s*$", re.IGNORECASE)
_CORS_ALLOW_ORIGINS_ENV = "CORS_ALLOW_ORIGINS"
_CORS_ALLOW_METHODS = "POST, OPTIONS"
_CORS_ALLOW_HEADERS = "Content-Type, Authorization, X-Request-Id, X-Session-Id"
_CORS_MAX_AGE_SECONDS = "600"
_TOP_LEVEL_STATUS_KEYS = {
    "confidence",
    "sources",
    "source_classification",
    "source_attribution",
    "executive_summary",
    "personalization_status",
    "capabilities_status",
    "entitlements_status",
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
_DEEP_MODE_ALLOWED_PROFILES = {"analysis_plus", "risk_plus"}
_DEEP_MODE_DEFAULT_PROFILE_BY_MODE = {
    "risk": "risk_plus",
    "basic": "analysis_plus",
    "extended": "analysis_plus",
}
_COORDINATE_SNAP_MODES = {"strict", "ch_bounds"}
_CH_WGS84_BOUNDS = {
    "lat_min": 45.8179,
    "lat_max": 47.8084,
    "lon_min": 5.9559,
    "lon_max": 10.4921,
}
_COORDINATE_SNAP_TOLERANCE_DEG = 0.02
_COORDINATE_IDENTIFY_TOLERANCE_M = 180.0
_COORDINATE_MAX_SNAP_DISTANCE_M = 120.0

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

_PREFERENCE_PRESET_VERSION = "v1"
_PREFERENCE_PRESETS: dict[str, dict[str, Any]] = {
    "urban_lifestyle": {
        "lifestyle_density": "urban",
        "noise_tolerance": "medium",
        "nightlife_preference": "prefer",
        "school_proximity": "neutral",
        "family_friendly_focus": "low",
        "commute_priority": "pt",
        "weights": {
            "nightlife_preference": 0.85,
            "commute_priority": 0.9,
            "noise_tolerance": 0.45,
        },
    },
    "family_friendly": {
        "lifestyle_density": "suburban",
        "noise_tolerance": "low",
        "nightlife_preference": "avoid",
        "school_proximity": "prefer",
        "family_friendly_focus": "high",
        "commute_priority": "mixed",
        "weights": {
            "school_proximity": 0.95,
            "family_friendly_focus": 0.95,
            "noise_tolerance": 0.75,
        },
    },
    "quiet_residential": {
        "lifestyle_density": "suburban",
        "noise_tolerance": "low",
        "nightlife_preference": "avoid",
        "school_proximity": "neutral",
        "family_friendly_focus": "medium",
        "commute_priority": "mixed",
        "weights": {
            "noise_tolerance": 0.95,
            "nightlife_preference": 0.7,
            "lifestyle_density": 0.6,
        },
    },
    "car_commuter": {
        "lifestyle_density": "suburban",
        "noise_tolerance": "medium",
        "nightlife_preference": "neutral",
        "school_proximity": "neutral",
        "family_friendly_focus": "medium",
        "commute_priority": "car",
        "weights": {
            "commute_priority": 0.95,
            "lifestyle_density": 0.55,
            "noise_tolerance": 0.4,
        },
    },
    "pt_commuter": {
        "lifestyle_density": "urban",
        "noise_tolerance": "medium",
        "nightlife_preference": "neutral",
        "school_proximity": "neutral",
        "family_friendly_focus": "medium",
        "commute_priority": "pt",
        "weights": {
            "commute_priority": 0.95,
            "lifestyle_density": 0.55,
            "noise_tolerance": 0.4,
        },
    },
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

_TRACE_DEBUG_ENABLED_ENV = "TRACE_DEBUG_ENABLED"
_TRACE_DEBUG_LOG_PATH_ENV = "TRACE_DEBUG_LOG_PATH"
_TRACE_DEBUG_CW_LOG_GROUP_ENV = "TRACE_DEBUG_CW_LOG_GROUP"
_TRACE_DEBUG_CW_LOG_STREAM_PREFIX_ENV = "TRACE_DEBUG_CW_LOG_STREAM_PREFIX"
_TRACE_DEBUG_LOOKBACK_SECONDS_ENV = "TRACE_DEBUG_LOOKBACK_SECONDS"
_TRACE_DEBUG_MAX_EVENTS_ENV = "TRACE_DEBUG_MAX_EVENTS"

_EXTERNAL_DIRECT_LOGIN_BLOCKED_PATHS = frozenset(
    {
        "/login",
        "/signin",
        "/sign-in",
        "/auth/login",
        "/auth/signin",
        "/auth/sign-in",
        "/oauth/login",
        "/oauth2/login",
    }
)
_EXTERNAL_DIRECT_LOGIN_ERROR = "external_direct_login_disabled"
_EXTERNAL_DIRECT_LOGIN_MESSAGE = (
    "direct login is disabled; access is only allowed via internal provisioning/export workflows"
)

_ASYNC_JOB_STORE = AsyncJobStore.from_env()
_ASYNC_JOB_RUNTIME = AsyncJobRuntime(store=_ASYNC_JOB_STORE)
_ASYNC_RUNTIME_START_LOCK = threading.Lock()
_ASYNC_RUNTIME_STARTED = False


def _ensure_async_runtime_started() -> None:
    global _ASYNC_RUNTIME_STARTED
    if _ASYNC_RUNTIME_STARTED:
        return

    with _ASYNC_RUNTIME_START_LOCK:
        if _ASYNC_RUNTIME_STARTED:
            return
        _ASYNC_JOB_RUNTIME.start()
        _ASYNC_JOB_RUNTIME.enqueue_pending_jobs()
        _ASYNC_RUNTIME_STARTED = True


def _env_flag_enabled(name: str, *, default: bool = False) -> bool:
    raw_value = str(os.getenv(name, "")).strip().lower()
    if not raw_value:
        return default
    return raw_value in {"1", "true", "yes", "on"}


def _trace_debug_enabled() -> bool:
    return _env_flag_enabled(_TRACE_DEBUG_ENABLED_ENV, default=False)


def _trace_debug_default_lookback_seconds() -> int:
    return normalize_lookback_seconds(os.getenv(_TRACE_DEBUG_LOOKBACK_SECONDS_ENV, ""))


def _trace_debug_default_max_events() -> int:
    return normalize_max_events(os.getenv(_TRACE_DEBUG_MAX_EVENTS_ENV, ""))


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


def _is_external_direct_login_path(request_path: str) -> bool:
    """True, wenn der Pfad einem explizit gesperrten Direktlogin-Endpoint entspricht."""
    normalized = str(request_path or "").strip().lower()
    if not normalized:
        return False
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    normalized = re.sub(r"/{2,}", "/", normalized)
    if normalized != "/":
        normalized = normalized.rstrip("/") or "/"
    return normalized in _EXTERNAL_DIRECT_LOGIN_BLOCKED_PATHS


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


def _emit_structured_log(
    *,
    event: str,
    level: str = "info",
    trace_id: str = "",
    request_id: str = "",
    session_id: str = "",
    **fields: Any,
) -> None:
    """Emit one schema-conform JSON event without breaking request handling."""
    try:
        emit_event(
            build_event(
                event,
                level=level,
                trace_id=trace_id,
                request_id=request_id,
                session_id=session_id,
                **fields,
            )
        )
    except Exception:
        # Logging must never break primary service logic.
        return


def _request_lifecycle_status(*, status_code: int, error_code: str = "") -> str:
    normalized_error = str(error_code or "").strip().lower()
    if normalized_error == "timeout" or status_code in {
        int(HTTPStatus.REQUEST_TIMEOUT),
        int(HTTPStatus.GATEWAY_TIMEOUT),
    }:
        return "timeout"
    if 200 <= status_code < 400:
        return "ok"
    if 400 <= status_code < 500:
        return "client_error"
    if status_code >= 500:
        return "server_error"
    return "unknown"


def _request_lifecycle_error_class(*, status_code: int, error_code: str = "") -> str:
    normalized_error = str(error_code or "").strip().lower()
    if normalized_error:
        return normalized_error
    if status_code in {
        int(HTTPStatus.REQUEST_TIMEOUT),
        int(HTTPStatus.GATEWAY_TIMEOUT),
    }:
        return "timeout"
    if status_code >= 500:
        return "internal"
    if status_code >= 400:
        return "client_error"
    return ""


def _request_lifecycle_level(*, status_code: int) -> str:
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "warn"
    return "info"


def _log_api_request_start(
    *,
    method: str,
    route: str,
    request_id: str,
    session_id: str,
) -> None:
    _emit_structured_log(
        event="api.request.start",
        level="info",
        trace_id=request_id,
        request_id=request_id,
        session_id=session_id,
        component="api.web_service",
        direction="client->api",
        status="received",
        route=route,
        method=method,
    )


def _log_api_request_end(
    *,
    method: str,
    route: str,
    request_id: str,
    session_id: str,
    status_code: int,
    duration_ms: float,
    error_code: str = "",
) -> None:
    lifecycle_status = _request_lifecycle_status(
        status_code=status_code,
        error_code=error_code,
    )
    error_class = _request_lifecycle_error_class(
        status_code=status_code,
        error_code=error_code,
    )

    fields: dict[str, Any] = {
        "component": "api.web_service",
        "direction": "api->client",
        "status": lifecycle_status,
        "route": route,
        "method": method,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }
    if error_code:
        fields["error_code"] = error_code
    if error_class:
        fields["error_class"] = error_class

    _emit_structured_log(
        event="api.request.end",
        level=_request_lifecycle_level(status_code=status_code),
        trace_id=request_id,
        request_id=request_id,
        session_id=session_id,
        **fields,
    )


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

    capabilities_status = report.get("capabilities_status")
    if isinstance(capabilities_status, dict) and capabilities_status:
        status_block["capabilities"] = deepcopy(capabilities_status)

    entitlements_status = report.get("entitlements_status")
    if isinstance(entitlements_status, dict) and entitlements_status:
        status_block["entitlements"] = deepcopy(entitlements_status)

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

    modules = _to_code_first_modules(cleaned)

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


def _as_finite_number(value: Any, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field_name} must be a finite number")
    return parsed


def _normalize_coordinate_snap_mode(raw_value: Any) -> str:
    if raw_value is None:
        return "ch_bounds"

    if isinstance(raw_value, bool):
        return "ch_bounds" if raw_value else "strict"

    if not isinstance(raw_value, str):
        raise ValueError("coordinates.snap_mode must be one of ['strict', 'ch_bounds']")

    mode = raw_value.strip().lower() or "ch_bounds"
    if mode not in _COORDINATE_SNAP_MODES:
        raise ValueError("coordinates.snap_mode must be one of ['strict', 'ch_bounds']")
    return mode


def _clamp_number(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _extract_postal_prefix(value: Any) -> str:
    text = str(value or "")
    match = re.search(r"\b(\d{4})\b", text)
    return match.group(1) if match else ""


def _fetch_json_url(
    url: str,
    *,
    timeout_seconds: float,
    source: str,
    upstream_log_emitter: Callable[..., None] | None = None,
) -> dict[str, Any]:
    target = urlsplit(url)
    target_host = str(target.netloc or "").lower()
    target_path = str(target.path or "/")
    if not target_path.startswith("/"):
        target_path = f"/{target_path}"

    started_at = time.perf_counter()
    if upstream_log_emitter is not None:
        upstream_log_emitter(
            event="api.upstream.request.start",
            level="info",
            component="api.web_service",
            direction="api->upstream",
            status="sent",
            source=source,
            target_host=target_host,
            target_path=target_path,
            attempt=1,
            max_attempts=1,
            retry_count=0,
            timeout_seconds=max(1.0, float(timeout_seconds)),
        )

    status_code = 0
    try:
        with urlopen(url, timeout=max(1.0, float(timeout_seconds))) as response:
            status_code = int(getattr(response, "status", 200) or 200)
            body = response.read().decode("utf-8")
    except Exception as exc:
        if upstream_log_emitter is not None:
            upstream_log_emitter(
                event="api.upstream.request.end",
                level="error",
                component="api.web_service",
                direction="upstream->api",
                status="error",
                source=source,
                target_host=target_host,
                target_path=target_path,
                attempt=1,
                max_attempts=1,
                retry_count=0,
                duration_ms=round((time.perf_counter() - started_at) * 1000.0, 3),
                error_class="network_error",
                error_message=str(exc),
            )
        raise ValueError(f"coordinate resolution failed at {source}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        if upstream_log_emitter is not None:
            upstream_log_emitter(
                event="api.upstream.request.end",
                level="error",
                component="api.web_service",
                direction="upstream->api",
                status="error",
                source=source,
                target_host=target_host,
                target_path=target_path,
                status_code=status_code,
                attempt=1,
                max_attempts=1,
                retry_count=0,
                duration_ms=round((time.perf_counter() - started_at) * 1000.0, 3),
                error_class="decode_error",
                error_message=str(exc),
            )
        raise ValueError(f"coordinate resolution returned invalid JSON at {source}") from exc

    if not isinstance(payload, dict):
        if upstream_log_emitter is not None:
            upstream_log_emitter(
                event="api.upstream.request.end",
                level="error",
                component="api.web_service",
                direction="upstream->api",
                status="error",
                source=source,
                target_host=target_host,
                target_path=target_path,
                status_code=status_code,
                attempt=1,
                max_attempts=1,
                retry_count=0,
                duration_ms=round((time.perf_counter() - started_at) * 1000.0, 3),
                error_class="invalid_payload",
                error_message="payload is not an object",
            )
        raise ValueError(f"coordinate resolution returned invalid payload at {source}")

    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
    result_records = payload.get("results") if isinstance(payload, dict) else None
    records = len(result_records) if isinstance(result_records, list) else 1

    if upstream_log_emitter is not None:
        upstream_log_emitter(
            event="api.upstream.request.end",
            level="info",
            component="api.web_service",
            direction="upstream->api",
            status="ok",
            source=source,
            target_host=target_host,
            target_path=target_path,
            status_code=status_code,
            attempt=1,
            max_attempts=1,
            retry_count=0,
            duration_ms=duration_ms,
        )
        upstream_log_emitter(
            event="api.upstream.response.summary",
            level="info",
            component="api.web_service",
            direction="upstream->api",
            status="ok",
            source=source,
            target_host=target_host,
            target_path=target_path,
            status_code=status_code,
            cache="miss",
            records=records,
            payload_kind=type(payload).__name__,
            attempt=1,
            max_attempts=1,
            retry_count=0,
        )
    return payload


def _wgs84_to_lv95(
    *,
    lat: float,
    lon: float,
    timeout_seconds: float,
    upstream_log_emitter: Callable[..., None] | None = None,
) -> tuple[float, float]:
    params = urlencode(
        {
            "easting": f"{lon:.8f}",
            "northing": f"{lat:.8f}",
            "format": "json",
        }
    )
    url = f"https://geodesy.geo.admin.ch/reframe/wgs84tolv95?{params}"
    payload = _fetch_json_url(
        url,
        timeout_seconds=timeout_seconds,
        source="wgs84tolv95",
        upstream_log_emitter=upstream_log_emitter,
    )

    lv95_e = _as_finite_number(payload.get("easting"), "coordinates.lv95_e")
    lv95_n = _as_finite_number(payload.get("northing"), "coordinates.lv95_n")
    return lv95_e, lv95_n


def _identify_gwr_candidates(
    *,
    lat: float,
    lon: float,
    timeout_seconds: float,
    upstream_log_emitter: Callable[..., None] | None = None,
) -> list[dict[str, Any]]:
    cos_lat = max(math.cos(math.radians(lat)), 0.2)
    margin_lat = max(_COORDINATE_IDENTIFY_TOLERANCE_M / 111320.0, 0.0015)
    margin_lon = max(_COORDINATE_IDENTIFY_TOLERANCE_M / (111320.0 * cos_lat), 0.0015)

    params = {
        "geometry": f"{lon:.8f},{lat:.8f}",
        "geometryType": "esriGeometryPoint",
        "imageDisplay": "500,500,96",
        "mapExtent": (
            f"{lon-margin_lon:.8f},{lat-margin_lat:.8f},"
            f"{lon+margin_lon:.8f},{lat+margin_lat:.8f}"
        ),
        "tolerance": "10",
        "layers": "all:ch.bfs.gebaeude_wohnungs_register",
        "sr": "4326",
        "lang": "de",
        "returnGeometry": "false",
        "f": "json",
    }
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify?" + urlencode(params)
    payload = _fetch_json_url(
        url,
        timeout_seconds=timeout_seconds,
        source="gwr_identify",
        upstream_log_emitter=upstream_log_emitter,
    )

    results = payload.get("results")
    if not isinstance(results, list):
        return []

    candidates: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        attrs = row.get("attributes")
        if not isinstance(attrs, dict):
            continue

        feature_id = str(row.get("featureId") or attrs.get("featureId") or "").strip()
        if not feature_id:
            continue

        street = str(attrs.get("strname_deinr") or "").strip()
        city = str(attrs.get("dplzname") or attrs.get("ggdename") or "").strip()
        postal_code = _extract_postal_prefix(attrs.get("plz_plz6"))

        lv95_e = None
        lv95_n = None
        try:
            lv95_e = _as_finite_number(attrs.get("gkode"), "coordinates.lv95_e")
            lv95_n = _as_finite_number(attrs.get("gkodn"), "coordinates.lv95_n")
        except ValueError:
            lv95_e = None
            lv95_n = None

        if not street or not postal_code:
            continue

        city_fallback = city or str(attrs.get("ggdename") or "").strip()
        candidates.append(
            {
                "feature_id": feature_id,
                "street": street,
                "postal_code": postal_code,
                "city": city_fallback,
                "lv95_e": lv95_e,
                "lv95_n": lv95_n,
            }
        )

    return candidates


def _resolve_query_from_coordinates(
    *,
    lat: float,
    lon: float,
    timeout_seconds: float = 8.0,
    upstream_log_emitter: Callable[..., None] | None = None,
) -> tuple[str, dict[str, Any]]:
    click_lv95_e, click_lv95_n = _wgs84_to_lv95(
        lat=lat,
        lon=lon,
        timeout_seconds=timeout_seconds,
        upstream_log_emitter=upstream_log_emitter,
    )
    candidates = _identify_gwr_candidates(
        lat=lat,
        lon=lon,
        timeout_seconds=timeout_seconds,
        upstream_log_emitter=upstream_log_emitter,
    )

    if not candidates:
        raise ValueError("coordinates could not be resolved to a Swiss building candidate")

    ranked: list[tuple[float, dict[str, Any]]] = []
    for candidate in candidates:
        c_e = candidate.get("lv95_e")
        c_n = candidate.get("lv95_n")
        if isinstance(c_e, (int, float)) and isinstance(c_n, (int, float)):
            distance_m = math.hypot(float(c_e) - click_lv95_e, float(c_n) - click_lv95_n)
        else:
            distance_m = float("inf")
        ranked.append((distance_m, candidate))

    ranked.sort(key=lambda row: row[0])
    best_distance_m, best = ranked[0]

    if math.isfinite(best_distance_m) and best_distance_m > _COORDINATE_MAX_SNAP_DISTANCE_M:
        raise ValueError(
            "no building candidate found within "
            f"{int(_COORDINATE_MAX_SNAP_DISTANCE_M)}m of the clicked coordinates"
        )

    city_part = str(best.get("city") or "").strip()
    resolved_query = f"{best['street']}, {best['postal_code']} {city_part}".strip()

    return resolved_query, {
        "provider": "ch.bfs.gebaeude_wohnungs_register",
        "feature_id": best.get("feature_id"),
        "distance_m": None if not math.isfinite(best_distance_m) else round(best_distance_m, 2),
        "resolved_query": resolved_query,
        "clickpoint_wgs84": {
            "lat": round(lat, 6),
            "lon": round(lon, 6),
        },
    }


def _extract_query_and_coordinate_context(
    data: dict[str, Any],
    *,
    upstream_log_emitter: Callable[..., None] | None = None,
) -> tuple[str, dict[str, Any] | None]:
    query = str(data.get("query", "")).strip()
    if query:
        return query, None

    raw_coordinates = data.get("coordinates")
    if raw_coordinates is None:
        raise ValueError("query is required")
    if not isinstance(raw_coordinates, dict):
        raise ValueError("coordinates must be an object when provided")

    raw_lat = raw_coordinates.get("lat")
    raw_lon = raw_coordinates.get("lon")
    if raw_lon is None:
        raw_lon = raw_coordinates.get("lng")
    if raw_lon is None:
        raw_lon = raw_coordinates.get("longitude")

    if raw_lat is None or raw_lon is None:
        raise ValueError("coordinates.lat and coordinates.lon are required when query is missing")

    lat = _as_finite_number(raw_lat, "coordinates.lat")
    lon = _as_finite_number(raw_lon, "coordinates.lon")

    if lat < -90 or lat > 90:
        raise ValueError("coordinates.lat must be between -90 and 90")
    if lon < -180 or lon > 180:
        raise ValueError("coordinates.lon must be between -180 and 180")

    snap_mode = _normalize_coordinate_snap_mode(raw_coordinates.get("snap_mode"))

    lat_min = float(_CH_WGS84_BOUNDS["lat_min"])
    lat_max = float(_CH_WGS84_BOUNDS["lat_max"])
    lon_min = float(_CH_WGS84_BOUNDS["lon_min"])
    lon_max = float(_CH_WGS84_BOUNDS["lon_max"])

    inside_ch = lat_min <= lat <= lat_max and lon_min <= lon <= lon_max
    snap_applied = False

    if not inside_ch:
        if snap_mode == "strict":
            raise ValueError("coordinates are outside Swiss coverage bounds")

        snapped_lat = _clamp_number(lat, lat_min, lat_max)
        snapped_lon = _clamp_number(lon, lon_min, lon_max)

        if (
            abs(snapped_lat - lat) > _COORDINATE_SNAP_TOLERANCE_DEG
            or abs(snapped_lon - lon) > _COORDINATE_SNAP_TOLERANCE_DEG
        ):
            raise ValueError(
                "coordinates are outside Swiss coverage bounds "
                f"(snap tolerance ±{_COORDINATE_SNAP_TOLERANCE_DEG:.2f}° exceeded)"
            )

        lat = snapped_lat
        lon = snapped_lon
        snap_applied = True

    resolved_query, resolution_context = _resolve_query_from_coordinates(
        lat=lat,
        lon=lon,
        upstream_log_emitter=upstream_log_emitter,
    )

    coordinate_context = {
        "input_mode": "coordinates",
        "snap_mode": snap_mode,
        "snap_applied": snap_applied,
        "snap_tolerance_deg": _COORDINATE_SNAP_TOLERANCE_DEG,
        "resolved": resolution_context,
    }
    return resolved_query, coordinate_context


def _attach_coordinate_resolution_context(report: dict[str, Any], context: dict[str, Any]) -> None:
    if not context:
        return

    match_block = report.get("match")
    if not isinstance(match_block, dict):
        match_block = {}
        report["match"] = match_block

    resolution_block = match_block.get("resolution")
    if not isinstance(resolution_block, dict):
        resolution_block = {}
        match_block["resolution"] = resolution_block

    resolution_block["input_mode"] = "coordinates"
    resolution_block["coordinate_input"] = deepcopy(context)


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


def _canonical_origin(value: Any) -> str:
    """Normalisiert eine Origin auf `scheme://host[:port]` oder gibt "" zurück."""
    raw = str(value or "").strip()
    if not raw:
        return ""

    parsed = urlsplit(raw)
    if parsed.scheme.lower() not in {"http", "https"}:
        return ""
    if not parsed.netloc:
        return ""
    if parsed.username or parsed.password:
        return ""
    if parsed.path not in {"", "/"}:
        return ""
    if parsed.query or parsed.fragment:
        return ""

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return ""

    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    authority = hostname
    if parsed.port is not None:
        authority = f"{authority}:{parsed.port}"
    return f"{parsed.scheme.lower()}://{authority}"


def _parse_cors_allow_origins(raw_value: Any) -> set[str]:
    allowed: set[str] = set()
    for chunk in str(raw_value or "").split(","):
        origin = _canonical_origin(chunk)
        if origin:
            allowed.add(origin)
    return allowed


def _resolve_cors_allow_origins() -> set[str]:
    return _parse_cors_allow_origins(os.getenv(_CORS_ALLOW_ORIGINS_ENV, ""))


def _build_cors_headers(
    origin_header: Any,
    *,
    allowed_origins: set[str],
    include_preflight: bool,
    allow_methods: str = _CORS_ALLOW_METHODS,
) -> dict[str, str] | None:
    """Ermittelt CORS-Response-Header.

    Returns:
      - `None`: Origin explizit abgelehnt (Allowlist aktiv + Origin ungültig/nicht erlaubt)
      - `{}`: keine CORS-Header nötig (keine Allowlist oder keine Origin)
      - `{...}`: konkrete Header für die Antwort
    """
    if not allowed_origins:
        return {}

    origin = _canonical_origin(origin_header)
    if not origin:
        return {}
    if origin not in allowed_origins:
        return None

    headers = {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
    }
    if include_preflight:
        headers.update(
            {
                "Access-Control-Allow-Methods": allow_methods,
                "Access-Control-Allow-Headers": _CORS_ALLOW_HEADERS,
                "Access-Control-Max-Age": _CORS_MAX_AGE_SECONDS,
            }
        )
    return headers


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


def _reject_legacy_options(options: dict[str, Any]) -> None:
    """Lehnt explizite Legacy-Flags im öffentlichen Request-Surface ab."""
    if "include_labels" in options:
        raise ValueError(
            "options.include_labels is no longer supported; use code-first responses via result.status.dictionary"
        )


def _extract_async_mode_request(options: dict[str, Any]) -> bool:
    """Liest den additiven Async-Mode-Schalter aus `options.async_mode.requested`."""
    async_mode_raw = options.get("async_mode")
    if async_mode_raw is None:
        return False
    if not isinstance(async_mode_raw, dict):
        raise ValueError("options.async_mode must be an object when provided")

    requested_raw = async_mode_raw.get("requested", False)
    if isinstance(requested_raw, bool):
        return requested_raw
    raise ValueError("options.async_mode.requested must be a boolean")


def _project_async_job_status(job: dict[str, Any], *, include_events: bool = False) -> dict[str, Any]:
    projected = {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "progress_percent": int(job.get("progress_percent", 0) or 0),
        "partial_count": int(job.get("partial_count", 0) or 0),
        "error_count": int(job.get("error_count", 0) or 0),
        "result_id": job.get("result_id"),
        "queued_at": job.get("queued_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "updated_at": job.get("updated_at"),
        "error_code": job.get("error_code"),
        "error_message": job.get("error_message"),
        "retryable": job.get("retryable"),
        "retry_hint": job.get("retry_hint"),
        "cancel_requested_at": job.get("cancel_requested_at"),
        "canceled_at": job.get("canceled_at"),
        "canceled_by": job.get("canceled_by"),
        "cancel_reason": job.get("cancel_reason"),
    }
    if include_events:
        projected["events"] = _ASYNC_JOB_STORE.list_events(str(job.get("job_id") or ""))
    return projected


def _build_async_result_stub(*, query: str, intelligence_mode: str) -> dict[str, Any]:
    return {
        "ok": True,
        "result": {
            "status": {
                "confidence": {
                    "score": None,
                    "max": 100,
                    "level": "pending_implementation",
                },
                "sources": {
                    "async_runtime": {
                        "status": "stub",
                    }
                },
                "source_attribution": {
                    "match": ["async_runtime"],
                },
            },
            "data": {
                "entity": {
                    "query": query,
                },
                "modules": {
                    "runtime": {
                        "status": "stub",
                        "intelligence_mode": intelligence_mode,
                        "message": "Async runtime skeleton placeholder result",
                    }
                },
                "by_source": {
                    "async_runtime": {
                        "module_refs": ["runtime"],
                    }
                },
            },
        },
    }


def _as_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer >= 0")
    if value < 0:
        raise ValueError(f"{field_name} must be an integer >= 0")
    return int(value)


def _resolve_deep_mode_profile(*, raw_profile: Any, intelligence_mode: str) -> str:
    if raw_profile is None:
        return _DEEP_MODE_DEFAULT_PROFILE_BY_MODE.get(intelligence_mode, "analysis_plus")
    if not isinstance(raw_profile, str):
        raise ValueError("options.capabilities.deep_mode.profile must be a string")

    normalized = raw_profile.strip().lower()
    if not normalized:
        raise ValueError("options.capabilities.deep_mode.profile must be a non-empty string")
    return normalized


def _extract_deep_mode_request(
    options: dict[str, Any],
    *,
    intelligence_mode: str,
) -> dict[str, Any]:
    capabilities_raw = options.get("capabilities")
    if capabilities_raw is not None and not isinstance(capabilities_raw, dict):
        raise ValueError("options.capabilities must be an object when provided")
    capabilities = capabilities_raw if isinstance(capabilities_raw, dict) else {}

    entitlements_raw = options.get("entitlements")
    if entitlements_raw is not None and not isinstance(entitlements_raw, dict):
        raise ValueError("options.entitlements must be an object when provided")
    entitlements = entitlements_raw if isinstance(entitlements_raw, dict) else {}

    deep_cap_raw = capabilities.get("deep_mode")
    if deep_cap_raw is not None and not isinstance(deep_cap_raw, dict):
        raise ValueError("options.capabilities.deep_mode must be an object when provided")
    deep_cap = deep_cap_raw if isinstance(deep_cap_raw, dict) else {}

    deep_ent_raw = entitlements.get("deep_mode")
    if deep_ent_raw is not None and not isinstance(deep_ent_raw, dict):
        raise ValueError("options.entitlements.deep_mode must be an object when provided")
    deep_ent = deep_ent_raw if isinstance(deep_ent_raw, dict) else {}

    raw_requested = deep_cap.get("requested")
    if raw_requested is None:
        requested = False
    elif isinstance(raw_requested, bool):
        requested = raw_requested
    else:
        raise ValueError("options.capabilities.deep_mode.requested must be a boolean")

    profile = _resolve_deep_mode_profile(
        raw_profile=deep_cap.get("profile"),
        intelligence_mode=intelligence_mode,
    )

    raw_max_budget_tokens = deep_cap.get("max_budget_tokens")
    max_budget_tokens: int | None = None
    if raw_max_budget_tokens is not None:
        max_budget_tokens = _as_non_negative_int(
            raw_max_budget_tokens,
            "options.capabilities.deep_mode.max_budget_tokens",
        )

    raw_allowed = deep_ent.get("allowed")
    if raw_allowed is None:
        allowed = False
    elif isinstance(raw_allowed, bool):
        allowed = raw_allowed
    else:
        raise ValueError("options.entitlements.deep_mode.allowed must be a boolean")

    raw_quota_remaining = deep_ent.get("quota_remaining")
    quota_remaining: int | None = None
    if raw_quota_remaining is not None:
        quota_remaining = _as_non_negative_int(
            raw_quota_remaining,
            "options.entitlements.deep_mode.quota_remaining",
        )

    return {
        "requested": requested,
        "profile": profile,
        "allowed": allowed,
        "quota_remaining": quota_remaining,
        "max_budget_tokens": max_budget_tokens,
    }


def _read_env_non_negative_int(name: str, *, default: int) -> int:
    raw_value = str(os.getenv(name, "")).strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    if parsed < 0:
        return default
    return parsed


def _read_env_unit_interval(name: str, *, default: float) -> float:
    raw_value = str(os.getenv(name, "")).strip()
    if not raw_value:
        return default
    try:
        parsed = float(raw_value)
    except ValueError:
        return default
    if not math.isfinite(parsed):
        return default
    return min(max(parsed, 0.0), 1.0)


def _derive_deep_mode_budget(
    *,
    timeout_seconds: float,
    profile: str,
    requested_budget_tokens: int | None,
) -> dict[str, int]:
    total_request_budget_ms = max(1, int(round(float(timeout_seconds) * 1000)))

    baseline_reserved_floor_ms = _read_env_non_negative_int(
        "DEEP_BASELINE_RESERVED_FLOOR_MS",
        default=1_000,
    )
    baseline_reserved_ratio = _read_env_unit_interval(
        "DEEP_BASELINE_RESERVED_RATIO",
        default=0.7,
    )
    safety_margin_ms = _read_env_non_negative_int(
        "DEEP_SAFETY_MARGIN_MS",
        default=250,
    )
    min_budget_ms = _read_env_non_negative_int(
        "DEEP_MIN_BUDGET_MS",
        default=600,
    )

    baseline_reserved_ms = max(
        baseline_reserved_floor_ms,
        int(round(total_request_budget_ms * baseline_reserved_ratio)),
    )
    baseline_reserved_ms = min(total_request_budget_ms, baseline_reserved_ms)

    deep_budget_ms = max(0, total_request_budget_ms - baseline_reserved_ms - safety_margin_ms)

    server_cap_tokens = _read_env_non_negative_int("DEEP_MAX_TOKENS_SERVER", default=12_000)
    profile_caps = {
        "analysis_plus": _read_env_non_negative_int("DEEP_PROFILE_CAP_ANALYSIS_PLUS", default=12_000),
        "risk_plus": _read_env_non_negative_int("DEEP_PROFILE_CAP_RISK_PLUS", default=9_000),
    }
    profile_cap_tokens = profile_caps.get(profile, 0)

    client_cap_tokens = server_cap_tokens if requested_budget_tokens is None else requested_budget_tokens
    deep_budget_tokens_effective = min(client_cap_tokens, profile_cap_tokens, server_cap_tokens)

    return {
        "total_request_budget_ms": total_request_budget_ms,
        "baseline_reserved_ms": baseline_reserved_ms,
        "safety_margin_ms": safety_margin_ms,
        "deep_budget_ms": deep_budget_ms,
        "deep_min_budget_ms": min_budget_ms,
        "deep_budget_tokens_effective": max(0, deep_budget_tokens_effective),
    }


def _evaluate_deep_mode_gate(
    *,
    requested: bool,
    profile: str,
    allowed: bool,
    quota_remaining: int | None,
    deep_budget_ms: int,
    deep_min_budget_ms: int,
) -> tuple[bool, str | None]:
    if not requested:
        return False, None
    if profile not in _DEEP_MODE_ALLOWED_PROFILES:
        return False, "policy_guard"
    if not allowed:
        return False, "not_entitled"
    if quota_remaining is not None and quota_remaining <= 0:
        return False, "quota_exhausted"
    if deep_budget_ms < deep_min_budget_ms:
        return False, "timeout_budget"
    return True, None


def _apply_deep_mode_runtime_status(
    report: dict[str, Any],
    *,
    options: dict[str, Any],
    intelligence_mode: str,
    timeout_seconds: float,
    request_id: str = "",
    session_id: str = "",
    execution_retry_count: int = 0,
) -> None:
    started_at = time.perf_counter()
    deep_request = _extract_deep_mode_request(options, intelligence_mode=intelligence_mode)
    budget = _derive_deep_mode_budget(
        timeout_seconds=timeout_seconds,
        profile=str(deep_request["profile"]),
        requested_budget_tokens=deep_request.get("max_budget_tokens"),
    )

    deep_effective, fallback_reason = _evaluate_deep_mode_gate(
        requested=bool(deep_request["requested"]),
        profile=str(deep_request["profile"]),
        allowed=bool(deep_request["allowed"]),
        quota_remaining=deep_request.get("quota_remaining"),
        deep_budget_ms=int(budget["deep_budget_ms"]),
        deep_min_budget_ms=int(budget["deep_min_budget_ms"]),
    )

    retry_count = 0
    if isinstance(execution_retry_count, (int, float)) and not isinstance(execution_retry_count, bool):
        retry_count = max(0, int(execution_retry_count))

    deep_requested = bool(deep_request["requested"])
    deep_profile = str(deep_request["profile"])
    deep_budget_ms = int(budget["deep_budget_ms"])
    deep_budget_tokens_effective = int(budget["deep_budget_tokens_effective"])

    def _emit_deep_mode_event(
        *,
        event: str,
        level: str,
        status: str,
        duration_ms: float | None = None,
    ) -> None:
        telemetry_fields: dict[str, Any] = {
            "component": "api.web_service",
            "direction": "internal",
            "route": "/analyze",
            "status": status,
            "deep_requested": deep_requested,
            "deep_effective": bool(deep_effective),
            "deep_profile": deep_profile,
            "deep_budget_ms": deep_budget_ms,
            "deep_budget_tokens_effective": deep_budget_tokens_effective,
            "retry_count": retry_count,
        }
        if fallback_reason:
            telemetry_fields["fallback_reason"] = fallback_reason
        if duration_ms is not None:
            telemetry_fields["duration_ms"] = round(max(0.0, float(duration_ms)), 3)

        _emit_structured_log(
            event=event,
            level=level,
            trace_id=request_id,
            request_id=request_id,
            session_id=session_id,
            **telemetry_fields,
        )

    _emit_deep_mode_event(
        event="api.deep_mode.gate_evaluated",
        level="info",
        status="evaluated",
    )

    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    if deep_requested:
        if deep_effective:
            _emit_deep_mode_event(
                event="api.deep_mode.execution.start",
                level="info",
                status="started",
            )
            if retry_count > 0:
                _emit_deep_mode_event(
                    event="api.deep_mode.execution.retry",
                    level="warn",
                    status="retrying",
                )
            _emit_deep_mode_event(
                event="api.deep_mode.execution.end",
                level="info",
                status="ok",
                duration_ms=elapsed_ms,
            )
        else:
            _emit_deep_mode_event(
                event="api.deep_mode.execution.abort",
                level="warn",
                status="aborted",
                duration_ms=elapsed_ms,
            )

    quota_before = deep_request.get("quota_remaining")
    quota_consumed = 1 if deep_effective else 0
    quota_after = quota_before
    if isinstance(quota_before, int) and deep_effective:
        quota_after = max(0, quota_before - quota_consumed)

    deep_capability_status: dict[str, Any] = {
        "requested": bool(deep_request["requested"]),
        "effective": bool(deep_effective),
    }
    if fallback_reason:
        deep_capability_status["fallback_reason"] = fallback_reason

    deep_entitlement_status: dict[str, Any] = {
        "allowed": bool(deep_request["allowed"]),
        "quota_consumed": quota_consumed,
    }
    if isinstance(quota_after, int):
        deep_entitlement_status["quota_remaining"] = quota_after

    existing_capabilities = report.get("capabilities_status")
    if not isinstance(existing_capabilities, dict):
        existing_capabilities = {}
    existing_capabilities["deep_mode"] = deep_capability_status
    report["capabilities_status"] = existing_capabilities

    existing_entitlements = report.get("entitlements_status")
    if not isinstance(existing_entitlements, dict):
        existing_entitlements = {}
    existing_entitlements["deep_mode"] = deep_entitlement_status
    report["entitlements_status"] = existing_entitlements


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
    - `preferences.preset` bietet vordefinierte Profile (versioniert über `preset_version`)
    - `weights` ist optional und auf bekannte Keys mit Werten im Bereich 0..1 begrenzt

    Konfliktregel (deterministisch):
    1) Defaults
    2) Preset (falls gesetzt)
    3) explizite Feld-Overrides aus dem Request
    4) explizite `weights`-Overrides aus dem Request
    """
    raw_preferences = data.get("preferences")
    effective = deepcopy(_DEFAULT_PREFERENCES)

    if raw_preferences is None:
        return effective
    if not isinstance(raw_preferences, dict):
        raise ValueError("preferences must be an object when provided")

    allowed_keys = set(_PREFERENCE_ENUMS) | {"weights", "preset", "preset_version"}
    unknown_keys = set(raw_preferences) - allowed_keys
    if unknown_keys:
        raise ValueError(f"preferences contains unknown keys: {sorted(unknown_keys)}")

    raw_preset = raw_preferences.get("preset")
    has_preset = raw_preset is not None
    if has_preset:
        if not isinstance(raw_preset, str) or not raw_preset.strip():
            raise ValueError("preferences.preset must be a non-empty string")
        preset_name = raw_preset.strip().lower()
        preset = _PREFERENCE_PRESETS.get(preset_name)
        if preset is None:
            raise ValueError(
                "preferences.preset must be one of "
                f"{sorted(_PREFERENCE_PRESETS)}"
            )

        raw_preset_version = raw_preferences.get("preset_version", _PREFERENCE_PRESET_VERSION)
        if not isinstance(raw_preset_version, str) or not raw_preset_version.strip():
            raise ValueError("preferences.preset_version must be a non-empty string")
        preset_version = raw_preset_version.strip().lower()
        if preset_version != _PREFERENCE_PRESET_VERSION:
            raise ValueError(
                "preferences.preset_version must be "
                f"{_PREFERENCE_PRESET_VERSION}"
            )

        effective.update(deepcopy(preset))
        effective["preset"] = preset_name
        effective["preset_version"] = preset_version
    elif raw_preferences.get("preset_version") is not None:
        raise ValueError("preferences.preset_version requires preferences.preset")

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

    merged_weights = deepcopy(effective.get("weights") or {})
    merged_weights.update(normalized_weights)
    effective["weights"] = merged_weights
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

    def _begin_request_lifecycle(self, *, method: str, request_path: str, request_id: str) -> None:
        self._request_lifecycle_started_at = time.perf_counter()
        self._request_lifecycle_method = str(method or "").strip().upper() or "GET"
        self._request_lifecycle_route = str(request_path or "/")
        self._request_lifecycle_request_id = str(request_id or "").strip()
        self._request_lifecycle_session_id = str(self.headers.get("X-Session-Id", "") or "").strip()
        self._response_status_code: int | None = None
        self._response_error_code = ""

        _log_api_request_start(
            method=self._request_lifecycle_method,
            route=self._request_lifecycle_route,
            request_id=self._request_lifecycle_request_id,
            session_id=self._request_lifecycle_session_id,
        )

    def _capture_response_error(self, *, payload: dict[str, Any] | None, status: int) -> None:
        self._response_error_code = ""
        if isinstance(payload, dict) and payload.get("ok") is False:
            self._response_error_code = str(payload.get("error") or "").strip().lower()
        if int(status) < HTTPStatus.BAD_REQUEST:
            self._response_error_code = ""

    def _finish_request_lifecycle(self) -> None:
        started_at = getattr(self, "_request_lifecycle_started_at", None)
        if not isinstance(started_at, (int, float)):
            return

        raw_status_code = getattr(self, "_response_status_code", None)
        status_code = int(raw_status_code) if isinstance(raw_status_code, int) else int(HTTPStatus.INTERNAL_SERVER_ERROR)
        duration_ms = round((time.perf_counter() - float(started_at)) * 1000.0, 3)

        _log_api_request_end(
            method=str(getattr(self, "_request_lifecycle_method", "")),
            route=str(getattr(self, "_request_lifecycle_route", "/")),
            request_id=str(getattr(self, "_request_lifecycle_request_id", "")),
            session_id=str(getattr(self, "_request_lifecycle_session_id", "")),
            status_code=status_code,
            duration_ms=duration_ms,
            error_code=str(getattr(self, "_response_error_code", "")),
        )

        self._request_lifecycle_started_at = None

    def send_response(self, code: int, message: str | None = None) -> None:
        self._response_status_code = int(code)
        super().send_response(code, message)

    def _send_json(
        self,
        payload: dict[str, Any],
        status: int = 200,
        *,
        request_id: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._capture_response_error(payload=payload, status=status)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if request_id:
            self.send_header("X-Request-Id", request_id)

        merged_headers: dict[str, str] = {}
        cors_headers = getattr(self, "_cors_response_headers", None)
        if isinstance(cors_headers, dict):
            merged_headers.update(cors_headers)
        if extra_headers:
            merged_headers.update(extra_headers)

        for key, value in merged_headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_html(
        self,
        body_text: str,
        status: int = 200,
        *,
        request_id: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._capture_response_error(payload=None, status=status)
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
        self._capture_response_error(payload=None, status=int(HTTPStatus.NOT_MODIFIED))
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

    def _cors_headers_for_analyze(self, *, include_preflight: bool) -> dict[str, str] | None:
        return _build_cors_headers(
            self.headers.get("Origin", ""),
            allowed_origins=_resolve_cors_allow_origins(),
            include_preflight=include_preflight,
            allow_methods=_CORS_ALLOW_METHODS,
        )

    def _cors_headers_for_debug_trace(self, *, include_preflight: bool) -> dict[str, str] | None:
        return _build_cors_headers(
            self.headers.get("Origin", ""),
            allowed_origins=_resolve_cors_allow_origins(),
            include_preflight=include_preflight,
            allow_methods="GET, OPTIONS",
        )

    def _send_external_direct_login_disabled(
        self,
        *,
        request_id: str,
        request_path: str,
        method: str,
    ) -> None:
        _emit_structured_log(
            event="api.auth.direct_login.blocked",
            level="warn",
            trace_id=request_id,
            request_id=request_id,
            session_id=str(getattr(self, "_request_lifecycle_session_id", "") or ""),
            component="api.web_service",
            direction="client->api",
            status="blocked",
            route=request_path,
            method=method,
            reason=_EXTERNAL_DIRECT_LOGIN_ERROR,
        )
        self._send_json(
            {
                "ok": False,
                "error": _EXTERNAL_DIRECT_LOGIN_ERROR,
                "message": _EXTERNAL_DIRECT_LOGIN_MESSAGE,
                "request_id": request_id,
            },
            status=HTTPStatus.FORBIDDEN,
            request_id=request_id,
            extra_headers={"Cache-Control": "no-store"},
        )

    def do_GET(self) -> None:  # noqa: N802
        request_id = self._request_id()
        request_path = self._normalized_path()
        self._begin_request_lifecycle(method="GET", request_path=request_path, request_id=request_id)

        try:
            self._cors_response_headers = None

            if _is_external_direct_login_path(request_path):
                self._send_external_direct_login_disabled(
                    request_id=request_id,
                    request_path=request_path,
                    method="GET",
                )
                return

            if request_path == "/gui":
                self._send_html(
                    render_gui_mvp_html(app_version=os.getenv("APP_VERSION", "dev")),
                    request_id=request_id,
                    extra_headers={"Cache-Control": "no-store"},
                )
                return
            if request_path == "/health":
                _emit_structured_log(
                    event="api.health.response",
                    trace_id=request_id,
                    request_id=request_id,
                    session_id=self.headers.get("X-Session-Id", "").strip(),
                    component="api.web_service",
                    direction="api->client",
                    status="ok",
                    route="/health",
                    method="GET",
                )
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
            if request_path.startswith("/analyze/jobs/"):
                job_id = request_path.removeprefix("/analyze/jobs/").strip()
                if not job_id or "/" in job_id:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "not_found",
                            "request_id": request_id,
                        },
                        status=HTTPStatus.NOT_FOUND,
                        request_id=request_id,
                    )
                    return

                job_record = _ASYNC_JOB_STORE.get_job(job_id)
                if job_record is None:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "not_found",
                            "message": "unknown job_id",
                            "request_id": request_id,
                        },
                        status=HTTPStatus.NOT_FOUND,
                        request_id=request_id,
                    )
                    return

                self._send_json(
                    {
                        "ok": True,
                        "job": _project_async_job_status(job_record, include_events=True),
                        "request_id": request_id,
                    },
                    request_id=request_id,
                    extra_headers={"Cache-Control": "no-store"},
                )
                return
            if request_path.startswith("/analyze/results/"):
                result_id = request_path.removeprefix("/analyze/results/").strip()
                if not result_id or "/" in result_id:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "not_found",
                            "request_id": request_id,
                        },
                        status=HTTPStatus.NOT_FOUND,
                        request_id=request_id,
                    )
                    return

                result_record = _ASYNC_JOB_STORE.get_result(result_id)
                if result_record is None:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "not_found",
                            "message": "unknown result_id",
                            "request_id": request_id,
                        },
                        status=HTTPStatus.NOT_FOUND,
                        request_id=request_id,
                    )
                    return

                self._send_json(
                    {
                        "ok": True,
                        "result_id": result_record.get("result_id"),
                        "job_id": result_record.get("job_id"),
                        "result_kind": result_record.get("result_kind"),
                        "result": result_record.get("result_payload", {}),
                        "request_id": request_id,
                    },
                    request_id=request_id,
                    extra_headers={"Cache-Control": "no-store"},
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
            if request_path == "/debug/trace":
                cors_headers = self._cors_headers_for_debug_trace(include_preflight=False)
                if cors_headers is None:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "cors_origin_not_allowed",
                            "request_id": request_id,
                        },
                        status=HTTPStatus.FORBIDDEN,
                        request_id=request_id,
                        extra_headers={"Cache-Control": "no-store"},
                    )
                    return
                self._cors_response_headers = cors_headers

                if not _trace_debug_enabled():
                    self._send_json(
                        {
                            "ok": False,
                            "error": "debug_trace_disabled",
                            "message": "trace debug endpoint is disabled",
                            "request_id": request_id,
                        },
                        status=HTTPStatus.FORBIDDEN,
                        request_id=request_id,
                        extra_headers={"Cache-Control": "no-store"},
                    )
                    return

                query_params = parse_qs(urlsplit(self.path).query, keep_blank_values=False)
                trace_request_id = normalize_request_id(query_params.get("request_id", [""])[0])
                if not trace_request_id:
                    self._send_json(
                        {
                            "ok": False,
                            "error": "invalid_request_id",
                            "message": "request_id query parameter is required",
                            "request_id": request_id,
                        },
                        status=HTTPStatus.BAD_REQUEST,
                        request_id=request_id,
                        extra_headers={"Cache-Control": "no-store"},
                    )
                    return

                default_lookback_seconds = _trace_debug_default_lookback_seconds()
                default_max_events = _trace_debug_default_max_events()
                lookback_seconds = normalize_lookback_seconds(
                    query_params.get("lookback_seconds", [str(default_lookback_seconds)])[0]
                )
                max_events = normalize_max_events(
                    query_params.get("max_events", [str(default_max_events)])[0]
                )

                trace_payload = build_trace_timeline(
                    request_id=trace_request_id,
                    log_path=os.getenv(_TRACE_DEBUG_LOG_PATH_ENV, ""),
                    cloudwatch_log_group=os.getenv(_TRACE_DEBUG_CW_LOG_GROUP_ENV, ""),
                    cloudwatch_log_stream_prefix=os.getenv(_TRACE_DEBUG_CW_LOG_STREAM_PREFIX_ENV, ""),
                    lookback_seconds=lookback_seconds,
                    max_events=max_events,
                )

                if not trace_payload.get("ok"):
                    self._send_json(
                        {
                            "ok": False,
                            "error": str(trace_payload.get("error") or "trace_unavailable"),
                            "message": str(trace_payload.get("message") or "trace unavailable"),
                            "request_id": request_id,
                            "trace_request_id": trace_request_id,
                        },
                        status=HTTPStatus.SERVICE_UNAVAILABLE,
                        request_id=request_id,
                        extra_headers={"Cache-Control": "no-store"},
                    )
                    return

                self._send_json(
                    {
                        "ok": True,
                        "request_id": request_id,
                        "trace_request_id": trace_request_id,
                        "trace": trace_payload,
                    },
                    request_id=request_id,
                    extra_headers={"Cache-Control": "no-store"},
                )
                return

            self._send_json(
                {"ok": False, "error": "not_found", "request_id": request_id},
                status=HTTPStatus.NOT_FOUND,
                request_id=request_id,
            )
        finally:
            self._finish_request_lifecycle()

    def do_POST(self) -> None:  # noqa: N802
        request_id = self._request_id()
        request_path = self._normalized_path()
        self._begin_request_lifecycle(method="POST", request_path=request_path, request_id=request_id)

        try:
            self._cors_response_headers = None

            if _is_external_direct_login_path(request_path):
                self._send_external_direct_login_disabled(
                    request_id=request_id,
                    request_path=request_path,
                    method="POST",
                )
                return

            is_cancel_route = (
                request_path.startswith("/analyze/jobs/")
                and request_path.endswith("/cancel")
            )
            if request_path != "/analyze" and not is_cancel_route:
                self._send_json(
                    {"ok": False, "error": "not_found", "request_id": request_id},
                    status=HTTPStatus.NOT_FOUND,
                    request_id=request_id,
                )
                return

            cors_headers = self._cors_headers_for_analyze(include_preflight=False)
            if cors_headers is None:
                self._send_json(
                    {
                        "ok": False,
                        "error": "cors_origin_not_allowed",
                        "request_id": request_id,
                    },
                    status=HTTPStatus.FORBIDDEN,
                    request_id=request_id,
                )
                return
            self._cors_response_headers = cors_headers

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
                if length < 0:
                    raise ValueError("invalid content length")

                if length == 0 and not is_cancel_route:
                    raise ValueError("empty body")

                raw = self.rfile.read(length) if length > 0 else b""
                if raw:
                    try:
                        decoded_body = raw.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise ValueError("body must be valid utf-8 json") from exc
                    data = json.loads(decoded_body)
                else:
                    data = {}

                if not isinstance(data, dict):
                    raise ValueError("json body must be an object")

                session_id = str(getattr(self, "_request_lifecycle_session_id", "") or "")

                if is_cancel_route:
                    job_id = request_path.removeprefix("/analyze/jobs/").removesuffix("/cancel").strip("/")
                    if not job_id or "/" in job_id:
                        self._send_json(
                            {
                                "ok": False,
                                "error": "not_found",
                                "request_id": request_id,
                            },
                            status=HTTPStatus.NOT_FOUND,
                            request_id=request_id,
                        )
                        return

                    cancel_reason = str(data.get("reason") or "cancel_requested").strip() or "cancel_requested"
                    canceled_by = str(data.get("canceled_by") or "user").strip() or "user"

                    _ensure_async_runtime_started()

                    try:
                        cancel_outcome = _ASYNC_JOB_STORE.request_cancel(
                            job_id=job_id,
                            canceled_by=canceled_by,
                            cancel_reason=cancel_reason,
                            actor_type="user",
                        )
                    except KeyError:
                        self._send_json(
                            {
                                "ok": False,
                                "error": "not_found",
                                "message": "unknown job_id",
                                "request_id": request_id,
                            },
                            status=HTTPStatus.NOT_FOUND,
                            request_id=request_id,
                        )
                        return

                    current_job = _ASYNC_JOB_STORE.get_job(job_id) or cancel_outcome.get("job") or {}
                    current_status = str(current_job.get("status") or "")
                    accepted = current_status in {"running", "partial", "queued", "canceled"}

                    if current_status in {"running", "partial"}:
                        _ASYNC_JOB_RUNTIME.enqueue(job_id)

                    status_code = HTTPStatus.ACCEPTED if current_status in {"running", "partial"} else HTTPStatus.OK
                    self._send_json(
                        {
                            "ok": True,
                            "accepted": accepted,
                            "job": _project_async_job_status(current_job, include_events=True),
                            "request_id": request_id,
                        },
                        status=status_code,
                        request_id=request_id,
                        extra_headers={"Cache-Control": "no-store"},
                    )
                    return

                def _emit_upstream_for_request(*, event: str, level: str = "info", **fields: Any) -> None:
                    _emit_structured_log(
                        event=event,
                        level=level,
                        trace_id=request_id,
                        request_id=request_id,
                        session_id=session_id,
                        route=request_path,
                        method="POST",
                        **fields,
                    )

                query, coordinate_context = _extract_query_and_coordinate_context(
                    data,
                    upstream_log_emitter=_emit_upstream_for_request,
                )

                mode = str(data.get("intelligence_mode", "basic")).strip() or "basic"
                mode = mode.lower()
                if mode not in SUPPORTED_INTELLIGENCE_MODES:
                    raise ValueError(
                        f"intelligence_mode must be one of {sorted(SUPPORTED_INTELLIGENCE_MODES)}"
                    )

                # Forward-Compatibility: optionaler, additiver Namespace für spätere
                # Request-Erweiterungen (z. B. Deep-Mode) ohne Breaking Changes.
                request_options = _extract_request_options(data)
                _reject_legacy_options(request_options)
                response_mode = _extract_response_mode(request_options)

                async_mode_requested = _extract_async_mode_request(request_options)

                # Optionales Preference-Profil für BL-20.4-Personalisierung.
                # Bei fehlendem Profil greifen explizite Defaults (Fallback-kompatibel).
                preferences_supplied = "preferences" in data and data.get("preferences") is not None
                preferences_profile = _extract_preferences(data)

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

                if async_mode_requested:
                    _ensure_async_runtime_started()
                    created_job = _ASYNC_JOB_STORE.create_job(
                        request_payload=data,
                        request_id=request_id,
                        query=query,
                        intelligence_mode=mode,
                    )
                    created_job_id = str(created_job.get("job_id") or "")
                    if created_job_id:
                        _ASYNC_JOB_RUNTIME.enqueue(created_job_id)

                    self._send_json(
                        {
                            "ok": True,
                            "accepted": True,
                            "job": _project_async_job_status(created_job, include_events=True),
                            "request_id": request_id,
                        },
                        status=HTTPStatus.ACCEPTED,
                        request_id=request_id,
                        extra_headers={"Cache-Control": "no-store"},
                    )
                    return

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
                        _apply_deep_mode_runtime_status(
                            stub_report,
                            options=request_options,
                            intelligence_mode=mode,
                            timeout_seconds=timeout,
                            request_id=request_id,
                            session_id=session_id,
                        )
                        self._send_json(
                            {
                                "ok": True,
                                "result": _grouped_api_result(
                                    stub_report,
                                    response_mode=response_mode,
                                ),
                                "request_id": request_id,
                            },
                            request_id=request_id,
                        )
                        return

                report = build_report(
                    query,
                    include_osm=True,
                    candidate_limit=8,
                    candidate_preview=3,
                    timeout=timeout,
                    retries=2,
                    backoff_seconds=0.6,
                    intelligence_mode=mode,
                    upstream_log_emitter=_emit_upstream_for_request,
                    trace_id=request_id,
                    request_id=request_id,
                    session_id=session_id,
                )
                _apply_personalized_suitability_scores(
                    report,
                    preferences_profile,
                    preferences_supplied=preferences_supplied,
                )
                if coordinate_context:
                    _attach_coordinate_resolution_context(report, coordinate_context)
                _apply_deep_mode_runtime_status(
                    report,
                    options=request_options,
                    intelligence_mode=mode,
                    timeout_seconds=timeout,
                    request_id=request_id,
                    session_id=session_id,
                )
                self._send_json(
                    {
                        "ok": True,
                        "result": _grouped_api_result(
                            report,
                            response_mode=response_mode,
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

        finally:
            self._finish_request_lifecycle()
    def do_OPTIONS(self) -> None:  # noqa: N802
        request_id = self._request_id()
        request_path = self._normalized_path()
        self._begin_request_lifecycle(method="OPTIONS", request_path=request_path, request_id=request_id)

        try:
            if _is_external_direct_login_path(request_path):
                self._send_external_direct_login_disabled(
                    request_id=request_id,
                    request_path=request_path,
                    method="OPTIONS",
                )
                return

            is_cancel_route = (
                request_path.startswith("/analyze/jobs/")
                and request_path.endswith("/cancel")
            )
            if request_path not in {"/analyze", "/debug/trace"} and not is_cancel_route:
                self._send_json(
                    {"ok": False, "error": "not_found", "request_id": request_id},
                    status=HTTPStatus.NOT_FOUND,
                    request_id=request_id,
                )
                return

            if request_path == "/debug/trace":
                cors_headers = self._cors_headers_for_debug_trace(include_preflight=True)
            else:
                cors_headers = self._cors_headers_for_analyze(include_preflight=True)
            if cors_headers is None:
                self._send_json(
                    {
                        "ok": False,
                        "error": "cors_origin_not_allowed",
                        "request_id": request_id,
                    },
                    status=HTTPStatus.FORBIDDEN,
                    request_id=request_id,
                )
                return

            self._capture_response_error(payload=None, status=int(HTTPStatus.NO_CONTENT))
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("X-Request-Id", request_id)
            self.send_header("Content-Length", "0")
            for key, value in cors_headers.items():
                self.send_header(key, value)
            self.end_headers()
        finally:
            self._finish_request_lifecycle()


def _resolve_port() -> int:
    """Liest die Service-Port-Konfiguration robust aus ENV.

    Kompatibilität: `PORT` bleibt primär, `WEB_PORT` dient als Fallback
    (z. B. für lokale Wrapper/Runner).
    """

    port_raw = os.getenv("PORT")
    if port_raw is None or not str(port_raw).strip():
        port_raw = os.getenv("WEB_PORT", "8080")
    return int(str(port_raw).strip())


def _env_flag_is_enabled(raw_value: Any) -> bool:
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_tls_settings() -> dict[str, Any] | None:
    """Liest optionale TLS-Konfiguration für Dev-Setups.

    TLS ist aktiv, wenn beide Variablen gesetzt sind:
    - TLS_CERT_FILE
    - TLS_KEY_FILE

    Optional kann parallel ein HTTP->HTTPS-Redirect-Listener aktiviert werden:
    - TLS_ENABLE_HTTP_REDIRECT=1
    - TLS_REDIRECT_HTTP_PORT=<port>
    - TLS_REDIRECT_HOST=<optional host override>
    """

    cert_file = os.getenv("TLS_CERT_FILE", "").strip()
    key_file = os.getenv("TLS_KEY_FILE", "").strip()
    redirect_enabled = _env_flag_is_enabled(os.getenv("TLS_ENABLE_HTTP_REDIRECT", "0"))
    redirect_port_raw = os.getenv("TLS_REDIRECT_HTTP_PORT", "8080").strip() or "8080"
    redirect_host = os.getenv("TLS_REDIRECT_HOST", "").strip()

    if bool(cert_file) ^ bool(key_file):
        raise ValueError("TLS_CERT_FILE and TLS_KEY_FILE must be set together")

    if not cert_file:
        if redirect_enabled:
            raise ValueError(
                "TLS_ENABLE_HTTP_REDIRECT requires TLS_CERT_FILE and TLS_KEY_FILE"
            )
        return None

    if not os.path.isfile(cert_file):
        raise ValueError(f"TLS_CERT_FILE does not exist: {cert_file}")
    if not os.path.isfile(key_file):
        raise ValueError(f"TLS_KEY_FILE does not exist: {key_file}")

    redirect_http_port: int | None = None
    if redirect_enabled:
        try:
            redirect_http_port = int(redirect_port_raw)
        except ValueError as exc:
            raise ValueError(
                "TLS_REDIRECT_HTTP_PORT must be a valid TCP port (1-65535)"
            ) from exc
        if not 1 <= redirect_http_port <= 65535:
            raise ValueError("TLS_REDIRECT_HTTP_PORT must be within 1..65535")

    return {
        "cert_file": cert_file,
        "key_file": key_file,
        "redirect_enabled": redirect_enabled,
        "redirect_http_port": redirect_http_port,
        "redirect_host": redirect_host,
    }


def _extract_host_without_port(host_header: str) -> str:
    value = str(host_header or "").strip()
    if not value:
        return ""

    if value.startswith("["):
        closing = value.find("]")
        if closing != -1:
            return value[: closing + 1]

    if ":" in value:
        return value.rsplit(":", 1)[0]
    return value


def _build_https_redirect_location(
    request_path: str,
    *,
    host_header: str,
    https_port: int,
    explicit_host: str = "",
) -> str:
    normalized_path = str(request_path or "/")
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"

    target_host = explicit_host.strip() or _extract_host_without_port(host_header)
    if not target_host:
        target_host = "localhost"

    authority = target_host if https_port == 443 else f"{target_host}:{https_port}"
    return f"https://{authority}{normalized_path}"


class RedirectToHttpsHandler(BaseHTTPRequestHandler):
    server_version = "geo-ranking-ch-redirect/0.1"

    def _send_redirect(self) -> None:
        https_port = int(getattr(self.server, "redirect_https_port", 443))
        explicit_host = str(getattr(self.server, "redirect_https_host", "") or "")
        location = _build_https_redirect_location(
            self.path,
            host_header=self.headers.get("Host", ""),
            https_port=https_port,
            explicit_host=explicit_host,
        )
        self.send_response(HTTPStatus.PERMANENT_REDIRECT)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._send_redirect()

    def do_POST(self) -> None:  # noqa: N802
        self._send_redirect()

    def do_PUT(self) -> None:  # noqa: N802
        self._send_redirect()

    def do_PATCH(self) -> None:  # noqa: N802
        self._send_redirect()

    def do_DELETE(self) -> None:  # noqa: N802
        self._send_redirect()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_redirect()

    def do_HEAD(self) -> None:  # noqa: N802
        self._send_redirect()


def _build_tls_context(*, cert_file: str, key_file: str) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    return context


def _start_http_redirect_server(
    *,
    host: str,
    http_port: int,
    https_port: int,
    https_host_override: str = "",
) -> ThreadingHTTPServer:
    redirect_server = ThreadingHTTPServer((host, http_port), RedirectToHttpsHandler)
    setattr(redirect_server, "redirect_https_port", https_port)
    setattr(redirect_server, "redirect_https_host", https_host_override)

    thread = threading.Thread(target=redirect_server.serve_forever, daemon=True)
    thread.start()
    return redirect_server


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = _resolve_port()
    tls_settings = _resolve_tls_settings()

    httpd = ThreadingHTTPServer((host, port), Handler)
    scheme = "http"

    if tls_settings:
        tls_context = _build_tls_context(
            cert_file=str(tls_settings["cert_file"]),
            key_file=str(tls_settings["key_file"]),
        )
        httpd.socket = tls_context.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"

        if tls_settings.get("redirect_enabled"):
            redirect_server = _start_http_redirect_server(
                host=host,
                http_port=int(tls_settings["redirect_http_port"]),
                https_port=port,
                https_host_override=str(tls_settings.get("redirect_host") or ""),
            )
            setattr(httpd, "redirect_server", redirect_server)
            _emit_structured_log(
                event="service.redirect_listener.enabled",
                level="info",
                component="api.web_service",
                direction="internal",
                status="enabled",
                redirect_from=f"http://{host}:{tls_settings['redirect_http_port']}",
                redirect_to=f"https://{host}:{port}",
            )
            print(
                "geo-ranking-ch redirect listener active on "
                f"http://{host}:{tls_settings['redirect_http_port']} -> https://{host}:{port}"
            )

    _ensure_async_runtime_started()

    _emit_structured_log(
        event="service.startup",
        level="info",
        component="api.web_service",
        direction="internal",
        status="listening",
        listen_url=f"{scheme}://{host}:{port}",
    )
    print(f"geo-ranking-ch web service listening on {scheme}://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
