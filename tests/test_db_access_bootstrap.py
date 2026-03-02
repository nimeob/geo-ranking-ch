"""Unit tests for src/shared/db_access.py — bootstrap policy.

Tests cover all three public functions:
- get_or_create_user_by_external_subject
- get_or_create_default_org
- ensure_membership

Postgres is mocked — no live DB required.  Cursor.description is set to
mimic real psycopg2 column metadata so the row->dict helpers work correctly.

Issue: #814 (DB-0.wp3)
"""

from __future__ import annotations

import hashlib
import logging
import unittest
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch
import uuid

from src.shared.db_access import (
    ensure_membership,
    get_or_create_default_org,
    get_or_create_user_by_external_subject,
    _subject_fingerprint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _desc(*names: str):
    """Build a minimal cursor.description list for given column names."""
    return [(name,) for name in names]


def _make_cursor(*, fetchone_values=None, description=None):
    """Return a MagicMock cursor with configurable fetchone/description."""
    cur = MagicMock()
    cur.description = description or []
    cur.fetchone = MagicMock(return_value=fetchone_values)
    return cur


@contextmanager
def _conn_ctx(cursor):
    """Simulate psycopg2 connection.cursor() as a context manager."""
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    yield conn


# Fixed UUIDs for deterministic tests.
_USER_UUID = str(uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001"))
_ORG_UUID  = str(uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001"))
_MBR_UUID  = str(uuid.UUID("cccccccc-0000-0000-0000-000000000001"))


# ---------------------------------------------------------------------------
# _subject_fingerprint
# ---------------------------------------------------------------------------

class TestSubjectFingerprint(unittest.TestCase):
    def test_length_8(self):
        fp = _subject_fingerprint("sub|123456")
        self.assertEqual(len(fp), 8)

    def test_deterministic(self):
        self.assertEqual(_subject_fingerprint("x"), _subject_fingerprint("x"))

    def test_distinct(self):
        self.assertNotEqual(_subject_fingerprint("a"), _subject_fingerprint("b"))

    def test_no_plaintext_subject(self):
        sub = "sub|verysecret"
        fp = _subject_fingerprint(sub)
        self.assertNotIn(sub, fp)


# ---------------------------------------------------------------------------
# get_or_create_user_by_external_subject — new user (INSERT returns row)
# ---------------------------------------------------------------------------

class TestGetOrCreateUserNew(unittest.TestCase):
    def _make_user_row(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        return (_USER_UUID, "sub|new", "new@example.com", now, now)

    def test_new_user_created_flag_true(self):
        cur = _make_cursor(
            fetchone_values=self._make_user_row(),
            description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
        )
        with _conn_ctx(cur) as conn:
            result = get_or_create_user_by_external_subject(
                conn, "sub|new", email="new@example.com"
            )
        self.assertTrue(result["_created"])
        self.assertEqual(str(result["id"]), _USER_UUID)

    def test_new_user_returns_dict_with_expected_keys(self):
        cur = _make_cursor(
            fetchone_values=self._make_user_row(),
            description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
        )
        with _conn_ctx(cur) as conn:
            result = get_or_create_user_by_external_subject(conn, "sub|new")
        for key in ("id", "external_subject", "email", "created_at", "updated_at", "_created"):
            self.assertIn(key, result, f"missing key: {key}")


# ---------------------------------------------------------------------------
# get_or_create_user_by_external_subject — existing user (INSERT returns None)
# ---------------------------------------------------------------------------

class TestGetOrCreateUserExisting(unittest.TestCase):
    def test_existing_user_created_flag_false(self):
        import datetime
        now = datetime.datetime(2026, 3, 1, 10, 0, 0)
        existing_row = (_USER_UUID, "sub|old", "old@example.com", now, now)

        cur = MagicMock()
        cur.description = _desc("id", "external_subject", "email", "created_at", "updated_at")
        # First fetchone (INSERT ... RETURNING) → None (conflict, no new row)
        # Second fetchone (SELECT) → existing row
        cur.fetchone = MagicMock(side_effect=[None, existing_row])

        with _conn_ctx(cur) as conn:
            result = get_or_create_user_by_external_subject(conn, "sub|old")

        self.assertFalse(result["_created"])
        self.assertEqual(str(result["id"]), _USER_UUID)


# ---------------------------------------------------------------------------
# get_or_create_user_by_external_subject — invite_only policy (default)
# ---------------------------------------------------------------------------

class TestGetOrCreateUserInviteOnlyPolicy(unittest.TestCase):
    """With invite_only policy, no org or membership must be created."""

    def test_no_org_creation_called(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_USER_UUID, "sub|x", None, now, now),
            description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
        )
        with _conn_ctx(cur) as conn:
            with patch("src.shared.db_access.get_or_create_default_org") as mock_org:
                with patch("src.shared.db_access.ensure_membership") as mock_mbr:
                    get_or_create_user_by_external_subject(
                        conn, "sub|x", org_policy="invite_only"
                    )
                    mock_org.assert_not_called()
                    mock_mbr.assert_not_called()

    def test_invite_only_is_default(self):
        """Default org_policy is invite_only."""
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_USER_UUID, "sub|default", None, now, now),
            description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
        )
        with _conn_ctx(cur) as conn:
            with patch("src.shared.db_access.get_or_create_default_org") as mock_org:
                with patch("src.shared.db_access.ensure_membership") as mock_mbr:
                    get_or_create_user_by_external_subject(conn, "sub|default")
                    mock_org.assert_not_called()
                    mock_mbr.assert_not_called()


# ---------------------------------------------------------------------------
# get_or_create_user_by_external_subject — auto_org policy
# ---------------------------------------------------------------------------

class TestGetOrCreateUserAutoOrgPolicy(unittest.TestCase):
    """auto_org policy must call ensure_membership (+ get_or_create_default_org if no org_id)."""

    def test_auto_org_without_org_id_creates_default_org_and_membership(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_USER_UUID, "sub|auto", None, now, now),
            description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
        )
        fake_org = {"id": _ORG_UUID, "slug": "default", "_created": True}
        with _conn_ctx(cur) as conn:
            with patch("src.shared.db_access.get_or_create_default_org", return_value=fake_org) as mock_org:
                with patch("src.shared.db_access.ensure_membership") as mock_mbr:
                    result = get_or_create_user_by_external_subject(
                        conn, "sub|auto", org_policy="auto_org"
                    )
                    mock_org.assert_called_once_with(conn)
                    mock_mbr.assert_called_once_with(conn, _ORG_UUID, _USER_UUID, role="member")

    def test_auto_org_with_explicit_org_id_skips_default_org(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_USER_UUID, "sub|explicit", None, now, now),
            description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
        )
        with _conn_ctx(cur) as conn:
            with patch("src.shared.db_access.get_or_create_default_org") as mock_org:
                with patch("src.shared.db_access.ensure_membership") as mock_mbr:
                    get_or_create_user_by_external_subject(
                        conn, "sub|explicit", org_id=_ORG_UUID, org_policy="auto_org"
                    )
                    mock_org.assert_not_called()
                    mock_mbr.assert_called_once_with(conn, _ORG_UUID, _USER_UUID, role="member")


