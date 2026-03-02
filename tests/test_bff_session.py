"""Unit tests for src/api/bff_session.py (BFF Session Store + Cookie helpers).

Issue: #850 (BFF-0.wp1)
"""

from __future__ import annotations

import os
import time

import pytest

from src.api.bff_session import (
    BffSession,
    BffSessionStore,
    build_clear_cookie_header,
    build_set_cookie_header,
    get_session_store,
    parse_session_id_from_cookie,
)


# ---------------------------------------------------------------------------
# BffSession model
# ---------------------------------------------------------------------------


class TestBffSession:
    def test_session_id_is_set(self) -> None:
        s = BffSession(session_id="abc", session_expires_at=time.time() + 3600)
        assert s.session_id == "abc"

    def test_not_expired_when_future(self) -> None:
        s = BffSession(session_id="x", session_expires_at=time.time() + 100)
        assert not s.is_expired()

    def test_expired_when_past(self) -> None:
        s = BffSession(session_id="x", session_expires_at=time.time() - 1)
        assert s.is_expired()

    def test_access_token_expired_when_past(self) -> None:
        s = BffSession(
            session_id="x",
            session_expires_at=time.time() + 3600,
            access_token="tok",
            access_token_expires_at=time.time() - 1,
        )
        assert s.is_access_token_expired()

    def test_access_token_not_expired_when_future(self) -> None:
        s = BffSession(
            session_id="x",
            session_expires_at=time.time() + 3600,
            access_token="tok",
            access_token_expires_at=time.time() + 3600,
        )
        assert not s.is_access_token_expired()

    def test_access_token_unknown_not_expired(self) -> None:
        """When access_token_expires_at == 0 (unknown), return not-expired."""
        s = BffSession(session_id="x", session_expires_at=time.time() + 3600)
        assert not s.is_access_token_expired()

    def test_clock_skew_triggers_early_refresh(self) -> None:
        """Token expires in 10s but clock skew is 30s → treated as expired."""
        s = BffSession(
            session_id="x",
            session_expires_at=time.time() + 3600,
            access_token="tok",
            access_token_expires_at=time.time() + 10,
        )
        assert s.is_access_token_expired(clock_skew_seconds=30)

    def test_safe_repr_redacts_tokens(self) -> None:
        s = BffSession(
            session_id="sess-1",
            session_expires_at=time.time() + 3600,
            access_token="secret-access-token",
            refresh_token="secret-refresh-token",
            id_token="secret-id-token",
            user_claims={"sub": "user123"},
        )
        r = s.safe_repr()
        assert r["access_token"] == "[REDACTED]"
        assert r["refresh_token"] == "[REDACTED]"
        assert r["id_token"] == "[REDACTED]"
        assert r["user_claims"]["sub"] == "user123"
        assert "secret-access-token" not in str(r)
        assert "secret-refresh-token" not in str(r)

    def test_safe_repr_empty_tokens_not_redacted(self) -> None:
        s = BffSession(session_id="x", session_expires_at=time.time() + 3600)
        r = s.safe_repr()
        assert r["access_token"] == ""
        assert r["refresh_token"] == ""


# ---------------------------------------------------------------------------
# BffSessionStore
# ---------------------------------------------------------------------------


