#!/usr/bin/env python3
"""backfill_async_jobs_to_db.py — One-shot migration of async jobs from file store to DB.

Reads ``runtime/async_jobs/store.v1.json`` (or the path set by
``ASYNC_JOBS_STORE_FILE``) and writes jobs, events, and results into the
Postgres schema created by migrations 002 + 003.

Features:
- Idempotent: jobs/results that already exist in the DB are silently skipped
  (ON CONFLICT DO NOTHING).
- ``--dry-run``: parse + validate without writing to DB.
- Tolerates missing or malformed fields in the JSON file (best-effort).
- Progress counters for jobs, events, and results inserted / skipped.

Usage:
    python scripts/backfill_async_jobs_to_db.py --dry-run
    python scripts/backfill_async_jobs_to_db.py --apply

Environment:
    DATABASE_URL or ASYNC_DB_URL   postgresql://user:pass@host/dbname  (required for --apply)
    ASYNC_JOBS_STORE_FILE          path to JSON store (default: runtime/async_jobs/store.v1.json)

Exit codes:
    0 — success
    1 — error (file not found, DB error, etc.)

Issue: #842 (ASYNC-DB-0.wp5)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_STORE_FILE = "runtime/async_jobs/store.v1.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _ensure_uuid(value: Any) -> str:
    """Return value if it looks like a UUID, otherwise generate a new one."""
    text = _safe_str(value)
    if text and len(text) >= 8:
        return text
    return str(uuid.uuid4())


def _load_store_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"[WARN] store file not found: {path} — nothing to backfill", file=sys.stderr)
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        print(f"[WARN] store file is empty: {path}", file=sys.stderr)
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] failed to parse store file: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, dict):
        print("[ERROR] store file root must be a JSON object", file=sys.stderr)
        sys.exit(1)
    return data


def _get_db_url() -> str:
    url = (os.getenv("ASYNC_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not url:
        print(
            "[ERROR] DATABASE_URL or ASYNC_DB_URL must be set for --apply mode.",
            file=sys.stderr,
        )
        sys.exit(1)
    return url


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _connect(db_url: str) -> Any:
    try:
        import psycopg2  # type: ignore[import]
    except ImportError:
        print("[ERROR] psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def _insert_job_if_not_exists(cur: Any, job: dict[str, Any]) -> bool:
    """Insert a job row; return True if inserted, False if already present."""
    job_id = _safe_str(job.get("job_id"))
    if not job_id:
        return False
    org_id = _safe_str(job.get("org_id") or job.get("owner_org_id"), "default-org")
    user_id = _safe_str(job.get("owner_user_id") or job.get("user_id")) or None
    status = _safe_str(job.get("status"), "completed")
    payload_hash = _safe_str(job.get("request_payload_hash"), "backfill")
    query = _safe_str(job.get("query"))
    mode = _safe_str(job.get("intelligence_mode"), "basic")
    progress = _safe_int(job.get("progress_percent"), 0)
    partial_count = _safe_int(job.get("partial_count"), 0)
    error_count = _safe_int(job.get("error_count"), 0)
    result_id = _safe_str(job.get("result_id")) or None
    error_code = _safe_str(job.get("error_code")) or None
    error_message = _safe_str(job.get("error_message")) or None
    queued_at = _safe_str(job.get("queued_at") or job.get("created_at"), _utc_now_iso())
    started_at = _safe_str(job.get("started_at")) or None
    finished_at = _safe_str(job.get("finished_at")) or None
    updated_at = _safe_str(job.get("updated_at"), queued_at)

    cur.execute(
        """
        INSERT INTO jobs (
            job_id, org_id, user_id, status,
            request_payload_hash, query, intelligence_mode,
            progress_percent, partial_count, error_count,
            result_id, error_code, error_message,
            queued_at, started_at, finished_at, updated_at
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (job_id) DO NOTHING
        """,
        (
            job_id, org_id, user_id, status,
            payload_hash, query, mode,
            progress, partial_count, error_count,
            result_id, error_code, error_message,
            queued_at, started_at, finished_at, updated_at,
        ),
    )
    return cur.rowcount > 0


def _insert_events_for_job(
    cur: Any,
    job_id: str,
    events: list[Any],
) -> tuple[int, int]:
    """Insert events; return (inserted_count, skipped_count)."""
    inserted = 0
    skipped = 0
    for seq, evt in enumerate(events, start=1):
        if not isinstance(evt, dict):
            skipped += 1
            continue
        event_id = _ensure_uuid(evt.get("event_id"))
        event_type = _safe_str(evt.get("event_type"), "unknown")
        event_seq = _safe_int(evt.get("event_seq") or evt.get("seq"), seq)
        occurred_at = _safe_str(evt.get("occurred_at"), _utc_now_iso())

        cur.execute(
            """
            INSERT INTO job_events (event_id, job_id, event_type, event_seq, occurred_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (event_id, job_id, event_type, event_seq, occurred_at),
        )
        if cur.rowcount > 0:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def _insert_result_if_not_exists(
    cur: Any,
    result: dict[str, Any],
) -> bool:
    """Insert a job_result row; return True if inserted."""
    result_id = _safe_str(result.get("result_id"))
    job_id = _safe_str(result.get("job_id"))
    if not result_id or not job_id:
        return False

    # Verify job exists in DB before inserting result (FK constraint)
    cur.execute("SELECT 1 FROM jobs WHERE job_id = %s", (job_id,))
    if cur.fetchone() is None:
        return False  # job not in DB, skip

    org_id = _safe_str(
        result.get("owner_org_id") or result.get("org_id"), "default-org"
    )
    user_id = _safe_str(result.get("owner_user_id") or result.get("user_id")) or None
    result_kind = _safe_str(result.get("result_kind"), "final")
    if result_kind not in ("partial", "final"):
        result_kind = "final"
    result_seq = _safe_int(result.get("result_seq"), 1)
    schema_version = _safe_str(result.get("schema_version"), "v1")
    created_at = _safe_str(result.get("created_at"), _utc_now_iso())

    # Build summary_json from result_payload if present
    result_payload = result.get("result_payload") or result.get("summary_json") or {}
    if isinstance(result_payload, dict):
        summary = json.dumps(result.get("summary_json") or {}, ensure_ascii=False)
    else:
        summary = str(result_payload)

    cur.execute(
        """
        INSERT INTO job_results (
            result_id, job_id, org_id, user_id,
            result_kind, result_seq, schema_version,
            content_type, summary_json, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (result_id) DO NOTHING
        """,
        (
            result_id, job_id, org_id, user_id,
            result_kind, result_seq, schema_version,
            "application/json", summary, created_at,
        ),
    )
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill async jobs from file store (store.v1.json) to Postgres DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true", help="Write to DB (requires DATABASE_URL)")
    mode.add_argument("--dry-run", action="store_true", help="Parse + validate only; no DB writes")
    parser.add_argument(
        "--store-file",
        default=None,
        help=f"Path to store.v1.json (default: {_DEFAULT_STORE_FILE} or ASYNC_JOBS_STORE_FILE)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    store_path = Path(
        args.store_file
        or os.getenv("ASYNC_JOBS_STORE_FILE", _DEFAULT_STORE_FILE)
    )

    print(f"[INFO] backfill source: {store_path}")
    print(f"[INFO] mode: {'dry-run' if args.dry_run else 'apply'}")

    data = _load_store_file(store_path)
    if not data:
        print("[INFO] nothing to backfill (empty or missing store file)")
        return

    jobs: dict[str, Any] = data.get("jobs") or {}
    events_by_job: dict[str, list] = data.get("events") or {}
    results: dict[str, Any] = data.get("results") or {}

    print(f"[INFO] found: {len(jobs)} jobs, {len(results)} results in store file")

    if args.dry_run:
        print("[INFO] dry-run: validating structure...")
        valid_jobs = sum(1 for j in jobs.values() if isinstance(j, dict) and j.get("job_id"))
        valid_results = sum(1 for r in results.values() if isinstance(r, dict) and r.get("result_id"))
        print(f"[OK]   {valid_jobs}/{len(jobs)} valid job records")
        print(f"[OK]   {valid_results}/{len(results)} valid result records")
        print("[INFO] dry-run complete — no changes made")
        return

    db_url = _get_db_url()
    print(f"[INFO] connecting to DB...")
    conn = _connect(db_url)

    jobs_inserted = 0
    jobs_skipped = 0
    events_inserted = 0
    events_skipped = 0
    results_inserted = 0
    results_skipped = 0

    try:
        cur = conn.cursor()

        # --- Jobs ---
        for job_id, job in jobs.items():
            if not isinstance(job, dict):
                jobs_skipped += 1
                continue
            if not job.get("job_id"):
                job = {**job, "job_id": str(job_id)}
            if _insert_job_if_not_exists(cur, job):
                jobs_inserted += 1
            else:
                jobs_skipped += 1

            # --- Events for this job ---
            job_events = events_by_job.get(str(job_id)) or []
            if isinstance(job_events, list):
                ei, es = _insert_events_for_job(cur, str(job_id), job_events)
                events_inserted += ei
                events_skipped += es

        # --- Results ---
        for result_id, result in results.items():
            if not isinstance(result, dict):
                results_skipped += 1
                continue
            if not result.get("result_id"):
                result = {**result, "result_id": str(result_id)}
            if _insert_result_if_not_exists(cur, result):
                results_inserted += 1
            else:
                results_skipped += 1

        conn.commit()
        print(
            f"[OK]   jobs:    {jobs_inserted} inserted, {jobs_skipped} skipped (already present or invalid)"
        )
        print(
            f"[OK]   events:  {events_inserted} inserted, {events_skipped} skipped"
        )
        print(
            f"[OK]   results: {results_inserted} inserted, {results_skipped} skipped"
        )
        print("[INFO] backfill complete")

    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] backfill failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
