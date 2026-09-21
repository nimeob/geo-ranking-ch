"""Factory for selecting the quota ledger backend.

Controlled via the ``QUOTA_STORE_BACKEND`` environment variable:

    none (default)  — NullQuotaLedger (legacy client-supplied quota fields)
    db              — DbQuotaLedger (Postgres, migration 004 tables)

Usage::

    from src.api.quota_store_factory import build_quota_ledger
    ledger = build_quota_ledger()

Environment variables:
    QUOTA_STORE_BACKEND   none | db     (default: none)
    QUOTA_DB_URL          postgresql://user:pass@host/dbname (backend=db)
    ASYNC_DB_URL          fallback for QUOTA_DB_URL
    DATABASE_URL          fallback for ASYNC_DB_URL

Reference: docs/VISION_GAP_ANALYSIS.md (G3).
"""

from __future__ import annotations

import logging
import os
from typing import Union

from src.shared.quota_ledger_db import DbQuotaLedger, NullQuotaLedger

logger = logging.getLogger(__name__)

AnyQuotaLedger = Union[DbQuotaLedger, NullQuotaLedger]

_VALID_BACKENDS = frozenset({"none", "db"})


def build_quota_ledger() -> AnyQuotaLedger:  # type: ignore[return]
    """Instantiate the configured quota ledger backend.

    Raises:
        ValueError: if QUOTA_STORE_BACKEND is set to an unknown value.
        RuntimeError: if backend=db but no DB URL is configured.
    """
    backend = os.getenv("QUOTA_STORE_BACKEND", "none").strip().lower()
    if backend not in _VALID_BACKENDS:
        raise ValueError(
            f"Unknown QUOTA_STORE_BACKEND={backend!r}. "
            f"Valid values: {sorted(_VALID_BACKENDS)}"
        )
    if backend == "db":
        logger.info("quota_store_factory: backend=db (DbQuotaLedger)")
        return DbQuotaLedger.from_env()

    logger.info("quota_store_factory: backend=none (NullQuotaLedger)")
    return NullQuotaLedger()
