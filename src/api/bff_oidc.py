"""BFF OIDC Auth Code + PKCE handler.

Implements ``/auth/login`` and ``/auth/callback`` for the Backend-for-Frontend.
This is a server-side OIDC Auth Code + PKCE flow: the browser only receives a
session cookie; tokens are stored in the BFF session store.

Issue: #851 (BFF-0.wp2)

Flow
----
1. ``GET /auth/login``
   - Generates a PKCE ``code_verifier`` (cryptographically random).
   - Derives ``code_challenge = BASE64URL(SHA256(code_verifier))``.
   - Generates a random ``state`` parameter (anti-CSRF).
   - Creates a new BFF session; stores ``code_verifier`` + ``state`` in it.
   - Sets session cookie and redirects the browser to the IdP authorization endpoint.

2. ``GET /auth/callback?code=<code>&state=<state>``
   - Reads the BFF session from the session cookie.
   - Validates ``state`` against the value stored in the session (anti-CSRF).
   - Exchanges ``code`` for tokens using the token endpoint (POST with
     ``code_verifier`` from session).
   - Stores ``access_token``, ``refresh_token``, ``id_token`` in the session.
   - Clears PKCE/state fields from the session.
   - Redirects the browser to ``/`` (or the ``next`` query-param if safe).
   - Returns 400 on ``error`` param from IdP, missing/mismatched ``state``, or
     missing ``code``.

Environment variables
---------------------
BFF_OIDC_ISSUER
    OIDC issuer URL.
    Cognito: ``https://cognito-idp.<region>.amazonaws.com/<pool-id>``

BFF_OIDC_CLIENT_ID
    OIDC client ID registered at the IdP.

BFF_OIDC_CLIENT_SECRET
    OIDC client secret (optional — leave empty for public PKCE-only clients).

BFF_OIDC_REDIRECT_URI
    Callback URL registered with the IdP.
    Example: ``https://myapp.example.com/auth/callback``

BFF_OIDC_SCOPES
    Space-separated OAuth 2.0 scopes. Default: ``openid email profile``.

BFF_OIDC_AUTH_ENDPOINT
    Authorization endpoint override.
    Default: ``{BFF_OIDC_ISSUER}/oauth2/authorize`` (Cognito convention).

BFF_OIDC_TOKEN_ENDPOINT
    Token endpoint override.
    Default: ``{BFF_OIDC_ISSUER}/oauth2/token`` (Cognito convention).

BFF_OIDC_NEXT_PARAM_ALLOW_SAME_ORIGIN
    Set to ``1`` to honour a ``?next=<path>`` redirect after login.
    Only same-origin relative paths are accepted. Default: ``1``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from src.api.bff_session import (
    BffSession,
    BffSessionStore,
    build_clear_cookie_header,
    build_set_cookie_header,
    parse_session_id_from_cookie,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_ENV_ISSUER = "BFF_OIDC_ISSUER"
_ENV_CLIENT_ID = "BFF_OIDC_CLIENT_ID"
_ENV_CLIENT_SECRET = "BFF_OIDC_CLIENT_SECRET"
_ENV_REDIRECT_URI = "BFF_OIDC_REDIRECT_URI"
_ENV_SCOPES = "BFF_OIDC_SCOPES"
_ENV_AUTH_ENDPOINT = "BFF_OIDC_AUTH_ENDPOINT"
_ENV_TOKEN_ENDPOINT = "BFF_OIDC_TOKEN_ENDPOINT"
_ENV_NEXT_PARAM = "BFF_OIDC_NEXT_PARAM_ALLOW_SAME_ORIGIN"

_DEFAULT_SCOPES = "openid email profile"
_DEFAULT_NEXT_PATH = "/"
_TOKEN_EXCHANGE_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class BffOidcConfig:
    """Resolved OIDC configuration.

    All fields are validated on construction; :func:`build_oidc_config_from_env`
    returns ``None`` when the BFF OIDC feature is disabled (no issuer set).
    """

    issuer: str
    client_id: str
    client_secret: str  # empty string for public PKCE-only clients
    redirect_uri: str
    scopes: str
    authorization_endpoint: str
    token_endpoint: str
    allow_next_param: bool = True

    def __post_init__(self) -> None:
        for attr, label in (
            ("issuer", "BFF_OIDC_ISSUER"),
            ("client_id", "BFF_OIDC_CLIENT_ID"),
            ("redirect_uri", "BFF_OIDC_REDIRECT_URI"),
            ("authorization_endpoint", "authorization_endpoint"),
            ("token_endpoint", "token_endpoint"),
        ):
            value = getattr(self, attr)
            if not value or not value.strip():
                raise ValueError(f"BffOidcConfig: {label} must not be empty")


def build_oidc_config_from_env() -> BffOidcConfig | None:
    """Build :class:`BffOidcConfig` from environment variables.

    Returns ``None`` if ``BFF_OIDC_ISSUER`` is not set (BFF OIDC disabled).
    Raises :class:`ValueError` if the issuer is set but required variables are
    missing.
    """
    issuer = os.environ.get(_ENV_ISSUER, "").strip()
    if not issuer:
        return None

    client_id = os.environ.get(_ENV_CLIENT_ID, "").strip()
    if not client_id:
        raise ValueError(
            f"BFF_OIDC_ISSUER is set but {_ENV_CLIENT_ID} is missing"
        )

    redirect_uri = os.environ.get(_ENV_REDIRECT_URI, "").strip()
    if not redirect_uri:
        raise ValueError(
            f"BFF_OIDC_ISSUER is set but {_ENV_REDIRECT_URI} is missing"
        )

    # Derive Cognito-style endpoints if not explicitly overridden
    auth_endpoint = os.environ.get(_ENV_AUTH_ENDPOINT, "").strip() or f"{issuer}/oauth2/authorize"
    token_endpoint = os.environ.get(_ENV_TOKEN_ENDPOINT, "").strip() or f"{issuer}/oauth2/token"

    allow_next = os.environ.get(_ENV_NEXT_PARAM, "1") not in ("0", "false", "False", "no")

    return BffOidcConfig(
        issuer=issuer,
        client_id=client_id,
        client_secret=os.environ.get(_ENV_CLIENT_SECRET, "").strip(),
        redirect_uri=redirect_uri,
        scopes=os.environ.get(_ENV_SCOPES, _DEFAULT_SCOPES).strip() or _DEFAULT_SCOPES,
        authorization_endpoint=auth_endpoint,
        token_endpoint=token_endpoint,
        allow_next_param=allow_next,
    )


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


def _generate_pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)``.

    - ``code_verifier``: random URL-safe string (43–128 chars per RFC 7636).
    - ``code_challenge``: ``BASE64URL(SHA256(code_verifier))``.
    """
    code_verifier = secrets.token_urlsafe(32)  # 43 chars, within RFC 7636 bounds
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    # RFC 7636 §4.2: BASE64URL without padding
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# ---------------------------------------------------------------------------
# Login builder
# ---------------------------------------------------------------------------


