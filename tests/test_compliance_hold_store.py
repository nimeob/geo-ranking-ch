"""Tests for src/compliance/hold_store.py  (Issue #523).

DoD coverage:
  - [x] Hold can be set with Vier-Augen-Prinzip (two distinct authorised roles)
  - [x] Hold reliably prevents deletion via deletion_guard()
  - [x] Releasing hold with proper approvals + reason lifts deletion block
  - [x] Unauthorised roles cannot set or release holds (PermissionError)
  - [x] Same role cannot fill both approver slots (Vier-Augen)
  - [x] hold_reason must be non-empty and substantive
  - [x] review_due_at must be in future and within 30 days
  - [x] Multiple independent holds on a document
  - [x] Releasing one hold does not lift other active holds
  - [x] Integration: HoldStore + DeletionScheduler — hold blocks execution
"""

import unittest
from datetime import datetime, timedelta, timezone

from src.compliance.hold_store import HoldStore, HoldStatus
from src.compliance.deletion_scheduler import DeletionScheduler, DeletionStatus

_NOW = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc)
_REVIEW_DUE = _NOW + timedelta(days=14)

_BASE_HOLD = dict(
    hold_reason="Laufendes Rechtsverfahren — Dokument gesperrt bis Klärung",
    requested_by_role="IT Product Owner",
    approved_by_role="Compliance Lead",
    counter_approved_by_role="Legal Counsel",
    review_due_at=_REVIEW_DUE,
)

_RELEASE_ARGS = dict(
    release_reason="Rechtsverfahren abgeschlossen — Hold aufgehoben",
    release_approved_by_role="Compliance Lead",
    release_counter_approved_by_role="Legal Counsel",
)


class TestHoldSetAndQuery(unittest.TestCase):
    def _store(self) -> HoldStore:
        return HoldStore()

    def test_set_hold_creates_active_record(self):
        store = self._store()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        self.assertEqual(record.status, HoldStatus.ACTIVE)
        self.assertEqual(record.document_id, "DOC-001")
        self.assertTrue(store.is_held("DOC-001"))

    def test_set_hold_returns_record_with_id(self):
        store = self._store()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        self.assertTrue(record.hold_id)

    def test_document_without_hold_is_not_held(self):
        store = self._store()
        self.assertFalse(store.is_held("DOC-NEVER-HELD"))

    def test_list_holds_by_document_id(self):
        store = self._store()
        r1 = store.set_hold("DOC-A", **_BASE_HOLD)
        store.set_hold("DOC-B", **_BASE_HOLD)
        result = store.list_holds(document_id="DOC-A")
        self.assertEqual([r.hold_id for r in result], [r1.hold_id])

    def test_list_holds_by_status(self):
        store = self._store()
        r1 = store.set_hold("DOC-A", **_BASE_HOLD)
        store.release_hold(r1.hold_id, **_RELEASE_ARGS)
        r2 = store.set_hold("DOC-B", **_BASE_HOLD)
        active = store.list_holds(status=HoldStatus.ACTIVE)
        self.assertEqual([r.hold_id for r in active], [r2.hold_id])

    def test_get_hold_by_id(self):
        store = self._store()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        fetched = store.get_hold(record.hold_id)
        self.assertIs(fetched, record)

    def test_get_unknown_hold_raises(self):
        store = self._store()
        with self.assertRaises(KeyError):
            store.get_hold("NONEXISTENT")


class TestDeletionGuard(unittest.TestCase):
    """Core DoD: Hold verhindert Löschung verlässlich."""

    def test_deletion_guard_raises_when_held(self):
        store = HoldStore()
        store.set_hold("DOC-GUARDED", **_BASE_HOLD)
        with self.assertRaises(RuntimeError, msg="deletion_guard must raise for held document"):
            store.deletion_guard("DOC-GUARDED")

    def test_deletion_guard_silent_when_not_held(self):
        store = HoldStore()
        # Should NOT raise
        store.deletion_guard("DOC-FREE")

    def test_deletion_guard_includes_hold_id_in_message(self):
        store = HoldStore()
        record = store.set_hold("DOC-GUARDED", **_BASE_HOLD)
        try:
            store.deletion_guard("DOC-GUARDED")
            self.fail("Expected RuntimeError")
        except RuntimeError as exc:
            self.assertIn(record.hold_id, str(exc))

    def test_deletion_guard_released_after_all_holds_lifted(self):
        store = HoldStore()
        record = store.set_hold("DOC-RELEASE", **_BASE_HOLD)
        # Guard raises while hold is active
        with self.assertRaises(RuntimeError):
            store.deletion_guard("DOC-RELEASE")
        # Release the hold
        store.release_hold(record.hold_id, **_RELEASE_ARGS)
        # After release, guard must NOT raise
        store.deletion_guard("DOC-RELEASE")  # should pass silently


