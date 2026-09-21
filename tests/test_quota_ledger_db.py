"""tests/test_quota_ledger_db.py

Unit tests for DbQuotaLedger (src/shared/quota_ledger_db.py) and the
web_service binding (_resolve_server_side_deep_quota,
_reserve_deep_quota_unit).

Strategy: mock the psycopg2 connection/cursor (same pattern as
tests/test_async_job_store_db.py) to verify:

  - resolve_and_reserve: atomic upsert SQL, exhaustion semantics
    (allowed=False, counter unchanged), unlimited (True, None)
  - _resolve_monthly_limit: reads entitlements table, fallback to param
  - org_id must be a UUID (else QuotaLedgerError)
  - NullQuotaLedger is a no-op
  - web_service helpers fall back to client quota on ledger errors
    (fail-safe: baseline never blocked)

No live DB required.

Issue: G3 (docs/VISION_GAP_ANALYSIS.md)
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from src.api import web_service
from src.shared.quota_ledger_db import (
    DEFAULT_METRIC_KEY,
    DEFAULT_SCOPE_TYPE,
    DbQuotaLedger,
    NullQuotaLedger,
    QuotaLedgerError,
)

ORG_UUID = "11111111-1111-1111-1111-111111111111"


def _make_conn_factory(fetchone_values=None, fetchall_values=None, rowcount=1):
    """Return a conn_factory whose cursor reports preset fetch results."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = fetchone_values or [None]
    mock_cursor.fetchall.return_value = fetchall_values or []
    mock_cursor.rowcount = rowcount
    mock_cursor.__enter__ = lambda s: mock_cursor
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    return (lambda: mock_conn), mock_cursor, mock_conn


def _get_executed_sqls(mock_cursor: MagicMock) -> list[str]:
    sqls = []
    for c in mock_cursor.execute.call_args_list:
        args = c[0]
        if args:
            sqls.append(str(args[0]))
    return sqls


class TestResolveAndReserve(unittest.TestCase):
    """resolve_and_reserve: atomic upsert + windowed limit semantics."""

    def test_reserve_within_limit_returns_true_and_remaining(self):
        factory, mock_cursor, _ = _make_conn_factory(
            fetchone_values=[({"monthly": 10},), (5,)]
        )
        ledger = DbQuotaLedger(conn_factory=factory)
        allowed, remaining = ledger.resolve_and_reserve(org_id=ORG_UUID)
        self.assertTrue(allowed)
        self.assertEqual(remaining, 5)

    def test_reserve_uses_atomic_upsert_on_usage_counters(self):
        factory, mock_cursor, _ = _make_conn_factory(
            fetchone_values=[({"monthly": 10},), (5,)]
        )
        ledger = DbQuotaLedger(conn_factory=factory)
        ledger.resolve_and_reserve(org_id=ORG_UUID)
        sqls = "\n".join(_get_executed_sqls(mock_cursor))
        self.assertIn("INSERT INTO usage_counters", sqls)
        self.assertIn("ON CONFLICT", sqls)
        self.assertIn("RETURNING value", sqls)
        self.assertIn("usage_counters.value + 1", sqls)

    def test_reserve_exhausted_returns_false_without_counter_rollback_gap(self):
        # consumed=11 > limit=10 -> (False, 0): deterministic rejection
        factory, _, _ = _make_conn_factory(fetchone_values=[({"monthly": 10},), (11,)])
        ledger = DbQuotaLedger(conn_factory=factory)
        allowed, remaining = ledger.resolve_and_reserve(org_id=ORG_UUID)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)

    def test_reserve_unlimited_when_no_limit_configured(self):
        # no entitlement row (None) and no fallback -> unlimited consumption
        factory, _, _ = _make_conn_factory(fetchone_values=[None, (3,)])
        ledger = DbQuotaLedger(conn_factory=factory)
        allowed, remaining = ledger.resolve_and_reserve(org_id=ORG_UUID)
        self.assertTrue(allowed)
        self.assertIsNone(remaining)

    def test_fallback_limit_param_wins_without_entitlement_query(self):
        factory, mock_cursor, _ = _make_conn_factory(fetchone_values=[(5,)])
        ledger = DbQuotaLedger(conn_factory=factory)
        allowed, remaining = ledger.resolve_and_reserve(
            org_id=ORG_UUID, monthly_limit=7
        )
        self.assertTrue(allowed)
        self.assertEqual(remaining, 2)
        sqls = "\n".join(_get_executed_sqls(mock_cursor))
        self.assertNotIn("FROM entitlements", sqls)

    def test_non_uuid_org_id_raises_quota_ledger_error(self):
        factory, _, _ = _make_conn_factory()
        ledger = DbQuotaLedger(conn_factory=factory)
        with self.assertRaises(QuotaLedgerError):
            ledger.resolve_and_reserve(org_id="default-org")

    def test_connection_error_wrapped_as_quota_ledger_error(self):
        def _broken_factory():
            raise RuntimeError("connection refused")

        ledger = DbQuotaLedger(conn_factory=_broken_factory)
        with self.assertRaises(QuotaLedgerError):
            ledger.resolve_and_reserve(org_id=ORG_UUID)


