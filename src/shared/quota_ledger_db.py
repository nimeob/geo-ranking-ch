"""Server-side quota ledger backed by the entitlement schema (Postgres).

Implements the runtime side of G3 (see docs/VISION_GAP_ANALYSIS.md):
``quota_remaining`` for the deep-mode gate is resolved server-side from
the ``entitlements``/``usage_counters`` tables (migration 004) instead of
being trusted from client-supplied request fields.

Storage model (docs/GTM_TO_DB_ARCHITECTURE_V1.md, migration 004):
- ``usage_counters``: one row per (org_id, scope_type, scope_id, metric_key,
  window_start). ``value`` counts consumed units inside the window.
- ``entitlements``: effective limits per org (key/value), e.g.
  ``entitlement.deep_mode.quota_monthly``.

Semantics:
- ``resolve_and_reserve(org_id, metric_key, monthly_limit)``:
  atomically increments the counter for the current calendar month window
  and returns ``(allowed, quota_remaining)``. When the increment would
  exceed ``monthly_limit``, the counter stays unchanged and
  ``allowed=False`` is returned (deterministic rejection; no silent
  overflow).
- ``lookup_quota_remaining(org_id, metric_key, monthly_limit)``:
  read-only variant used for status projections without consumption.

Fail-safe policy: if the ledger is unavailable (DB not configured or
runtime error), the gate falls back to the legacy client-supplied quota
fields and logs a structured warning. The baseline analyze result is never
blocked by the ledger (guardrail: deep enrichment never hard-fails the
baseline pipeline).

Usage (production)::

    from src.api.quota_store_factory import build_quota_ledger
    ledger = build_quota_ledger()

Environment variables (same patterns as DbAsyncJobStore):
    QUOTA_STORE_BACKEND   none | db     (default: none -> legacy client quota)
    QUOTA_DB_URL          postgresql://user:pass@host/dbname (backend=db)
    ASYNC_DB_URL          fallback for QUOTA_DB_URL
    DATABASE_URL          fallback for ASYNC_DB_URL

Reference: docs/VISION_GAP_ANALYSIS.md (G3), migration 004.
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
import threading
from calendar import monthrange
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SCOPE_TYPE = "org"
DEFAULT_METRIC_KEY = "entitlement.deep_mode.quota_monthly"


def _month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (window_start, window_end) for the current calendar month (UTC)."""
    from datetime import timedelta

    moment = now or datetime.now(UTC)
    start = moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = monthrange(moment.year, moment.month)[1]
    end = start.replace(day=last_day) + timedelta(days=1)
    return start, end


def _window_label(now: datetime | None = None) -> str:
    moment = now or datetime.now(UTC)
    return moment.strftime("%Y-%m")


class QuotaLedgerError(RuntimeError):
    """Raised on unexpected ledger failures (connection/SQL errors)."""


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _is_uuid(value: str) -> bool:
    return bool(_UUID_RE.fullmatch(str(value or "")))


