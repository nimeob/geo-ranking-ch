from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "docs" / "sql" / "db_core_schema_v1.sql"


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is not None


class TestDbCoreSchemaSql(unittest.TestCase):
    def test_schema_file_exists(self) -> None:
        self.assertTrue(SCHEMA_PATH.exists(), f"missing schema file: {SCHEMA_PATH}")

    def test_schema_contains_core_tables(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")

        self.assertTrue(
            _has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+organizations\b", sql)
        )
        self.assertTrue(_has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+users\b", sql))
        self.assertTrue(
            _has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+memberships\b", sql)
        )
        self.assertTrue(_has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+api_keys\b", sql))

    def test_memberships_unique_constraint_present(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertTrue(
            _has(r"UNIQUE\s*\(\s*org_id\s*,\s*user_id\s*\)", sql),
            "expected memberships unique(org_id,user_id)",
        )

    def test_api_keys_store_hash_and_fingerprint_only(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")

        self.assertTrue(_has(r"key_fingerprint\s+text\s+NOT\s+NULL", sql))
        self.assertTrue(_has(r"key_hash\s+text\s+NOT\s+NULL", sql))

        # Guardrail: no explicit plaintext column naming.
        self.assertFalse(_has(r"key_plaintext", sql))
        self.assertFalse(_has(r"secret_plaintext", sql))

    def test_schema_contains_entitlement_layer_tables(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertTrue(_has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+plans\b", sql))
        self.assertTrue(
            _has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+subscriptions\b", sql)
        )
        self.assertTrue(
            _has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+entitlements\b", sql)
        )
        self.assertTrue(
            _has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+usage_counters\b", sql)
        )
        self.assertTrue(
            _has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+audit_events\b", sql)
        )

    def test_plans_are_versioned_and_historized(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertTrue(
            _has(
                r"plans_code_version_unique\s*UNIQUE\s*\(\s*plan_code\s*,\s*version\s*\)",
                sql,
            )
        )

    def test_subscriptions_enforce_one_active_per_org(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertTrue(
            _has(
                r"CREATE\s+UNIQUE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+subscriptions_one_active_per_org",
                sql,
            )
        )

    def test_usage_counters_use_generic_scope_model(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertTrue(_has(r"scope_type\s+text\s+NOT\s+NULL", sql))
        self.assertTrue(_has(r"scope_id\s+text\s+NULL", sql))
        self.assertTrue(_has(r"window_start\s+timestamptz\s+NOT\s+NULL", sql))

    def test_audit_events_are_append_only_shape(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self.assertTrue(_has(r"actor_type\s+text\s+NOT\s+NULL", sql))
        self.assertTrue(_has(r"entity_type\s+text\s+NOT\s+NULL", sql))
        self.assertTrue(
            _has(r"occurred_at\s+timestamptz\s+NOT\s+NULL\s+DEFAULT\s+now\(\)", sql)
        )

    def test_migration_004_matches_canonical_doc_tables(self) -> None:
        migration_sql = (
            REPO_ROOT / "db" / "migrations" / "004_entitlements_schema.sql"
        ).read_text(encoding="utf-8")
        doc_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        for table in (
            "plans",
            "subscriptions",
            "entitlements",
            "usage_counters",
            "audit_events",
        ):
            self.assertTrue(
                _has(rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{table}\b", migration_sql),
                f"migration 004 missing table: {table}",
            )
            self.assertTrue(
                _has(rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{table}\b", doc_sql),
                f"canonical doc schema missing table: {table}",
            )


if __name__ == "__main__":
    unittest.main()
