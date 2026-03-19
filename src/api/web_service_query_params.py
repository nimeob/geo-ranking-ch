from __future__ import annotations


def _normalize_optional_text(raw_value: str | None) -> str:
    return str(raw_value or "").strip()


def _resolve_bounded_positive_limit(raw_value: str | None, *, default: int, maximum: int) -> int:
    normalized = _normalize_optional_text(raw_value)
    if not normalized:
        return default
    try:
        parsed = int(normalized)
    except ValueError as exc:
        raise ValueError("limit must be an integer >= 1") from exc
    if parsed < 1:
        raise ValueError("limit must be an integer >= 1")
    return min(parsed, maximum)


def _resolve_result_projection_mode(raw_value: str | None) -> str:
    mode = _normalize_optional_text(raw_value or "latest").lower() or "latest"
    if mode not in {"latest", "requested"}:
        raise ValueError("view must be one of ['latest', 'requested']")
    return mode


def _resolve_notification_channel(raw_value: str | None) -> str | None:
    normalized = _normalize_optional_text(raw_value).lower()
    if not normalized:
        return None
    if normalized not in {"in_app", "email", "webhook"}:
        raise ValueError("channel must be one of ['in_app', 'email', 'webhook']")
    return normalized


def _resolve_notification_limit(raw_value: str | None) -> int:
    return _resolve_bounded_positive_limit(raw_value, default=50, maximum=200)


def _resolve_history_limit(raw_value: str | None) -> int:
    return _resolve_bounded_positive_limit(raw_value, default=50, maximum=200)


def _resolve_history_offset(raw_value: str | None) -> int:
    normalized = _normalize_optional_text(raw_value)
    if not normalized:
        return 0
    try:
        parsed = int(normalized)
    except ValueError as exc:
        raise ValueError("offset must be a non-negative integer") from exc
    if parsed < 0:
        raise ValueError("offset must be a non-negative integer")
    return parsed
