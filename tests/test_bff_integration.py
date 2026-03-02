"""BFF Integration Smoke Tests.

Tests the full BFF stack end-to-end using mock OIDC and API servers.
No real network calls; all external interactions use injectable function
parameters to simulate Cognito token exchange and downstream API responses.

Issue: #854 (BFF-0.wp5)

Scenarios:
1. Full Login Flow: build_login_redirect → mock callback → handle_callback
   → session contains tokens + user_claims
2. /me after login: handle_me returns user_claims (no tokens)
3. Logout flow: handle_logout clears session; /me returns 401 after
4. Portal proxy: handle_portal_proxy forwards request with Bearer token
5. Auto-Refresh integration: expired token → bff_get_valid_access_token
   triggers refresh → updated session used for proxy call
6. Refresh failure: refresh error → session deleted → proxy returns 401
7. CSRF enforcement on proxy POST: missing header → 403; correct header → 200
8. State mismatch on callback: handle_callback raises OidcCallbackError
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from src.api.bff_oidc import (
    BffOidcConfig,
    OidcCallbackError,
    build_login_redirect,
    handle_callback,
)
from src.api.bff_portal_proxy import handle_portal_proxy
from src.api.bff_session import BffSessionStore, parse_session_id_from_cookie
from src.api.bff_token_delegation import (
    BffTokenError,
    bff_get_valid_access_token,
    handle_logout,
    handle_me,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_ISSUER = "https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_TEST"
_CLIENT_ID = "test-client-id"
_REDIRECT_URI = "https://app.example.com/auth/callback"
_PORTAL_API_BASE = "http://api.internal:8080"
_COOKIE_NAME = "__Host-session"


@pytest.fixture()
def oidc_config() -> BffOidcConfig:
    return BffOidcConfig(
        issuer=_ISSUER,
        client_id=_CLIENT_ID,
        client_secret="",
        redirect_uri=_REDIRECT_URI,
        scopes="openid email profile",
        authorization_endpoint=f"{_ISSUER}/oauth2/authorize",
        token_endpoint=f"{_ISSUER}/oauth2/token",
    )


@pytest.fixture()
def store() -> BffSessionStore:
    return BffSessionStore(ttl_seconds=3600)


# ---------------------------------------------------------------------------
# Helper: build a minimal valid id_token payload (not signed)
# ---------------------------------------------------------------------------


def _make_id_token(claims: dict[str, Any]) -> str:
    """Build a minimal unsigned JWT (header.payload.sig) for testing."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload_bytes = json.dumps(claims).encode()
    payload = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


def _cookie_header(session_id: str) -> str:
    return f"{_COOKIE_NAME}={session_id}"


# ---------------------------------------------------------------------------
# Helpers: mock token exchange functions
# ---------------------------------------------------------------------------


def _make_token_exchange_fn(
    access_token: str = "AT-test",
    refresh_token: str = "RT-test",
    expires_in: int = 3600,
    user_claims: dict[str, Any] | None = None,
) -> Any:
    claims = user_claims or {"sub": "u-001", "email": "test@example.com"}
    id_token = _make_id_token(claims)

    def _fn(token_endpoint: str, params: dict[str, str], client_secret: str | None) -> dict[str, Any]:
        # Basic validation: required params must be present
        assert "code" in params
        assert "code_verifier" in params
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "id_token": id_token,
            "expires_in": expires_in,
        }

    return _fn


def _make_refresh_fn(
    access_token: str = "AT-refreshed",
    expires_in: int = 3600,
) -> Any:
    def _fn(endpoint: str, client_id: str, refresh_token: str, *, client_secret: str = "") -> dict[str, Any]:
        return {"access_token": access_token, "expires_in": expires_in}

    return _fn


def _make_urlopen_fn(status: int, body: bytes) -> Any:
    class _Resp:
        def __init__(self):
            self.status = status
            self.headers = {"Content-Type": "application/json"}

        def read(self):
            return body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    def _fn(req, timeout=None):
        return _Resp()

    return _fn


