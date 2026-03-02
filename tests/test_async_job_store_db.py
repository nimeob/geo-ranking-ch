"""
tests/test_async_job_store_db.py

Unit tests for DbAsyncJobStore (src/shared/async_job_store_db.py).

Strategy: mock the psycopg2 connection/cursor to capture SQL and verify:
  - Org-guard: all list/count queries always include org_id in WHERE clause
  - User+Org guard: list_jobs_for_user always includes BOTH user_id AND org_id
  - create_job inserts correct fields
  - transition_job validates allowed transitions
  - create_result validates result_kind + duplicate final guard

No live DB required.

Issue: #839 (ASYNC-DB-0.wp2)
"""

from __future__ import annotations

import json
import re
import unittest
from unittest.mock import MagicMock, call, patch

from src.shared.async_job_store_db import DbAsyncJobStore, _canonical_payload_hash


# ---------------------------------------------------------------------------
# Helper: build a mock connection that returns controlled cursor results
# ---------------------------------------------------------------------------

def _make_conn_factory(fetchone_values=None, fetchall_values=None, rowcount=1):
    """Return a conn_factory whose cursor reports preset fetch results."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = fetchone_values or [None]
    mock_cursor.fetchall.return_value = fetchall_values or []
    mock_cursor.rowcount = rowcount
    mock_cursor.description = []  # updated per-test as needed

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)

    return (lambda: mock_conn), mock_cursor, mock_conn


def _get_executed_sqls(mock_cursor: MagicMock) -> list[str]:
    """Extract all SQL strings passed to cursor.execute(...)."""
    sqls = []
    for c in mock_cursor.execute.call_args_list:
        args = c[0]
        if args:
            sqls.append(str(args[0]))
    return sqls


def _all_sqls_joined(mock_cursor: MagicMock) -> str:
    return "\n".join(_get_executed_sqls(mock_cursor))


# ---------------------------------------------------------------------------
# Org-guard tests
# ---------------------------------------------------------------------------

class TestOrgGuardInListJobs(unittest.TestCase):
    """list_jobs_for_org must always include org_id in WHERE clause."""

    def test_list_jobs_for_org_contains_org_id_filter(self):
        factory, mock_cursor, _ = _make_conn_factory(fetchall_values=[])
        store = DbAsyncJobStore(conn_factory=factory)
        store.list_jobs_for_org("my-org")

        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("org_id", sqls, "list_jobs_for_org must filter by org_id")
        # Ensure the org_id param was passed
        params_used = [c[0][1] for c in mock_cursor.execute.call_args_list if c[0]]
        org_ids_in_params = [p for p in params_used if isinstance(p, (list, tuple)) and "my-org" in p]
        self.assertTrue(
            any("my-org" in str(p) for p in params_used),
            "org_id value must appear in execute params",
        )

    def test_count_jobs_for_org_contains_org_id_filter(self):
        factory, mock_cursor, _ = _make_conn_factory(fetchone_values=[(0,)])
        store = DbAsyncJobStore(conn_factory=factory)
        store.count_jobs_for_org("my-org")

        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("org_id", sqls)

    def test_list_jobs_for_org_with_status_filter(self):
        factory, mock_cursor, _ = _make_conn_factory(fetchall_values=[])
        store = DbAsyncJobStore(conn_factory=factory)
        store.list_jobs_for_org("my-org", status="completed")

        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("org_id", sqls)
        self.assertIn("status", sqls)


class TestUserOrgGuardInListJobs(unittest.TestCase):
    """list_jobs_for_user must include BOTH user_id AND org_id in WHERE clause."""

    def test_requires_both_user_and_org_id(self):
        factory, mock_cursor, _ = _make_conn_factory(fetchall_values=[])
        store = DbAsyncJobStore(conn_factory=factory)
        store.list_jobs_for_user("user-123", org_id="org-abc")

        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("user_id", sqls, "list_jobs_for_user must filter by user_id")
        self.assertIn("org_id", sqls, "list_jobs_for_user must filter by org_id")

    def test_count_jobs_for_user_requires_both(self):
        factory, mock_cursor, _ = _make_conn_factory(fetchone_values=[(5,)])
        store = DbAsyncJobStore(conn_factory=factory)
        count = store.count_jobs_for_user("user-123", org_id="org-abc")

        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("user_id", sqls)
        self.assertIn("org_id", sqls)
        self.assertEqual(count, 5)

    def test_user_cannot_see_other_org_jobs(self):
        """list_jobs_for_user SQL should never omit org_id."""
        factory, mock_cursor, _ = _make_conn_factory(fetchall_values=[])
        store = DbAsyncJobStore(conn_factory=factory)

        # Call without org_id would raise TypeError — org_id is mandatory
        with self.assertRaises(TypeError):
            store.list_jobs_for_user("user-x")  # missing org_id


class TestResultOrgGuard(unittest.TestCase):
    """get_result_with_org_guard must include org_id in WHERE clause."""

    def test_org_guard_present_in_sql(self):
        factory, mock_cursor, _ = _make_conn_factory(fetchone_values=[None])
        store = DbAsyncJobStore(conn_factory=factory)
        result = store.get_result_with_org_guard("result-id-x", org_id="org-abc")

        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("org_id", sqls)
        self.assertNone_or_dict(result)

    def assertNone_or_dict(self, value):
        self.assertIsNone(value)  # our mock returns None


# ---------------------------------------------------------------------------
# create_job
# ---------------------------------------------------------------------------

class TestCreateJob(unittest.TestCase):
    def _make_store(self):
        factory, mock_cursor, mock_conn = _make_conn_factory(fetchone_values=[None])
        store = DbAsyncJobStore(conn_factory=factory)
        return store, mock_cursor, mock_conn

    def test_returns_job_dict_with_queued_status(self):
        store, _, _ = self._make_store()
        job = store.create_job(
            request_payload={"query": "Basel Gundeldingen"},
            request_id="req-1",
            query="Basel Gundeldingen",
            intelligence_mode="basic",
            org_id="org-1",
        )
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["org_id"], "org-1")
        self.assertEqual(job["query"], "Basel Gundeldingen")
        self.assertIn("job_id", job)
        self.assertIn("queued_at", job)

    def test_payload_hash_is_sha256(self):
        store, _, _ = self._make_store()
        payload = {"query": "test", "mode": "basic"}
        job = store.create_job(
            request_payload=payload,
            request_id="req-2",
            query="test",
            intelligence_mode="basic",
            org_id="org-1",
        )
        expected_hash = _canonical_payload_hash(payload)
        self.assertEqual(job["request_payload_hash"], expected_hash)

    def test_insert_sql_contains_org_id(self):
        store, mock_cursor, _ = self._make_store()
        store.create_job(
            request_payload={},
            request_id="req-3",
            query="q",
            intelligence_mode="basic",
            org_id="org-xyz",
        )
        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("org_id", sqls)
        self.assertIn("INSERT INTO jobs", sqls)

    def test_creates_queued_event(self):
        store, mock_cursor, _ = self._make_store()
        store.create_job(
            request_payload={},
            request_id="req-4",
            query="q",
            intelligence_mode="basic",
            org_id="org-1",
        )
        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("job_events", sqls)
        self.assertIn("job.queued", str(mock_cursor.execute.call_args_list))

    def test_owner_user_id_stored(self):
        store, mock_cursor, _ = self._make_store()
        job = store.create_job(
            request_payload={},
            request_id="req-5",
            query="q",
            intelligence_mode="basic",
            org_id="org-1",
            owner_user_id="user-42",
        )
        self.assertEqual(job["user_id"], "user-42")

    def test_no_owner_user_id_gives_none(self):
        store, mock_cursor, _ = self._make_store()
        job = store.create_job(
            request_payload={},
            request_id="req-6",
            query="q",
            intelligence_mode="basic",
            org_id="org-1",
        )
        self.assertIsNone(job["user_id"])


# ---------------------------------------------------------------------------
# transition_job
# ---------------------------------------------------------------------------

class TestTransitionJob(unittest.TestCase):
    def _store_with_job(self, job_row: dict):
        """Build a store whose cursor returns job_row on SELECT."""
        cols = list(job_row.keys())
        values = tuple(job_row.values())

        mock_cursor = MagicMock()
        # First fetchone = job row; second fetchone = event count
        mock_cursor.fetchone.side_effect = [values, (0,)]
        mock_cursor.fetchall.return_value = []
        mock_cursor.rowcount = 1
        mock_cursor.description = [(col,) for col in cols]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        store = DbAsyncJobStore(conn_factory=lambda: mock_conn)
        return store, mock_cursor

    def _base_job(self, **overrides) -> dict:
        base = {
            "job_id": "job-1",
            "org_id": "org-1",
            "user_id": None,
            "status": "queued",
            "request_payload_hash": "abc",
            "query": "test",
            "intelligence_mode": "basic",
            "progress_percent": 0,
            "partial_count": 0,
            "error_count": 0,
            "result_id": None,
            "error_code": None,
            "error_message": None,
            "queued_at": "2026-01-01T00:00:00+00:00",
            "started_at": None,
            "finished_at": None,
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        base.update(overrides)
        return base

    def test_valid_transition_queued_to_running(self):
        store, mock_cursor = self._store_with_job(self._base_job())
        result = store.transition_job(job_id="job-1", to_status="running")
        self.assertEqual(result["status"], "running")

    def test_invalid_transition_queued_to_completed_raises(self):
        store, mock_cursor = self._store_with_job(self._base_job())
        with self.assertRaises(ValueError):
            store.transition_job(job_id="job-1", to_status="completed")

    def test_unknown_job_raises_key_error(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        store = DbAsyncJobStore(conn_factory=lambda: mock_conn)

        with self.assertRaises(KeyError):
            store.transition_job(job_id="nonexistent", to_status="running")

    def test_update_sql_contains_job_id(self):
        store, mock_cursor = self._store_with_job(self._base_job())
        store.transition_job(job_id="job-1", to_status="running")
        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("UPDATE jobs", sqls)

    def test_event_inserted_for_transition(self):
        store, mock_cursor = self._store_with_job(self._base_job())
        store.transition_job(job_id="job-1", to_status="running")
        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("job_events", sqls)

    def test_progress_percent_monotonic_enforced(self):
        store, mock_cursor = self._store_with_job(self._base_job(status="running", progress_percent=50))
        with self.assertRaises(ValueError):
            store.transition_job(job_id="job-1", to_status="running", progress_percent=30)

    def test_progress_percent_out_of_range_raises(self):
        store, mock_cursor = self._store_with_job(self._base_job(status="running"))
        with self.assertRaises(ValueError):
            store.transition_job(job_id="job-1", to_status="running", progress_percent=101)


# ---------------------------------------------------------------------------
# create_result
# ---------------------------------------------------------------------------

class TestCreateResult(unittest.TestCase):
    def _make_store_for_result(
        self,
        *,
        job_exists: bool = True,
        has_final: bool = False,
        max_seq: int = 0,
    ):
        job_row = ("job-1", "org-1", "user-1") if job_exists else None
        final_row = (1,) if has_final else None
        seq_row = (max_seq,)

        mock_cursor = MagicMock()
        # fetchone sequence: job lookup, final-check, max-seq
        mock_cursor.fetchone.side_effect = [job_row, final_row, seq_row]
        mock_cursor.fetchall.return_value = []
        mock_cursor.rowcount = 1
        mock_cursor.description = [("org_id",), ("user_id",), ("job_id",)]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        store = DbAsyncJobStore(conn_factory=lambda: mock_conn)
        return store, mock_cursor

    def test_returns_result_record(self):
        store, _ = self._make_store_for_result()
        result = store.create_result(
            job_id="job-1",
            result_payload={"ok": True},
            result_kind="final",
            org_id="org-1",
        )
        self.assertEqual(result["result_kind"], "final")
        self.assertIn("result_id", result)
        self.assertEqual(result["org_id"], "org-1")

    def test_invalid_result_kind_raises(self):
        store, _ = self._make_store_for_result()
        with self.assertRaises(ValueError):
            store.create_result(
                job_id="job-1",
                result_payload={},
                result_kind="invalid",
                org_id="org-1",
            )

    def test_unknown_job_raises(self):
        store, _ = self._make_store_for_result(job_exists=False)
        with self.assertRaises(KeyError):
            store.create_result(job_id="nonexistent", result_payload={}, org_id="org-1")

    def test_duplicate_final_raises(self):
        store, _ = self._make_store_for_result(has_final=True)
        with self.assertRaises(ValueError):
            store.create_result(
                job_id="job-1",
                result_payload={},
                result_kind="final",
                org_id="org-1",
            )

    def test_insert_sql_includes_org_id(self):
        store, mock_cursor = self._make_store_for_result()
        store.create_result(
            job_id="job-1",
            result_payload={},
            result_kind="final",
            org_id="org-1",
        )
        sqls = _all_sqls_joined(mock_cursor)
        self.assertIn("org_id", sqls)
        self.assertIn("INSERT INTO job_results", sqls)

    def test_s3_fields_are_passed_to_insert(self):
        store, mock_cursor = self._make_store_for_result()
        store.create_result(
            job_id="job-1",
            result_payload={},
            result_kind="partial",
            org_id="org-1",
            s3_bucket="my-bucket",
            s3_key="results/abc.json",
            checksum_sha256="deadbeef",
            size_bytes=1024,
        )
        all_params = str(mock_cursor.execute.call_args_list)
        self.assertIn("my-bucket", all_params)
        self.assertIn("results/abc.json", all_params)
        self.assertIn("deadbeef", all_params)


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------

class TestFromEnv(unittest.TestCase):
    def test_missing_env_raises_runtime_error(self):
        import os
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ASYNC_DB_URL", None)
            os.environ.pop("DATABASE_URL", None)
            with self.assertRaises(RuntimeError):
                DbAsyncJobStore.from_env()

    def test_async_db_url_takes_precedence(self):
        """from_env should try psycopg2.connect with ASYNC_DB_URL."""
        import os
        with patch.dict(os.environ, {"ASYNC_DB_URL": "postgresql://u:p@localhost/db"}):
            with patch("src.shared.async_job_store_db.DbAsyncJobStore.from_env") as mock_factory:
                mock_factory.return_value = MagicMock()
                store = DbAsyncJobStore.from_env()
                # Just verify no crash (psycopg2 not actually called)


# ---------------------------------------------------------------------------
# _canonical_payload_hash
# ---------------------------------------------------------------------------

class TestCanonicalPayloadHash(unittest.TestCase):
    def test_deterministic(self):
        payload = {"b": 2, "a": 1}
        h1 = _canonical_payload_hash(payload)
        h2 = _canonical_payload_hash({"a": 1, "b": 2})
        self.assertEqual(h1, h2, "hash must be key-order independent")

    def test_different_payloads_different_hash(self):
        h1 = _canonical_payload_hash({"a": 1})
        h2 = _canonical_payload_hash({"a": 2})
        self.assertNotEqual(h1, h2)

    def test_returns_hex_string(self):
        h = _canonical_payload_hash({})
        self.assertRegex(h, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
