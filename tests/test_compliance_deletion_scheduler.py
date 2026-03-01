"""Tests for src/compliance/deletion_scheduler.py  (Issue #522).

DoD coverage:
  - [x] Deletion can be scheduled with notice_period_days
  - [x] Notification fires when notice window opens (tick at notify_after)
  - [x] Final deletion executes after execute_after (tick at execute_after)
  - [x] E2E: schedule → notify → execute lifecycle
  - [x] Cancel before notification → status=canceled, no execution
  - [x] Cancel after notification → status=canceled, no execution
  - [x] Already-executed deletion cannot be canceled
  - [x] Hold blocks scheduling
  - [x] Hold acquired after scheduling blocks tick execution
  - [x] Acceptance: "End-to-End-Test erfolgreich"
  - [x] Multiple records for different documents are independent
  - [x] delete_reason and requested_by_role are required
"""

import unittest
from datetime import datetime, timedelta, timezone

from src.compliance.deletion_scheduler import DeletionScheduler, DeletionStatus


_NOW = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc)

_BASE_SCHEDULE = dict(
    execute_after=_NOW + timedelta(days=14),
    requested_by_role="Compliance Lead",
    delete_reason="Aufbewahrungsfrist abgelaufen; Löschung gemäß Kontrollplan #518",
)


def _ts(offset_days: float = 0, offset_hours: float = 0) -> datetime:
    return _NOW + timedelta(days=offset_days, hours=offset_hours)


class TestDeletionSchedulerE2E(unittest.TestCase):
    """Acceptance: End-to-End-Test — schedule → notified → executed."""

    def test_e2e_full_lifecycle(self):
        notifications: list = []
        executions: list = []

        scheduler = DeletionScheduler(
            default_notice_period_days=7,
            on_notify=notifications.append,
            on_execute=executions.append,
        )

        # 1. Schedule deletion: execute_after = +14 days, notice = 7 days
        record = scheduler.schedule(
            "DOC-E2E-001",
            **_BASE_SCHEDULE,  # execute_after = +14 days
            notice_period_days=7,
        )
        self.assertEqual(record.status, DeletionStatus.PENDING)
        # notify_after = execute_after − 7 days = +7 days
        self.assertEqual(record.notify_after, _ts(7))

        # 2. Tick before notice window — nothing happens
        result = scheduler.tick(now=_ts(6))
        self.assertEqual(result, {"notified": [], "executed": []})
        self.assertEqual(record.status, DeletionStatus.PENDING)

        # 3. Tick at notify_after — notification fires
        result = scheduler.tick(now=_ts(7))
        self.assertIn(record.record_id, result["notified"])
        self.assertEqual(record.status, DeletionStatus.NOTIFIED)
        self.assertIsNotNone(record.notified_at)
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].record_id, record.record_id)

        # 4. Tick after notification but before execute_after — nothing new
        result = scheduler.tick(now=_ts(10))
        self.assertEqual(result["executed"], [])
        self.assertEqual(len(executions), 0)

        # 5. Tick at execute_after — deletion executes
        result = scheduler.tick(now=_ts(14))
        self.assertIn(record.record_id, result["executed"])
        self.assertEqual(record.status, DeletionStatus.EXECUTED)
        self.assertIsNotNone(record.executed_at)
        self.assertEqual(len(executions), 1)
        self.assertEqual(executions[0].record_id, record.record_id)

        # 6. Further ticks are no-ops for completed records
        result = scheduler.tick(now=_ts(20))
        self.assertEqual(result, {"notified": [], "executed": []})