# ---------------------------------------------------------------------------
# Scenario 1: Full Login Flow
# ---------------------------------------------------------------------------


class TestFullLoginFlow:
    def test_login_redirect_creates_session(self, oidc_config, store):
        result = build_login_redirect(oidc_config, store)
        assert result.session.session_id
        assert result.session.pkce_code_verifier
        assert result.session.oauth_state
        assert oidc_config.authorization_endpoint in result.redirect_url
        assert "code_challenge" in result.redirect_url
        assert "state=" in result.redirect_url

    def test_callback_stores_tokens_in_session(self, oidc_config, store):
        # Step 1: Login
        login = build_login_redirect(oidc_config, store)
        session = login.session
        cookie = _cookie_header(session.session_id)

        # Step 2: Simulate IdP callback
        query = {
            "code": ["auth-code-xyz"],
            "state": [session.oauth_state],
        }
        result = handle_callback(
            oidc_config,
            store,
            cookie_header=cookie,
            query_params=query,
            token_exchange_fn=_make_token_exchange_fn(),
        )

        # Tokens stored in session
        assert result.session.access_token == "AT-test"
        assert result.session.refresh_token == "RT-test"
        # PKCE fields cleared
        assert result.session.pkce_code_verifier == ""
        assert result.session.oauth_state == ""
        # Redirect path
        assert result.redirect_path == "/"

    def test_callback_populates_user_claims(self, oidc_config, store):
        login = build_login_redirect(oidc_config, store)
        session = login.session
        cookie = _cookie_header(session.session_id)

        query = {"code": ["code-001"], "state": [session.oauth_state]}
        result = handle_callback(
            oidc_config,
            store,
            cookie_header=cookie,
            query_params=query,
            token_exchange_fn=_make_token_exchange_fn(
                user_claims={"sub": "u-42", "email": "alice@test.com", "org": "acme"}
            ),
        )
        assert result.session.user_claims.get("sub") == "u-42"
        assert result.session.user_claims.get("email") == "alice@test.com"

    def test_state_mismatch_raises_error(self, oidc_config, store):
        login = build_login_redirect(oidc_config, store)
        session = login.session
        cookie = _cookie_header(session.session_id)

        query = {"code": ["code-001"], "state": ["WRONG-STATE"]}
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                oidc_config,
                store,
                cookie_header=cookie,
                query_params=query,
                token_exchange_fn=_make_token_exchange_fn(),
            )
        assert exc_info.value.error_code == "state_mismatch"
        assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# Scenario 2: /me after Login
# ---------------------------------------------------------------------------


class TestMeAfterLogin:
    def _do_login_callback(self, oidc_config, store, claims=None):
        login = build_login_redirect(oidc_config, store)
        session = login.session
        cookie = _cookie_header(session.session_id)
        query = {"code": ["code-me"], "state": [session.oauth_state]}
        handle_callback(
            oidc_config,
            store,
            cookie_header=cookie,
            query_params=query,
            token_exchange_fn=_make_token_exchange_fn(user_claims=claims or {"sub": "u-me"}),
        )
        return session, cookie

    def test_me_returns_200_with_claims(self, oidc_config, store):
        session, cookie = self._do_login_callback(
            oidc_config, store, claims={"sub": "u-999", "email": "me@test.com"}
        )
        result = handle_me(store, cookie)
        assert result.http_status == 200
        assert result.user_claims["sub"] == "u-999"
        assert result.user_claims["email"] == "me@test.com"

    def test_me_no_tokens_in_response(self, oidc_config, store):
        _, cookie = self._do_login_callback(oidc_config, store)
        result = handle_me(store, cookie)
        assert "access_token" not in result.user_claims
        assert "refresh_token" not in result.user_claims
        assert "id_token" not in result.user_claims

    def test_me_without_login_returns_401(self, store):
        result = handle_me(store, None)
        assert result.http_status == 401

    def test_me_with_fake_session_returns_401(self, store):
        result = handle_me(store, _cookie_header("fake-session-id"))
        assert result.http_status == 401