@dataclass
class LoginResult:
    """Output of :func:`build_login_redirect`."""

    redirect_url: str
    session: BffSession
    set_cookie_header: str


def build_login_redirect(
    config: BffOidcConfig,
    session_store: BffSessionStore,
    *,
    next_path: str = _DEFAULT_NEXT_PATH,
) -> LoginResult:
    """Create a new BFF session + PKCE pair and return the IdP redirect URL.

    Stores ``pkce_code_verifier`` and ``oauth_state`` in the session. The
    session cookie must be sent back with the redirect response so the callback
    can look them up.

    Args:
        config: Resolved OIDC configuration.
        session_store: The module-level session store singleton.
        next_path: Optional path to redirect to after successful login
                   (stored in session; not in state sent to IdP).

    Returns:
        :class:`LoginResult` with the redirect URL, session object, and the
        Set-Cookie header value to send with the redirect response.
    """
    code_verifier, code_challenge = _generate_pkce_pair()
    oauth_state = secrets.token_hex(16)

    session = session_store.create()
    session.pkce_code_verifier = code_verifier
    session.oauth_state = oauth_state
    # Stash next_path safely in user_claims dict (never sent to IdP)
    session.user_claims["_next"] = _safe_next_path(next_path, config.allow_next_param)

    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scopes,
        "state": oauth_state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }
    redirect_url = f"{config.authorization_endpoint}?{urlencode(params)}"
    cookie_header = build_set_cookie_header(session.session_id)

    return LoginResult(
        redirect_url=redirect_url,
        session=session,
        set_cookie_header=cookie_header,
    )