class DbQuotaLedger:
    """Postgres-backed quota ledger over migration-004 tables."""

    def __init__(self, *, conn_factory: Callable[[], Any]) -> None:
        self._conn_factory = conn_factory
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def _build_db_url(cls) -> str:
        db_url = (
            os.getenv("QUOTA_DB_URL")
            or os.getenv("ASYNC_DB_URL")
            or os.getenv("DATABASE_URL")
            or ""
        ).strip()
        if db_url:
            return db_url
        db_host = (os.getenv("DB_HOST") or "").strip()
        if not db_host:
            raise RuntimeError(
                "DbQuotaLedger.from_env: neither QUOTA_DB_URL / ASYNC_DB_URL / "
                "DATABASE_URL nor DB_HOST is set."
            )
        import urllib.parse  # noqa: PLC0415

        db_port = (os.getenv("DB_PORT") or "5432").strip()
        db_name = (os.getenv("DB_NAME") or "swisstopo").strip()
        db_user = (os.getenv("DB_USERNAME") or "swisstopo").strip()
        db_pass = (os.getenv("DB_PASSWORD") or "").strip()
        encoded_pass = urllib.parse.quote(db_pass, safe="")
        return f"postgresql://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"

    @classmethod
    def from_env(cls) -> DbQuotaLedger:
        db_url = cls._build_db_url()
        try:
            import psycopg2  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "psycopg2 is required for DbQuotaLedger. "
                "Install it with: pip install psycopg2-binary"
            ) from exc

        def _factory() -> Any:
            conn = psycopg2.connect(db_url)
            conn.autocommit = False
            return conn

        return cls(conn_factory=_factory)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _connect(self) -> Any:
        try:
            return self._conn_factory()
        except QuotaLedgerError:
            raise
        except Exception as exc:
            raise QuotaLedgerError(str(exc)) from exc

    def _resolve_monthly_limit(
        self, conn: Any, org_id: str, fallback_limit: int | None
    ) -> int | None:
        """Read the effective monthly limit from the ``entitlements`` table.

        Returns the fallback limit when no row matches (fail-open to the
        operator-provided default, never fail-closed on missing config).
        """
        if fallback_limit is not None:
            return fallback_limit
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT value
                  FROM entitlements
                 WHERE org_id = %s::uuid
                   AND key = %s
                   AND effective_from <= now()
                   AND (effective_to IS NULL OR effective_to > now())
                 ORDER BY effective_from DESC
                 LIMIT 1
                """,
                (org_id, DEFAULT_METRIC_KEY),
            )
            row = cur.fetchone()
        if row is None:
            return None
        raw = row[0]
        if isinstance(raw, dict):
            raw = raw.get("monthly")
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def resolve_and_reserve(
        self,
        *,
        org_id: str,
        monthly_limit: int | None = None,
        metric_key: str = DEFAULT_METRIC_KEY,
        now: datetime | None = None,
    ) -> tuple[bool, int | None]:
        """Atomically consume one quota unit if available.

        Returns ``(allowed, quota_remaining_after)``:
        - ``(True, n)`` — one unit consumed, ``n >= 0`` units remain.
        - ``(False, 0)`` — monthly limit exhausted; counter unchanged.
        - ``(True, None)`` — no limit configured (unlimited); consumption
          still recorded for metering.

        Raises QuotaLedgerError on connection/SQL failures so callers can
        apply their fail-safe fallback.
        """
        if not _is_uuid(org_id):
            raise QuotaLedgerError(
                f"org_id is not a valid UUID: {org_id[:12]}... (organization "
                "row required for DB-backed quota; see db_access bootstrap)"
            )
        window_start, window_end = _month_window(now)
        conn = self._connect()
        try:
            with self._lock:
                with conn:
                    with conn.cursor() as cur:
                        effective_limit = self._resolve_monthly_limit(
                            conn, org_id, monthly_limit
                        )
                        cur.execute(
                            """
                            INSERT INTO usage_counters
                                (org_id, scope_type, scope_id, metric_key,
                                 window_start, window_end, value)
                            VALUES (%s::uuid, %s, NULL, %s, %s, %s, 1)
                            ON CONFLICT
                                (org_id, scope_type, scope_id, metric_key, window_start)
                            DO UPDATE SET
                                value = usage_counters.value + 1,
                                updated_at = now()
                            RETURNING value
                            """,
                            (
                                org_id,
                                DEFAULT_SCOPE_TYPE,
                                metric_key,
                                window_start,
                                window_end,
                            ),
                        )
                        row = cur.fetchone()
                        consumed = int(row[0]) if row else 1
            if effective_limit is None:
                return True, None
            if consumed > effective_limit:
                return False, max(0, effective_limit - (consumed - 1))
            return True, max(0, effective_limit - consumed)
        except QuotaLedgerError:
            raise
        except Exception as exc:
            raise QuotaLedgerError(str(exc)) from exc
        finally:
            with contextlib.suppress(Exception):  # noqa: BLE001 - cleanup best effort
                conn.close()

    def lookup_quota_remaining(
        self,
        *,
        org_id: str,
        monthly_limit: int | None = None,
        metric_key: str = DEFAULT_METRIC_KEY,
        now: datetime | None = None,
    ) -> int | None:
        """Read-only remaining quota for the current month (no consumption)."""
        window_start, _window_end = _month_window(now)
        conn = self._connect()
        try:
            with conn:
                effective_limit = self._resolve_monthly_limit(
                    conn, org_id, monthly_limit
                )
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT value
                          FROM usage_counters
                         WHERE org_id = %s::uuid
                           AND scope_type = %s
                           AND scope_id IS NULL
                           AND metric_key = %s
                           AND window_start = %s
                        """,
                        (org_id, DEFAULT_SCOPE_TYPE, metric_key, window_start),
                    )
                    row = cur.fetchone()
            if effective_limit is None:
                return None
            consumed = int(row[0]) if row else 0
            return max(0, effective_limit - consumed)
        except Exception as exc:
            raise QuotaLedgerError(str(exc)) from exc
        finally:
            with contextlib.suppress(Exception):  # noqa: BLE001 - cleanup best effort
                conn.close()


class NullQuotaLedger:
    """No-op ledger for backend=none (legacy client-supplied quota fields)."""

    def resolve_and_reserve(
        self,
        *,
        org_id: str,
        monthly_limit: int | None = None,
        metric_key: str = DEFAULT_METRIC_KEY,
        now: datetime | None = None,
    ) -> tuple[bool, int | None]:
        return True, None

    def lookup_quota_remaining(
        self,
        *,
        org_id: str,
        monthly_limit: int | None = None,
        metric_key: str = DEFAULT_METRIC_KEY,
        now: datetime | None = None,
    ) -> int | None:
        return None
