"""Hold-Flag per Document — runtime implementation (Issue #523 / BL-342).

Implements the hold governance rules defined in
``docs/compliance/HOLD_GOVERNANCE_V1.md``:

  - Only authorised roles may set/release holds.
  - Every hold requires two approvals (Vier-Augen-Prinzip).
  - Holds have a mandatory ``review_due_at`` (max 30 days from creation).
  - Holds must have a non-empty ``hold_reason``.
  - Releasing a hold requires a documented ``release_reason`` and two approvals.
  - Hold reliably prevents deletion (integration with DeletionScheduler).

Roles with authority to set/release holds
-----------------------------------------
``Compliance Lead``, ``Legal Counsel``, ``Security Lead`` (security scope only).

``IT Product Owner`` and ``Operations`` may *propose* but not *approve*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional
import uuid


_AUTHORISED_HOLD_ROLES: frozenset[str] = frozenset(
    {"Compliance Lead", "Legal Counsel", "Security Lead"}
)

_MAX_REVIEW_PERIOD_DAYS = 30


class HoldStatus(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"


@dataclass
class HoldRecord:
    """Represents a single hold on a document."""

    hold_id: str
    document_id: str
    hold_reason: str
    requested_by_role: str      # role that proposed/requested the hold
    approved_by_role: str       # primary approver (role)
    counter_approved_by_role: str  # second approver (Vier-Augen)
    review_due_at: datetime     # deadline for hold review (≤ 30 days)
    status: HoldStatus = HoldStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    released_at: Optional[datetime] = None
    release_reason: Optional[str] = None
    release_approved_by_role: Optional[str] = None
    release_counter_approved_by_role: Optional[str] = None


class HoldStore:
    """Manages document hold flags with governance enforcement.

    Usage
    -----
    1.  ``set_hold()`` — place a hold on a document (requires two approvals).
    2.  ``release_hold()`` — lift the hold (requires two approvals + reason).
    3.  ``is_held()`` — check whether a document is currently on hold.
    4.  ``deletion_guard()`` — raises ``RuntimeError`` if document is held
        (call this from deletion paths).
    """

    def __init__(self) -> None:
        self._records: Dict[str, HoldRecord] = {}
        # document_id → set of active hold_ids
        self._active_holds: Dict[str, set[str]] = {}

    # ------------------------------------------------------------------ set
    def set_hold(
        self,
        document_id: str,
        *,
        hold_reason: str,
        requested_by_role: str,
        approved_by_role: str,
        counter_approved_by_role: str,
        review_due_at: datetime,
        hold_id: Optional[str] = None,
    ) -> HoldRecord:
        """Place a hold on *document_id*.

        Raises:
            ValueError   — validation failure (role, reason, date)
            PermissionError — approver(s) lack authority
        """
        self._validate_common(
            document_id=document_id,
            hold_reason=hold_reason,
            approved_by_role=approved_by_role,
            counter_approved_by_role=counter_approved_by_role,
            review_due_at=review_due_at,
        )
        if not requested_by_role or not requested_by_role.strip():
            raise ValueError("requested_by_role is required")

        now = datetime.now(tz=timezone.utc)
        max_review = now + timedelta(days=_MAX_REVIEW_PERIOD_DAYS)
        if review_due_at > max_review:
            raise ValueError(
                f"review_due_at must be within {_MAX_REVIEW_PERIOD_DAYS} days "
                f"(maximum: {max_review.date().isoformat()})"
            )
        if review_due_at <= now:
            raise ValueError("review_due_at must be in the future")

        rid = hold_id or str(uuid.uuid4())
        record = HoldRecord(
            hold_id=rid,
            document_id=document_id,
            hold_reason=hold_reason,
            requested_by_role=requested_by_role,
            approved_by_role=approved_by_role,
            counter_approved_by_role=counter_approved_by_role,
            review_due_at=review_due_at,
        )
        self._records[rid] = record
        self._active_holds.setdefault(document_id, set()).add(rid)
        return record

    # ------------------------------------------------------------------ release
    def release_hold(
        self,
        hold_id: str,
        *,
        release_reason: str,
        release_approved_by_role: str,
        release_counter_approved_by_role: str,
    ) -> HoldRecord:
        """Release a hold.

        Raises:
            KeyError       — hold_id not found
            ValueError     — already released, invalid reason, or missing approval
            PermissionError — approver(s) lack authority
        """
        record = self._get(hold_id)
        if record.status == HoldStatus.RELEASED:
            raise ValueError(f"hold '{hold_id}' is already released")

        if not release_reason or not release_reason.strip():
            raise ValueError("release_reason must be a non-empty string")
        if len(release_reason.strip()) < 10:
            raise ValueError("release_reason must be at least 10 characters")

        self._check_authority("release_approved_by_role", release_approved_by_role)
        self._check_authority(
            "release_counter_approved_by_role", release_counter_approved_by_role
        )
        if release_approved_by_role == release_counter_approved_by_role:
            raise ValueError(
                "release_approved_by_role and release_counter_approved_by_role "
                "must differ (Vier-Augen-Prinzip)"
            )

        record.status = HoldStatus.RELEASED
        record.released_at = datetime.now(tz=timezone.utc)
        record.release_reason = release_reason
        record.release_approved_by_role = release_approved_by_role
        record.release_counter_approved_by_role = release_counter_approved_by_role

        self._active_holds.get(record.document_id, set()).discard(hold_id)
        return record

    # ------------------------------------------------------------------ guards
    def is_held(self, document_id: str) -> bool:
        """Return True if *document_id* has at least one active hold."""
        return bool(self._active_holds.get(document_id))

    def deletion_guard(self, document_id: str) -> None:
        """Raise RuntimeError if *document_id* is on hold.

        Call this in any deletion path to reliably prevent deletion of held documents.
        """
        if self.is_held(document_id):
            active = list(self._active_holds[document_id])
            raise RuntimeError(
                f"document '{document_id}' is on hold "
                f"(active hold_ids: {active}) — deletion is blocked"
            )

    # ------------------------------------------------------------------ queries
    def get_hold(self, hold_id: str) -> HoldRecord:
        return self._get(hold_id)

    def list_holds(
        self,
        *,
        document_id: Optional[str] = None,
        status: Optional[HoldStatus] = None,
    ) -> List[HoldRecord]:
        results = list(self._records.values())
        if document_id is not None:
            results = [r for r in results if r.document_id == document_id]
        if status is not None:
            results = [r for r in results if r.status == status]
        return results

    def active_hold_ids(self, document_id: str) -> List[str]:
        return list(self._active_holds.get(document_id, set()))

    # ------------------------------------------------------------------ internal
    def _get(self, hold_id: str) -> HoldRecord:
        try:
            return self._records[hold_id]
        except KeyError:
            raise KeyError(f"hold '{hold_id}' not found")

    def _check_authority(self, field_name: str, role: str) -> None:
        if not role or not role.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        if role not in _AUTHORISED_HOLD_ROLES:
            raise PermissionError(
                f"role '{role}' is not authorised to set/release holds "
                f"(authorised: {sorted(_AUTHORISED_HOLD_ROLES)})"
            )

    def _validate_common(
        self,
        *,
        document_id: str,
        hold_reason: str,
        approved_by_role: str,
        counter_approved_by_role: str,
        review_due_at: datetime,
    ) -> None:
        if not document_id or not document_id.strip():
            raise ValueError("document_id must be a non-empty string")
        if not hold_reason or not hold_reason.strip():
            raise ValueError("hold_reason must be a non-empty string")
        if len(hold_reason.strip()) < 10:
            raise ValueError("hold_reason must be at least 10 characters")
        if review_due_at.tzinfo is None:
            raise ValueError("review_due_at must be timezone-aware")

        self._check_authority("approved_by_role", approved_by_role)
        self._check_authority("counter_approved_by_role", counter_approved_by_role)
        if approved_by_role == counter_approved_by_role:
            raise ValueError(
                "approved_by_role and counter_approved_by_role must differ "
                "(Vier-Augen-Prinzip)"
            )
