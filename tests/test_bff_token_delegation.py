"""Unit tests for src/api/bff_token_delegation.py.

Issue: #852 (BFF-0.wp3)

Coverage:
- bff_get_valid_access_token: valid token (no refresh), expired → refresh success,
  expired → refresh HTTP error (session deleted), expired → grant error response,
  expired → missing access_token in response, no access_token in session,
  no refresh_token in session, refresh token rotation, unknown expiry (0.0).
- bff_api_call: success path, downstream HTTP error passthrough, network error,
  Authorization header injection (cannot be overridden).
- handle_logout: with IdP config → 302 + redirect URL, without IdP config → 204,
  missing cookie → still clears, already-expired session → idempotent.
- handle_me: 200 with claims, 401 no cookie, 401 session expired/missing,
  internal fields (_next, token fields) filtered out.
- safe_log: redacts token fields.
"""

from __future__ import annotations

import time
from http.client import HTTPMessage
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.api.bff_session import BffSession, BffSessionStore
from src.api.bff_token_delegation import (
    BffApiCallError,
    BffApiResponse,
    BffTokenError,
    LogoutResult,
    MeResult,
    bff_api_call,
    bff_get_valid_access_token,
    handle_logout,
    handle_me,
    safe_log,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_COOKIE_NAME = "__Host-session"


def _make_store() -> BffSessionStore:
    return BffSessionStore(ttl_seconds=3600)


def _make_session(
    store: BffSessionStore,
    *,
    access_token: str = "AT-valid",
    refresh_token: str = "RT-valid",
    expires_at: float = 0.0,  # 0 = unknown → assume valid
    claims: dict[str, Any] | None = None,
) -> BffSession:
    session = store.create()
    session.access_token = access_token
    session.refresh_token = refresh_token
    session.access_token_expires_at = expires_at
    if claims:
        session.user_claims.update(claims)
    return session


def _cookie_header(session_id: str) -> str:
    return f"{_COOKIE_NAME}={session_id}"


def _make_refresh_fn(response: dict[str, Any]):
    """Return a mock refresh function that returns *response*."""

    def _fn(endpoint, client_id, refresh_token, *, client_secret=""):
        return response

    return _fn


def _make_urlopen_fn(status: int, body: bytes, content_type: str = "application/json"):
    """Return a mock urlopen callable that returns a fake HTTP response."""

    class _FakeResp:
        def __init__(self) -> None:
            self.status = status
            self.headers = {"Content-Type": content_type}

        def read(self) -> bytes:
            return body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    def _fn(req, timeout=None):
        return _FakeResp()

    return _fn


# ---------------------------------------------------------------------------
# safe_log
# ---------------------------------------------------------------------------


class TestSafeLog:
    def test_redacts_access_token(self):
        result = safe_log({"access_token": "secret", "email": "u@test.com"})
        assert result["access_token"] == "[REDACTED]"
        assert result["email"] == "u@test.com"

    def test_redacts_refresh_token(self):
        result = safe_log({"refresh_token": "secret"})
        assert result["refresh_token"] == "[REDACTED]"

    def test_redacts_id_token(self):
        result = safe_log({"id_token": "secret"})
        assert result["id_token"] == "[REDACTED]"

    def test_non_token_keys_unchanged(self):
        result = safe_log({"sub": "123", "email": "x@y.com"})
        assert result == {"sub": "123", "email": "x@y.com"}

    def test_empty_dict(self):
        assert safe_log({}) == {}


# ---------------------------------------------------------------------------
# bff_get_valid_access_token
# ---------------------------------------------------------------------------


class TestBffGetValidAccessToken:
    def test_returns_token_when_not_expired(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-good", expires_at=time.time() + 300)
        token = bff_get_valid_access_token(session, store)
        assert token == "AT-good"

    def test_returns_token_when_expiry_unknown(self):
        """expires_at == 0 → assume valid, no refresh."""
        store = _make_store()
        session = _make_session(store, access_token="AT-good", expires_at=0.0)
        token = bff_get_valid_access_token(session, store)
        assert token == "AT-good"

    def test_raises_when_no_access_token(self):
        store = _make_store()
        session = _make_session(store, access_token="", expires_at=0.0)
        with pytest.raises(BffTokenError) as exc_info:
            bff_get_valid_access_token(session, store)
        assert exc_info.value.error_code == "no_access_token"
        # Session should be deleted
        assert store.get(session.session_id) is None

    def test_raises_when_expired_no_refresh_token(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-expired", refresh_token="", expires_at=1.0)
        with pytest.raises(BffTokenError) as exc_info:
            bff_get_valid_access_token(session, store)
        assert exc_info.value.error_code == "no_refresh_token"
        assert store.get(session.session_id) is None

    def test_refreshes_expired_token(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-old", expires_at=1.0)

        refresh_resp = {
            "access_token": "AT-new",
            "refresh_token": "RT-new",
            "expires_in": 3600,
        }
        token = bff_get_valid_access_token(
            session,
            store,
            _token_endpoint_override="https://tok.test",
            _client_id_override="cid-test",
            _refresh_fn=_make_refresh_fn(refresh_resp),
        )
        assert token == "AT-new"
        assert session.access_token == "AT-new"
        assert session.refresh_token == "RT-new"
        assert session.access_token_expires_at > time.time()

    def test_refresh_token_rotation_stored(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-old", refresh_token="RT-old", expires_at=1.0)
        refresh_resp = {"access_token": "AT-new", "expires_in": 3600, "refresh_token": "RT-rotated"}
        bff_get_valid_access_token(
            session,
            store,
            _token_endpoint_override="https://tok.test",
            _client_id_override="cid-test",
            _refresh_fn=_make_refresh_fn(refresh_resp),
        )
        assert session.refresh_token == "RT-rotated"

    def test_refresh_no_expires_in_sets_zero(self):
        """If no expires_in in response, expires_at becomes 0 (unknown)."""
        store = _make_store()
        session = _make_session(store, access_token="AT-old", expires_at=1.0)
        refresh_resp = {"access_token": "AT-new"}
        bff_get_valid_access_token(
            session,
            store,
            _token_endpoint_override="https://tok.test",
            _client_id_override="cid-test",
            _refresh_fn=_make_refresh_fn(refresh_resp),
        )
        assert session.access_token_expires_at == 0.0

    def test_refresh_error_response_deletes_session(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-old", expires_at=1.0)
        refresh_resp = {"error": "invalid_grant", "error_description": "Token expired"}
        with pytest.raises(BffTokenError) as exc_info:
            bff_get_valid_access_token(
                session,
                store,
                _token_endpoint_override="https://tok.test",
                _client_id_override="cid-test",
                _refresh_fn=_make_refresh_fn(refresh_resp),
            )
        assert exc_info.value.error_code == "refresh_grant_error"
        assert "Token expired" in exc_info.value.message
        assert store.get(session.session_id) is None

    def test_refresh_missing_access_token_deletes_session(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-old", expires_at=1.0)
        refresh_resp = {"expires_in": 3600}  # no access_token key
        with pytest.raises(BffTokenError) as exc_info:
            bff_get_valid_access_token(
                session,
                store,
                _token_endpoint_override="https://tok.test",
                _client_id_override="cid-test",
                _refresh_fn=_make_refresh_fn(refresh_resp),
            )
        assert exc_info.value.error_code == "refresh_missing_token"
        assert store.get(session.session_id) is None

    def test_refresh_network_error_deletes_session(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-old", expires_at=1.0)

        def _fail(*_args, **_kwargs):
            raise BffTokenError("network failure", error_code="refresh_network_error")

        with pytest.raises(BffTokenError):
            bff_get_valid_access_token(
                session,
                store,
                _token_endpoint_override="https://tok.test",
                _client_id_override="cid-test",
                _refresh_fn=_fail,
            )
        assert store.get(session.session_id) is None

    def test_missing_oidc_config_deletes_session(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-old", expires_at=1.0)
        # No override, no env vars
        with pytest.raises(BffTokenError) as exc_info:
            bff_get_valid_access_token(session, store)
        assert exc_info.value.error_code == "missing_oidc_config"
        assert store.get(session.session_id) is None


# ---------------------------------------------------------------------------
# bff_api_call
# ---------------------------------------------------------------------------


class TestBffApiCall:
    def test_success_injects_bearer_header(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-valid", expires_at=0.0)

        captured_req = {}

        def _urlopen(req, timeout=None):
            captured_req["headers"] = dict(req.headers)
            return MagicMock(
                status=200,
                headers={"Content-Type": "application/json"},
                read=lambda: b'{"ok": true}',
                __enter__=lambda self: self,
                __exit__=MagicMock(return_value=False),
            )

        resp = bff_api_call(
            session,
            store,
            "GET",
            "https://api.internal/v1/data",
            _urlopen_fn=_urlopen,
        )
        assert resp.status_code == 200
        assert resp.body == b'{"ok": true}'
        assert captured_req["headers"].get("Authorization") == "Bearer AT-valid"

    def test_downstream_http_error_passthrough(self):
        """HTTPError from downstream → BffApiResponse with that status (not raised)."""
        store = _make_store()
        session = _make_session(store, access_token="AT-valid", expires_at=0.0)

        from urllib.error import HTTPError

        def _urlopen(req, timeout=None):
            raise HTTPError(
                url="https://api.internal/v1/data",
                code=404,
                msg="Not Found",
                hdrs=MagicMock(get=lambda k, d="": "application/json" if k == "Content-Type" else d),
                fp=BytesIO(b'{"error": "not_found"}'),
            )

        resp = bff_api_call(
            session,
            store,
            "GET",
            "https://api.internal/v1/data",
            _urlopen_fn=_urlopen,
        )
        assert resp.status_code == 404

    def test_network_error_raises_bff_api_call_error(self):
        store = _make_store()
        session = _make_session(store, access_token="AT-valid", expires_at=0.0)

        from urllib.error import URLError

        def _urlopen(req, timeout=None):
            raise URLError("Connection refused")

        with pytest.raises(BffApiCallError) as exc_info:
            bff_api_call(
                session,
                store,
                "GET",
                "https://api.internal/v1/data",
                _urlopen_fn=_urlopen,
            )
        assert exc_info.value.http_status == 502
        assert exc_info.value.error_code == "api_network_error"

    def test_extra_headers_merged_but_not_override_auth(self):
        """extra_headers are forwarded; Authorization must always be the token."""
        store = _make_store()
        session = _make_session(store, access_token="AT-valid", expires_at=0.0)

        captured_req = {}

        def _urlopen(req, timeout=None):
            captured_req["headers"] = dict(req.headers)
            return MagicMock(
                status=200,
                headers={"Content-Type": "text/plain"},
                read=lambda: b"ok",
                __enter__=lambda self: self,
                __exit__=MagicMock(return_value=False),
            )

        bff_api_call(
            session,
            store,
            "GET",
            "https://api.internal/v1/x",
            extra_headers={"X-Custom": "test", "Authorization": "Bearer MUST-BE-OVERRIDDEN"},
            _urlopen_fn=_urlopen,
        )
        # The injected token must win even if caller passes an Authorization header
        assert captured_req["headers"].get("Authorization") == "Bearer AT-valid"
        assert captured_req["headers"].get("X-custom") == "test"

    def test_token_error_propagates(self):
        """If bff_get_valid_access_token raises, bff_api_call propagates it."""
        store = _make_store()
        session = _make_session(store, access_token="", expires_at=0.0)
        with pytest.raises(BffTokenError):
            bff_api_call(session, store, "GET", "https://api.internal/v1/x")


# ---------------------------------------------------------------------------
# handle_logout
# ---------------------------------------------------------------------------


class TestHandleLogout:
    def test_logout_without_idp_config_returns_204(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        result = handle_logout(store, cookie)

        assert result.http_status == 204
        assert result.redirect_url == ""
        assert "Max-Age=0" in result.set_cookie_header
        # Session deleted
        assert store.get(session.session_id) is None

    def test_logout_with_idp_config_returns_302(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        result = handle_logout(
            store,
            cookie,
            _logout_endpoint_override="https://auth.test/logout",
            _client_id_override="cid-test",
            _post_logout_redirect_uri_override="https://app.test/",
        )

        assert result.http_status == 302
        assert "https://auth.test/logout" in result.redirect_url
        assert "cid-test" in result.redirect_url
        assert "Max-Age=0" in result.set_cookie_header
        assert store.get(session.session_id) is None

    def test_logout_redirect_url_contains_logout_uri(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        result = handle_logout(
            store,
            cookie,
            _logout_endpoint_override="https://auth.test/logout",
            _client_id_override="cid",
            _post_logout_redirect_uri_override="https://app.test/post-logout",
        )
        assert "logout_uri=https%3A%2F%2Fapp.test%2Fpost-logout" in result.redirect_url

    def test_logout_prefers_explicit_post_logout_env(self, monkeypatch):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        monkeypatch.setenv("BFF_OIDC_POST_LOGOUT_REDIRECT_URI", "https://app.test/bye")
        monkeypatch.setenv("BFF_OIDC_REDIRECT_URI", "https://app.test/auth/callback")

        result = handle_logout(
            store,
            cookie,
            _logout_endpoint_override="https://auth.test/logout",
            _client_id_override="cid",
        )

        assert "logout_uri=https%3A%2F%2Fapp.test%2Fbye" in result.redirect_url

    def test_logout_derives_login_path_from_callback_when_no_post_logout_env(self, monkeypatch):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        monkeypatch.delenv("BFF_OIDC_POST_LOGOUT_REDIRECT_URI", raising=False)
        monkeypatch.setenv("BFF_OIDC_REDIRECT_URI", "https://app.test/auth/callback")

        result = handle_logout(
            store,
            cookie,
            _logout_endpoint_override="https://auth.test/logout",
            _client_id_override="cid",
        )

        assert "logout_uri=https%3A%2F%2Fapp.test%2Fauth%2Flogin" in result.redirect_url

    def test_logout_missing_cookie_still_clears(self):
        """Even without a session cookie, logout returns a clear-cookie header."""
        store = _make_store()
        result = handle_logout(store, None)
        assert "Max-Age=0" in result.set_cookie_header
        assert result.http_status == 204

    def test_logout_expired_session_idempotent(self):
        """Expired session: still returns clear cookie, no error."""
        store = _make_store()
        session = _make_session(store)
        # Force-expire by deleting from store
        store.delete(session.session_id)
        cookie = _cookie_header(session.session_id)
        result = handle_logout(store, cookie)
        assert "Max-Age=0" in result.set_cookie_header


# ---------------------------------------------------------------------------
# handle_me
# ---------------------------------------------------------------------------


class TestHandleMe:
    def test_200_returns_user_claims(self):
        store = _make_store()
        session = _make_session(
            store,
            claims={"sub": "u-123", "email": "user@test.com", "org": "test-org"},
        )
        cookie = _cookie_header(session.session_id)

        result = handle_me(store, cookie)

        assert result.http_status == 200
        assert result.user_claims["sub"] == "u-123"
        assert result.user_claims["email"] == "user@test.com"
        assert result.session_expires_at >= time.time()
        assert result.session_expires_in_seconds >= 0
        assert result.error == ""

    def test_401_no_cookie(self):
        store = _make_store()
        result = handle_me(store, None)
        assert result.http_status == 401
        assert result.error == "no_session_cookie"
        assert result.user_claims == {}
        assert result.session_expires_at == 0.0
        assert result.session_expires_in_seconds == 0

    def test_401_missing_session(self):
        store = _make_store()
        cookie = f"{_COOKIE_NAME}=nonexistent-session-id"
        result = handle_me(store, cookie)
        assert result.http_status == 401
        assert result.error == "session_not_found"

    def test_401_expired_session(self):
        store = BffSessionStore(ttl_seconds=1)
        session = store.create()
        session.user_claims["sub"] = "u-expire"
        # Force expire by setting ttl in the past
        session.session_expires_at = time.time() - 1
        cookie = _cookie_header(session.session_id)

        result = handle_me(store, cookie)
        assert result.http_status == 401

    def test_internal_fields_filtered(self):
        """_next, token fields must not appear in /me response."""
        store = _make_store()
        session = _make_session(
            store,
            claims={
                "sub": "u-123",
                "_next": "/dashboard",
                "access_token": "SHOULD-NOT-APPEAR",
                "refresh_token": "SHOULD-NOT-APPEAR",
                "id_token": "SHOULD-NOT-APPEAR",
            },
        )
        cookie = _cookie_header(session.session_id)

        result = handle_me(store, cookie)
        assert result.http_status == 200
        assert "_next" not in result.user_claims
        assert "access_token" not in result.user_claims
        assert "refresh_token" not in result.user_claims
        assert "id_token" not in result.user_claims
        assert result.user_claims.get("sub") == "u-123"

    def test_empty_claims_returns_empty_dict(self):
        store = _make_store()
        session = _make_session(store)
        # No user_claims
        cookie = _cookie_header(session.session_id)
        result = handle_me(store, cookie)
        assert result.http_status == 200
        assert result.user_claims == {}
