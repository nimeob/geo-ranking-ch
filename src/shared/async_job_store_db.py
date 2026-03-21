"""DB-backed AsyncJobStore — Postgres implementation using psycopg2.

Provides the same public interface as ``AsyncJobStore`` (file-backed) in
``src/api/async_jobs.py``, but persists data in the Postgres schema defined
by migrations 002 + 003.

Usage (production)::

    from src.shared.async_job_store_db import DbAsyncJobStore
    store = DbAsyncJobStore.from_env()

Usage (test / custom conn)::

    store = DbAsyncJobStore(conn_factory=my_factory)

Environment variables (two supported patterns):

Pattern A — full URL (preferred):
    ASYNC_DB_URL   postgresql://user:pass@host:port/dbname
    DATABASE_URL   fallback when ASYNC_DB_URL is absent

Pattern B — individual components (ECS SecretsManager wiring):
    DB_HOST        Postgres host
    DB_PORT        Postgres port (default: 5432)
    DB_NAME        Database name (default: swisstopo)
    DB_USERNAME    Login user (default: swisstopo)
    DB_PASSWORD    Password — injected by ECS from Secrets Manager; never set in plaintext

Pattern B is used automatically when ASYNC_DB_URL and DATABASE_URL are both absent but
DB_HOST is present.  The resulting URL is built in-process; the password is consumed only
at connection time and is never logged or stored.

Issue: #839 (ASYNC-DB-0.wp2)
Issue: #867 (DEV-WIRE-0: ECS secrets wiring — component env var support)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

logger = logging.getLogger(__name__)

_TERMINAL_STATES = frozenset({"completed", "failed", "canceled"})
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued":    frozenset({"running", "canceled"}),
    "running":   frozenset({"partial", "completed", "failed", "canceled"}),
    "partial":   frozenset({"partial", "completed", "failed", "canceled"}),
    "completed": frozenset(),
    "failed":    frozenset(),
    "canceled":  frozenset(),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _row_to_dict(cursor: Any, row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a cursor row tuple to a dict using column descriptions."""
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))


def _parse_json_object(raw_value: Any) -> dict[str, Any]:
    """Best-effort parser for TEXT/JSON(B) payload columns.

    Returns an object dict or ``{}`` when parsing fails / payload is not an object.
    """
    if isinstance(raw_value, dict):
        return dict(raw_value)

    normalized_text = ""
    if isinstance(raw_value, (bytes, bytearray)):
        normalized_text = raw_value.decode("utf-8", errors="ignore").strip()
    elif isinstance(raw_value, str):
        normalized_text = raw_value.strip()

    if not normalized_text:
        return {}

    try:
        parsed = json.loads(normalized_text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}

    if isinstance(parsed, dict):
        return parsed
    return {}


