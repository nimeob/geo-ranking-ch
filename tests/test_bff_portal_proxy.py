"""Unit tests for src/api/bff_portal_proxy.py.

Issue: #853 (BFF-0.wp4)

Coverage:
- require_csrf_header: safe methods (GET/HEAD/OPTIONS) pass without header,
  POST/PUT/PATCH/DELETE require X-BFF-CSRF: 1, wrong value → CsrfError,
  missing → CsrfError, case-insensitive header match.
- is_https_request / get_secure_cookie_flag: X-Forwarded-Proto, X-Forwarded-Ssl,
  missing → False, BFF_SESSION_SECURE_COOKIE=0 overrides.
- build_strict_set_cookie_header: SameSite=Strict present, HttpOnly, Secure,
  Max-Age, Path=/, no Secure when disabled.
- redact_authorization_header: Authorization, Cookie, Set-Cookie, X-Api-Key
  redacted; other headers unchanged; original not mutated.
- handle_portal_proxy: 401 no cookie, 401 missing session, 403 CSRF failure,
  502 missing base URL, 200 success passthrough, 404 downstream passthrough,
  502 network error, 401 token refresh failure, Cookie header stripped from
  downstream request.
"""

from __future__ import annotations

import json
import time
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.api.bff_session import BffSession, BffSessionStore
from src.api.bff_token_delegation import BffApiCallError, BffTokenError
from src.api.bff_portal_proxy import (
    CsrfError,
    build_strict_set_cookie_header,
    get_secure_cookie_flag,
    handle_portal_proxy,
    is_https_request,
    redact_authorization_header,
    require_csrf_header,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COOKIE_NAME = "__Host-session"


def _make_store() -> BffSessionStore:
    return BffSessionStore(ttl_seconds=3600)


def _make_session(store: BffSessionStore, *, access_token: str = "AT-valid") -> BffSession:
    session = store.create()
    session.access_token = access_token
    session.refresh_token = "RT-valid"
    session.access_token_expires_at = 0.0  # unknown → assume valid
    return session


def _cookie_header(session_id: str) -> str:
    return f"{_COOKIE_NAME}={session_id}"


def _make_urlopen_fn(status: int, body: bytes, content_type: str = "application/json"):
    class _Resp:
        def __init__(self):
            self.status = status
            self.headers = {"Content-Type": content_type}

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
# require_csrf_header
# ---------------------------------------------------------------------------


class TestRequireCsrfHeader:
    def test_get_passes_without_header(self):
        require_csrf_header("GET", {})

    def test_head_passes_without_header(self):
        require_csrf_header("HEAD", {})

    def test_options_passes_without_header(self):
        require_csrf_header("OPTIONS", {})

    def test_post_without_header_raises(self):
        with pytest.raises(CsrfError):
            require_csrf_header("POST", {})

    def test_put_without_header_raises(self):
        with pytest.raises(CsrfError):
            require_csrf_header("PUT", {})

    def test_patch_without_header_raises(self):
        with pytest.raises(CsrfError):
            require_csrf_header("PATCH", {})

    def test_delete_without_header_raises(self):
        with pytest.raises(CsrfError):
            require_csrf_header("DELETE", {})

    def test_post_with_correct_header_passes(self):
        require_csrf_header("POST", {"X-BFF-CSRF": "1"})

    def test_post_with_wrong_value_raises(self):
        with pytest.raises(CsrfError):
            require_csrf_header("POST", {"X-BFF-CSRF": "wrong"})

    def test_post_case_insensitive_header_key(self):
        # Header key matching should be case-insensitive
        require_csrf_header("POST", {"x-bff-csrf": "1"}, _header_name_override="X-BFF-CSRF")

    def test_custom_header_name_override(self):
        require_csrf_header(
            "POST",
            {"X-Custom-CSRF": "token"},
            _header_name_override="X-Custom-CSRF",
            _header_value_override="token",
        )

    def test_csrf_error_has_http_status_403(self):
        with pytest.raises(CsrfError) as exc_info:
            require_csrf_header("DELETE", {})
        assert exc_info.value.http_status == 403

    def test_method_case_insensitive(self):
        with pytest.raises(CsrfError):
            require_csrf_header("post", {})


# ---------------------------------------------------------------------------
# is_https_request / get_secure_cookie_flag
# ---------------------------------------------------------------------------


class TestIsHttpsRequest:
    def test_x_forwarded_proto_https(self):
        assert is_https_request({"X-Forwarded-Proto": "https"}) is True

    def test_x_forwarded_proto_http(self):
        assert is_https_request({"X-Forwarded-Proto": "http"}) is False

    def test_x_forwarded_ssl_on(self):
        assert is_https_request({"X-Forwarded-Ssl": "on"}) is True

    def test_x_forwarded_ssl_off(self):
        assert is_https_request({"X-Forwarded-Ssl": "off"}) is False

    def test_no_headers_returns_false(self):
        assert is_https_request({}) is False

    def test_case_insensitive_header_key(self):
        assert is_https_request({"x-forwarded-proto": "https"}) is True

    def test_case_insensitive_value(self):
        assert is_https_request({"X-Forwarded-Proto": "HTTPS"}) is True


class TestGetSecureCookieFlag:
    def test_https_returns_true(self):
        assert get_secure_cookie_flag({"X-Forwarded-Proto": "https"}) is True

    def test_no_https_returns_false(self):
        assert get_secure_cookie_flag({}) is False

    def test_env_override_disables(self, monkeypatch):
        monkeypatch.setenv("BFF_SESSION_SECURE_COOKIE", "0")
        assert get_secure_cookie_flag({"X-Forwarded-Proto": "https"}) is False


# ---------------------------------------------------------------------------
# build_strict_set_cookie_header
# ---------------------------------------------------------------------------


class TestBuildStrictSetCookieHeader:
    def test_contains_samesite_strict(self):
        header = build_strict_set_cookie_header("sess-abc")
        assert "SameSite=Strict" in header

    def test_contains_httponly(self):
        header = build_strict_set_cookie_header("sess-abc")
        assert "HttpOnly" in header

    def test_contains_secure_by_default(self):
        header = build_strict_set_cookie_header("sess-abc", secure=True)
        assert "Secure" in header

    def test_no_secure_when_disabled(self):
        header = build_strict_set_cookie_header("sess-abc", secure=False)
        assert "Secure" not in header

    def test_host_cookie_name_downgrades_when_secure_false(self, monkeypatch):
        monkeypatch.delenv("BFF_SESSION_COOKIE_NAME", raising=False)
        header = build_strict_set_cookie_header("sess-abc", secure=False)
        assert header.startswith("bff-session=sess-abc")

    def test_contains_path_root(self):
        header = build_strict_set_cookie_header("sess-abc")
        assert "Path=/" in header

    def test_custom_ttl(self):
        header = build_strict_set_cookie_header("sess-abc", ttl_seconds=7200)
        assert "Max-Age=7200" in header

    def test_session_id_in_header(self):
        header = build_strict_set_cookie_header("my-session-123")
        assert "my-session-123" in header

    def test_custom_cookie_name(self):
        header = build_strict_set_cookie_header("sid", cookie_name="my-bff-session")
        assert header.startswith("my-bff-session=sid")

    def test_invalid_cookie_name_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("BFF_SESSION_COOKIE_NAME", "bad;name")
        header = build_strict_set_cookie_header("sid", secure=True)
        assert header.startswith("__Host-session=sid")

    def test_invalid_session_id_raises(self):
        with pytest.raises(ValueError):
            build_strict_set_cookie_header("bad;sid")


# ---------------------------------------------------------------------------
# redact_authorization_header
# ---------------------------------------------------------------------------


class TestRedactAuthorizationHeader:
    def test_redacts_authorization(self):
        result = redact_authorization_header({"Authorization": "Bearer secret-token"})
        assert result["Authorization"] == "[REDACTED]"

    def test_redacts_cookie(self):
        result = redact_authorization_header({"Cookie": "__Host-session=abc"})
        assert result["Cookie"] == "[REDACTED]"

    def test_redacts_set_cookie(self):
        result = redact_authorization_header({"Set-Cookie": "__Host-session=abc; HttpOnly"})
        assert result["Set-Cookie"] == "[REDACTED]"

    def test_redacts_x_api_key(self):
        result = redact_authorization_header({"X-Api-Key": "mykey"})
        assert result["X-Api-Key"] == "[REDACTED]"

    def test_non_sensitive_headers_unchanged(self):
        result = redact_authorization_header({"Content-Type": "application/json", "Accept": "*/*"})
        assert result["Content-Type"] == "application/json"
        assert result["Accept"] == "*/*"

    def test_case_insensitive_redaction(self):
        result = redact_authorization_header({"authorization": "Bearer secret"})
        assert result["authorization"] == "[REDACTED]"

    def test_original_not_mutated(self):
        original = {"Authorization": "Bearer secret", "Content-Type": "application/json"}
        redact_authorization_header(original)
        assert original["Authorization"] == "Bearer secret"

    def test_empty_dict(self):
        assert redact_authorization_header({}) == {}


# ---------------------------------------------------------------------------
# handle_portal_proxy
# ---------------------------------------------------------------------------


class TestHandlePortalProxy:
    def test_401_no_cookie(self):
        store = _make_store()
        result = handle_portal_proxy(
            store,
            None,
            "GET",
            "/portal/api/health",
            _portal_api_base_override="http://api.internal",
        )
        assert result.http_status == 401
        assert result.error == "no_session_cookie"
        payload = json.loads(result.body.decode("utf-8"))
        assert payload.get("code") == "unauthorized"
        assert payload.get("error") == "no_session_cookie"
        assert payload.get("auth_reason") == "no_session_cookie"
        assert isinstance(payload.get("request_id"), str)
        assert payload.get("request_id", "").strip()

    def test_401_missing_session(self):
        store = _make_store()
        cookie = _cookie_header("nonexistent-session")
        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/health",
            _portal_api_base_override="http://api.internal",
        )
        assert result.http_status == 401
        assert result.error == "session_not_found"
        payload = json.loads(result.body.decode("utf-8"))
        assert payload.get("code") == "unauthorized"
        assert payload.get("error") == "session_not_found"
        assert payload.get("auth_reason") == "session_not_found"
        assert isinstance(payload.get("request_id"), str)
        assert payload.get("request_id", "").strip()

    def test_403_csrf_failure_on_post(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)
        result = handle_portal_proxy(
            store,
            cookie,
            "POST",
            "/portal/api/data",
            request_headers={},  # missing X-BFF-CSRF
            _portal_api_base_override="http://api.internal",
        )
        assert result.http_status == 403
        assert result.error == "csrf_check_failed"
        payload = json.loads(result.body.decode("utf-8"))
        assert payload.get("code") == "forbidden"
        assert payload.get("error") == "csrf_check_failed"
        assert payload.get("auth_reason") == "csrf_check_failed"
        assert isinstance(payload.get("request_id"), str)
        assert payload.get("request_id", "").strip()

    def test_200_get_success_passthrough(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        urlopen_fn = _make_urlopen_fn(200, b'{"data": "ok"}')
        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/results",
            _portal_api_base_override="http://api.internal",
            _urlopen_fn=urlopen_fn,
        )
        assert result.http_status == 200
        assert result.body == b'{"data": "ok"}'
        assert result.error == ""

    def test_post_with_csrf_header_passes(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        urlopen_fn = _make_urlopen_fn(201, b'{"created": true}')
        result = handle_portal_proxy(
            store,
            cookie,
            "POST",
            "/portal/api/jobs",
            request_headers={"X-BFF-CSRF": "1", "Content-Type": "application/json"},
            _portal_api_base_override="http://api.internal",
            _urlopen_fn=urlopen_fn,
        )
        assert result.http_status == 201

    def test_404_downstream_passthrough(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        from urllib.error import HTTPError
        from unittest.mock import MagicMock as MM

        def _urlopen(req, timeout=None):
            raise HTTPError(
                url=req.full_url,
                code=404,
                msg="Not Found",
                hdrs=MM(get=lambda k, d="": "application/json" if k == "Content-Type" else d),
                fp=BytesIO(b'{"error": "not_found"}'),
            )

        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/missing",
            _portal_api_base_override="http://api.internal",
            _urlopen_fn=_urlopen,
        )
        assert result.http_status == 404

    def test_502_network_error(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        from urllib.error import URLError

        def _urlopen(req, timeout=None):
            raise URLError("Connection refused")

        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/health",
            _portal_api_base_override="http://api.internal",
            _urlopen_fn=_urlopen,
        )
        assert result.http_status == 502
        assert result.error == "api_network_error"

    def test_502_missing_portal_api_base(self):
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)
        # No base URL configured, no override
        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/health",
            _portal_api_base_override="",
        )
        assert result.http_status == 502
        assert result.error == "missing_portal_api_base"

    def test_401_on_token_error(self):
        """If token refresh fails, proxy should return 401."""
        store = _make_store()
        session = _make_session(store, access_token="")  # no token → BffTokenError
        cookie = _cookie_header(session.session_id)

        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/health",
            _portal_api_base_override="http://api.internal",
        )
        assert result.http_status == 401

    def test_401_refresh_grant_error_code_passthrough(self):
        """Refresh-grant failures should surface as refresh_grant_error (for UI re-login handling)."""
        store = _make_store()
        session = _make_session(store, access_token="AT-expired")
        session.access_token_expires_at = time.time() - 10  # force refresh path
        cookie = _cookie_header(session.session_id)

        def _refresh_fn(*_args, **_kwargs):
            return {"error": "invalid_grant", "error_description": "refresh token revoked"}

        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/health",
            _portal_api_base_override="http://api.internal",
            _token_endpoint_override="https://issuer.example.test/oauth2/token",
            _client_id_override="client-id-test",
            _client_secret="client-secret-test",
            _refresh_fn=_refresh_fn,
        )
        assert result.http_status == 401
        assert result.error == "refresh_grant_error"
        assert b'"refresh_grant_error"' in result.body

    def test_401_no_refresh_token_error_code_passthrough(self):
        """Expired access-token without refresh-token should surface no_refresh_token."""
        store = _make_store()
        session = _make_session(store, access_token="AT-expired")
        session.access_token_expires_at = time.time() - 10  # force refresh path
        session.refresh_token = ""
        cookie = _cookie_header(session.session_id)

        result = handle_portal_proxy(
            store,
            cookie,
            "GET",
            "/portal/api/health",
            _portal_api_base_override="http://api.internal",
        )
        assert result.http_status == 401
        assert result.error == "no_refresh_token"
        assert b'"no_refresh_token"' in result.body

    def test_cookie_header_not_forwarded_downstream(self):
        """Session Cookie must not be forwarded to the downstream API."""
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        captured_headers: dict = {}

        def _urlopen(req, timeout=None):
            captured_headers.update(dict(req.headers))
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
            request_headers={"Cookie": f"__Host-session={session.session_id}"},
            _portal_api_base_override="http://api.internal",
            _urlopen_fn=_urlopen,
        )
        # Cookie must not appear in forwarded headers
        assert "Cookie" not in captured_headers
        assert "cookie" not in {k.lower() for k in captured_headers}

    def test_authorization_header_injected(self):
        """Downstream request must have Authorization: Bearer <token>."""
        store = _make_store()
        session = _make_session(store, access_token="AT-for-downstream")
        cookie = _cookie_header(session.session_id)

        captured_headers: dict = {}

        def _urlopen(req, timeout=None):
            captured_headers.update(dict(req.headers))
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
            _portal_api_base_override="http://api.internal",
            _urlopen_fn=_urlopen,
        )
        assert captured_headers.get("Authorization") == "Bearer AT-for-downstream"

    def test_url_constructed_correctly(self):
        """Downstream URL = base + proxy_path."""
        store = _make_store()
        session = _make_session(store)
        cookie = _cookie_header(session.session_id)

        captured_urls: list[str] = []

        def _urlopen(req, timeout=None):
            captured_urls.append(req.full_url)
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
            "/portal/api/analyze/history",
            _portal_api_base_override="http://api.internal:8080",
            _urlopen_fn=_urlopen,
        )
        assert len(captured_urls) == 1
        assert captured_urls[0] == "http://api.internal:8080/portal/api/analyze/history"
