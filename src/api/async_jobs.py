"""Persistenter Async-Job-Store (v1) für den Analyze-Runtime-Skeleton.

Der Store ist bewusst leichtgewichtig (JSON-Datei + atomische Writes), damit
frühe Async-Pfade ohne zusätzliche Infrastruktur testbar sind.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SCHEMA_VERSION = 1
_DEFAULT_STORE_FILE = "runtime/async_jobs/store.v1.json"
_TERMINAL_STATES = {"completed", "failed", "canceled"}
_ALLOWED_TRANSITIONS = {
    "queued": {"running", "canceled"},
    "running": {"partial", "completed", "failed", "canceled"},
    "partial": {"partial", "completed", "failed", "canceled"},
    "completed": set(),
    "failed": set(),
    "canceled": set(),
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_payload_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


class AsyncJobStore:
    """File-backed Store für `jobs`, `job_events` und `job_results`."""

    def __init__(self, *, store_file: str | Path):
        self._store_file = Path(store_file)
        self._lock = threading.Lock()
        self._state = self._load_or_initialize_state()

    @classmethod
    def from_env(cls) -> "AsyncJobStore":
        return cls(store_file=os.getenv("ASYNC_JOBS_STORE_FILE", _DEFAULT_STORE_FILE))

    def _load_or_initialize_state(self) -> dict[str, Any]:
        if not self._store_file.exists():
            state = self._empty_state()
            self._persist_state_atomic(state)
            return state

        raw = self._store_file.read_text(encoding="utf-8").strip()
        if not raw:
            state = self._empty_state()
            self._persist_state_atomic(state)
            return state

        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError("async jobs store must contain a JSON object")

        migrated = self._migrate_state(loaded)
        self._persist_state_atomic(migrated)
        return migrated

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "jobs": {},
            "results": {},
            "events": {},
        }

    def _migrate_state(self, state: dict[str, Any]) -> dict[str, Any]:
        migrated = deepcopy(state)

        schema_version = int(migrated.get("schema_version", 0) or 0)
        if schema_version < 1:
            migrated["schema_version"] = 1

        for key in ("jobs", "results", "events"):
            value = migrated.get(key)
            if not isinstance(value, dict):
                migrated[key] = {}

        return migrated

    def _persist_state_atomic(self, state: dict[str, Any]) -> None:
        self._store_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._store_file.with_suffix(f"{self._store_file.suffix}.tmp")
        tmp_path.write_text(
            json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp_path, self._store_file)

    def _append_event_locked(
        self,
        *,
        job_id: str,
        event_type: str,
        actor_type: str = "system",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        events_by_job = self._state["events"].setdefault(job_id, [])
        event_seq = len(events_by_job) + 1
        event = {
            "event_id": str(uuid.uuid4()),
            "job_id": job_id,
            "event_type": event_type,
            "event_seq": event_seq,
            "occurred_at": _utc_now_iso(),
            "actor_type": actor_type,
            "payload_json": payload or {},
        }
        events_by_job.append(event)
        return deepcopy(event)

    def create_job(
        self,
        *,
        request_payload: dict[str, Any],
        request_id: str,
        query: str,
        intelligence_mode: str,
        org_id: str = "default-org",
    ) -> dict[str, Any]:
        with self._lock:
            job_id = str(uuid.uuid4())
            now = _utc_now_iso()
            job = {
                "job_id": job_id,
                "org_id": org_id,
                "status": "queued",
                "request_payload_hash": _canonical_payload_hash(request_payload),
                "request_payload_ref": f"inline:{job_id}",
                "query": query,
                "intelligence_mode": intelligence_mode,
                "progress_percent": 0,
                "partial_count": 0,
                "error_count": 0,
                "result_id": None,
                "error_code": None,
                "error_message": None,
                "queued_at": now,
                "started_at": None,
                "finished_at": None,
                "updated_at": now,
            }
            self._state["jobs"][job_id] = job
            self._append_event_locked(
                job_id=job_id,
                event_type="job.queued",
                payload={"request_id": request_id, "status": "queued"},
            )
            self._persist_state_atomic(self._state)
            return deepcopy(job)

    def transition_job(
        self,
        *,
        job_id: str,
        to_status: str,
        progress_percent: int | None = None,
        result_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        actor_type: str = "system",
    ) -> dict[str, Any]:
        with self._lock:
            job = self._state["jobs"].get(job_id)
            if job is None:
                raise KeyError(f"unknown job_id: {job_id}")

            current_status = str(job.get("status", "queued"))
            if to_status not in _ALLOWED_TRANSITIONS.get(current_status, set()):
                raise ValueError(
                    f"invalid transition from {current_status} to {to_status}"
                )

            if progress_percent is not None:
                if not isinstance(progress_percent, int):
                    raise ValueError("progress_percent must be int")
                if progress_percent < 0 or progress_percent > 100:
                    raise ValueError("progress_percent must be within 0..100")
                existing_progress = int(job.get("progress_percent", 0) or 0)
                if progress_percent < existing_progress:
                    raise ValueError("progress_percent must be monotonic")
                job["progress_percent"] = progress_percent

            now = _utc_now_iso()
            if to_status == "running" and not job.get("started_at"):
                job["started_at"] = now

            if to_status in _TERMINAL_STATES:
                job["finished_at"] = now

            if to_status == "failed":
                job["error_count"] = int(job.get("error_count", 0) or 0) + 1
                job["error_code"] = error_code or "runtime_error"
                job["error_message"] = error_message or "async job failed"
            elif to_status != "partial":
                job["error_code"] = None
                job["error_message"] = None

            if result_id is not None:
                job["result_id"] = result_id

            job["status"] = to_status
            job["updated_at"] = now

            self._append_event_locked(
                job_id=job_id,
                event_type=f"job.{to_status}",
                actor_type=actor_type,
                payload={
                    "status": to_status,
                    "progress_percent": job.get("progress_percent", 0),
                    "result_id": job.get("result_id"),
                    "error_code": job.get("error_code"),
                },
            )
            self._persist_state_atomic(self._state)
            return deepcopy(job)

    def create_result(
        self,
        *,
        job_id: str,
        result_payload: dict[str, Any],
        result_kind: str = "final",
        schema_version: str = "v1",
    ) -> dict[str, Any]:
        with self._lock:
            job = self._state["jobs"].get(job_id)
            if job is None:
                raise KeyError(f"unknown job_id: {job_id}")

            result_id = str(uuid.uuid4())
            result_seq = 1
            result_record = {
                "result_id": result_id,
                "job_id": job_id,
                "result_kind": result_kind,
                "result_seq": result_seq,
                "schema_version": schema_version,
                "result_payload": result_payload,
                "summary_json": {
                    "status": str(job.get("status", "queued")),
                    "query": str(job.get("query", "")),
                    "intelligence_mode": str(job.get("intelligence_mode", "basic")),
                },
                "created_at": _utc_now_iso(),
            }
            self._state["results"][result_id] = result_record
            self._persist_state_atomic(self._state)
            return deepcopy(result_record)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._state["jobs"].get(job_id)
            return deepcopy(record) if record is not None else None

    def get_result(self, result_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._state["results"].get(result_id)
            return deepcopy(record) if record is not None else None

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        with self._lock:
            events = self._state["events"].get(job_id, [])
            return deepcopy(events)
