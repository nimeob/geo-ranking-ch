"""Structured JSON logging helpers for cross-component observability.

This module provides a small, dependency-free logging primitive used by API/UI
runtime code. It standardizes a minimal event envelope (`ts`, `level`, `event`,
`trace_id`, `request_id`, `session_id`) and applies best-effort redaction for
sensitive values before logs are emitted.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Mapping, TextIO

LOG_EVENT_SCHEMA_V1_REQUIRED_FIELDS = (
    "ts",
    "level",
    "event",
    "trace_id",
    "request_id",
    "session_id",
)

LOG_EVENT_SCHEMA_V1_RECOMMENDED_FIELDS = (
    "component",
    "direction",
    "status",
    "duration_ms",
)

# Key-based redaction rules.
#
# We keep two tiers:
# - exact keys: safe and targeted for PII-like request payload fields
# - marker substrings: broader for credential-ish headers and secrets
_SENSITIVE_KEYS_EXACT = frozenset(
    {
        # Address/query inputs (PII-ish).
        "query",
        "resolved_query",
        "matched_address",
        "street",
        "house_number",
        "postal_code",
        "postcode",
    }
)

_SENSITIVE_KEY_MARKERS = (
    "authorization",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "cookie",
    "set-cookie",
)

_BEARER_TOKEN_RE = re.compile(r"\bBearer\s+[^\s]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+\-])([A-Za-z0-9._%+\-]{0,63})@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b")


def utc_timestamp() -> str:
    """Return a UTC ISO8601 timestamp with trailing `Z`."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _looks_sensitive_key(key: str) -> bool:
    lowered = str(key or "").strip().lower()
    if lowered in _SENSITIVE_KEYS_EXACT:
        return True
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def _mask_email(value: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        first = match.group(1)
        domain = match.group(3)
        return f"{first}***@{domain}"

    return _EMAIL_RE.sub(_replace, value)


def redact_scalar(*, key: str, value: Any) -> Any:
    """Redact sensitive scalar values using key-based and pattern-based rules."""
    if value is None:
        return None

    if _looks_sensitive_key(key):
        return "[REDACTED]"

    if isinstance(value, str):
        sanitized = _BEARER_TOKEN_RE.sub("Bearer [REDACTED]", value)
        sanitized = _mask_email(sanitized)
        return sanitized

    return value


def redact_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a recursively redacted copy of a mapping payload.

    Policy: when a key is considered sensitive, we redact the *entire* value
    regardless of whether it is a scalar, list or nested mapping. This matches
    the logging schema contract ("fully masked") and prevents accidental leaks
    through structured sub-objects.
    """

    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if _looks_sensitive_key(str(key)):
            redacted[key] = "[REDACTED]"
            continue
        if isinstance(value, Mapping):
            redacted[key] = redact_mapping(value)
            continue
        if isinstance(value, list):
            redacted[key] = [
                redact_mapping(item)
                if isinstance(item, Mapping)
                else redact_scalar(key=str(key), value=item)
                for item in value
            ]
            continue
        redacted[key] = redact_scalar(key=str(key), value=value)
    return redacted


def redact_headers(headers: Mapping[str, Any]) -> dict[str, Any]:
    """Return a redacted copy of HTTP-style headers.

    This is an explicit convenience wrapper around ``redact_mapping`` so call
    sites can sanitize request/response headers without rebuilding redaction
    rules locally.
    """
    return {str(key): redact_scalar(key=str(key), value=value) for key, value in headers.items()}


def build_event(
    event: str,
    *,
    level: str = "info",
    trace_id: str = "",
    request_id: str = "",
    session_id: str = "",
    **fields: Any,
) -> dict[str, Any]:
    """Build a schema-conform structured event payload."""
    if not str(event or "").strip():
        raise ValueError("event must be a non-empty string")

    payload: dict[str, Any] = {
        "ts": utc_timestamp(),
        "level": str(level or "info").strip().lower() or "info",
        "event": str(event).strip(),
        "trace_id": str(trace_id or "").strip(),
        "request_id": str(request_id or "").strip(),
        "session_id": str(session_id or "").strip(),
    }
    payload.update(fields)

    # Ensure required keys stay present even if overridden through fields.
    for required_key in LOG_EVENT_SCHEMA_V1_REQUIRED_FIELDS:
        payload.setdefault(required_key, "")

    return payload


def emit_event(payload: Mapping[str, Any], *, stream: TextIO | None = None) -> dict[str, Any]:
    """Redact and emit one JSON log line to stdout (or a custom stream)."""
    target = stream or sys.stdout
    redacted_payload = redact_mapping(dict(payload))
    serialized = json.dumps(redacted_payload, ensure_ascii=False, sort_keys=True)
    target.write(serialized + "\n")
    target.flush()
    return redacted_payload