# ---------------------------------------------------------------------------
# Scenario 3: Logout Flow
# ---------------------------------------------------------------------------


class TestLogoutFlow:
    def _do_login(self, oidc_config, store):
        login = build_login_redirect(oidc_config, store)
        session = login.session
        cookie = _cookie_header(session.session_id)
        query = {"code": ["code-logout"], "state": [session.oauth_state]}
        handle_callback(
            oidc_config,
            store,
            cookie_header=cookie,
            query_params=query,
            token_exchange_fn=_make_token_exchange_fn(),
        )
        return session, cookie

    def test_logout_clears_session(self, oidc_config, store):
        session, cookie = self._do_login(oidc_config, store)

        # Verify session exists
        assert store.get(session.session_id) is not None

        result = handle_logout(store, cookie)
        assert "Max-Age=0" in result.set_cookie_header
        # Session deleted
        assert store.get(session.session_id) is None

    def test_me_after_logout_returns_401(self, oidc_config, store):
        session, cookie = self._do_login(oidc_config, store)
        handle_logout(store, cookie)
        result = handle_me(store, cookie)
        assert result.http_status == 401

    def test_logout_with_idp_config_returns_302(self, oidc_config, store):
        _, cookie = self._do_login(oidc_config, store)
        result = handle_logout(
            store,
            cookie,
            _logout_endpoint_override=f"{_ISSUER}/logout",
            _client_id_override=_CLIENT_ID,
        )
        assert result.http_status == 302
        assert _ISSUER in result.redirect_url

    def test_double_logout_is_idempotent(self, oidc_config, store):
        _, cookie = self._do_login(oidc_config, store)
        handle_logout(store, cookie)
        result2 = handle_logout(store, cookie)  # session already gone
        assert "Max-Age=0" in result2.set_cookie_header


# ---------------------------------------------------------------------------
# Scenario 4: Portal Proxy Call
# ---------------------------------------------------------------------------


class TestPortalProxyIntegration:
    def _do_login(self, oidc_config, store, access_token="AT-proxy"):
        login = build_login_redirect(oidc_config, store)
        session = login.session
        cookie = _cookie_header(session.session_id)
        query = {"code": ["code-proxy"], "state": [session.oauth_state]}
        handle_callback(
            oidc_config,
            store,
            cookie_header=cookie,
            query_params=query,
            token_exchange_fn=_make_token_exchange_fn(access_token=access_token),
        )
        return session, cookie

    def test_proxy_forwards_request_with_bearer(self, oidc_config, store):
        session, cookie = self._do_login(oidc_config, store, access_token="AT-proxy")
        urlopen_fn = _make_urlopen_fn(200, b'{"results": []}')

        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/analyze/history",
            _portal_api_base_override=_PORTAL_API_BASE,
            _urlopen_fn=urlopen_fn,
        )
        assert result.http_status == 200
        assert result.error == ""

    def test_proxy_without_login_returns_401(self, store):
        result = handle_portal_proxy(
            store,
            None,
            "GET",
            "/portal/api/data",
            _portal_api_base_override=_PORTAL_API_BASE,
        )
        assert result.http_status == 401

    def test_proxy_post_csrf_failure_returns_403(self, oidc_config, store):
        _, cookie = self._do_login(oidc_config, store)
        result = handle_portal_proxy(
            store,
            cookie,
            "POST",
            "/portal/api/jobs",
            request_headers={},  # no X-BFF-CSRF
            _portal_api_base_override=_PORTAL_API_BASE,
        )
        assert result.http_status == 403

    def test_proxy_post_with_csrf_header_succeeds(self, oidc_config, store):
        _, cookie = self._do_login(oidc_config, store)
        urlopen_fn = _make_urlopen_fn(201, b'{"id": "job-1"}')

        result = handle_portal_proxy(
            store,
            cookie,
            "POST",
            "/portal/api/jobs",
            request_headers={"X-BFF-CSRF": "1"},
            _portal_api_base_override=_PORTAL_API_BASE,
            _urlopen_fn=urlopen_fn,
        )
        assert result.http_status == 201