class TestHoldRelease(unittest.TestCase):
    def test_release_sets_status_to_released(self):
        store = HoldStore()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        store.release_hold(record.hold_id, **_RELEASE_ARGS)
        self.assertEqual(record.status, HoldStatus.RELEASED)
        self.assertIsNotNone(record.released_at)
        self.assertFalse(store.is_held("DOC-001"))

    def test_releasing_already_released_raises(self):
        store = HoldStore()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        store.release_hold(record.hold_id, **_RELEASE_ARGS)
        with self.assertRaises(ValueError):
            store.release_hold(record.hold_id, **_RELEASE_ARGS)

    def test_release_requires_reason(self):
        store = HoldStore()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        with self.assertRaises(ValueError):
            store.release_hold(record.hold_id,
                               release_reason="",
                               release_approved_by_role="Compliance Lead",
                               release_counter_approved_by_role="Legal Counsel")

    def test_release_reason_must_be_substantive(self):
        store = HoldStore()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        with self.assertRaises(ValueError):
            store.release_hold(record.hold_id,
                               release_reason="kurz",
                               release_approved_by_role="Compliance Lead",
                               release_counter_approved_by_role="Legal Counsel")


class TestMultipleHolds(unittest.TestCase):
    def test_multiple_active_holds_document_still_held(self):
        store = HoldStore()
        r1 = store.set_hold("DOC-MULTI", **_BASE_HOLD)
        r2 = store.set_hold("DOC-MULTI", **{
            **_BASE_HOLD,
            "hold_reason": "Zweite Sperre — sicherheitsrelevanter Vorfall gemeldet",
        })
        # Both active
        self.assertEqual(len(store.active_hold_ids("DOC-MULTI")), 2)

        # Release one
        store.release_hold(r1.hold_id, **_RELEASE_ARGS)
        # Still held (r2 active)
        self.assertTrue(store.is_held("DOC-MULTI"))

        # Release second
        store.release_hold(r2.hold_id, **RELEASE_ARGS_VARIANT)
        self.assertFalse(store.is_held("DOC-MULTI"))

    def test_multiple_documents_independent(self):
        store = HoldStore()
        store.set_hold("DOC-A", **_BASE_HOLD)
        store.set_hold("DOC-B", **_BASE_HOLD)
        # Releasing DOC-A hold doesn't affect DOC-B
        for hold in store.list_holds(document_id="DOC-A"):
            store.release_hold(hold.hold_id, **_RELEASE_ARGS)
        self.assertFalse(store.is_held("DOC-A"))
        self.assertTrue(store.is_held("DOC-B"))


RELEASE_ARGS_VARIANT = dict(
    release_reason="Zweite Freigabe — Sicherheitsvorfall abgeschlossen",
    release_approved_by_role="Security Lead",
    release_counter_approved_by_role="Compliance Lead",
)


class TestGovernanceEnforcement(unittest.TestCase):
    """Vier-Augen, role authority, required fields."""

    def test_unauthorized_role_set_raises_permission_error(self):
        store = HoldStore()
        with self.assertRaises(PermissionError):
            store.set_hold("DOC-001", **{**_BASE_HOLD, "approved_by_role": "IT Product Owner"})

    def test_unauthorized_counter_role_set_raises_permission_error(self):
        store = HoldStore()
        with self.assertRaises(PermissionError):
            store.set_hold("DOC-001", **{
                **_BASE_HOLD,
                "counter_approved_by_role": "Operations",
            })

    def test_same_role_both_approvals_raises(self):
        store = HoldStore()
        with self.assertRaises(ValueError):
            store.set_hold("DOC-001", **{
                **_BASE_HOLD,
                "approved_by_role": "Compliance Lead",
                "counter_approved_by_role": "Compliance Lead",
            })

    def test_unauthorized_release_role_raises(self):
        store = HoldStore()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        with self.assertRaises(PermissionError):
            store.release_hold(record.hold_id,
                               release_reason="Freigabeversuch ohne Berechtigung",
                               release_approved_by_role="Operations",
                               release_counter_approved_by_role="Compliance Lead")

    def test_same_role_release_vier_augen_raises(self):
        store = HoldStore()
        record = store.set_hold("DOC-001", **_BASE_HOLD)
        with self.assertRaises(ValueError):
            store.release_hold(record.hold_id,
                               release_reason="Freigabe mit identischer Rolle — soll scheitern",
                               release_approved_by_role="Compliance Lead",
                               release_counter_approved_by_role="Compliance Lead")

    def test_empty_hold_reason_raises(self):
        store = HoldStore()
        with self.assertRaises(ValueError):
            store.set_hold("DOC-001", **{**_BASE_HOLD, "hold_reason": ""})

    def test_short_hold_reason_raises(self):
        store = HoldStore()
        with self.assertRaises(ValueError):
            store.set_hold("DOC-001", **{**_BASE_HOLD, "hold_reason": "kurz"})

    def test_review_due_past_raises(self):
        store = HoldStore()
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        with self.assertRaises(ValueError):
            store.set_hold("DOC-001", **{**_BASE_HOLD, "review_due_at": past})

    def test_review_due_over_30_days_raises(self):
        store = HoldStore()
        too_far = datetime.now(tz=timezone.utc) + timedelta(days=31)
        with self.assertRaises(ValueError):
            store.set_hold("DOC-001", **{**_BASE_HOLD, "review_due_at": too_far})

    def test_naive_review_due_raises(self):
        store = HoldStore()
        naive = datetime(2026, 3, 20, 0, 0, 0)
        with self.assertRaises(ValueError):
            store.set_hold("DOC-001", **{**_BASE_HOLD, "review_due_at": naive})


