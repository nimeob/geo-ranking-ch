"""
tests/test_db_migrate.py — Unit tests for scripts/db-migrate.py

Tests cover the pure-Python logic (file collection, checksum, CLI parsing)
without requiring a live Postgres connection.

Issue: #813 (DB-0.wp2 — migration runner + CI harness)
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Load module under test (not on sys.path by default)
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"

_spec = importlib.util.spec_from_file_location("db_migrate", SCRIPTS_DIR / "db-migrate.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# collect_migration_files
# ---------------------------------------------------------------------------

class TestCollectMigrationFiles:
    def test_returns_sorted_list(self):
        files = _mod.collect_migration_files()
        versions = [v for v, _ in files]
        assert versions == sorted(versions), "Migration files must be sorted lexicographically"

    def test_all_files_exist(self):
        for version, path in _mod.collect_migration_files():
            assert path.exists(), f"Migration file missing: {path}"
            assert path.suffix == ".sql", f"Expected .sql suffix: {path}"

    def test_at_least_one_migration_present(self):
        files = _mod.collect_migration_files()
        assert len(files) >= 1, "Expected at least one migration file in db/migrations/"

    def test_includes_core_schema(self):
        versions = [v for v, _ in _mod.collect_migration_files()]
        assert any("001" in v for v in versions), "Expected 001_core_schema migration"


# ---------------------------------------------------------------------------
# file_checksum
# ---------------------------------------------------------------------------

class TestFileChecksum:
    def test_sha256_hex(self, tmp_path):
        f = tmp_path / "test.sql"
        content = b"SELECT 1;"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert _mod.file_checksum(f) == expected

    def test_different_files_different_checksums(self, tmp_path):
        a = tmp_path / "a.sql"
        b = tmp_path / "b.sql"
        a.write_text("SELECT 1;")
        b.write_text("SELECT 2;")
        assert _mod.file_checksum(a) != _mod.file_checksum(b)

    def test_same_content_same_checksum(self, tmp_path):
        a = tmp_path / "a.sql"
        b = tmp_path / "b.sql"
        a.write_text("SELECT 1;")
        b.write_text("SELECT 1;")
        assert _mod.file_checksum(a) == _mod.file_checksum(b)

    def test_real_migrations_have_stable_checksums(self):
        """Checksums must be consistent across calls (deterministic)."""
        for _version, path in _mod.collect_migration_files():
            c1 = _mod.file_checksum(path)
            c2 = _mod.file_checksum(path)
            assert c1 == c2


# ---------------------------------------------------------------------------
# Migration SQL content validation
# ---------------------------------------------------------------------------

class TestMigrationContent:
    def test_core_schema_contains_expected_tables(self):
        """Verify 001_core_schema.sql defines the 4 canonical tables."""
        core = MIGRATIONS_DIR / "001_core_schema.sql"
        content = core.read_text()
        for table in ("organizations", "users", "memberships", "api_keys"):
            assert f"CREATE TABLE IF NOT EXISTS {table}" in content, \
                f"Expected table '{table}' in 001_core_schema.sql"

    def test_core_schema_no_plaintext_secret_comment(self):
        """api_keys must never store plaintext. Check schema comment."""
        core = MIGRATIONS_DIR / "001_core_schema.sql"
        content = core.read_text()
        # The schema should mention that full secret is never stored.
        assert "NEVER" in content or "never" in content, \
            "api_keys schema should document that plaintext tokens are never stored"

    def test_async_jobs_schema_contains_jobs_table(self):
        async_schema = MIGRATIONS_DIR / "002_async_jobs_schema.sql"
        content = async_schema.read_text()
        assert "CREATE TABLE IF NOT EXISTS jobs" in content

    def test_migration_files_wrapped_in_transactions(self):
        """All migrations should be wrapped in BEGIN/COMMIT."""
        for version, path in _mod.collect_migration_files():
            content = path.read_text()
            assert "BEGIN;" in content or "BEGIN\n" in content, \
                f"{version}: migration should start with BEGIN;"
            assert "COMMIT;" in content or "COMMIT\n" in content, \
                f"{version}: migration should end with COMMIT;"


# ---------------------------------------------------------------------------
# get_db_url (env var handling)
# ---------------------------------------------------------------------------

class TestGetDbUrl:
    def test_missing_env_raises_systemexit(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            _mod.get_db_url()
        assert exc_info.value.code == 1

    def test_set_env_returns_value(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")
        assert _mod.get_db_url() == "postgresql://user:pass@localhost:5432/test"

    def test_whitespace_stripped(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "  postgresql://user:pass@localhost:5432/test  ")
        url = _mod.get_db_url()
        assert url == "postgresql://user:pass@localhost:5432/test"


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestArgParsing:
    def test_status_flag(self):
        args = _mod.parse_args.__wrapped__() if hasattr(_mod.parse_args, "__wrapped__") else None
        # Use direct argv patching
        with patch("sys.argv", ["db-migrate.py", "--status"]):
            args = _mod.parse_args()
        assert args.status is True
        assert args.apply is False
        assert args.dry_run is False

    def test_apply_flag(self):
        with patch("sys.argv", ["db-migrate.py", "--apply"]):
            args = _mod.parse_args()
        assert args.apply is True

    def test_dry_run_flag(self):
        with patch("sys.argv", ["db-migrate.py", "--dry-run"]):
            args = _mod.parse_args()
        assert args.dry_run is True

    def test_check_flag(self):
        with patch("sys.argv", ["db-migrate.py", "--check"]):
            args = _mod.parse_args()
        assert args.check is True

    def test_target_option(self):
        with patch("sys.argv", ["db-migrate.py", "--apply", "--target", "001_core_schema"]):
            args = _mod.parse_args()
        assert args.target == "001_core_schema"

    def test_db_url_option(self):
        with patch("sys.argv", ["db-migrate.py", "--status", "--db-url", "postgresql://x:y@localhost/z"]):
            args = _mod.parse_args()
        assert args.db_url == "postgresql://x:y@localhost/z"

    def test_mutually_exclusive_flags_error(self):
        with patch("sys.argv", ["db-migrate.py", "--apply", "--dry-run"]):
            with pytest.raises(SystemExit) as exc_info:
                _mod.parse_args()
            assert exc_info.value.code == 2

    def test_no_flags_error(self):
        with patch("sys.argv", ["db-migrate.py"]):
            with pytest.raises(SystemExit) as exc_info:
                _mod.parse_args()
            assert exc_info.value.code == 2