class TestDeletionScheduling(unittest.TestCase):
    def _sched(self, **kwargs) -> tuple[DeletionScheduler, any]:
        scheduler = DeletionScheduler(default_notice_period_days=7)
        record = scheduler.schedule("DOC-001", **{**_BASE_SCHEDULE, **kwargs})
        return scheduler, record

    def test_schedule_creates_pending_record(self):
        _, record = self._sched()
        self.assertEqual(record.status, DeletionStatus.PENDING)
        self.assertIsNotNone(record.record_id)
        self.assertIsNone(record.notified_at)
        self.assertIsNone(record.executed_at)

    def test_notify_after_is_execute_after_minus_notice(self):
        _, record = self._sched(notice_period_days=5)
        expected = _BASE_SCHEDULE["execute_after"] - timedelta(days=5)
        self.assertEqual(record.notify_after, expected)

    def test_zero_notice_period_immediate_notify(self):
        scheduler = DeletionScheduler(default_notice_period_days=0)
        record = scheduler.schedule("DOC-ZERO", **_BASE_SCHEDULE)
        # notify_after == execute_after
        self.assertEqual(record.notify_after, record.execute_after)

    def test_missing_delete_reason_raises(self):
        scheduler = DeletionScheduler()
        with self.assertRaises(ValueError):
            scheduler.schedule(
                "DOC-X",
                execute_after=_ts(14),
                requested_by_role="Compliance Lead",
                delete_reason="",
            )

    def test_missing_requested_by_role_raises(self):
        scheduler = DeletionScheduler()
        with self.assertRaises(ValueError):
            scheduler.schedule(
                "DOC-X",
                execute_after=_ts(14),
                requested_by_role="",
                delete_reason="Frist abgelaufen",
            )

    def test_empty_document_id_raises(self):
        scheduler = DeletionScheduler()
        with self.assertRaises(ValueError):
            scheduler.schedule("", **_BASE_SCHEDULE)

    def test_naive_execute_after_raises(self):
        scheduler = DeletionScheduler()
        naive = datetime(2026, 3, 20, 0, 0, 0)  # no tzinfo
        with self.assertRaises(ValueError):
            scheduler.schedule("DOC-X", execute_after=naive,
                               requested_by_role="Compliance Lead",
                               delete_reason="Frist abgelaufen")

    def test_hold_blocks_scheduling(self):
        scheduler = DeletionScheduler()
        scheduler.set_hold("DOC-HELD")
        with self.assertRaises(RuntimeError):
            scheduler.schedule("DOC-HELD", **_BASE_SCHEDULE)

    def test_list_records_by_status(self):
        scheduler = DeletionScheduler(default_notice_period_days=7)
        r1 = scheduler.schedule("DOC-A", **_BASE_SCHEDULE)
        r2 = scheduler.schedule("DOC-B", **_BASE_SCHEDULE)
        pending = scheduler.list_records(status=DeletionStatus.PENDING)
        self.assertEqual({r.record_id for r in pending}, {r1.record_id, r2.record_id})


class TestDeletionCancellation(unittest.TestCase):
    def test_cancel_pending_record(self):
        scheduler = DeletionScheduler(default_notice_period_days=7)
        record = scheduler.schedule("DOC-CANCEL", **_BASE_SCHEDULE)
        scheduler.cancel(record.record_id, cancel_reason="Rücknahme — Aufbewahrung verlängert")
        self.assertEqual(record.status, DeletionStatus.CANCELED)
        self.assertIsNotNone(record.canceled_at)
        self.assertEqual(record.cancel_reason, "Rücknahme — Aufbewahrung verlängert")

    def test_cancel_notified_record(self):
        scheduler = DeletionScheduler(default_notice_period_days=7)
        record = scheduler.schedule("DOC-CANCEL-NOTIFIED", **_BASE_SCHEDULE)
        scheduler.tick(now=_ts(7))  # → notified
        self.assertEqual(record.status, DeletionStatus.NOTIFIED)
        scheduler.cancel(record.record_id, cancel_reason="Hold gesetzt nach Benachrichtigung")
        self.assertEqual(record.status, DeletionStatus.CANCELED)

    def test_cancel_notified_prevents_execution(self):
        scheduler = DeletionScheduler(default_notice_period_days=7)
        record = scheduler.schedule("DOC-CANCEL-EXEC", **_BASE_SCHEDULE)
        scheduler.tick(now=_ts(7))   # → notified
        scheduler.cancel(record.record_id, cancel_reason="Stornierung nach Vorankündigung")
        result = scheduler.tick(now=_ts(15))  # past execute_after
        self.assertEqual(result["executed"], [])
        self.assertEqual(record.status, DeletionStatus.CANCELED)

    def test_cancel_executed_raises(self):
        # Use notice_period_days=7 (default):
        # tick at +7 → notified; tick at +14 → executed
        scheduler = DeletionScheduler(default_notice_period_days=7)
        record = scheduler.schedule("DOC-EXEC", **_BASE_SCHEDULE)
        scheduler.tick(now=_ts(7))   # → notified
        self.assertEqual(record.status, DeletionStatus.NOTIFIED)
        scheduler.tick(now=_ts(14))  # → executed
        self.assertEqual(record.status, DeletionStatus.EXECUTED)
        with self.assertRaises(ValueError):
            scheduler.cancel(record.record_id, cancel_reason="Zu spät")

    def test_cancel_requires_reason(self):
        scheduler = DeletionScheduler()
        record = scheduler.schedule("DOC-X", **_BASE_SCHEDULE)
        with self.assertRaises(ValueError):
            scheduler.cancel(record.record_id, cancel_reason="")

    def test_cancel_unknown_record_raises(self):
        scheduler = DeletionScheduler()
        with self.assertRaises(KeyError):
            scheduler.cancel("UNKNOWN-ID", cancel_reason="Testabbruch")