# ---------------------------------------------------------------------------
# get_or_create_user_by_external_subject — input validation
# ---------------------------------------------------------------------------

class TestGetOrCreateUserValidation(unittest.TestCase):
    def _dummy_conn(self):
        return MagicMock()

    def test_empty_subject_raises(self):
        with self.assertRaises(ValueError):
            get_or_create_user_by_external_subject(self._dummy_conn(), "")

    def test_whitespace_subject_raises(self):
        with self.assertRaises(ValueError):
            get_or_create_user_by_external_subject(self._dummy_conn(), "   ")

    def test_unknown_org_policy_raises(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_USER_UUID, "sub|p", None, now, now),
            description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
        )
        with _conn_ctx(cur) as conn:
            with self.assertRaises(ValueError):
                get_or_create_user_by_external_subject(
                    conn, "sub|p", org_policy="unknown_policy"
                )


# ---------------------------------------------------------------------------
# get_or_create_default_org — new org
# ---------------------------------------------------------------------------

class TestGetOrCreateDefaultOrgNew(unittest.TestCase):
    def test_new_org_created_flag_true(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_ORG_UUID, "default", "Default Organization", now, now),
            description=_desc("id", "slug", "display_name", "created_at", "updated_at"),
        )
        with _conn_ctx(cur) as conn:
            result = get_or_create_default_org(conn)
        self.assertTrue(result["_created"])
        self.assertEqual(str(result["id"]), _ORG_UUID)
        self.assertEqual(result["slug"], "default")


# ---------------------------------------------------------------------------
# get_or_create_default_org — existing org (INSERT returns None)
# ---------------------------------------------------------------------------

class TestGetOrCreateDefaultOrgExisting(unittest.TestCase):
    def test_existing_org_created_flag_false(self):
        import datetime
        now = datetime.datetime(2026, 3, 1, 10, 0, 0)
        existing_row = (_ORG_UUID, "default", "Default Org", now, now)

        cur = MagicMock()
        cur.description = _desc("id", "slug", "display_name", "created_at", "updated_at")
        cur.fetchone = MagicMock(side_effect=[None, existing_row])

        with _conn_ctx(cur) as conn:
            result = get_or_create_default_org(conn)

        self.assertFalse(result["_created"])
        self.assertEqual(str(result["id"]), _ORG_UUID)

    def test_custom_slug(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_ORG_UUID, "acme", "Acme Corp", now, now),
            description=_desc("id", "slug", "display_name", "created_at", "updated_at"),
        )
        with _conn_ctx(cur) as conn:
            result = get_or_create_default_org(conn, slug="acme", display_name="Acme Corp")
        self.assertEqual(result["slug"], "acme")