class TestLookupQuotaRemaining(unittest.TestCase):
    """lookup_quota_remaining: read-only windowed status projection."""

    def test_lookup_returns_limit_minus_consumed(self):
        factory, mock_cursor, _ = _make_conn_factory(
            fetchone_values=[({"monthly": 10},), (4,)]
        )
        ledger = DbQuotaLedger(conn_factory=factory)
        remaining = ledger.lookup_quota_remaining(org_id=ORG_UUID)
        self.assertEqual(remaining, 6)

    def test_lookup_unlimited_when_no_limit(self):
        factory, _, _ = _make_conn_factory(fetchone_values=[None, (4,)])
        ledger = DbQuotaLedger(conn_factory=factory)
        remaining = ledger.lookup_quota_remaining(org_id=ORG_UUID)
        self.assertIsNone(remaining)

    def test_lookup_no_counter_row_counts_zero_consumed(self):
        factory, _, _ = _make_conn_factory(fetchone_values=[({"monthly": 10},), None])
        ledger = DbQuotaLedger(conn_factory=factory)
        remaining = ledger.lookup_quota_remaining(org_id=ORG_UUID)
        self.assertEqual(remaining, 10)

    def test_lookup_reads_scope_and_metric_key(self):
        factory, mock_cursor, _ = _make_conn_factory(
            fetchone_values=[({"monthly": 10},), (0,)]
        )
        ledger = DbQuotaLedger(conn_factory=factory)
        ledger.lookup_quota_remaining(org_id=ORG_UUID)
        sqls = "\n".join(_get_executed_sqls(mock_cursor))
        self.assertIn("FROM usage_counters", sqls)
        params_used = [c[0][1] for c in mock_cursor.execute.call_args_list if c[0]]
        self.assertTrue(
            any(
                isinstance(p, (list, tuple))
                and DEFAULT_SCOPE_TYPE in p
                and DEFAULT_METRIC_KEY in p
                for p in params_used
            ),
            "lookup must filter by scope_type and metric_key",
        )


class TestNullQuotaLedger(unittest.TestCase):
    """NullQuotaLedger: no-op for backend=none (legacy client quota)."""

    def test_reserve_is_noop_unlimited(self):
        ledger = NullQuotaLedger()
        self.assertEqual(ledger.resolve_and_reserve(org_id="anything"), (True, None))

    def test_lookup_is_noop(self):
        ledger = NullQuotaLedger()
        self.assertIsNone(ledger.lookup_quota_remaining(org_id="anything"))


_RUNTIME_ENV_DEFAULTS = {
    "DEEP_BASELINE_RESERVED_FLOOR_MS": "1000",
    "DEEP_BASELINE_RESERVED_RATIO": "0.7",
    "DEEP_SAFETY_MARGIN_MS": "250",
    "DEEP_MIN_BUDGET_MS": "600",
    "DEEP_MAX_TOKENS_SERVER": "12000",
    "DEEP_PROFILE_CAP_ANALYSIS_PLUS": "12000",
    "DEEP_PROFILE_CAP_RISK_PLUS": "9000",
}