class TestHoldInteraction(unittest.TestCase):
    def test_hold_acquired_after_scheduling_blocks_tick(self):
        """A hold set after scheduling prevents notification and execution."""
        executed: list = []
        scheduler = DeletionScheduler(
            default_notice_period_days=7,
            on_execute=executed.append,
        )
        record = scheduler.schedule("DOC-HOLD", **_BASE_SCHEDULE)
        # Tick at notify window — should fire
        scheduler.tick(now=_ts(7))
        self.assertEqual(record.status, DeletionStatus.NOTIFIED)

        # Now put on hold before execution
        scheduler.set_hold("DOC-HOLD")
        result = scheduler.tick(now=_ts(14))
        self.assertEqual(result["executed"], [])
        self.assertEqual(record.status, DeletionStatus.NOTIFIED)  # still notified, not executed
        self.assertEqual(len(executed), 0)

    def test_releasing_hold_allows_execution(self):
        scheduler = DeletionScheduler(default_notice_period_days=7)
        record = scheduler.schedule("DOC-UNHOLD", **_BASE_SCHEDULE)
        scheduler.tick(now=_ts(7))   # → notified
        scheduler.set_hold("DOC-UNHOLD")
        scheduler.tick(now=_ts(14))  # blocked
        self.assertEqual(record.status, DeletionStatus.NOTIFIED)
        scheduler.release_hold("DOC-UNHOLD")
        scheduler.tick(now=_ts(14))  # now executes
        self.assertEqual(record.status, DeletionStatus.EXECUTED)


class TestMultipleDocuments(unittest.TestCase):
    def test_independent_records_for_different_documents(self):
        scheduler = DeletionScheduler(default_notice_period_days=7)
        r1 = scheduler.schedule("DOC-A", **_BASE_SCHEDULE)
        r2 = scheduler.schedule("DOC-B", **{**_BASE_SCHEDULE, "execute_after": _ts(20)})
        scheduler.tick(now=_ts(7))
        self.assertEqual(r1.status, DeletionStatus.NOTIFIED)
        self.assertEqual(r2.status, DeletionStatus.PENDING)

    def test_list_records_by_document_id(self):
        scheduler = DeletionScheduler(default_notice_period_days=7)
        r1 = scheduler.schedule("DOC-A", **_BASE_SCHEDULE)
        scheduler.schedule("DOC-B", **_BASE_SCHEDULE)
        result = scheduler.list_records(document_id="DOC-A")
        self.assertEqual([r.record_id for r in result], [r1.record_id])

    def test_get_record_by_id(self):
        scheduler = DeletionScheduler()
        record = scheduler.schedule("DOC-GET", **_BASE_SCHEDULE)
        fetched = scheduler.get_record(record.record_id)
        self.assertIs(fetched, record)

    def test_get_unknown_record_raises(self):
        scheduler = DeletionScheduler()
        with self.assertRaises(KeyError):
            scheduler.get_record("NONEXISTENT")


if __name__ == "__main__":
    unittest.main()