def _hydrate_result_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize DB result rows to AsyncJobStore-compatible shape.

    DB rows contain ``summary_json`` (TEXT) but no dedicated ``result_payload``
    column. The API/UI path expects ``result_payload``; therefore we derive it from
    ``summary_json`` when absent.
    """
    if record is None:
        return None

    projected = dict(record)
    existing_payload = projected.get("result_payload")
    if isinstance(existing_payload, dict) and existing_payload:
        return projected

    projected["result_payload"] = _parse_json_object(projected.get("summary_json"))
    return projected


def _normalize_owner_org_id(raw_value: Any) -> str:
    value = str(raw_value or "").strip()
    return value or "default-org"


# ---------------------------------------------------------------------------
# DbAsyncJobStore
# ---------------------------------------------------------------------------

class DbAsyncJobStore:
    """Postgres-backed job store.

    Thread-safe: a threading.Lock serialises write operations; reads use
    separate short-lived connections from the factory.
    """

    def __init__(self, *, conn_factory: Callable[[], Any]) -> None:
        self._conn_factory = conn_factory
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def _build_db_url(cls) -> str:
        """Resolve the Postgres connection URL from environment variables.

        Tries in order:
        1. ``ASYNC_DB_URL`` — explicit full URL (highest precedence)
        2. ``DATABASE_URL`` — common fallback URL
        3. Component vars — ``DB_HOST`` + ``DB_PORT`` + ``DB_NAME`` + ``DB_USERNAME``
           + ``DB_PASSWORD`` (ECS SecretsManager pattern)

        Raises ``RuntimeError`` when no usable configuration is found.
        """
        db_url = (os.getenv("ASYNC_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
        if db_url:
            return db_url

        # Pattern B: individual component env vars (ECS SecretsManager wiring)
        db_host = (os.getenv("DB_HOST") or "").strip()
        if not db_host:
            raise RuntimeError(
                "DbAsyncJobStore.from_env: neither ASYNC_DB_URL / DATABASE_URL nor "
                "DB_HOST is set. Configure one of the two patterns described in the "
                "module docstring."
            )
        db_port = (os.getenv("DB_PORT") or "5432").strip()
        db_name = (os.getenv("DB_NAME") or "swisstopo").strip()
        db_user = (os.getenv("DB_USERNAME") or "swisstopo").strip()
        db_pass = (os.getenv("DB_PASSWORD") or "").strip()

        # urllib.parse.quote is used so that special characters in the password
        # are safely percent-encoded in the URL.  The password itself is NOT
        # logged anywhere in this code path.
        import urllib.parse  # noqa: PLC0415

        encoded_pass = urllib.parse.quote(db_pass, safe="")
        return f"postgresql://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"

    @classmethod
    def from_env(cls) -> "DbAsyncJobStore":
        """Build store from environment variables.

        Supports both a full connection URL (``ASYNC_DB_URL`` / ``DATABASE_URL``) and
        individual component vars (``DB_HOST`` / ``DB_PORT`` / ``DB_NAME`` /
        ``DB_USERNAME`` / ``DB_PASSWORD``).  See module docstring for details.
        """
        db_url = cls._build_db_url()
        try:
            import psycopg2  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "psycopg2 is required for DbAsyncJobStore. "
                "Install it with: pip install psycopg2-binary"
            ) from exc

        def _factory() -> Any:
            conn = psycopg2.connect(db_url)
            conn.autocommit = False
            return conn

        return cls(conn_factory=_factory)

    # ------------------------------------------------------------------
    # Internal connection helpers
    # ------------------------------------------------------------------

    def _connect(self) -> Any:
        return self._conn_factory()

    # ------------------------------------------------------------------
    # create_job
    # ------------------------------------------------------------------

    def create_job(
        self,
        *,
        request_payload: dict[str, Any],
        request_id: str,
        query: str,
        intelligence_mode: str,
        org_id: str = "default-org",
        owner_user_id: str | None = None,
        owner_org_id: str | None = None,
    ) -> dict[str, Any]:
        """Insert a new queued job and its initial event; return the job dict."""
        job_id = str(uuid.uuid4())
        resolved_org_id = str(org_id or "default-org")
        resolved_owner_org = owner_org_id if owner_org_id is not None else resolved_org_id
        resolved_user_id = str(owner_user_id) if owner_user_id else None
        payload_hash = _canonical_payload_hash(request_payload)
        now = _utc_now_iso()

        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO jobs (
                        job_id, org_id, user_id, status,
                        request_payload_hash, query, intelligence_mode,
                        progress_percent, partial_count, error_count,
                        queued_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        job_id, resolved_org_id, resolved_user_id, "queued",
                        payload_hash, str(query or ""), str(intelligence_mode or "basic"),
                        0, 0, 0,
                        now, now,
                    ),
                )
                self._insert_event(
                    cur,
                    job_id=job_id,
                    event_type="job.queued",
                    event_seq=1,
                    occurred_at=now,
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        return {
            "job_id": job_id,
            "org_id": resolved_org_id,
            "owner_org_id": resolved_owner_org,
            "user_id": resolved_user_id,
            "owner_user_id": resolved_user_id,
            "status": "queued",
            "request_payload_hash": payload_hash,
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

    # ------------------------------------------------------------------
    # transition_job
    # ------------------------------------------------------------------

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
        """Transition a job's status; insert event; return updated job dict."""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()

                # Fetch current row (org_id guard always present)
                cur.execute(
                    "SELECT * FROM jobs WHERE job_id = %s",
                    (str(job_id),),
                )
                row = cur.fetchone()
                if row is None:
                    raise KeyError(f"unknown job_id: {job_id}")
                job = _row_to_dict(cur, row)

                current_status = str(job.get("status", "queued"))
                allowed = _ALLOWED_TRANSITIONS.get(current_status, frozenset())
                if to_status not in allowed:
                    raise ValueError(
                        f"invalid transition from {current_status!r} to {to_status!r}"
                    )

                now = _utc_now_iso()
                updates: dict[str, Any] = {"status": to_status, "updated_at": now}

                if progress_percent is not None:
                    if not isinstance(progress_percent, int):
                        raise ValueError("progress_percent must be int")
                    if not 0 <= progress_percent <= 100:
                        raise ValueError("progress_percent must be within 0..100")
                    existing_progress = int(job.get("progress_percent") or 0)
                    if progress_percent < existing_progress:
                        raise ValueError("progress_percent must be monotonic")
                    updates["progress_percent"] = progress_percent

                if to_status == "running" and not job.get("started_at"):
                    updates["started_at"] = now

                if to_status == "partial":
                    updates["partial_count"] = int(job.get("partial_count") or 0) + 1

                if to_status in _TERMINAL_STATES:
                    updates["finished_at"] = now

                if to_status == "failed":
                    updates["error_count"] = int(job.get("error_count") or 0) + 1
                    updates["error_code"] = str(error_code or "runtime_error")
                    updates["error_message"] = str(error_message or "async job failed")

                if result_id is not None:
                    updates["result_id"] = str(result_id)

                # Build SET clause
                set_clause = ", ".join(f"{k} = %s" for k in updates)
                params = list(updates.values()) + [str(job_id)]
                cur.execute(
                    f"UPDATE jobs SET {set_clause} WHERE job_id = %s",  # noqa: S608
                    params,
                )

                # Event sequence: count existing events + 1
                cur.execute(
                    "SELECT COUNT(*) FROM job_events WHERE job_id = %s",
                    (str(job_id),),
                )
                count_row = cur.fetchone()
                next_seq = (int(count_row[0]) if count_row else 0) + 1

                self._insert_event(
                    cur,
                    job_id=str(job_id),
                    event_type=f"job.{to_status}",
                    event_seq=next_seq,
                    occurred_at=now,
                )
                conn.commit()

                # Return merged state
                merged = {**job, **updates}
                return deepcopy(merged)
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # request_cancel / consume_cancel_request
    # ------------------------------------------------------------------

    def request_cancel(
        self,
        *,
        job_id: str,
        canceled_by: str = "user",
        cancel_reason: str | None = None,
        org_id: str | None = None,
    ) -> dict[str, Any]:
        """Mark job as cancel-requested (non-terminal)."""
        now = _utc_now_iso()
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                sql = "UPDATE jobs SET cancel_requested_at = %s, updated_at = %s WHERE job_id = %s"
                params: list[Any] = [now, now, str(job_id)]
                if org_id:
                    sql += " AND org_id = %s"
                    params.append(str(org_id))
                cur.execute(sql, params)
                if cur.rowcount == 0:
                    raise KeyError(f"unknown or unauthorized job_id: {job_id}")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f"job disappeared after cancel request: {job_id}")
        return job

    def consume_cancel_request(self, *, job_id: str) -> bool:
        """Clear cancel_requested_at; return True if it was set."""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT cancel_requested_at FROM jobs WHERE job_id = %s",
                    (str(job_id),),
                )
                row = cur.fetchone()
                if row is None:
                    return False
                was_set = bool(row[0])
                if was_set:
                    cur.execute(
                        "UPDATE jobs SET cancel_requested_at = NULL, updated_at = %s WHERE job_id = %s",
                        (_utc_now_iso(), str(job_id)),
                    )
                    conn.commit()
                return was_set
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # list_job_ids
    # ------------------------------------------------------------------

    def list_job_ids(
        self,
        *,
        statuses: Iterable[str] | None = None,
        org_id: str | None = None,
    ) -> list[str]:
        """Return job_ids optionally filtered by status and/or org_id."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            sql = "SELECT job_id FROM jobs WHERE 1=1"
            params: list[Any] = []
            if org_id:
                sql += " AND org_id = %s"
                params.append(str(org_id))
            if statuses is not None:
                status_list = list(statuses)
                if not status_list:
                    return []
                placeholders = ", ".join("%s" for _ in status_list)
                sql += f" AND status IN ({placeholders})"
                params.extend(status_list)
            cur.execute(sql, params)
            return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # create_result
    # ------------------------------------------------------------------

    def create_result(
        self,
        *,
        job_id: str,
        result_payload: dict[str, Any],
        result_kind: str = "final",
        schema_version: str = "v1",
        org_id: str | None = None,
        user_id: str | None = None,
        s3_bucket: str | None = None,
        s3_key: str | None = None,
        checksum_sha256: str | None = None,
        content_type: str = "application/json",
        size_bytes: int | None = None,
    ) -> dict[str, Any]:
        """Insert a job result; return the result record."""
        normalized_kind = str(result_kind or "").strip().lower()
        if normalized_kind not in {"partial", "final"}:
            raise ValueError("result_kind must be 'partial' or 'final'")

        normalized_payload = result_payload if isinstance(result_payload, dict) else {}

        result_id = str(uuid.uuid4())
        now = _utc_now_iso()

        # DB schema has no dedicated result_payload column. Persist an inline payload in
        # summary_json when no external object storage key is provided.
        if s3_key:
            inline_payload = normalized_payload.get("summary")
            if not isinstance(inline_payload, dict) or not inline_payload:
                inline_payload = normalized_payload
        else:
            inline_payload = normalized_payload
        if not isinstance(inline_payload, dict):
            inline_payload = {}

        summary = json.dumps(inline_payload, ensure_ascii=False)

        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()

                # Validate job exists
                cur.execute("SELECT org_id, user_id FROM jobs WHERE job_id = %s", (str(job_id),))
                job_row = cur.fetchone()
                if job_row is None:
                    raise KeyError(f"unknown job_id: {job_id}")

                resolved_org_id = str(org_id or job_row[0] or "")
                resolved_user_id = str(user_id or job_row[1] or "") or None

                # Guard: no duplicate final result
                if normalized_kind == "final":
                    cur.execute(
                        "SELECT 1 FROM job_results WHERE job_id = %s AND result_kind = 'final' AND org_id = %s",
                        (str(job_id), resolved_org_id),
                    )
                    if cur.fetchone():
                        raise ValueError("final result already exists for job")

                # Next sequence number
                cur.execute(
                    "SELECT COALESCE(MAX(result_seq), 0) FROM job_results WHERE job_id = %s AND org_id = %s",
                    (str(job_id), resolved_org_id),
                )
                max_seq_row = cur.fetchone()
                next_seq = int(max_seq_row[0] if max_seq_row else 0) + 1

                cur.execute(
                    """
                    INSERT INTO job_results (
                        result_id, job_id, org_id, user_id,
                        result_kind, result_seq, schema_version,
                        s3_bucket, s3_key, checksum_sha256, content_type, size_bytes,
                        summary_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        result_id, str(job_id), resolved_org_id, resolved_user_id,
                        normalized_kind, next_seq, str(schema_version or "v1"),
                        s3_bucket, s3_key, checksum_sha256, content_type, size_bytes,
                        summary, now,
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        return {
            "result_id": result_id,
            "job_id": job_id,
            "org_id": resolved_org_id,
            "user_id": resolved_user_id,
            "result_kind": normalized_kind,
            "result_seq": next_seq,
            "schema_version": schema_version,
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "checksum_sha256": checksum_sha256,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "summary_json": summary,
            "result_payload": deepcopy(normalized_payload),
            "created_at": now,
        }

    # ------------------------------------------------------------------
    # get_job / get_result
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM jobs WHERE job_id = %s", (str(job_id),))
            row = cur.fetchone()
            return _row_to_dict(cur, row) if row else None
        finally:
            conn.close()

    def get_result(self, result_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM job_results WHERE result_id = %s", (str(result_id),))
            row = cur.fetchone()
            return _hydrate_result_record(_row_to_dict(cur, row) if row else None)
        finally:
            conn.close()

    def get_result_with_org_guard(
        self,
        result_id: str,
        *,
        org_id: str,
    ) -> dict[str, Any] | None:
        """Fetch result only if org_id matches (tenant guard)."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM job_results WHERE result_id = %s AND org_id = %s",
                (str(result_id), str(org_id)),
            )
            row = cur.fetchone()
            return _hydrate_result_record(_row_to_dict(cur, row) if row else None)
        finally:
            conn.close()

    def get_result_for_owner(
        self,
        result_id: str,
        *,
        owner_user_id: str,
        owner_org_id: str,
    ) -> dict[str, Any] | None:
        """Fetch result only for exact owner user+org.

        Legacy compatibility:
        - New rows: enforce strict `job_results.user_id + job_results.org_id` match.
        - Old rows with partial metadata: fall back to the parent `jobs` owner guard.
        """
        owner_user_id_norm = str(owner_user_id or "").strip()
        owner_org_id_norm = _normalize_owner_org_id(owner_org_id)
        if not owner_user_id_norm:
            return None

        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM job_results
                WHERE result_id = %s
                """,
                (str(result_id),),
            )
            row = cur.fetchone()
            if row is None:
                return None

            projected = _row_to_dict(cur, row)
            result_user_id = str(projected.get("user_id") or "").strip()
            result_org_id_norm = _normalize_owner_org_id(projected.get("org_id"))

            # Fast path: result row already has complete owner metadata.
            if result_user_id:
                if result_user_id == owner_user_id_norm and result_org_id_norm == owner_org_id_norm:
                    return _hydrate_result_record(projected)
                return None

            # Legacy fallback: allow only when the parent job owner matches.
            job_id = str(projected.get("job_id") or "").strip()
            if not job_id:
                return None

            cur.execute(
                """
                SELECT user_id, org_id
                FROM jobs
                WHERE job_id = %s
                """,
                (job_id,),
            )
            parent_row = cur.fetchone()
            if parent_row is None:
                return None

            parent_user_id = str(parent_row[0] or "").strip()
            parent_org_id_norm = _normalize_owner_org_id(parent_row[1])
            if parent_user_id != owner_user_id_norm:
                return None
            if parent_org_id_norm != owner_org_id_norm:
                return None
            return _hydrate_result_record(projected)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # list_results / list_events
    # ------------------------------------------------------------------

    def list_results(self, job_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM job_results WHERE job_id = %s ORDER BY result_seq ASC",
                (str(job_id),),
            )
            return [
                _hydrate_result_record(_row_to_dict(cur, row)) or {}
                for row in cur.fetchall()
            ]
        finally:
            conn.close()

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM job_events WHERE job_id = %s ORDER BY event_seq ASC",
                (str(job_id),),
            )
            return [_row_to_dict(cur, row) for row in cur.fetchall()]
        finally:
            conn.close()

    def list_notifications(
        self,
        job_id: str,
        *,
        channel: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return terminal in-app notifications for a job.

        DB schema v2 has no dedicated ``job_notifications`` table yet. For API/UI
        compatibility we synthesize a deterministic in-app notification from the
        current terminal job state (completed/failed).
        """

        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            return []

        normalized_channel = str(channel).strip().lower() if channel else None
        if normalized_channel and normalized_channel != "in_app":
            return []

        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    job_id,
                    status,
                    result_id,
                    progress_percent,
                    error_code,
                    to_jsonb(jobs)->>'retry_hint' AS retry_hint,
                    finished_at,
                    updated_at,
                    queued_at
                FROM jobs
                WHERE job_id = %s
                """,
                (normalized_job_id,),
            )
            row = cur.fetchone()
            if row is None:
                return []
            job_record = _row_to_dict(cur, row)
        finally:
            conn.close()

        status = str(job_record.get("status") or "").strip().lower()
        if status not in {"completed", "failed"}:
            return []

        template_key = f"async.job.{status}"
        dedupe_key = f"{normalized_job_id}:in_app:{template_key}"
        created_at = str(
            job_record.get("finished_at")
            or job_record.get("updated_at")
            or job_record.get("queued_at")
            or _utc_now_iso()
        )
        notification_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"db-notify:{dedupe_key}"))

        return [
            {
                "notification_id": notification_id,
                "job_id": normalized_job_id,
                "channel": "in_app",
                "template_key": template_key,
                "delivery_status": "pending",
                "attempt_count": 0,
                "last_error": None,
                "dedupe_key": dedupe_key,
                "scheduled_at": created_at,
                "sent_at": None,
                "created_at": created_at,
                "payload_json": {
                    "job_id": normalized_job_id,
                    "status": status,
                    "result_id": job_record.get("result_id"),
                    "progress_percent": int(job_record.get("progress_percent", 0) or 0),
                    "error_code": job_record.get("error_code"),
                    "retry_hint": job_record.get("retry_hint"),
                    "finished_at": job_record.get("finished_at"),
                },
            },
        ]

    # ------------------------------------------------------------------
    # list_jobs_for_org / list_jobs_for_user  (DB-only, not in file store)
    # ------------------------------------------------------------------

    def list_jobs_for_org(
        self,
        org_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return jobs for an org, newest first (paginated)."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            sql = (
                "SELECT * FROM jobs WHERE org_id = %s"
            )
            params: list[Any] = [str(org_id)]
            if status:
                sql += " AND status = %s"
                params.append(str(status))
            sql += " ORDER BY queued_at DESC LIMIT %s OFFSET %s"
            params += [int(limit), int(offset)]
            cur.execute(sql, params)
            return [_row_to_dict(cur, row) for row in cur.fetchall()]
        finally:
            conn.close()

    def count_jobs_for_org(self, org_id: str, *, status: str | None = None) -> int:
        """Return total job count for an org (for pagination metadata)."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            sql = "SELECT COUNT(*) FROM jobs WHERE org_id = %s"
            params: list[Any] = [str(org_id)]
            if status:
                sql += " AND status = %s"
                params.append(str(status))
            cur.execute(sql, params)
            row = cur.fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()

    def list_jobs_for_user(
        self,
        user_id: str,
        *,
        org_id: str,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return jobs for a specific user within an org (paginated).

        Both user_id AND org_id are required — this enforces the tenant boundary.
        """
        conn = self._connect()
        try:
            cur = conn.cursor()
            sql = "SELECT * FROM jobs WHERE user_id = %s AND org_id = %s"
            params: list[Any] = [str(user_id), str(org_id)]
            if status:
                sql += " AND status = %s"
                params.append(str(status))
            sql += " ORDER BY queued_at DESC LIMIT %s OFFSET %s"
            params += [int(limit), int(offset)]
            cur.execute(sql, params)
            return [_row_to_dict(cur, row) for row in cur.fetchall()]
        finally:
            conn.close()

    def count_jobs_for_user(
        self,
        user_id: str,
        *,
        org_id: str,
        status: str | None = None,
    ) -> int:
        """Return total job count for a user within an org."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            sql = "SELECT COUNT(*) FROM jobs WHERE user_id = %s AND org_id = %s"
            params: list[Any] = [str(user_id), str(org_id)]
            if status:
                sql += " AND status = %s"
                params.append(str(status))
            cur.execute(sql, params)
            row = cur.fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _insert_event(
        cur: Any,
        *,
        job_id: str,
        event_type: str,
        event_seq: int,
        occurred_at: str,
    ) -> None:
        event_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO job_events (event_id, job_id, event_type, event_seq, occurred_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (event_id, str(job_id), str(event_type), int(event_seq), str(occurred_at)),
        )
