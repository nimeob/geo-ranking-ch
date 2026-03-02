"""Factory for selecting the async job store backend.

Controlled via the ``ASYNC_STORE_BACKEND`` environment variable:

    file (default)  — file-backed AsyncJobStore (runtime/async_jobs/store.v1.json)
    db              — Postgres-backed DbAsyncJobStore (requires ASYNC_DB_URL)

Usage::

    from src.api.async_store_factory import build_async_job_store
    store = build_async_job_store()

Environment variables:
    ASYNC_STORE_BACKEND   file | db     (default: file)
    ASYNC_DB_URL          postgresql://user:pass@host/dbname  (required when backend=db)
    DATABASE_URL          fallback for ASYNC_DB_URL
    ASYNC_JOBS_STORE_FILE path to JSON store file              (used when backend=file)

Issue: #840 (ASYNC-DB-0.wp3)
"""

from __future__ import annotations

import logging
import os
from typing import Union

logger = logging.getLogger(__name__)

# Type alias for the union of both store types (avoids importing both at module level)
AnyJobStore = Union["AsyncJobStore", "DbAsyncJobStore"]  # type: ignore[name-defined]

_VALID_BACKENDS = frozenset({"file", "db"})


def build_async_job_store() -> AnyJobStore:  # type: ignore[return]
    """Instantiate the configured job store backend.

    Returns either an ``AsyncJobStore`` (file) or ``DbAsyncJobStore`` (db)
    depending on ``ASYNC_STORE_BACKEND``.

    Raises:
        ValueError: if ASYNC_STORE_BACKEND is set to an unknown value.
        RuntimeError: if backend=db but ASYNC_DB_URL / DATABASE_URL is missing.
    """
    backend = os.getenv("ASYNC_STORE_BACKEND", "file").strip().lower()

    if backend not in _VALID_BACKENDS:
        raise ValueError(
            f"Unknown ASYNC_STORE_BACKEND={backend!r}. "
            f"Valid values: {sorted(_VALID_BACKENDS)}"
        )

    if backend == "db":
        logger.info("async_store_factory: backend=db (DbAsyncJobStore)")
        from src.shared.async_job_store_db import DbAsyncJobStore  # noqa: PLC0415
        return DbAsyncJobStore.from_env()

    # Default: file backend
    logger.info("async_store_factory: backend=file (AsyncJobStore)")
    from src.api.async_jobs import AsyncJobStore  # noqa: PLC0415
    return AsyncJobStore.from_env()
