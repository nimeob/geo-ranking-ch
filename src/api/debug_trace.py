"""Helpers for dev-only request trace lookups by ``request_id``.

The module reads structured JSONL log events and projects them into a compact,
redacted timeline that can be consumed by a debug UI.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.shared.structured_logging import redact_mapping

_ALLOWED_TIMELINE_EVENTS = {
    "api.request.start",
    "api.request.end",
    "api.upstream.request.start",
    "api.upstream.request.end",
    "api.upstream.response.summary",
}

_CORE_FIELDS = {
    "ts",
    "level",
    "event",
    "trace_id",
    "request_id",
    "session_id",
}

_DEFAULT_LOOKBACK_SECONDS = 48 * 60 * 60
_DEFAULT_MAX_EVENTS = 200
_HARD_MAX_EVENTS = 500


def normalize_positive_int(
    raw_value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Return a bounded positive integer with permissive parsing."""
    if raw_value is None:
        return default

    try:
        parsed = int(str(raw_value).strip())
    except Exception:
        return default

    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def normalize_lookback_seconds(raw_value: Any) -> int:
    """Parse lookback seconds with safe defaults and limits."""
    return normalize_positive_int(
        raw_value,
        default=_DEFAULT_LOOKBACK_SECONDS,
        minimum=60,
        maximum=7 * 24 * 60 * 60,
    )


def normalize_max_events(raw_value: Any) -> int:
    """Parse timeline max events with safe defaults and limits."""
    return normalize_positive_int(
        raw_value,
        default=_DEFAULT_MAX_EVENTS,
        minimum=1,
        maximum=_HARD_MAX_EVENTS,
    )


def normalize_request_id(raw_value: Any) -> str:
    """Normalize request id for lookups; invalid values yield an empty string."""
    candidate = str(raw_value or "").strip()
    if not candidate:
        return ""
    if len(candidate) > 128:
        return ""
    if any(character.isspace() for character in candidate):
        return ""
    if "," in candidate or ";" in candidate:
        return ""
    try:
        candidate.encode("ascii")
    except UnicodeEncodeError:
        return ""
    return candidate


def _parse_timestamp(raw_value: Any) -> datetime | None:
    text = str(raw_value or "").strip()
    if not text:
        return None

    normalized = text
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _event_phase(event_name: str) -> str:
    if event_name == "api.request.start":
        return "start"
    if event_name == "api.request.end":
        return "end"
    return "upstream"


def _summarize_event(event_name: str, payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "").strip()
    status_code = payload.get("status_code")
    source = str(payload.get("source") or "").strip()

    if event_name == "api.request.start":
        route = str(payload.get("route") or "").strip() or "/analyze"
        method = str(payload.get("method") or "").strip().upper() or "POST"
        return f"{method} {route} started"

    if event_name == "api.request.end":
        if isinstance(status_code, int):
            return f"request finished ({status or 'unknown'}, status {status_code})"
        return f"request finished ({status or 'unknown'})"

    if event_name == "api.upstream.request.start":
        return f"upstream request started ({source or 'unknown source'})"

    if event_name == "api.upstream.request.end":
        if isinstance(status_code, int):
            return f"upstream request ended ({status or 'unknown'}, status {status_code})"
        return f"upstream request ended ({status or 'unknown'})"

    if event_name == "api.upstream.response.summary":
        records = payload.get("records")
        if isinstance(records, int):
            return f"upstream response summary ({records} records)"
        return "upstream response summary"

    return event_name


def _extract_details(payload: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _CORE_FIELDS:
            continue
        details[key] = value
    return redact_mapping(details)


def _normalize_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    event_name = str(payload.get("event") or "").strip()
    if event_name not in _ALLOWED_TIMELINE_EVENTS:
        return None

    details = _extract_details(payload)
    event_ts = str(payload.get("ts") or "").strip()

    normalized: dict[str, Any] = {
        "ts": event_ts,
        "event": event_name,
        "phase": _event_phase(event_name),
        "level": str(payload.get("level") or "info").strip().lower() or "info",
        "status": str(payload.get("status") or "").strip(),
        "summary": _summarize_event(event_name, payload),
        "details": details,
    }

    component = str(payload.get("component") or "").strip()
    if component:
        normalized["component"] = component

    direction = str(payload.get("direction") or "").strip()
    if direction:
        normalized["direction"] = direction

    return normalized


def build_trace_timeline(
    *,
    request_id: str,
    log_path: str,
    lookback_seconds: int,
    max_events: int,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build a redacted, chronological trace timeline for one request id."""
    normalized_request_id = normalize_request_id(request_id)
    if not normalized_request_id:
        return {
            "ok": False,
            "error": "invalid_request_id",
            "message": "request_id is missing or invalid",
        }

    normalized_path = str(log_path or "").strip()
    if not normalized_path:
        return {
            "ok": False,
            "error": "trace_source_unavailable",
            "message": "TRACE_DEBUG_LOG_PATH is not configured",
        }

    path = Path(normalized_path)
    if not path.exists() or not path.is_file():
        return {
            "ok": False,
            "error": "trace_source_unavailable",
            "message": f"trace source not found: {normalized_path}",
        }

    window_seconds = normalize_lookback_seconds(lookback_seconds)
    event_limit = normalize_max_events(max_events)
    current_time = now_utc or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(seconds=window_seconds)

    timeline_candidates: list[tuple[datetime, int, dict[str, Any]]] = []
    matched_outside_window = False
    matched_without_timestamp = False

    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue

                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(payload, dict):
                    continue

                if str(payload.get("request_id") or "").strip() != normalized_request_id:
                    continue

                normalized_event = _normalize_event(payload)
                if normalized_event is None:
                    continue

                parsed_ts = _parse_timestamp(payload.get("ts"))
                if parsed_ts is None:
                    matched_without_timestamp = True
                    parsed_ts = datetime.fromtimestamp(0, tz=timezone.utc)
                elif parsed_ts < cutoff:
                    matched_outside_window = True
                    continue

                timeline_candidates.append((parsed_ts, line_number, normalized_event))
    except OSError as exc:
        return {
            "ok": False,
            "error": "trace_source_unavailable",
            "message": f"trace source unreadable: {exc}",
        }

    timeline_candidates.sort(key=lambda item: (item[0], item[1]))
    limited_candidates = timeline_candidates[:event_limit]
    timeline = [entry for _, _, entry in limited_candidates]

    state = "ready"
    reason = ""
    if not timeline:
        state = "empty"
        if matched_outside_window:
            reason = "request_id_outside_window"
        else:
            reason = "request_id_unknown_or_no_events"

    return {
        "ok": True,
        "request_id": normalized_request_id,
        "state": state,
        "reason": reason,
        "found": bool(timeline),
        "events": timeline,
        "event_count": len(timeline),
        "window_seconds": window_seconds,
        "max_events": event_limit,
        "source": {
            "kind": "jsonl_file",
            "path": str(path),
        },
        "incomplete": matched_without_timestamp,
    }