# ---------------------------------------------------------------------------
# Scenario 5: Auto-Refresh Integration
# ---------------------------------------------------------------------------


class TestAutoRefreshIntegration:
    def test_expired_token_is_refreshed_transparently(self, store):
        """When access_token is expired, bff_get_valid_access_token refreshes it."""
        session = store.create()
        session.access_token = "AT-expired"
        session.refresh_token = "RT-valid"
        session.access_token_expires_at = 1.0  # epoch → already expired

        new_token = bff_get_valid_access_token(
            session,
            store,
            _token_endpoint_override=f"{_ISSUER}/oauth2/token",
            _client_id_override=_CLIENT_ID,
            _refresh_fn=_make_refresh_fn(access_token="AT-new", expires_in=3600),
        )
        assert new_token == "AT-new"
        assert session.access_token == "AT-new"
        assert session.access_token_expires_at > time.time()

    def test_proxy_uses_refreshed_token_on_expired(self, oidc_config, store):
        """Proxy call with expired AT → auto-refresh → downstream receives new token."""
        login = build_login_redirect(oidc_config, store)
        session = login.session
        cookie = _cookie_header(session.session_id)

        # Simulate login callback
        query = {"code": ["code-refresh"], "state": [session.oauth_state]}
        handle_callback(
            oidc_config,
            store,
            cookie_header=cookie,
            query_params=query,
            token_exchange_fn=_make_token_exchange_fn(access_token="AT-old"),
        )

        # Force token expiry
        session.access_token_expires_at = 1.0

        captured_auth: list[str] = []

        def _urlopen(req, timeout=None):
            captured_auth.append(req.get_header("Authorization") or "")
            return MagicMock(
                status=200,
                headers={"Content-Type": "application/json"},
                read=lambda: b"{}",
                __enter__=lambda self: self,
                __exit__=MagicMock(return_value=False),
            )

        handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/data",
            _portal_api_base_override=_PORTAL_API_BASE,
            _token_endpoint_override=f"{_ISSUER}/oauth2/token",
            _client_id_override=_CLIENT_ID,
            _refresh_fn=_make_refresh_fn(access_token="AT-refreshed"),
            _urlopen_fn=_urlopen,
        )
        assert len(captured_auth) == 1
        assert captured_auth[0] == "Bearer AT-refreshed"


# ---------------------------------------------------------------------------
# Scenario 6: Refresh Failure → 401
# ---------------------------------------------------------------------------


class TestRefreshFailureIntegration:
    def test_refresh_failure_returns_401_from_proxy(self, oidc_config, store):
        login = build_login_redirect(oidc_config, store)
        session = login.session
        cookie = _cookie_header(session.session_id)

        query = {"code": ["code-fail"], "state": [session.oauth_state]}
        handle_callback(
            oidc_config,
            store,
            cookie_header=cookie,
            query_params=query,
            token_exchange_fn=_make_token_exchange_fn(access_token="AT-old"),
        )

        # Force expiry + bad refresh response
        session.access_token_expires_at = 1.0

        def _fail_refresh(endpoint, client_id, refresh_token, *, client_secret=""):
            raise BffTokenError("refresh_token invalid", error_code="refresh_network_error")

        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/data",
            _portal_api_base_override=_PORTAL_API_BASE,
            _token_endpoint_override=f"{_ISSUER}/oauth2/token",
            _client_id_override=_CLIENT_ID,
            _refresh_fn=_fail_refresh,
        )
        assert result.http_status == 401
        # Session should be deleted
        assert store.get(session.session_id) is None