class TestHoldDeletionSchedulerIntegration(unittest.TestCase):
    """Integration: HoldStore + DeletionScheduler — Hold verhindert Löschung verlässlich."""

    def _setup(self) -> tuple[HoldStore, DeletionScheduler]:
        hold_store = HoldStore()
        executed: list = []

        def guarded_on_execute(record):
            hold_store.deletion_guard(record.document_id)
            executed.append(record)

        scheduler = DeletionScheduler(
            default_notice_period_days=7,
            on_execute=guarded_on_execute,
        )
        return hold_store, scheduler

    def test_hold_prevents_deletion_via_scheduler(self):
        """Hold blocks DeletionScheduler from executing — core DoD."""
        hold_store, scheduler = self._setup()
        _BASE_TS = datetime.now(tz=timezone.utc)

        # Schedule deletion
        execute_at = _BASE_TS + timedelta(days=14)
        record = scheduler.schedule(
            "DOC-HOLD-INT",
            execute_after=execute_at,
            requested_by_role="Compliance Lead",
            delete_reason="Aufbewahrungsfrist abgelaufen",
            notice_period_days=7,
        )

        # Tick to notified
        scheduler.tick(now=_BASE_TS + timedelta(days=7))
        self.assertEqual(record.status, DeletionStatus.NOTIFIED)

        # Set hold before execution
        hold_record = hold_store.set_hold(
            "DOC-HOLD-INT",
            **{
                **_BASE_HOLD,
                "review_due_at": datetime.now(tz=timezone.utc) + timedelta(days=7),
            },
        )

        # Tick at execute_after — on_execute raises via deletion_guard
        with self.assertRaises(RuntimeError, msg="Hold must block execution"):
            scheduler.tick(now=_BASE_TS + timedelta(days=15))

    def test_release_hold_allows_deletion(self):
        """After releasing hold, deletion executes successfully."""
        hold_store = HoldStore()
        executed: list = []

        def guarded_on_execute(record):
            hold_store.deletion_guard(record.document_id)
            executed.append(record)

        scheduler = DeletionScheduler(
            default_notice_period_days=7,
            on_execute=guarded_on_execute,
        )
        _BASE_TS = datetime.now(tz=timezone.utc)
        execute_at = _BASE_TS + timedelta(days=14)

        record = scheduler.schedule(
            "DOC-RELEASE-INT",
            execute_after=execute_at,
            requested_by_role="Compliance Lead",
            delete_reason="Aufbewahrungsfrist abgelaufen",
        )

        scheduler.tick(now=_BASE_TS + timedelta(days=7))  # → notified

        hold_record = hold_store.set_hold(
            "DOC-RELEASE-INT",
            **{
                **_BASE_HOLD,
                "review_due_at": datetime.now(tz=timezone.utc) + timedelta(days=7),
            },
        )
        hold_store.release_hold(hold_record.hold_id, **_RELEASE_ARGS)

        # Now deletion executes without error
        result = scheduler.tick(now=_BASE_TS + timedelta(days=14))
        self.assertIn(record.record_id, result["executed"])
        self.assertEqual(len(executed), 1)


if __name__ == "__main__":
    unittest.main()
