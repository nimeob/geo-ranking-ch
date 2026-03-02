"""
tests/test_async_store_factory.py

Tests for src/shared/async_store_factory.py.

Verifies:
- ASYNC_STORE_BACKEND=file (default) → AsyncJobStore
- ASYNC_STORE_BACKEND=db → DbAsyncJobStore (when ASYNC_DB_URL set)
- ASYNC_STORE_BACKEND=<unknown> → ValueError
- ASYNC_STORE_BACKEND=db without DB URL → RuntimeError
- Default (no env var) → AsyncJobStore (file backend)

Issue: #840 (ASYNC-DB-0.wp3)
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch


class TestBuildAsyncJobStore(unittest.TestCase):

    def _import_factory(self):
        # Re-import to avoid cached module state between tests
        import importlib
        import src.shared.async_store_factory as mod
        importlib.reload(mod)
        return mod.build_async_job_store

    def test_default_backend_is_file(self):
        """No env var → file backend → AsyncJobStore."""
        env = {k: v for k, v in os.environ.items() if k != "ASYNC_STORE_BACKEND"}
        env.pop("ASYNC_STORE_BACKEND", None)
        env.setdefault("ASYNC_JOBS_STORE_FILE", "/tmp/test_store_default.json")

        with patch.dict(os.environ, env, clear=True):
            from src.shared.async_store_factory import build_async_job_store
            from src.api.async_jobs import AsyncJobStore
            store = build_async_job_store()
            self.assertIsInstance(store, AsyncJobStore)

    def test_explicit_file_backend(self):
        """ASYNC_STORE_BACKEND=file → AsyncJobStore."""
        env = {
            "ASYNC_STORE_BACKEND": "file",
            "ASYNC_JOBS_STORE_FILE": "/tmp/test_store_file.json",
        }
        with patch.dict(os.environ, env, clear=True):
            from src.shared.async_store_factory import build_async_job_store
            from src.api.async_jobs import AsyncJobStore
            store = build_async_job_store()
            self.assertIsInstance(store, AsyncJobStore)

    def test_db_backend_without_url_raises_runtime_error(self):
        """ASYNC_STORE_BACKEND=db without DB URL → RuntimeError."""
        env = {"ASYNC_STORE_BACKEND": "db"}
        # Ensure no DB URL leaks from real env
        env_clean = {k: v for k, v in os.environ.items()
                     if k not in ("ASYNC_DB_URL", "DATABASE_URL", "ASYNC_STORE_BACKEND")}
        env_clean["ASYNC_STORE_BACKEND"] = "db"

        with patch.dict(os.environ, env_clean, clear=True):
            from src.shared.async_store_factory import build_async_job_store
            with self.assertRaises(RuntimeError):
                build_async_job_store()

    def test_unknown_backend_raises_value_error(self):
        """Unknown ASYNC_STORE_BACKEND value → ValueError."""
        with patch.dict(os.environ, {"ASYNC_STORE_BACKEND": "redis"}):
            from src.shared.async_store_factory import build_async_job_store
            with self.assertRaises(ValueError) as ctx:
                build_async_job_store()
            self.assertIn("redis", str(ctx.exception))

    def test_db_backend_with_url_returns_db_store(self):
        """ASYNC_STORE_BACKEND=db with ASYNC_DB_URL → DbAsyncJobStore (psycopg2 mocked)."""
        env = {
            "ASYNC_STORE_BACKEND": "db",
            "ASYNC_DB_URL": "postgresql://u:p@localhost/testdb",
        }
        with patch.dict(os.environ, env, clear=False):
            # Mock psycopg2 so no real connection is attempted
            mock_psycopg2 = MagicMock()
            with patch.dict("sys.modules", {"psycopg2": mock_psycopg2}):
                from src.shared.async_store_factory import build_async_job_store
                from src.shared.async_job_store_db import DbAsyncJobStore
                store = build_async_job_store()
                self.assertIsInstance(store, DbAsyncJobStore)

    def test_file_backend_unaffected_by_db_url(self):
        """ASYNC_STORE_BACKEND=file should not use DB even if ASYNC_DB_URL is set."""
        env = {
            "ASYNC_STORE_BACKEND": "file",
            "ASYNC_DB_URL": "postgresql://u:p@localhost/testdb",
            "ASYNC_JOBS_STORE_FILE": "/tmp/test_store_fileonly.json",
        }
        with patch.dict(os.environ, env, clear=True):
            from src.shared.async_store_factory import build_async_job_store
            from src.api.async_jobs import AsyncJobStore
            store = build_async_job_store()
            self.assertIsInstance(store, AsyncJobStore)

    def test_backend_value_is_case_insensitive(self):
        """ASYNC_STORE_BACKEND=FILE → still treated as file."""
        env = {
            "ASYNC_STORE_BACKEND": "FILE",
            "ASYNC_JOBS_STORE_FILE": "/tmp/test_store_upper.json",
        }
        with patch.dict(os.environ, env, clear=True):
            from src.shared.async_store_factory import build_async_job_store
            from src.api.async_jobs import AsyncJobStore
            store = build_async_job_store()
            self.assertIsInstance(store, AsyncJobStore)


class TestWebServiceImportDoesNotBreak(unittest.TestCase):
    """Smoke-check: web_service module can still be imported with the factory change."""

    def test_build_async_job_store_importable_from_web_service_module(self):
        """The factory is imported in web_service; verify the symbol exists there."""
        import importlib
        import src.api.web_service as ws_mod
        self.assertTrue(
            hasattr(ws_mod, "build_async_job_store"),
            "build_async_job_store must be importable from web_service",
        )


if __name__ == "__main__":
    unittest.main()
