"""Persistenter Async-Job-Store für Analyze-Langläufer.

Der Store bleibt bewusst leichtgewichtig (JSON-Datei + atomische Writes), damit
Async-Pfade ohne externe Infrastruktur testbar bleiben.
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
from typing import Any, Iterable


_SCHEMA_VERSION = 2
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


def _as_retry_hint(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


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

        jobs = migrated["jobs"]
        if isinstance(jobs, dict):
            for job_id, raw_job in list(jobs.items()):
                if not isinstance(raw_job, dict):
                    jobs[job_id] = {}
                    raw_job = jobs[job_id]

                now = _utc_now_iso()
                raw_job.setdefault("job_id", str(job_id))
                raw_job.setdefault("org_id", "default-org")
                raw_job.setdefault("status", "queued")
                raw_job.setdefault("request_payload_hash", "")
                raw_job.setdefault("request_payload_ref", f"inline:{job_id}")
                raw_job.setdefault("request_payload_json", {})
                raw_job.setdefault("query", "")
                raw_job.setdefault("intelligence_mode", "basic")
                raw_job.setdefault("progress_percent", 0)
                raw_job.setdefault("partial_count", 0)
                raw_job.setdefault("error_count", 0)
                raw_job.setdefault("result_id", None)
                raw_job.setdefault("error_code", None)
                raw_job.setdefault("error_message", None)
                raw_job.setdefault("retryable", None)
                raw_job.setdefault("retry_hint", None)
                raw_job.setdefault("cancel_requested_at", None)
                raw_job.setdefault("canceled_at", None)
                raw_job.setdefault("canceled_by", None)
                raw_job.setdefault("cancel_reason", None)
                raw_job.setdefault("queued_at", now)
                raw_job.setdefault("started_at", None)
                raw_job.setdefault("finished_at", None)
                raw_job.setdefault("updated_at", now)

        results = migrated["results"]
        if isinstance(results, dict):
            # Ergebnis-Sequenzen pro Job stabilisieren (backfill für alte Skeleton-Daten).
            results_by_job: dict[str, list[dict[str, Any]]] = {}
            for result_id, raw_result in results.items():
                if not isinstance(raw_result, dict):
                    continue
                raw_result.setdefault("result_id", str(result_id))
                raw_result.setdefault("result_kind", "final")
                raw_result.setdefault("schema_version", "v1")
                raw_result.setdefault("created_at", _utc_now_iso())
                raw_result.setdefault("summary_json", {})
                raw_result.setdefault("result_payload", {})
                job_id = str(raw_result.get("job_id") or "")
                if not job_id:
                    continue
                results_by_job.setdefault(job_id, []).append(raw_result)

            for rows in results_by_job.values():
                rows.sort(key=lambda item: str(item.get("created_at") or ""))
                for index, row in enumerate(rows, start=1):
                    seq_raw = row.get("result_seq")
                    if isinstance(seq_raw, int) and seq_raw > 0:
                        continue
                    row["result_seq"] = index

        migrated["schema_version"] = _SCHEMA_VERSION
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

    @staticmethod
    def _default_job_record(
        *,
        job_id: str,
        request_payload: dict[str, Any],
        query: str,
        intelligence_mode: str,
        org_id: str,
    ) -> dict[str, Any]:
        now = _utc_now_iso()
        payload_copy = deepcopy(request_payload)
        return {
            "job_id": job_id,
            "org_id": org_id,
            "status": "queued",
            "request_payload_hash": _canonical_payload_hash(payload_copy),
            "request_payload_ref": f"inline:{job_id}",
            "request_payload_json": payload_copy,
            "query": query,
            "intelligence_mode": intelligence_mode,
            "progress_percent": 0,
            "partial_count": 0,
            "error_count": 0,
            "result_id": None,
            "error_code": None,
            "error_message": None,
            "retryable": None,
            "retry_hint": None,
            "cancel_requested_at": None,
            "canceled_at": None,
            "canceled_by": None,
            "cancel_reason": None,
            "queued_at": now,
            "started_at": None,
            "finished_at": None,
            "updated_at": now,
        }

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
            job = self._default_job_record(
                job_id=job_id,
                request_payload=request_payload,
                query=query,
                intelligence_mode=intelligence_mode,
                org_id=org_id,
            )
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
        retryable: bool | None = None,
        retry_hint: str | None = None,
        canceled_by: str | None = None,
        cancel_reason: str | None = None,
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

            if to_status == "partial":
                job["partial_count"] = int(job.get("partial_count", 0) or 0) + 1

            if to_status in _TERMINAL_STATES:
                job["finished_at"] = now

            if to_status == "failed":
                job["error_count"] = int(job.get("error_count", 0) or 0) + 1
                job["error_code"] = str(error_code or "runtime_error")
                job["error_message"] = str(error_message or "async job failed")
                job["retryable"] = bool(True if retryable is None else retryable)
                job["retry_hint"] = _as_retry_hint(retry_hint) or "retry_with_backoff"
            elif to_status != "partial":
                job["error_code"] = None
                job["error_message"] = None
                job["retryable"] = None
                job["retry_hint"] = None

            if to_status == "canceled":
                job["canceled_at"] = now
                job["canceled_by"] = str(canceled_by or job.get("canceled_by") or "user")
                job["cancel_reason"] = str(
                    cancel_reason or job.get("cancel_reason") or "cancel_requested"
                )

            if result_id is not None:
                job["result_id"] = result_id

            job["status"] = to_status
            job["updated_at"] = now

            payload = {
                "status": to_status,
                "progress_percent": job.get("progress_percent", 0),
                "result_id": job.get("result_id"),
                "error_code": job.get("error_code"),
                "retry_hint": job.get("retry_hint"),
                "cancel_requested_at": job.get("cancel_requested_at"),
            }
            self._append_event_locked(
                job_id=job_id,
                event_type=f"job.{to_status}",
                actor_type=actor_type,
                payload=payload,
            )
            self._persist_state_atomic(self._state)
            return deepcopy(job)

    def request_cancel(
        self,
        *,
        job_id: str,
        canceled_by: str = "user",
        cancel_reason: str = "cancel_requested",
        actor_type: str = "user",
    ) -> dict[str, Any]:
        """Setzt einen idempotenten Cancel-Request.

        - queued: sofortiger Übergang nach `canceled`
        - running/partial: markiert `cancel_requested_at`, Worker finalisiert terminal
        - terminale States bleiben unverändert
        """
        with self._lock:
            job = self._state["jobs"].get(job_id)
            if job is None:
                raise KeyError(f"unknown job_id: {job_id}")

            status = str(job.get("status") or "queued")
            if status in _TERMINAL_STATES:
                return {
                    "job": deepcopy(job),
                    "cancel_requested": bool(job.get("cancel_requested_at")),
                    "cancel_applied": status == "canceled",
                    "terminal": True,
                }

            now = _utc_now_iso()
            cancel_requested = bool(job.get("cancel_requested_at"))
            if not cancel_requested:
                job["cancel_requested_at"] = now
                job["canceled_by"] = str(canceled_by or "user")
                job["cancel_reason"] = str(cancel_reason or "cancel_requested")
                job["updated_at"] = now
                self._append_event_locked(
                    job_id=job_id,
                    event_type="job.cancel_requested",
                    actor_type=actor_type,
                    payload={
                        "status": status,
                        "cancel_requested_at": now,
                        "canceled_by": job.get("canceled_by"),
                        "cancel_reason": job.get("cancel_reason"),
                    },
                )

            cancel_applied = False
            if status == "queued":
                # queued -> canceled darf direkt und idempotent erfolgen
                job["status"] = "canceled"
                job["finished_at"] = now
                job["canceled_at"] = now
                job["updated_at"] = now
                self._append_event_locked(
                    job_id=job_id,
                    event_type="job.canceled",
                    actor_type=actor_type,
                    payload={
                        "status": "canceled",
                        "progress_percent": job.get("progress_percent", 0),
                        "cancel_requested_at": job.get("cancel_requested_at"),
                    },
                )
                cancel_applied = True

            self._persist_state_atomic(self._state)
            return {
                "job": deepcopy(job),
                "cancel_requested": True,
                "cancel_applied": cancel_applied,
                "terminal": bool(cancel_applied),
            }

    def consume_cancel_request(
        self,
        *,
        job_id: str,
        actor_type: str = "worker",
    ) -> dict[str, Any] | None:
        """Wendet einen offenen Cancel-Request atomar auf den Job an.

        Gibt den aktualisierten Job zurück, wenn ein Übergang nach `canceled`
        erfolgt ist, ansonsten ``None``.
        """
        with self._lock:
            job = self._state["jobs"].get(job_id)
            if job is None:
                return None

            status = str(job.get("status") or "queued")
            if status in _TERMINAL_STATES:
                return deepcopy(job)
            if not job.get("cancel_requested_at"):
                return None

            if "canceled" not in _ALLOWED_TRANSITIONS.get(status, set()):
                return None

            now = _utc_now_iso()
            job["status"] = "canceled"
            job["finished_at"] = now
            job["canceled_at"] = now
            job["canceled_by"] = str(job.get("canceled_by") or "worker")
            job["cancel_reason"] = str(job.get("cancel_reason") or "cancel_requested")
            job["updated_at"] = now
            self._append_event_locked(
                job_id=job_id,
                event_type="job.canceled",
                actor_type=actor_type,
                payload={
                    "status": "canceled",
                    "progress_percent": job.get("progress_percent", 0),
                    "cancel_requested_at": job.get("cancel_requested_at"),
                },
            )
            self._persist_state_atomic(self._state)
            return deepcopy(job)

    def list_job_ids(self, *, statuses: Iterable[str] | None = None) -> list[str]:
        with self._lock:
            allowed_statuses = {str(status) for status in statuses} if statuses is not None else None
            rows: list[tuple[str, str]] = []
            for job_id, row in self._state["jobs"].items():
                if not isinstance(row, dict):
                    continue
                status = str(row.get("status") or "")
                if allowed_statuses is not None and status not in allowed_statuses:
                    continue
                queued_at = str(row.get("queued_at") or "")
                rows.append((queued_at, str(job_id)))
            rows.sort(key=lambda item: (item[0], item[1]))
            return [job_id for _, job_id in rows]

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

            normalized_kind = str(result_kind or "").strip().lower()
            if normalized_kind not in {"partial", "final"}:
                raise ValueError("result_kind must be one of {'partial', 'final'}")

            existing_for_job = [
                row
                for row in self._state["results"].values()
                if isinstance(row, dict) and str(row.get("job_id")) == job_id
            ]
            if normalized_kind == "final":
                if any(str(row.get("result_kind")) == "final" for row in existing_for_job):
                    raise ValueError("final result already exists for job")

            next_seq = 1
            if existing_for_job:
                max_seq = max(
                    int(row.get("result_seq", 0) or 0)
                    for row in existing_for_job
                    if isinstance(row.get("result_seq", 0), int)
                )
                next_seq = max_seq + 1

            result_id = str(uuid.uuid4())
            result_record = {
                "result_id": result_id,
                "job_id": job_id,
                "result_kind": normalized_kind,
                "result_seq": next_seq,
                "schema_version": schema_version,
                "result_payload": deepcopy(result_payload),
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

    def list_results(self, job_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = [
                deepcopy(row)
                for row in self._state["results"].values()
                if isinstance(row, dict) and str(row.get("job_id")) == str(job_id)
            ]
            rows.sort(key=lambda row: int(row.get("result_seq", 0) or 0))
            return rows

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        with self._lock:
            events = self._state["events"].get(job_id, [])
            return deepcopy(events)
