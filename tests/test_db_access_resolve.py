"""Unit tests for resolve_oidc_subject — OIDC claim mapping.

Covers:
- Unknown subject → returns None
- Known user, no membership → org_id=None, roles=[]
- Known user, single membership → correct org_id + role
- Known user, multiple memberships → primary=oldest, all in memberships list
- Empty/whitespace subject → ValueError
- Logging safety: subject never logged, only fingerprint

Postgres is mocked — no live DB required.

Issue: #820 (OIDC-0.wp4)
"""

from __future__ import annotations

import logging
import unittest
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, call, patch
import uuid
from datetime import datetime, timezone

from src.shared.db_access import resolve_oidc_subject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 2, 20, 0, 0, tzinfo=timezone.utc)

# Fixed UUIDs
_USER_UUID = str(uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001"))
_ORG_UUID  = str(uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001"))
_ORG2_UUID = str(uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002"))
_MBR_UUID  = str(uuid.UUID("cccccccc-0000-0000-0000-000000000001"))
_MBR2_UUID = str(uuid.UUID("cccccccc-0000-0000-0000-000000000002"))


def _desc(*names: str):
    """Build minimal cursor.description for given column names."""
    return [(name,) for name in names]


def _make_multi_cursor(*, fetchone_seq=None, fetchall_values=None, description=None):
    """Return a cursor mock whose fetchone returns values from a list (pop-left),
    and fetchall returns fetchall_values."""
    cur = MagicMock()
    cur.description = description or []
    _fetchone_seq = list(fetchone_seq or [])
    _fetchall = fetchall_values or []

    def _fetchone():
        return _fetchone_seq.pop(0) if _fetchone_seq else None

    cur.fetchone = MagicMock(side_effect=_fetchone)
    cur.fetchall = MagicMock(return_value=_fetchall)
    return cur


class _ConnBuilder:
    """Build a mock connection that returns different cursors per call."""

    def __init__(self):
        self._cursors: list[Any] = []

    def add_cursor(self, cur):
        self._cursors.append(cur)

    def build(self):
        idx = [0]
        cursors = self._cursors

        class _CtxMgr:
            def __init__(inner):
                pass
            def __enter__(inner):
                c = cursors[idx[0]]
                idx[0] += 1
                return c
            def __exit__(inner, *_):
                pass

        conn = MagicMock()
        conn.cursor = MagicMock(return_value=_CtxMgr())
        return conn


# ---------------------------------------------------------------------------
# Tests — resolve_oidc_subject
# ---------------------------------------------------------------------------

class TestResolveOidcSubjectUnknown(unittest.TestCase):
    """Unknown subject → returns None."""

    def test_unknown_subject_returns_none(self):
        # Step 1 cursor: user lookup returns no row.
        cur1 = _make_multi_cursor(fetchone_seq=[None])
        cur1.description = _desc("id", "external_subject", "email", "created_at", "updated_at")

        builder = _ConnBuilder()
        builder.add_cursor(cur1)
        conn = builder.build()

        result = resolve_oidc_subject(conn, "sub|unknown")
        self.assertIsNone(result)

    def test_empty_subject_raises(self):
        conn = MagicMock()
        with self.assertRaises(ValueError):
            resolve_oidc_subject(conn, "")

    def test_whitespace_subject_raises(self):
        conn = MagicMock()
        with self.assertRaises(ValueError):
            resolve_oidc_subject(conn, "   ")


class TestResolveOidcSubjectNoMembership(unittest.TestCase):
    """Known user, no membership → org_id=None, roles=[]."""

    def _build_conn(self):
        # Step 1: user found
        cur1 = _make_multi_cursor(
            fetchone_seq=[(
                uuid.UUID(_USER_UUID),
                "sub|test",
                "test@example.com",
                _NOW,
                _NOW,
            )],
        )
        cur1.description = _desc("id", "external_subject", "email", "created_at", "updated_at")

        # Step 2: memberships → empty
        cur2 = _make_multi_cursor(fetchall_values=[])
        cur2.description = _desc("id", "org_id", "user_id", "role", "created_at")

        builder = _ConnBuilder()
        builder.add_cursor(cur1)
        builder.add_cursor(cur2)
        return builder.build()

    def test_no_membership_org_id_none(self):
        conn = self._build_conn()
        result = resolve_oidc_subject(conn, "sub|test")
        self.assertIsNotNone(result)
        self.assertEqual(result["user_id"], _USER_UUID)
        self.assertIsNone(result["org_id"])
        self.assertEqual(result["roles"], [])
        self.assertEqual(result["memberships"], [])

    def test_no_membership_memberships_empty_list(self):
        conn = self._build_conn()
        result = resolve_oidc_subject(conn, "sub|test")
        self.assertIsInstance(result["memberships"], list)
        self.assertEqual(len(result["memberships"]), 0)


class TestResolveOidcSubjectSingleMembership(unittest.TestCase):
    """Known user, single membership → correct org_id + role."""

    def _build_conn(self, role="member"):
        cur1 = _make_multi_cursor(
            fetchone_seq=[(
                uuid.UUID(_USER_UUID),
                "sub|test",
                "test@example.com",
                _NOW,
                _NOW,
            )],
        )
        cur1.description = _desc("id", "external_subject", "email", "created_at", "updated_at")

        cur2 = _make_multi_cursor(
            fetchall_values=[(
                uuid.UUID(_MBR_UUID),
                uuid.UUID(_ORG_UUID),
                uuid.UUID(_USER_UUID),
                role,
                _NOW,
            )],
        )
        cur2.description = _desc("id", "org_id", "user_id", "role", "created_at")

        builder = _ConnBuilder()
        builder.add_cursor(cur1)
        builder.add_cursor(cur2)
        return builder.build()

    def test_single_membership_org_id(self):
        conn = self._build_conn(role="member")
        result = resolve_oidc_subject(conn, "sub|test")
        self.assertEqual(result["user_id"], _USER_UUID)
        self.assertEqual(result["org_id"], _ORG_UUID)

    def test_single_membership_roles(self):
        conn = self._build_conn(role="admin")
        result = resolve_oidc_subject(conn, "sub|test")
        self.assertEqual(result["roles"], ["admin"])

    def test_single_membership_memberships_count(self):
        conn = self._build_conn()
        result = resolve_oidc_subject(conn, "sub|test")
        self.assertEqual(len(result["memberships"]), 1)
        self.assertEqual(result["memberships"][0]["org_id"], _ORG_UUID)

    def test_single_membership_uuid_as_str(self):
        """UUID columns must be stringified."""
        conn = self._build_conn()
        result = resolve_oidc_subject(conn, "sub|test")
        self.assertIsInstance(result["user_id"], str)
        self.assertIsInstance(result["org_id"], str)
        self.assertIsInstance(result["memberships"][0]["id"], str)
        self.assertIsInstance(result["memberships"][0]["org_id"], str)
        self.assertIsInstance(result["memberships"][0]["user_id"], str)


class TestResolveOidcSubjectMultipleMemberships(unittest.TestCase):
    """Known user, multiple memberships → primary=oldest, all returned."""

    def _build_conn(self):
        cur1 = _make_multi_cursor(
            fetchone_seq=[(
                uuid.UUID(_USER_UUID),
                "sub|multi",
                "multi@example.com",
                _NOW,
                _NOW,
            )],
        )
        cur1.description = _desc("id", "external_subject", "email", "created_at", "updated_at")

        # Two memberships: org1 (older / primary), org2 (newer)
        cur2 = _make_multi_cursor(
            fetchall_values=[
                (uuid.UUID(_MBR_UUID),  uuid.UUID(_ORG_UUID),  uuid.UUID(_USER_UUID), "member", _NOW),
                (uuid.UUID(_MBR2_UUID), uuid.UUID(_ORG2_UUID), uuid.UUID(_USER_UUID), "admin",  _NOW),
            ],
        )
        cur2.description = _desc("id", "org_id", "user_id", "role", "created_at")

        builder = _ConnBuilder()
        builder.add_cursor(cur1)
        builder.add_cursor(cur2)
        return builder.build()

    def test_primary_org_is_first(self):
        conn = self._build_conn()
        result = resolve_oidc_subject(conn, "sub|multi")
        self.assertEqual(result["org_id"], _ORG_UUID)

    def test_roles_include_all(self):
        """roles list has one entry per membership (in order)."""
        conn = self._build_conn()
        result = resolve_oidc_subject(conn, "sub|multi")
        self.assertEqual(result["roles"], ["member", "admin"])

    def test_memberships_count(self):
        conn = self._build_conn()
        result = resolve_oidc_subject(conn, "sub|multi")
        self.assertEqual(len(result["memberships"]), 2)

    def test_memberships_org_ids(self):
        conn = self._build_conn()
        result = resolve_oidc_subject(conn, "sub|multi")
        org_ids = [m["org_id"] for m in result["memberships"]]
        self.assertIn(_ORG_UUID, org_ids)
        self.assertIn(_ORG2_UUID, org_ids)


class TestResolveOidcSubjectLogging(unittest.TestCase):
    """Logging safety: plaintext subject must never appear in log records."""

    def _build_conn_for_found(self):
        cur1 = _make_multi_cursor(
            fetchone_seq=[(
                uuid.UUID(_USER_UUID),
                "sub|secretvalue",
                None,
                _NOW,
                _NOW,
            )],
        )
        cur1.description = _desc("id", "external_subject", "email", "created_at", "updated_at")

        cur2 = _make_multi_cursor(fetchall_values=[])
        cur2.description = _desc("id", "org_id", "user_id", "role", "created_at")

        builder = _ConnBuilder()
        builder.add_cursor(cur1)
        builder.add_cursor(cur2)
        return builder.build()

    def _build_conn_for_not_found(self):
        cur1 = _make_multi_cursor(fetchone_seq=[None])
        cur1.description = _desc("id", "external_subject", "email", "created_at", "updated_at")

        builder = _ConnBuilder()
        builder.add_cursor(cur1)
        return builder.build()

    def test_subject_not_in_log_on_found(self):
        with self.assertLogs("src.shared.db_access", level="DEBUG") as lm:
            conn = self._build_conn_for_found()
            resolve_oidc_subject(conn, "sub|secretvalue")
        full_log = "\n".join(lm.output)
        self.assertNotIn("sub|secretvalue", full_log)

    def test_subject_not_in_log_on_not_found(self):
        with self.assertLogs("src.shared.db_access", level="DEBUG") as lm:
            conn = self._build_conn_for_not_found()
            resolve_oidc_subject(conn, "sub|secretvalue")
        full_log = "\n".join(lm.output)
        self.assertNotIn("sub|secretvalue", full_log)


if __name__ == "__main__":
    unittest.main()
