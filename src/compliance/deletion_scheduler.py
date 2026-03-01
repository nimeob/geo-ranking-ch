"""Lösch-Scheduler mit Vorankündigungsmechanismus (Issue #522 / BL-342).

Implements an automatic deletion scheduler that:
  1. Schedules a document for deletion with a configurable notice period.
  2. Marks deletions as *notified* once the notice window opens.
  3. Executes (or marks as executed) the deletion after the notice period expires.
  4. Respects hold flags — held documents cannot be deleted (stub for #523).
  5. Supports cancelation with an audit reason.

State machine
-------------
  pending  ──► notified ──► executed
      └──────────────────► canceled
      └──► canceled
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import uuid


class DeletionStatus(str, Enum):
    PENDING = "pending"       # scheduled, notice window not yet open
    NOTIFIED = "notified"     # notice window open, pre-deletion notification sent
    EXECUTED = "executed"     # final deletion completed
    CANCELED = "canceled"     # deletion canceled (hold, manual override, etc.)


@dataclass
class DeletionRecord:
    """Tracks a scheduled deletion for a single document."""

    record_id: str
    document_id: str
    requested_by_role: str
    delete_reason: str
    execute_after: datetime           # timestamp after which deletion may execute
    notice_period_days: int           # days before execute_after when notification fires
    status: DeletionStatus = DeletionStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    notified_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None

    @property
    def notify_after(self) -> datetime:
        """Earliest point when the pre-deletion notification should fire."""
        return self.execute_after - timedelta(days=self.notice_period_days)

    def is_notification_due(self, now: datetime) -> bool:
        return (
            self.status == DeletionStatus.PENDING
            and now >= self.notify_after
        )

    def is_execution_due(self, now: datetime) -> bool:
        return (
            self.status == DeletionStatus.NOTIFIED
            and now >= self.execute_after
        )


NotificationCallback = Callable[[DeletionRecord], None]
DeletionCallback = Callable[[DeletionRecord], None]


class DeletionScheduler:
    """In-memory deletion scheduler with pre-notification support.

    Usage
    -----
    1.  ``schedule()`` a document for deletion.
    2.  Call ``tick()`` periodically (or in tests with a fixed ``now``).
        ``tick()`` will fire notifications and execute deletions as their
        windows open.
    3.  ``cancel()`` a pending/notified deletion if needed.

    Callbacks
    ---------
    - ``on_notify``: called when a deletion enters the notification window.
    - ``on_execute``: called when a deletion is actually executed.

    These are deliberately simple callables so they can be replaced with
    database writes, message-queue enqueues, or log statements in production.
    """

    def __init__(
        self,
        *,
        default_notice_period_days: int = 7,
        on_notify: Optional[NotificationCallback] = None,
        on_execute: Optional[DeletionCallback] = None,
    ) -> None:
        if default_notice_period_days < 0:
            raise ValueError("default_notice_period_days must be >= 0")
        self._default_notice_period_days = default_notice_period_days
        self._on_notify = on_notify or (lambda _: None)
        self._on_execute = on_execute or (lambda _: None)
        self._records: Dict[str, DeletionRecord] = {}
        # Simple stub: track held document IDs (populated by #523 Hold-Flag impl.)
        self._held_document_ids: set[str] = set()

    # ------------------------------------------------------------------ schedule
    def schedule(
        self,
        document_id: str,
        *,
        execute_after: datetime,
        requested_by_role: str,
        delete_reason: str,
        notice_period_days: Optional[int] = None,
        record_id: Optional[str] = None,
    ) -> DeletionRecord:
        """Register a new deletion record.

        Raises:
            ValueError  — if arguments are invalid.
            RuntimeError — if the document is on hold.
        """
        if not document_id or not document_id.strip():
            raise ValueError("document_id must be a non-empty string")
        if not requested_by_role or not requested_by_role.strip():
            raise ValueError("requested_by_role is required")
        if not delete_reason or not delete_reason.strip():
            raise ValueError("delete_reason is required")
        if execute_after.tzinfo is None:
            raise ValueError("execute_after must be timezone-aware")

        notice_days = (
            notice_period_days
            if notice_period_days is not None
            else self._default_notice_period_days
        )
        if notice_days < 0:
            raise ValueError("notice_period_days must be >= 0")
        notice_delta = timedelta(days=notice_days)
        if notice_delta > (execute_after - datetime.now(tz=timezone.utc)):
            # Notice period would start in the past — still valid; tick() will
            # immediately fire the notification on the first run.
            pass

        if document_id in self._held_document_ids:
            raise RuntimeError(
                f"document '{document_id}' is on hold — deletion cannot be scheduled"
            )

        rid = record_id or str(uuid.uuid4())
        record = DeletionRecord(
            record_id=rid,
            document_id=document_id,
            requested_by_role=requested_by_role,
            delete_reason=delete_reason,
            execute_after=execute_after,
            notice_period_days=notice_days,
        )
        self._records[rid] = record
        return record

    # ------------------------------------------------------------------ tick
    def tick(self, now: Optional[datetime] = None) -> dict[str, List[str]]:
        """Advance the scheduler: fire pending notifications and execute due deletions.

        Returns a summary ``{"notified": [...record_ids], "executed": [...record_ids]}``.
        """
        if now is None:
            now = datetime.now(tz=timezone.utc)

        notified: List[str] = []
        executed: List[str] = []

        for record in list(self._records.values()):
            if record.status in (DeletionStatus.EXECUTED, DeletionStatus.CANCELED):
                continue

            # Check hold status (documents may acquire hold after scheduling)
            if record.document_id in self._held_document_ids:
                continue

            if record.is_execution_due(now):
                record.status = DeletionStatus.EXECUTED
                record.executed_at = now
                self._on_execute(record)
                executed.append(record.record_id)

            elif record.is_notification_due(now):
                record.status = DeletionStatus.NOTIFIED
                record.notified_at = now
                self._on_notify(record)
                notified.append(record.record_id)

        return {"notified": notified, "executed": executed}

    # ------------------------------------------------------------------ cancel
    def cancel(
        self,
        record_id: str,
        *,
        cancel_reason: str,
    ) -> DeletionRecord:
        """Cancel a pending or notified deletion.

        Raises:
            KeyError    — if record_id not found.
            ValueError  — if deletion is already executed or if cancel_reason is empty.
        """
        if not cancel_reason or not cancel_reason.strip():
            raise ValueError("cancel_reason must be a non-empty string")
        record = self._get(record_id)
        if record.status == DeletionStatus.EXECUTED:
            raise ValueError(
                f"record '{record_id}' is already executed — cannot cancel"
            )
        if record.status == DeletionStatus.CANCELED:
            raise ValueError(
                f"record '{record_id}' is already canceled"
            )
        record.status = DeletionStatus.CANCELED
        record.canceled_at = datetime.now(tz=timezone.utc)
        record.cancel_reason = cancel_reason
        return record

    # ------------------------------------------------------------------ hold stubs (for #523)
    def set_hold(self, document_id: str) -> None:
        """Mark a document as held (stub — full impl in #523)."""
        self._held_document_ids.add(document_id)

    def release_hold(self, document_id: str) -> None:
        """Release a hold on a document (stub — full impl in #523)."""
        self._held_document_ids.discard(document_id)

    def is_held(self, document_id: str) -> bool:
        return document_id in self._held_document_ids

    # ------------------------------------------------------------------ queries
    def get_record(self, record_id: str) -> DeletionRecord:
        return self._get(record_id)

    def list_records(
        self,
        *,
        document_id: Optional[str] = None,
        status: Optional[DeletionStatus] = None,
    ) -> List[DeletionRecord]:
        results = list(self._records.values())
        if document_id is not None:
            results = [r for r in results if r.document_id == document_id]
        if status is not None:
            results = [r for r in results if r.status == status]
        return results

    def _get(self, record_id: str) -> DeletionRecord:
        try:
            return self._records[record_id]
        except KeyError:
            raise KeyError(f"deletion record '{record_id}' not found")