class TestBffSessionStore:
    def test_create_returns_session(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        session = store.create()
        assert isinstance(session, BffSession)
        assert len(session.session_id) == 64  # 32 bytes hex = 64 chars

    def test_session_id_is_unique(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        ids = {store.create().session_id for _ in range(50)}
        assert len(ids) == 50

    def test_get_returns_session(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        s = store.create()
        fetched = store.get(s.session_id)
        assert fetched is not None
        assert fetched.session_id == s.session_id

    def test_get_unknown_id_returns_none(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        assert store.get("nonexistent") is None

    def test_get_expired_session_returns_none(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        s = store.create()
        # Force expiry
        s.session_expires_at = time.time() - 1
        assert store.get(s.session_id) is None

    def test_get_expired_removes_from_store(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        s = store.create()
        s.session_expires_at = time.time() - 1
        store.get(s.session_id)
        assert len(store) == 0

    def test_delete_removes_session(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        s = store.create()
        store.delete(s.session_id)
        assert store.get(s.session_id) is None

    def test_delete_nonexistent_is_idempotent(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        store.delete("nonexistent")  # must not raise

    def test_renew_extends_expiry(self) -> None:
        store = BffSessionStore(ttl_seconds=100)
        s = store.create()
        old_expiry = s.session_expires_at
        time.sleep(0.01)
        result = store.renew(s.session_id)
        assert result is True
        assert s.session_expires_at > old_expiry

    def test_renew_nonexistent_returns_false(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        assert store.renew("nonexistent") is False

    def test_renew_expired_session_returns_false(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        s = store.create()
        s.session_expires_at = time.time() - 1
        assert store.renew(s.session_id) is False

    def test_evict_expired(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        s1 = store.create()
        s2 = store.create()
        s3 = store.create()
        s1.session_expires_at = time.time() - 1
        s2.session_expires_at = time.time() - 1
        removed = store.evict_expired()
        assert removed == 2
        assert len(store) == 1
        assert store.get(s3.session_id) is not None

    def test_len_counts_active_sessions(self) -> None:
        store = BffSessionStore(ttl_seconds=3600)
        assert len(store) == 0
        store.create()
        store.create()
        assert len(store) == 2

    def test_store_is_independent_per_instance(self) -> None:
        store1 = BffSessionStore(ttl_seconds=3600)
        store2 = BffSessionStore(ttl_seconds=3600)
        s = store1.create()
        assert store2.get(s.session_id) is None

    def test_tokens_can_be_stored_in_session(self) -> None:
        """Ensure tokens persist through store get/create cycle."""
        store = BffSessionStore(ttl_seconds=3600)
        s = store.create()
        s.access_token = "at-value"
        s.refresh_token = "rt-value"
        s.id_token = "it-value"
        s.user_claims = {"sub": "user-42", "email": "test@example.com"}

        fetched = store.get(s.session_id)
        assert fetched is not None
        assert fetched.access_token == "at-value"
        assert fetched.refresh_token == "rt-value"
        assert fetched.user_claims["sub"] == "user-42"


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------


class TestBuildSetCookieHeader:
    def test_contains_session_id(self) -> None:
        hdr = build_set_cookie_header("test-session-id", ttl_seconds=3600)
        assert "test-session-id" in hdr

    def test_contains_httponly(self) -> None:
        hdr = build_set_cookie_header("sid", ttl_seconds=3600)
        assert "HttpOnly" in hdr

    def test_contains_samesite_lax(self) -> None:
        hdr = build_set_cookie_header("sid", ttl_seconds=3600)
        assert "SameSite=Lax" in hdr

    def test_contains_path_root(self) -> None:
        hdr = build_set_cookie_header("sid", ttl_seconds=3600)
        assert "Path=/" in hdr

    def test_contains_max_age(self) -> None:
        hdr = build_set_cookie_header("sid", ttl_seconds=7200)
        assert "Max-Age=7200" in hdr

    def test_secure_flag_when_enabled(self, monkeypatch) -> None:
        monkeypatch.setenv("BFF_SESSION_SECURE_COOKIE", "1")
        hdr = build_set_cookie_header("sid", ttl_seconds=3600)
        assert "Secure" in hdr

    def test_no_secure_flag_when_disabled(self, monkeypatch) -> None:
        monkeypatch.setenv("BFF_SESSION_SECURE_COOKIE", "0")
        hdr = build_set_cookie_header("sid", ttl_seconds=3600)
        assert "Secure" not in hdr

    def test_custom_cookie_name(self, monkeypatch) -> None:
        monkeypatch.setenv("BFF_SESSION_COOKIE_NAME", "my-session")
        hdr = build_set_cookie_header("sid", ttl_seconds=3600)
        assert hdr.startswith("my-session=sid")

    def test_default_cookie_name_is_host_prefixed(self, monkeypatch) -> None:
        monkeypatch.delenv("BFF_SESSION_COOKIE_NAME", raising=False)
        hdr = build_set_cookie_header("sid", ttl_seconds=3600)
        assert hdr.startswith("__Host-session=sid")


class TestBuildClearCookieHeader:
    def test_max_age_zero(self) -> None:
        hdr = build_clear_cookie_header()
        assert "Max-Age=0" in hdr

    def test_contains_httponly(self) -> None:
        hdr = build_clear_cookie_header()
        assert "HttpOnly" in hdr

    def test_cookie_name_present(self, monkeypatch) -> None:
        monkeypatch.delenv("BFF_SESSION_COOKIE_NAME", raising=False)
        hdr = build_clear_cookie_header()
        assert "__Host-session=deleted" in hdr


class TestParseSessionIdFromCookie:
    def test_single_cookie(self, monkeypatch) -> None:
        monkeypatch.delenv("BFF_SESSION_COOKIE_NAME", raising=False)
        sid = parse_session_id_from_cookie("__Host-session=abc123")
        assert sid == "abc123"

    def test_multiple_cookies(self, monkeypatch) -> None:
        monkeypatch.delenv("BFF_SESSION_COOKIE_NAME", raising=False)
        sid = parse_session_id_from_cookie("other=val; __Host-session=myid; another=x")
        assert sid == "myid"

    def test_missing_cookie_returns_none(self, monkeypatch) -> None:
        monkeypatch.delenv("BFF_SESSION_COOKIE_NAME", raising=False)
        assert parse_session_id_from_cookie("other=val") is None

    def test_none_header_returns_none(self) -> None:
        assert parse_session_id_from_cookie(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_session_id_from_cookie("") is None

    def test_custom_cookie_name(self, monkeypatch) -> None:
        monkeypatch.setenv("BFF_SESSION_COOKIE_NAME", "my-session")
        sid = parse_session_id_from_cookie("my-session=xyz; other=abc")
        assert sid == "xyz"

    def test_empty_value_returns_none(self, monkeypatch) -> None:
        monkeypatch.delenv("BFF_SESSION_COOKIE_NAME", raising=False)
        assert parse_session_id_from_cookie("__Host-session=") is None


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------


class TestGetSessionStore:
    def test_returns_same_instance(self) -> None:
        import importlib
        import src.api.bff_session as mod

        # Reset singleton for test isolation
        mod._store_instance = None
        s1 = get_session_store()
        s2 = get_session_store()
        assert s1 is s2

    def test_custom_ttl_from_env(self, monkeypatch) -> None:
        import src.api.bff_session as mod

        mod._store_instance = None
        monkeypatch.setenv("BFF_SESSION_TTL_SECONDS", "7200")
        store = get_session_store()
        assert store.ttl_seconds == 7200
        mod._store_instance = None  # cleanup