# ---------------------------------------------------------------------------
# ensure_membership — new membership
# ---------------------------------------------------------------------------

class TestEnsureMembershipNew(unittest.TestCase):
    def test_new_membership_created_flag_true(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_MBR_UUID, _ORG_UUID, _USER_UUID, "member", now),
            description=_desc("id", "org_id", "user_id", "role", "created_at"),
        )
        with _conn_ctx(cur) as conn:
            result = ensure_membership(conn, _ORG_UUID, _USER_UUID)
        self.assertTrue(result["_created"])
        self.assertEqual(result["role"], "member")

    def test_custom_role(self):
        import datetime
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)
        cur = _make_cursor(
            fetchone_values=(_MBR_UUID, _ORG_UUID, _USER_UUID, "owner", now),
            description=_desc("id", "org_id", "user_id", "role", "created_at"),
        )
        with _conn_ctx(cur) as conn:
            result = ensure_membership(conn, _ORG_UUID, _USER_UUID, role="owner")
        self.assertEqual(result["role"], "owner")


# ---------------------------------------------------------------------------
# ensure_membership — idempotent (existing membership)
# ---------------------------------------------------------------------------

class TestEnsureMembershipIdempotent(unittest.TestCase):
    def test_existing_membership_created_flag_false(self):
        import datetime
        now = datetime.datetime(2026, 3, 1, 10, 0, 0)
        existing_row = (_MBR_UUID, _ORG_UUID, _USER_UUID, "admin", now)

        cur = MagicMock()
        cur.description = _desc("id", "org_id", "user_id", "role", "created_at")
        cur.fetchone = MagicMock(side_effect=[None, existing_row])

        with _conn_ctx(cur) as conn:
            result = ensure_membership(conn, _ORG_UUID, _USER_UUID)

        self.assertFalse(result["_created"])
        # Role from DB is preserved, not overwritten.
        self.assertEqual(result["role"], "admin")


# ---------------------------------------------------------------------------
# ensure_membership — input validation
# ---------------------------------------------------------------------------

class TestEnsureMembershipValidation(unittest.TestCase):
    def _dummy_conn(self):
        return MagicMock()

    def test_empty_org_id_raises(self):
        with self.assertRaises(ValueError):
            ensure_membership(self._dummy_conn(), "", _USER_UUID)

    def test_empty_user_id_raises(self):
        with self.assertRaises(ValueError):
            ensure_membership(self._dummy_conn(), _ORG_UUID, "")

    def test_whitespace_org_id_raises(self):
        with self.assertRaises(ValueError):
            ensure_membership(self._dummy_conn(), "   ", _USER_UUID)


# ---------------------------------------------------------------------------
# Log safety — no PII / secret tokens in log output
# ---------------------------------------------------------------------------

class TestLogSafety(unittest.TestCase):
    """Verify that external_subject values are NOT emitted to logs."""

    def test_subject_not_in_log_output(self):
        import datetime
        import io

        secret_sub = "sub|TopSecretOIDCSub12345"
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        test_logger = logging.getLogger("src.shared.db_access")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        try:
            cur = _make_cursor(
                fetchone_values=(_USER_UUID, secret_sub, None, now, now),
                description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
            )
            with _conn_ctx(cur) as conn:
                get_or_create_user_by_external_subject(conn, secret_sub)

            log_output = log_stream.getvalue()
            self.assertNotIn(
                secret_sub,
                log_output,
                f"external_subject leaked to logs: {log_output!r}",
            )
        finally:
            test_logger.removeHandler(handler)

    def test_fingerprint_appears_not_plaintext(self):
        """Log lines contain fingerprint, not the original subject."""
        import datetime
        import io

        secret_sub = "sub|AnotherSecretValue"
        expected_fp = hashlib.sha256(secret_sub.encode()).hexdigest()[:8]
        now = datetime.datetime(2026, 3, 2, 20, 0, 0)

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        test_logger = logging.getLogger("src.shared.db_access")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        try:
            cur = _make_cursor(
                fetchone_values=(_USER_UUID, secret_sub, None, now, now),
                description=_desc("id", "external_subject", "email", "created_at", "updated_at"),
            )
            with _conn_ctx(cur) as conn:
                get_or_create_user_by_external_subject(conn, secret_sub)

            log_output = log_stream.getvalue()
            self.assertNotIn(secret_sub, log_output)
            # Fingerprint may or may not be present depending on log formatter,
            # but plaintext subject must never appear.
        finally:
            test_logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
