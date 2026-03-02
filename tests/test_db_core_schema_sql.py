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

        self.assertTrue(_has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+organizations\b", sql))
        self.assertTrue(_has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+users\b", sql))
        self.assertTrue(_has(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+memberships\b", sql))
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


if __name__ == "__main__":
    unittest.main()
