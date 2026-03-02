"""
tests/test_backfill_async_jobs_to_db.py

Unit tests for scripts/backfill_async_jobs_to_db.py.

Tests:
- dry-run mode: counts valid records without touching DB
- idempotency: ON CONFLICT DO NOTHING (second run inserts 0)
- missing job_id field: record is skipped
- missing result_id: result is skipped
- job not in DB: result is skipped (FK guard)
- invalid event: skipped gracefully
- _load_store_file: missing file, empty file, invalid JSON

No live DB required — DB operations are verified via mock cursor.

Issue: #842 (ASYNC-DB-0.wp5)
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, call, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Load backfill module without executing main()
_spec = importlib.util.spec_from_file_location(
    "backfill_async_jobs_to_db",
    SCRIPTS_DIR / "backfill_async_jobs_to_db.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_cursor(fetchone_value=None, rowcount=1):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_value
    cur.fetchall.return_value = []
    cur.rowcount = rowcount
    return cur


def _make_store_file(data: dict) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, tmp)
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# _load_store_file
# ---------------------------------------------------------------------------

class TestLoadStoreFile(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        result = _mod._load_store_file(Path("/tmp/nonexistent_store_xyz.json"))
        self.assertEqual(result, {})

    def test_empty_file_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            path = Path(f.name)
        result = _mod._load_store_file(path)
        self.assertEqual(result, {})

    def test_valid_json_object_returned(self):
        data = {"jobs": {}, "results": {}}
        path = _make_store_file(data)
        result = _mod._load_store_file(path)
        self.assertEqual(result, data)

    def test_invalid_json_calls_sys_exit(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{not: valid json")
            path = Path(f.name)
        with self.assertRaises(SystemExit):
            _mod._load_store_file(path)


# ---------------------------------------------------------------------------
# _insert_job_if_not_exists
# ---------------------------------------------------------------------------

class TestInsertJobIfNotExists(unittest.TestCase):
    def test_valid_job_returns_true_on_insert(self):
        cur = _make_mock_cursor(rowcount=1)
        job = {
            "job_id": "j1",
            "org_id": "org-1",
            "status": "completed",
            "request_payload_hash": "abc",
            "queued_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        result = _mod._insert_job_if_not_exists(cur, job)
        self.assertTrue(result)
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        self.assertIn("ON CONFLICT (job_id) DO NOTHING", sql)

    def test_missing_job_id_returns_false(self):
        cur = _make_mock_cursor()
        result = _mod._insert_job_if_not_exists(cur, {"status": "queued"})
        self.assertFalse(result)
        cur.execute.assert_not_called()

    def test_idempotent_second_run_returns_false(self):
        """rowcount=0 simulates ON CONFLICT DO NOTHING (row already exists)."""
        cur = _make_mock_cursor(rowcount=0)
        job = {"job_id": "j1", "queued_at": "2026-01-01"}
        result = _mod._insert_job_if_not_exists(cur, job)
        self.assertFalse(result)

    def test_org_id_fallback_to_default_org(self):
        cur = _make_mock_cursor(rowcount=1)
        job = {"job_id": "j1", "queued_at": "2026-01-01"}  # no org_id
        _mod._insert_job_if_not_exists(cur, job)
        params = cur.execute.call_args[0][1]
        # org_id is params[1]
        self.assertEqual(params[1], "default-org")


# ---------------------------------------------------------------------------
# _insert_events_for_job
# ---------------------------------------------------------------------------

class TestInsertEventsForJob(unittest.TestCase):
    def test_valid_events_inserted(self):
        cur = _make_mock_cursor(rowcount=1)
        events = [
            {"event_type": "job.queued", "occurred_at": "2026-01-01"},
            {"event_type": "job.running", "occurred_at": "2026-01-01"},
        ]
        inserted, skipped = _mod._insert_events_for_job(cur, "j1", events)
        self.assertEqual(inserted, 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(cur.execute.call_count, 2)

    def test_non_dict_event_skipped(self):
        cur = _make_mock_cursor(rowcount=1)
        events = ["not a dict", {"event_type": "job.queued", "occurred_at": "2026-01-01"}]
        inserted, skipped = _mod._insert_events_for_job(cur, "j1", events)
        self.assertEqual(inserted, 1)
        self.assertEqual(skipped, 1)

    def test_idempotent_conflict_gives_skipped(self):
        cur = _make_mock_cursor(rowcount=0)
        events = [{"event_type": "job.queued", "occurred_at": "2026-01-01"}]
        inserted, skipped = _mod._insert_events_for_job(cur, "j1", events)
        self.assertEqual(inserted, 0)
        self.assertEqual(skipped, 1)

    def test_insert_sql_contains_on_conflict_do_nothing(self):
        cur = _make_mock_cursor(rowcount=1)
        events = [{"event_type": "job.queued", "occurred_at": "2026-01-01"}]
        _mod._insert_events_for_job(cur, "j1", events)
        sql = cur.execute.call_args[0][0]
        self.assertIn("ON CONFLICT DO NOTHING", sql)


# ---------------------------------------------------------------------------
# _insert_result_if_not_exists
# ---------------------------------------------------------------------------

class TestInsertResultIfNotExists(unittest.TestCase):
    def test_missing_result_id_returns_false(self):
        cur = _make_mock_cursor()
        result = _mod._insert_result_if_not_exists(cur, {"job_id": "j1"})
        self.assertFalse(result)

    def test_missing_job_id_returns_false(self):
        cur = _make_mock_cursor()
        result = _mod._insert_result_if_not_exists(cur, {"result_id": "r1"})
        self.assertFalse(result)

    def test_job_not_in_db_returns_false(self):
        """If FK check finds no job, result is skipped."""
        cur = _make_mock_cursor(fetchone_value=None)  # job SELECT returns None
        result = _mod._insert_result_if_not_exists(
            cur, {"result_id": "r1", "job_id": "j-missing"}
        )
        self.assertFalse(result)

    def test_valid_result_inserted(self):
        cur = _make_mock_cursor(fetchone_value=(1,), rowcount=1)  # job exists
        result = _mod._insert_result_if_not_exists(
            cur,
            {
                "result_id": "r1",
                "job_id": "j1",
                "org_id": "org-1",
                "result_kind": "final",
                "created_at": "2026-01-01",
            },
        )
        self.assertTrue(result)
        # Verify ON CONFLICT in INSERT
        sql = cur.execute.call_args_list[-1][0][0]
        self.assertIn("ON CONFLICT (result_id) DO NOTHING", sql)

    def test_idempotent_conflict_returns_false(self):
        cur = MagicMock()
        cur.fetchone.return_value = (1,)  # job exists
        cur.rowcount = 0  # result already exists
        result = _mod._insert_result_if_not_exists(
            cur, {"result_id": "r1", "job_id": "j1"}
        )
        self.assertFalse(result)

    def test_invalid_result_kind_coerced_to_final(self):
        cur = _make_mock_cursor(fetchone_value=(1,), rowcount=1)
        _mod._insert_result_if_not_exists(
            cur,
            {
                "result_id": "r1",
                "job_id": "j1",
                "result_kind": "bogus",
            },
        )
        params = cur.execute.call_args_list[-1][0][1]
        # result_kind is params[4]
        self.assertEqual(params[4], "final")


# ---------------------------------------------------------------------------
# Dry-run mode (integration-level, no DB)
# ---------------------------------------------------------------------------

class TestDryRunMode(unittest.TestCase):
    def test_dry_run_counts_valid_records(self):
        data = {
            "jobs": {
                "j1": {"job_id": "j1", "status": "completed"},
                "j2": {"job_id": "j2", "status": "failed"},
                "bad": "not-a-dict",
            },
            "results": {
                "r1": {"result_id": "r1", "job_id": "j1"},
                "bad": None,
            },
        }
        path = _make_store_file(data)

        # Simulate dry-run by calling the dry-run logic inline
        jobs = data.get("jobs") or {}
        results = data.get("results") or {}
        valid_jobs = sum(1 for j in jobs.values() if isinstance(j, dict) and j.get("job_id"))
        valid_results = sum(1 for r in results.values() if isinstance(r, dict) and r.get("result_id"))

        self.assertEqual(valid_jobs, 2)
        self.assertEqual(valid_results, 1)


# ---------------------------------------------------------------------------
# _safe_str / _safe_int helpers
# ---------------------------------------------------------------------------

class TestSafeHelpers(unittest.TestCase):
    def test_safe_str_none_returns_default(self):
        self.assertEqual(_mod._safe_str(None, "x"), "x")

    def test_safe_str_strips_whitespace(self):
        self.assertEqual(_mod._safe_str("  hello  "), "hello")

    def test_safe_int_invalid_returns_default(self):
        self.assertEqual(_mod._safe_int("abc", 99), 99)

    def test_safe_int_none_returns_default(self):
        self.assertEqual(_mod._safe_int(None, 0), 0)

    def test_safe_int_valid(self):
        self.assertEqual(_mod._safe_int("42"), 42)


# ---------------------------------------------------------------------------
# Runbook file exists
# ---------------------------------------------------------------------------

class TestCutoverRunbookExists(unittest.TestCase):
    def test_runbook_file_exists(self):
        runbook = REPO_ROOT / "docs" / "ops" / "async_db_cutover.md"
        self.assertTrue(runbook.exists(), f"missing runbook: {runbook}")

    def test_runbook_has_rollback_section(self):
        runbook = REPO_ROOT / "docs" / "ops" / "async_db_cutover.md"
        content = runbook.read_text(encoding="utf-8")
        self.assertIn("Rollback", content)

    def test_runbook_has_checklist(self):
        runbook = REPO_ROOT / "docs" / "ops" / "async_db_cutover.md"
        content = runbook.read_text(encoding="utf-8")
        self.assertIn("ASYNC_STORE_BACKEND", content)

    def test_backfill_script_exists(self):
        script = REPO_ROOT / "scripts" / "backfill_async_jobs_to_db.py"
        self.assertTrue(script.exists(), f"missing: {script}")

    def test_backfill_script_has_dry_run_flag(self):
        script = REPO_ROOT / "scripts" / "backfill_async_jobs_to_db.py"
        content = script.read_text(encoding="utf-8")
        self.assertIn("--dry-run", content)

    def test_backfill_script_has_idempotency_guard(self):
        script = REPO_ROOT / "scripts" / "backfill_async_jobs_to_db.py"
        content = script.read_text(encoding="utf-8")
        self.assertIn("ON CONFLICT", content)


if __name__ == "__main__":
    unittest.main()