# ---------------------------------------------------------------------------
# Callback handler
# ---------------------------------------------------------------------------


class OidcCallbackError(Exception):
    """Raised when the OIDC callback cannot be processed.

    Attributes:
        http_status: Suggested HTTP status code (400 or 502).
        error_code: Machine-readable error code (string).
        message: Human-readable description.
    """

    def __init__(self, message: str, *, http_status: int = 400, error_code: str = "oidc_error") -> None:
        super().__init__(message)
        self.http_status = http_status
        self.error_code = error_code
        self.message = message


@dataclass
class CallbackResult:
    """Output of :func:`handle_callback`."""

    session: BffSession
    redirect_path: str
    set_cookie_header: str


# Type alias for the injectable token-exchange function (for testing)
_TokenExchangeFn = Callable[[str, dict[str, str], str | None], dict[str, Any]]


def _default_token_exchange(
    token_endpoint: str,
    params: dict[str, str],
    client_secret: str | None,
) -> dict[str, Any]:
    """POST to *token_endpoint* with form-encoded *params*.

    If *client_secret* is non-empty, it is sent as a ``client_secret`` form
    field (Cognito supports both HTTP Basic Auth and body secret for
    confidential clients).

    Returns parsed JSON response or raises :class:`OidcCallbackError`.
    """
    if client_secret:
        params = {**params, "client_secret": client_secret}

    body = urlencode(params).encode("ascii")
    req = Request(
        token_endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, timeout=_TOKEN_EXCHANGE_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
    except HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = "(unreadable)"
        raise OidcCallbackError(
            f"token endpoint returned HTTP {exc.code}: {err_body}",
            http_status=502,
            error_code="token_endpoint_error",
        ) from exc
    except URLError as exc:
        raise OidcCallbackError(
            f"token endpoint unreachable: {exc.reason}",
            http_status=502,
            error_code="token_endpoint_unreachable",
        ) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OidcCallbackError(
            "token endpoint returned non-JSON response",
            http_status=502,
            error_code="token_endpoint_invalid_response",
        ) from exc


def handle_callback(
    config: BffOidcConfig,
    session_store: BffSessionStore,
    *,
    cookie_header: str | None,
    query_params: dict[str, list[str]],
    token_exchange_fn: _TokenExchangeFn = _default_token_exchange,
) -> CallbackResult:
    """Process the OIDC callback.

    Args:
        config: Resolved OIDC configuration.
        session_store: The module-level session store singleton.
        cookie_header: Raw ``Cookie`` header value from the incoming request.
        query_params: Parsed query string (from :func:`urllib.parse.parse_qs`).
        token_exchange_fn: Injectable token exchange function (for unit tests).

    Returns:
        :class:`CallbackResult` with the updated session, redirect path, and
        Set-Cookie header (to renew the session cookie).

    Raises:
        :class:`OidcCallbackError` on any error (state mismatch, missing code,
        token exchange failure, etc.).
    """
    # --- Check for error from IdP ---
    if "error" in query_params:
        idp_error = _first(query_params, "error")
        idp_desc = _first(query_params, "error_description") or idp_error
        raise OidcCallbackError(
            f"IdP returned error: {idp_desc}",
            http_status=400,
            error_code=f"idp_{idp_error}",
        )

    # --- Validate required params ---
    code = _first(query_params, "code")
    if not code:
        raise OidcCallbackError(
            "missing 'code' parameter in callback",
            http_status=400,
            error_code="missing_code",
        )

    received_state = _first(query_params, "state")
    if not received_state:
        raise OidcCallbackError(
            "missing 'state' parameter in callback",
            http_status=400,
            error_code="missing_state",
        )

    # --- Look up session ---
    session_id = parse_session_id_from_cookie(cookie_header)
    if not session_id:
        raise OidcCallbackError(
            "no BFF session cookie present in callback request",
            http_status=400,
            error_code="missing_session_cookie",
        )

    session = session_store.get(session_id)
    if session is None:
        raise OidcCallbackError(
            "BFF session not found or expired",
            http_status=400,
            error_code="session_not_found",
        )

    # --- Validate state (anti-CSRF) ---
    if not secrets.compare_digest(received_state, session.oauth_state):
        raise OidcCallbackError(
            "state parameter mismatch (possible CSRF)",
            http_status=400,
            error_code="state_mismatch",
        )

    code_verifier = session.pkce_code_verifier
    if not code_verifier:
        raise OidcCallbackError(
            "no PKCE code_verifier in session (login flow incomplete)",
            http_status=400,
            error_code="missing_code_verifier",
        )

    # --- Exchange code for tokens ---
    token_params: dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": config.client_id,
        "code": code,
        "redirect_uri": config.redirect_uri,
        "code_verifier": code_verifier,
    }
    token_response = token_exchange_fn(
        config.token_endpoint,
        token_params,
        config.client_secret or None,
    )

    if "error" in token_response:
        raise OidcCallbackError(
            f"token exchange failed: {token_response.get('error_description', token_response['error'])}",
            http_status=400,
            error_code="token_exchange_error",
        )

    # --- Store tokens in session (never in response body) ---
    access_token = str(token_response.get("access_token", ""))
    refresh_token = str(token_response.get("refresh_token", ""))
    id_token = str(token_response.get("id_token", ""))
    expires_in = token_response.get("expires_in")

    session.access_token = access_token
    session.refresh_token = refresh_token
    session.id_token = id_token
    if isinstance(expires_in, (int, float)) and expires_in > 0:
        session.access_token_expires_at = time.time() + float(expires_in)

    # Decode user claims from id_token (without signature verification — we
    # trust our own token exchange; full JWT validation happens in oidc_jwt.py
    # for API bearer tokens).
    if id_token:
        try:
            claims = _decode_jwt_payload(id_token)
            # Preserve the internal _next redirect path
            next_path = session.user_claims.pop("_next", _DEFAULT_NEXT_PATH)
            session.user_claims.update(claims)
            session.user_claims["_next"] = next_path
        except Exception:  # noqa: BLE001
            pass  # non-fatal; claims remain empty

    # Clear PKCE/state fields (no longer needed)
    session.pkce_code_verifier = ""
    session.oauth_state = ""

    # Determine redirect target
    next_path = session.user_claims.pop("_next", _DEFAULT_NEXT_PATH)
    if not _is_safe_redirect_path(next_path):
        next_path = _DEFAULT_NEXT_PATH

    cookie_header_out = build_set_cookie_header(session.session_id)
    return CallbackResult(
        session=session,
        redirect_path=next_path,
        set_cookie_header=cookie_header_out,
    )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _first(params: dict[str, list[str]], key: str) -> str:
    """Return the first value for *key* from a :func:`parse_qs` result."""
    values = params.get(key)
    if not values:
        return ""
    return str(values[0]) if values[0] else ""


def _safe_next_path(next_path: str | None, allow: bool) -> str:
    """Return *next_path* if it is a safe same-origin relative path, else ``/``."""
    if not allow:
        return _DEFAULT_NEXT_PATH
    return _DEFAULT_NEXT_PATH if not _is_safe_redirect_path(next_path) else str(next_path)


def _is_safe_redirect_path(path: str | None) -> bool:
    """Return True only for same-origin relative paths (no scheme, no host)."""
    if not path or not isinstance(path, str):
        return False
    path = path.strip()
    if not path.startswith("/"):
        return False
    # Reject protocol-relative URLs (//evil.com) and paths with schemes
    parsed = urlsplit(path)
    return parsed.scheme == "" and parsed.netloc == ""


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode the payload of a JWT without signature verification.

    Only used to extract user claims after a trusted token exchange.
    Raises on malformed tokens.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("not a three-part JWT")
    # Add padding for base64url
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    raw = base64.urlsafe_b64decode(payload_b64)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Feature-flag check
# ---------------------------------------------------------------------------


def is_bff_oidc_enabled() -> bool:
    """Return True if ``BFF_OIDC_ISSUER`` is configured (BFF OIDC active)."""
    return bool(os.environ.get(_ENV_ISSUER, "").strip())
