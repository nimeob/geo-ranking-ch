"""Unit tests for src/api/bff_oidc.py (BFF OIDC Auth Code + PKCE handler).

Issue: #851 (BFF-0.wp2)

Coverage targets:
- build_login_redirect: PKCE pair generation, state, session fields, redirect URL
- handle_callback: state-mismatch → 400, missing code → 400, idp error → 400,
  missing session → 400, success flow with mock token exchange
- Utility helpers: _decode_jwt_payload, _is_safe_redirect_path, _safe_next_path
- build_oidc_config_from_env: missing required vars raise ValueError
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time

import pytest

from src.api.bff_oidc import (
    BffOidcConfig,
    CallbackResult,
    LoginResult,
    OidcCallbackError,
    _decode_jwt_payload,
    _generate_pkce_pair,
    _is_safe_redirect_path,
    _safe_next_path,
    build_login_redirect,
    build_oidc_config_from_env,
    handle_callback,
    is_bff_oidc_enabled,
)
from src.api.bff_session import BffSessionStore, build_set_cookie_header


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ISSUER = "https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_TEST"
_CLIENT_ID = "test-client-id"
_CLIENT_SECRET = "test-client-secret"
_REDIRECT_URI = "https://app.example.com/auth/callback"


@pytest.fixture()
def config() -> BffOidcConfig:
    return BffOidcConfig(
        issuer=_ISSUER,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
        redirect_uri=_REDIRECT_URI,
        scopes="openid email profile",
        authorization_endpoint=f"{_ISSUER}/oauth2/authorize",
        token_endpoint=f"{_ISSUER}/oauth2/token",
    )


@pytest.fixture()
def config_no_secret() -> BffOidcConfig:
    return BffOidcConfig(
        issuer=_ISSUER,
        client_id=_CLIENT_ID,
        client_secret="",  # public PKCE-only client
        redirect_uri=_REDIRECT_URI,
        scopes="openid email profile",
        authorization_endpoint=f"{_ISSUER}/oauth2/authorize",
        token_endpoint=f"{_ISSUER}/oauth2/token",
    )


@pytest.fixture()
def store() -> BffSessionStore:
    return BffSessionStore(ttl_seconds=3600)


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


class TestGeneratePkcePair:
    def test_returns_two_strings(self) -> None:
        verifier, challenge = _generate_pkce_pair()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)

    def test_verifier_length(self) -> None:
        verifier, _ = _generate_pkce_pair()
        # secrets.token_urlsafe(32) → 43 chars (base64url of 32 bytes)
        assert 43 <= len(verifier) <= 128

    def test_challenge_is_correct_sha256_base64url(self) -> None:
        verifier, challenge = _generate_pkce_pair()
        expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
        assert challenge == expected_challenge

    def test_no_padding_in_challenge(self) -> None:
        _, challenge = _generate_pkce_pair()
        assert "=" not in challenge

    def test_uniqueness(self) -> None:
        pairs = [_generate_pkce_pair() for _ in range(5)]
        verifiers = [p[0] for p in pairs]
        assert len(set(verifiers)) == 5, "PKCE verifiers should be unique"


# ---------------------------------------------------------------------------
# BffOidcConfig validation
# ---------------------------------------------------------------------------


class TestBffOidcConfig:
    def test_valid_config(self, config: BffOidcConfig) -> None:
        assert config.issuer == _ISSUER
        assert config.client_id == _CLIENT_ID
        assert config.redirect_uri == _REDIRECT_URI

    def test_missing_issuer_raises(self) -> None:
        with pytest.raises(ValueError, match="BFF_OIDC_ISSUER"):
            BffOidcConfig(
                issuer="",
                client_id=_CLIENT_ID,
                client_secret="",
                redirect_uri=_REDIRECT_URI,
                scopes="openid",
                authorization_endpoint="https://example.com/auth",
                token_endpoint="https://example.com/token",
            )

    def test_missing_client_id_raises(self) -> None:
        with pytest.raises(ValueError, match="BFF_OIDC_CLIENT_ID"):
            BffOidcConfig(
                issuer=_ISSUER,
                client_id="",
                client_secret="",
                redirect_uri=_REDIRECT_URI,
                scopes="openid",
                authorization_endpoint=f"{_ISSUER}/oauth2/authorize",
                token_endpoint=f"{_ISSUER}/oauth2/token",
            )

    def test_missing_redirect_uri_raises(self) -> None:
        with pytest.raises(ValueError, match="BFF_OIDC_REDIRECT_URI"):
            BffOidcConfig(
                issuer=_ISSUER,
                client_id=_CLIENT_ID,
                client_secret="",
                redirect_uri="",
                scopes="openid",
                authorization_endpoint=f"{_ISSUER}/oauth2/authorize",
                token_endpoint=f"{_ISSUER}/oauth2/token",
            )


# ---------------------------------------------------------------------------
# build_oidc_config_from_env
# ---------------------------------------------------------------------------


class TestBuildOidcConfigFromEnv:
    def test_returns_none_when_no_issuer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BFF_OIDC_ISSUER", raising=False)
        result = build_oidc_config_from_env()
        assert result is None

    def test_raises_when_issuer_set_but_client_id_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BFF_OIDC_ISSUER", _ISSUER)
        monkeypatch.delenv("BFF_OIDC_CLIENT_ID", raising=False)
        monkeypatch.delenv("BFF_OIDC_REDIRECT_URI", raising=False)
        with pytest.raises(ValueError, match="BFF_OIDC_CLIENT_ID"):
            build_oidc_config_from_env()

    def test_raises_when_issuer_and_client_id_set_but_redirect_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BFF_OIDC_ISSUER", _ISSUER)
        monkeypatch.setenv("BFF_OIDC_CLIENT_ID", _CLIENT_ID)
        monkeypatch.delenv("BFF_OIDC_REDIRECT_URI", raising=False)
        with pytest.raises(ValueError, match="BFF_OIDC_REDIRECT_URI"):
            build_oidc_config_from_env()

    def test_full_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BFF_OIDC_ISSUER", _ISSUER)
        monkeypatch.setenv("BFF_OIDC_CLIENT_ID", _CLIENT_ID)
        monkeypatch.setenv("BFF_OIDC_REDIRECT_URI", _REDIRECT_URI)
        monkeypatch.delenv("BFF_OIDC_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("BFF_OIDC_AUTH_ENDPOINT", raising=False)
        monkeypatch.delenv("BFF_OIDC_TOKEN_ENDPOINT", raising=False)
        monkeypatch.delenv("BFF_OIDC_SCOPES", raising=False)
        cfg = build_oidc_config_from_env()
        assert cfg is not None
        assert cfg.issuer == _ISSUER
        assert cfg.client_id == _CLIENT_ID
        assert cfg.redirect_uri == _REDIRECT_URI
        assert cfg.client_secret == ""
        assert cfg.scopes == "openid email profile"
        assert cfg.authorization_endpoint == f"{_ISSUER}/oauth2/authorize"
        assert cfg.token_endpoint == f"{_ISSUER}/oauth2/token"
        assert cfg.allow_next_param is True

    def test_custom_endpoints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BFF_OIDC_ISSUER", _ISSUER)
        monkeypatch.setenv("BFF_OIDC_CLIENT_ID", _CLIENT_ID)
        monkeypatch.setenv("BFF_OIDC_REDIRECT_URI", _REDIRECT_URI)
        monkeypatch.setenv("BFF_OIDC_AUTH_ENDPOINT", "https://custom.example.com/auth")
        monkeypatch.setenv("BFF_OIDC_TOKEN_ENDPOINT", "https://custom.example.com/token")
        cfg = build_oidc_config_from_env()
        assert cfg is not None
        assert cfg.authorization_endpoint == "https://custom.example.com/auth"
        assert cfg.token_endpoint == "https://custom.example.com/token"

    def test_is_bff_oidc_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BFF_OIDC_ISSUER", _ISSUER)
        assert is_bff_oidc_enabled() is True
        monkeypatch.delenv("BFF_OIDC_ISSUER")
        assert is_bff_oidc_enabled() is False


# ---------------------------------------------------------------------------
# build_login_redirect
# ---------------------------------------------------------------------------


class TestBuildLoginRedirect:
    def test_returns_login_result(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store)
        assert isinstance(result, LoginResult)

    def test_redirect_url_starts_with_auth_endpoint(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store)
        assert result.redirect_url.startswith(config.authorization_endpoint)

    def test_redirect_url_contains_required_params(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store)
        url = result.redirect_url
        assert "response_type=code" in url
        assert f"client_id={config.client_id}" in url
        assert "code_challenge_method=S256" in url
        assert "code_challenge=" in url
        assert "state=" in url
        assert "scope=" in url

    def test_session_has_pkce_and_state(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store)
        session = result.session
        assert session.pkce_code_verifier != ""
        assert session.oauth_state != ""

    def test_session_stored_in_store(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store)
        found = store.get(result.session.session_id)
        assert found is not None
        assert found.session_id == result.session.session_id

    def test_set_cookie_header_present(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store)
        assert result.session.session_id in result.set_cookie_header

    def test_state_in_url_matches_session(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store)
        assert f"state={result.session.oauth_state}" in result.redirect_url

    def test_redirect_uri_in_url(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store)
        # redirect_uri is URL-encoded in the query string
        assert "redirect_uri=" in result.redirect_url

    def test_unique_state_per_call(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        r1 = build_login_redirect(config, store)
        r2 = build_login_redirect(config, store)
        assert r1.session.oauth_state != r2.session.oauth_state

    def test_next_path_stored_in_session(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store, next_path="/dashboard")
        assert result.session.user_claims.get("_next") == "/dashboard"

    def test_unsafe_next_path_defaults_to_slash(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        result = build_login_redirect(config, store, next_path="https://evil.com/phish")
        assert result.session.user_claims.get("_next") == "/"


# ---------------------------------------------------------------------------
# handle_callback – error cases
# ---------------------------------------------------------------------------


def _make_cookie(session_id: str) -> str:
    return f"__Host-session={session_id}"


def _mock_token_exchange_success(
    token_endpoint: str,
    params: dict[str, str],
    client_secret: str | None,
) -> dict:
    """Mock token exchange that returns a valid token response."""
    # Minimal JWT: header.payload.signature (payload = {"sub": "user123"})
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "user123"}).encode()).rstrip(b"=").decode()
    fake_jwt = f"eyJhbGciOiJSUzI1NiJ9.{payload}.fake_sig"
    return {
        "access_token": "access_tok_abc",
        "refresh_token": "refresh_tok_xyz",
        "id_token": fake_jwt,
        "expires_in": 3600,
        "token_type": "Bearer",
    }


def _mock_token_exchange_error(
    token_endpoint: str,
    params: dict[str, str],
    client_secret: str | None,
) -> dict:
    return {"error": "invalid_grant", "error_description": "Code expired or invalid"}


class TestHandleCallbackErrors:
    def test_idp_error_param_raises(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "my_state"
        session.pkce_code_verifier = "verifier"
        cookie = _make_cookie(session.session_id)
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                config,
                store,
                cookie_header=cookie,
                query_params={"error": ["access_denied"], "error_description": ["User denied access"]},
                token_exchange_fn=_mock_token_exchange_success,
            )
        assert exc_info.value.http_status == 400
        assert "idp_access_denied" in exc_info.value.error_code

    def test_missing_code_raises(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "my_state"
        session.pkce_code_verifier = "verifier"
        cookie = _make_cookie(session.session_id)
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                config,
                store,
                cookie_header=cookie,
                query_params={"state": ["my_state"]},
                token_exchange_fn=_mock_token_exchange_success,
            )
        assert exc_info.value.http_status == 400
        assert exc_info.value.error_code == "missing_code"

    def test_missing_state_raises(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "my_state"
        session.pkce_code_verifier = "verifier"
        cookie = _make_cookie(session.session_id)
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                config,
                store,
                cookie_header=cookie,
                query_params={"code": ["auth_code_xyz"]},
                token_exchange_fn=_mock_token_exchange_success,
            )
        assert exc_info.value.http_status == 400
        assert exc_info.value.error_code == "missing_state"

    def test_state_mismatch_raises(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "correct_state"
        session.pkce_code_verifier = "verifier"
        cookie = _make_cookie(session.session_id)
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                config,
                store,
                cookie_header=cookie,
                query_params={"code": ["auth_code"], "state": ["WRONG_STATE"]},
                token_exchange_fn=_mock_token_exchange_success,
            )
        assert exc_info.value.http_status == 400
        assert exc_info.value.error_code == "state_mismatch"

    def test_missing_cookie_raises(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                config,
                store,
                cookie_header=None,
                query_params={"code": ["auth_code"], "state": ["some_state"]},
                token_exchange_fn=_mock_token_exchange_success,
            )
        assert exc_info.value.http_status == 400
        assert exc_info.value.error_code == "missing_session_cookie"

    def test_expired_session_raises(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "my_state"
        session.pkce_code_verifier = "verifier"
        # Force-expire the session
        session.session_expires_at = time.time() - 1
        cookie = _make_cookie(session.session_id)
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                config,
                store,
                cookie_header=cookie,
                query_params={"code": ["auth_code"], "state": ["my_state"]},
                token_exchange_fn=_mock_token_exchange_success,
            )
        assert exc_info.value.http_status == 400
        assert exc_info.value.error_code == "session_not_found"

    def test_token_exchange_error_raises(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "my_state"
        session.pkce_code_verifier = "verifier"
        cookie = _make_cookie(session.session_id)
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                config,
                store,
                cookie_header=cookie,
                query_params={"code": ["auth_code"], "state": ["my_state"]},
                token_exchange_fn=_mock_token_exchange_error,
            )
        assert exc_info.value.http_status == 400
        assert exc_info.value.error_code == "token_exchange_error"

    def test_missing_code_verifier_in_session_raises(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "my_state"
        # pkce_code_verifier deliberately left empty
        cookie = _make_cookie(session.session_id)
        with pytest.raises(OidcCallbackError) as exc_info:
            handle_callback(
                config,
                store,
                cookie_header=cookie,
                query_params={"code": ["auth_code"], "state": ["my_state"]},
                token_exchange_fn=_mock_token_exchange_success,
            )
        assert exc_info.value.http_status == 400
        assert exc_info.value.error_code == "missing_code_verifier"


# ---------------------------------------------------------------------------
# handle_callback – success flow
# ---------------------------------------------------------------------------


class TestHandleCallbackSuccess:
    def _setup_session(self, store: BffSessionStore, state: str = "good_state") -> tuple:
        session = store.create()
        session.oauth_state = state
        session.pkce_code_verifier = "verifier_abc"
        cookie = _make_cookie(session.session_id)
        return session, cookie

    def test_success_returns_callback_result(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session, cookie = self._setup_session(store)
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        assert isinstance(result, CallbackResult)

    def test_tokens_stored_in_session_not_in_response(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session, cookie = self._setup_session(store)
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        # Tokens must be in the session
        assert result.session.access_token == "access_tok_abc"
        assert result.session.refresh_token == "refresh_tok_xyz"
        assert result.session.id_token != ""
        # CallbackResult itself must NOT have raw token fields
        assert not hasattr(result, "access_token")
        assert not hasattr(result, "id_token")

    def test_pkce_state_cleared_after_success(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session, cookie = self._setup_session(store)
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        assert result.session.pkce_code_verifier == ""
        assert result.session.oauth_state == ""

    def test_default_redirect_path_is_root(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session, cookie = self._setup_session(store)
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        assert result.redirect_path == "/"

    def test_next_path_honoured_when_safe(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "good_state"
        session.pkce_code_verifier = "verifier_abc"
        session.user_claims["_next"] = "/dashboard"
        cookie = _make_cookie(session.session_id)
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        assert result.redirect_path == "/dashboard"

    def test_unsafe_next_path_falls_back_to_root(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session = store.create()
        session.oauth_state = "good_state"
        session.pkce_code_verifier = "verifier_abc"
        session.user_claims["_next"] = "https://evil.com/"
        cookie = _make_cookie(session.session_id)
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        assert result.redirect_path == "/"

    def test_set_cookie_header_present(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session, cookie = self._setup_session(store)
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        assert session.session_id in result.set_cookie_header

    def test_access_token_expires_at_set(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session, cookie = self._setup_session(store)
        before = time.time()
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        after = time.time()
        assert before + 3599 <= result.session.access_token_expires_at <= after + 3601

    def test_user_claims_decoded_from_id_token(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        session, cookie = self._setup_session(store)
        result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_xyz"], "state": ["good_state"]},
            token_exchange_fn=_mock_token_exchange_success,
        )
        assert result.session.user_claims.get("sub") == "user123"

    def test_client_secret_not_sent_for_public_client(
        self, config_no_secret: BffOidcConfig, store: BffSessionStore
    ) -> None:
        captured: list[dict] = []

        def capturing_exchange(endpoint, params, secret):
            captured.append({"params": params, "secret": secret})
            return _mock_token_exchange_success(endpoint, params, secret)

        session = store.create()
        session.oauth_state = "st"
        session.pkce_code_verifier = "v"
        cookie = _make_cookie(session.session_id)
        handle_callback(
            config_no_secret,
            store,
            cookie_header=cookie,
            query_params={"code": ["code"], "state": ["st"]},
            token_exchange_fn=capturing_exchange,
        )
        assert captured[0]["secret"] is None

    def test_client_secret_passed_for_confidential_client(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        captured: list[dict] = []

        def capturing_exchange(endpoint, params, secret):
            captured.append({"params": params, "secret": secret})
            return _mock_token_exchange_success(endpoint, params, secret)

        session = store.create()
        session.oauth_state = "st"
        session.pkce_code_verifier = "v"
        cookie = _make_cookie(session.session_id)
        handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["code"], "state": ["st"]},
            token_exchange_fn=capturing_exchange,
        )
        assert captured[0]["secret"] == _CLIENT_SECRET


# ---------------------------------------------------------------------------
# Full flow: login → callback (integration-style with shared store)
# ---------------------------------------------------------------------------


class TestFullLoginCallbackFlow:
    def test_full_pkce_flow(
        self, config: BffOidcConfig, store: BffSessionStore
    ) -> None:
        """Simulates browser login flow end-to-end using the in-process store."""
        # 1. Build login redirect
        login_result = build_login_redirect(config, store)
        assert "code_challenge=" in login_result.redirect_url

        session_id = login_result.session.session_id
        state = login_result.session.oauth_state
        cookie = _make_cookie(session_id)

        # 2. Simulate callback from IdP
        def exchange_with_code_verifier(endpoint, params, secret):
            # Ensure code_verifier is present and non-empty
            assert "code_verifier" in params
            assert params["code_verifier"] == login_result.session.pkce_code_verifier
            return _mock_token_exchange_success(endpoint, params, secret)

        callback_result = handle_callback(
            config,
            store,
            cookie_header=cookie,
            query_params={"code": ["auth_code_from_idp"], "state": [state]},
            token_exchange_fn=exchange_with_code_verifier,
        )

        # Session tokens stored
        assert callback_result.session.access_token == "access_tok_abc"
        # PKCE state cleared
        assert callback_result.session.pkce_code_verifier == ""
        assert callback_result.session.oauth_state == ""
        # Redirect to root
        assert callback_result.redirect_path == "/"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


class TestIsSafeRedirectPath:
    def test_root_is_safe(self) -> None:
        assert _is_safe_redirect_path("/") is True

    def test_subpath_is_safe(self) -> None:
        assert _is_safe_redirect_path("/dashboard") is True

    def test_nested_path_is_safe(self) -> None:
        assert _is_safe_redirect_path("/app/reports/123") is True

    def test_absolute_url_is_unsafe(self) -> None:
        assert _is_safe_redirect_path("https://evil.com/") is False

    def test_protocol_relative_is_unsafe(self) -> None:
        assert _is_safe_redirect_path("//evil.com/path") is False

    def test_empty_string_is_unsafe(self) -> None:
        assert _is_safe_redirect_path("") is False

    def test_none_is_unsafe(self) -> None:
        assert _is_safe_redirect_path(None) is False  # type: ignore[arg-type]

    def test_relative_without_leading_slash_is_unsafe(self) -> None:
        assert _is_safe_redirect_path("evil") is False


class TestSafeNextPath:
    def test_safe_path_returned_when_allowed(self) -> None:
        assert _safe_next_path("/dashboard", allow=True) == "/dashboard"

    def test_defaults_to_root_when_not_allowed(self) -> None:
        assert _safe_next_path("/dashboard", allow=False) == "/"

    def test_defaults_to_root_for_unsafe_path(self) -> None:
        assert _safe_next_path("https://evil.com", allow=True) == "/"

    def test_none_defaults_to_root(self) -> None:
        assert _safe_next_path(None, allow=True) == "/"  # type: ignore[arg-type]


class TestDecodeJwtPayload:
    def test_decodes_valid_jwt(self) -> None:
        payload = {"sub": "user1", "email": "user@example.com"}
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        fake_jwt = f"eyJhbGciOiJSUzI1NiJ9.{encoded}.fakesig"
        result = _decode_jwt_payload(fake_jwt)
        assert result["sub"] == "user1"
        assert result["email"] == "user@example.com"

    def test_raises_on_non_three_part_token(self) -> None:
        with pytest.raises(ValueError):
            _decode_jwt_payload("not.a.valid.jwt.token")

    def test_handles_padding_correctly(self) -> None:
        # Payload length that requires padding
        payload = {"sub": "x"}
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        fake_jwt = f"header.{encoded}.sig"
        result = _decode_jwt_payload(fake_jwt)
        assert result["sub"] == "x"
