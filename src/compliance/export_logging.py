"""Export logging helpers for Minimum-Compliance-Set controls.

This module standardizes export audit entries with the mandatory fields
`actor` (wer), `exported_at_utc` (wann) and `channel` (Kanal).
Entries are persisted as JSONL so controls can evaluate exports with simple
CLI tooling (`jq`, `python`, SIEM ingestion).
"""

from __future__ import annotations

from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
from typing import Any, Mapping


_EXPORT_LOG_PATH_ENV = "COMPLIANCE_EXPORT_LOG_PATH"
_EXPORT_ACTOR_ENV = "COMPLIANCE_EXPORT_ACTOR"
_DEFAULT_EVENT_NAME = "compliance.export.logged"
_DEFAULT_LOG_REL_PATH = Path("artifacts/compliance/export/export_log_v1.jsonl")
_REPO_ROOT = Path(__file__).resolve().parents[2]
_VALID_STATUSES = {"ok", "partial", "error"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_non_empty(value: str, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _detect_actor() -> str:
    for env_name in (_EXPORT_ACTOR_ENV, "EXPORT_ACTOR", "GITHUB_ACTOR", "USER", "USERNAME"):
        raw = str(os.getenv(env_name, "")).strip()
        if raw:
            return raw

    try:
        fallback = getpass.getuser().strip()
    except Exception:
        fallback = ""
    return fallback or "unknown"


def _resolve_log_path(log_path: str | Path | None = None) -> Path:
    if log_path is not None and str(log_path).strip():
        path = Path(log_path)
    else:
        raw = str(os.getenv(_EXPORT_LOG_PATH_ENV, "")).strip()
        path = Path(raw) if raw else _DEFAULT_LOG_REL_PATH

    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    return path


def build_export_log_entry(
    *,
    channel: str,
    artifact_path: str,
    export_kind: str,
    row_count: int,
    error_count: int = 0,
    status: str = "ok",
    actor: str | None = None,
    exported_at_utc: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one normalized export log entry (schema v1)."""

    normalized_channel = _require_non_empty(channel, field_name="channel")
    normalized_artifact_path = _require_non_empty(artifact_path, field_name="artifact_path")
    normalized_kind = _require_non_empty(export_kind, field_name="export_kind")
    normalized_actor = _require_non_empty(actor or _detect_actor(), field_name="actor")

    row_count_normalized = max(0, int(row_count))
    error_count_normalized = max(0, int(error_count))

    normalized_status = str(status or "ok").strip().lower() or "ok"
    if normalized_status not in _VALID_STATUSES:
        raise ValueError("status must be one of: ok, partial, error")

    return {
        "version": 1,
        "event": _DEFAULT_EVENT_NAME,
        "control": "bl342-export-logging-v1",
        "actor": normalized_actor,
        "channel": normalized_channel,
        "exported_at_utc": (exported_at_utc or _utc_now_iso()),
        "artifact_path": normalized_artifact_path,
        "export_kind": normalized_kind,
        "row_count": row_count_normalized,
        "error_count": error_count_normalized,
        "status": normalized_status,
        "details": dict(details or {}),
    }


def record_export_log_entry(
    *,
    channel: str,
    artifact_path: str,
    export_kind: str,
    row_count: int,
    error_count: int = 0,
    status: str = "ok",
    actor: str | None = None,
    exported_at_utc: str | None = None,
    details: Mapping[str, Any] | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist one export log entry to JSONL and return the serialized payload."""

    payload = build_export_log_entry(
        channel=channel,
        artifact_path=artifact_path,
        export_kind=export_kind,
        row_count=row_count,
        error_count=error_count,
        status=status,
        actor=actor,
        exported_at_utc=exported_at_utc,
        details=details,
    )

    target_path = _resolve_log_path(log_path=log_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    return payload