class TestWebServiceQuotaBinding(unittest.TestCase):
    """web_service helpers: fail-safe fallback to client quota."""

    def _apply(self, options, owner_org_id=None, ledger=None):
        report: dict = {}
        with patch.dict(os.environ, _RUNTIME_ENV_DEFAULTS, clear=False):
            with patch.object(web_service, "_QUOTA_LEDGER", ledger):
                web_service._apply_deep_mode_runtime_status(
                    report,
                    options=options,
                    intelligence_mode="basic",
                    timeout_seconds=5.0,
                    owner_org_id=owner_org_id,
                )
        return report

    def test_db_ledger_replaces_client_quota_when_active(self):
        factory, _, _ = _make_conn_factory(
            fetchone_values=[({"monthly": 10},), (2,)]  # lookup, then reserve
        )
        ledger = DbQuotaLedger(conn_factory=factory)
        options = {
            "capabilities": {
                "deep_mode": {"requested": True, "profile": "analysis_plus"}
            },
            "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 999}},
        }
        report = self._apply(options, owner_org_id=ORG_UUID, ledger=ledger)
        deep_mode = report.get("capabilities_status", {}).get("deep_mode", {})
        self.assertTrue(deep_mode.get("effective"))

    def test_ledger_error_falls_back_to_client_quota(self):
        def _broken_factory():
            raise RuntimeError("db down")

        ledger = DbQuotaLedger(conn_factory=_broken_factory)
        options = {
            "capabilities": {
                "deep_mode": {"requested": True, "profile": "analysis_plus"}
            },
            "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 3}},
        }
        report = self._apply(options, owner_org_id=ORG_UUID, ledger=ledger)
        deep_mode = report.get("capabilities_status", {}).get("deep_mode", {})
        self.assertTrue(deep_mode.get("effective"))

    def test_ledger_exhausted_downgrades_deep_mode(self):
        # lookup: limit 10, consumed 1 -> 9 remaining -> gate passes;
        # reserve: limit 10 again, consumed 11 > 10 -> deterministic reject
        factory, _, _ = _make_conn_factory(
            fetchone_values=[
                ({"monthly": 10},),
                (1,),
                ({"monthly": 10},),
                (11,),
            ]
        )
        ledger = DbQuotaLedger(conn_factory=factory)
        options = {
            "capabilities": {
                "deep_mode": {"requested": True, "profile": "analysis_plus"}
            },
            "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 999}},
        }
        report = self._apply(options, owner_org_id=ORG_UUID, ledger=ledger)
        deep_mode = report.get("capabilities_status", {}).get("deep_mode", {})
        self.assertFalse(deep_mode.get("effective"))
        self.assertEqual(deep_mode.get("fallback_reason"), "quota_exhausted")

    def test_null_ledger_keeps_client_quota_path(self):
        options = {
            "capabilities": {
                "deep_mode": {"requested": True, "profile": "analysis_plus"}
            },
            "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 5}},
        }
        report = self._apply(options, owner_org_id=ORG_UUID, ledger=NullQuotaLedger())
        deep_mode = report.get("capabilities_status", {}).get("deep_mode", {})
        self.assertTrue(deep_mode.get("effective"))

    def test_non_uuid_org_id_fails_open_to_client_quota(self):
        options = {
            "capabilities": {
                "deep_mode": {"requested": True, "profile": "analysis_plus"}
            },
            "entitlements": {"deep_mode": {"allowed": True, "quota_remaining": 5}},
        }
        factory, _, _ = _make_conn_factory(fetchone_values=[({"monthly": 10},), (1,)])
        ledger = DbQuotaLedger(conn_factory=factory)
        report = self._apply(options, owner_org_id="default-org", ledger=ledger)
        deep_mode = report.get("capabilities_status", {}).get("deep_mode", {})
        self.assertTrue(deep_mode.get("effective"))


if __name__ == "__main__":
    unittest.main()
