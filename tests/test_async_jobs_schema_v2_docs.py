"""
tests/test_async_jobs_schema_v2_docs.py

Schema-document test for async jobs v2 (migration 003).

Checks:
- Migration file 003 exists and has expected DDL
- jobs table has user_id column (added in 003)
- job_results table has all required fields (S3 refs + org_id + user_id)
- Canonical reference doc (docs/sql/async_jobs_schema_v2.sql) is consistent

Issue: #838 (ASYNC-DB-0.wp1)
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_003 = REPO_ROOT / "db" / "migrations" / "003_async_jobs_results.sql"
SCHEMA_V2_DOC = REPO_ROOT / "docs" / "sql" / "async_jobs_schema_v2.sql"


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is not None


# ---------------------------------------------------------------------------
# Migration file
# ---------------------------------------------------------------------------

class TestMigration003Exists(unittest.TestCase):
    def test_file_exists(self) -> None:
        self.assertTrue(MIGRATION_003.exists(), f"missing: {MIGRATION_003}")

    def test_wrapped_in_transaction(self) -> None:
        sql = MIGRATION_003.read_text(encoding="utf-8")
        self.assertTrue(_has(r"^\s*BEGIN\s*;", sql), "migration must start with BEGIN;")
        self.assertTrue(_has(r"^\s*COMMIT\s*;", sql), "migration must end with COMMIT;")


class TestMigration003JobsUserIdColumn(unittest.TestCase):
    """Migration 003 must add user_id to the jobs table."""

    def setUp(self) -> None:
        self._sql = MIGRATION_003.read_text(encoding="utf-8")

    def test_adds_user_id_column(self) -> None:
        self.assertTrue(
            _has(r"ALTER\s+TABLE\s+jobs\s+ADD\s+COLUMN", self._sql),
            "expected ALTER TABLE jobs ADD COLUMN",
        )
        self.assertTrue(
            _has(r"user_id", self._sql),
            "expected user_id field",
        )

    def test_creates_user_id_index(self) -> None:
        self.assertTrue(
            _has(r"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+jobs_user_id_idx", self._sql),
            "expected index jobs_user_id_idx",
        )

    def test_creates_org_user_composite_index(self) -> None:
        self.assertTrue(
            _has(r"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+jobs_org_user_idx", self._sql),
            "expected composite index jobs_org_user_idx",
        )


class TestMigration003JobResultsTable(unittest.TestCase):
    """Migration 003 must create job_results table with all required fields."""

    def setUp(self) -> None:
        self._sql = MIGRATION_003.read_text(encoding="utf-8")

    def test_creates_job_results_table(self) -> None:
        self.assertTrue(
            _has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+job_results\b", self._sql),
            "expected CREATE TABLE IF NOT EXISTS job_results",
        )

    def test_has_result_id_primary_key(self) -> None:
        self.assertTrue(_has(r"result_id\s+text\s+PRIMARY\s+KEY", self._sql))

    def test_has_job_id_foreign_key(self) -> None:
        self.assertTrue(
            _has(r"job_id\s+text\s+NOT\s+NULL\s+REFERENCES\s+jobs", self._sql),
            "job_id should reference jobs table",
        )

    def test_has_org_id(self) -> None:
        self.assertTrue(_has(r"org_id\s+text\s+NOT\s+NULL", self._sql))

    def test_has_user_id(self) -> None:
        self.assertTrue(_has(r"user_id\s+text", self._sql))

    def test_has_result_kind_with_check(self) -> None:
        self.assertTrue(
            _has(r"result_kind.*CHECK.*partial.*final", self._sql),
            "result_kind must have CHECK constraint",
        )

    def test_has_s3_fields(self) -> None:
        sql = self._sql
        self.assertTrue(_has(r"s3_bucket\s+text", sql), "missing s3_bucket field")
        self.assertTrue(_has(r"s3_key\s+text", sql), "missing s3_key field")
        self.assertTrue(_has(r"checksum_sha256\s+text", sql), "missing checksum_sha256 field")
        self.assertTrue(_has(r"content_type\s+text", sql), "missing content_type field")
        self.assertTrue(_has(r"size_bytes\s+bigint", sql), "missing size_bytes field")

    def test_has_summary_json(self) -> None:
        self.assertTrue(_has(r"summary_json\s+text", self._sql))

    def test_has_created_at(self) -> None:
        self.assertTrue(_has(r"created_at\s+text\s+NOT\s+NULL", self._sql))

    def test_has_unique_constraint_job_seq(self) -> None:
        self.assertTrue(
            _has(r"UNIQUE\s*\(\s*job_id\s*,\s*result_seq\s*\)", self._sql),
            "expected UNIQUE(job_id, result_seq)",
        )

    def test_has_org_id_index(self) -> None:
        self.assertTrue(_has(r"job_results_org_id_idx", self._sql))

    def test_has_job_id_index(self) -> None:
        self.assertTrue(_has(r"job_results_job_id_idx", self._sql))


# ---------------------------------------------------------------------------
# Schema v2 reference doc
# ---------------------------------------------------------------------------

class TestAsyncJobsSchemaV2Doc(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(SCHEMA_V2_DOC.exists(), f"missing: {SCHEMA_V2_DOC}")
        self._sql = SCHEMA_V2_DOC.read_text(encoding="utf-8")

    def test_doc_has_all_three_tables(self) -> None:
        sql = self._sql
        for table in ("jobs", "job_events", "job_results"):
            self.assertTrue(
                _has(rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{table}\b", sql),
                f"schema v2 doc missing table: {table}",
            )

    def test_doc_jobs_has_user_id(self) -> None:
        self.assertTrue(_has(r"user_id", self._sql))

    def test_doc_job_results_has_s3_fields(self) -> None:
        sql = self._sql
        for field in ("s3_bucket", "s3_key", "checksum_sha256", "size_bytes"):
            self.assertTrue(_has(field, sql), f"schema v2 doc missing field: {field}")


if __name__ == "__main__":
    unittest.main()
