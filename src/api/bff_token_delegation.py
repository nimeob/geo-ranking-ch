"""BFF Token Delegation, Auto-Refresh, /me endpoint, /auth/logout.

Implements the server-side helpers and HTTP handler logic for:

- ``bff_get_valid_access_token(session)``
    Returns a valid access token for *session*. If the stored token is expired
    (or about to expire), it transparently refreshes via the Cognito token
    endpoint using the Refresh Token. On refresh failure the session is deleted
    and a :class:`BffTokenError` is raised (caller should return HTTP 401).

- ``bff_api_call(session, method, url, ...)``
    Makes an authenticated HTTP call on behalf of the user. Fetches a valid
    access token, injects ``Authorization: Bearer <token>``, and returns the
    raw response body + status code.

- ``handle_logout(session_store, cookie_header, [config])``
    Invalidates the BFF session, clears the cookie, and optionally redirects to
    the Cognito logout endpoint.

- ``handle_me(session_store, cookie_header)``
    Returns ``user_claims`` for the current session (no tokens). Returns 401
    when no valid session is present.

Security notes
--------------
- Tokens are **never** serialised to logs. The ``safe_log`` helper redacts any
  dict key matching the token-field names.
- ``bff_get_valid_access_token`` uses ``BffSession.is_access_token_expired``
  (which subtracts a 30 s clock-skew buffer) to trigger refresh early.
- Refresh Token failures (bad token / revoked / network error) always delete
  the session so the user is forced to re-authenticate cleanly.

Environment variables
---------------------
BFF_OIDC_ISSUER
    Required for logout redirect. When absent, logout only clears local
    session (no redirect to IdP).
BFF_OIDC_CLIENT_ID
    Required for the token refresh call.
BFF_OIDC_TOKEN_ENDPOINT
    Override token endpoint (default: ``{BFF_OIDC_ISSUER}/oauth2/token``).
BFF_OIDC_LOGOUT_ENDPOINT
    Override logout endpoint (default: ``{BFF_OIDC_ISSUER}/logout``).
BFF_OIDC_REDIRECT_URI
    Used as ``logout_uri`` / ``redirect_uri`` for post-logout redirect.
BFF_API_CALL_TIMEOUT_SECONDS
    Timeout in seconds for ``bff_api_call``. Default: 10.

Issue: #852 (BFF-0.wp3)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.api.bff_session import (
    BffSession,
    BffSessionStore,
    build_clear_cookie_header,
    parse_session_id_from_cookie,
)

# ---------------------------------------------------------------------------
# Constants / env helpers
# ---------------------------------------------------------------------------

_REDACTED = "[REDACTED]"
_TOKEN_FIELDS = frozenset({"access_token", "refresh_token", "id_token"})

_REFRESH_TIMEOUT_SECONDS = 10
_DEFAULT_API_CALL_TIMEOUT = 10


def _token_endpoint() -> str:
    issuer = os.environ.get("BFF_OIDC_ISSUER", "").strip()
    override = os.environ.get("BFF_OIDC_TOKEN_ENDPOINT", "").strip()
    return override or (f"{issuer}/oauth2/token" if issuer else "")


def _logout_endpoint() -> str:
    issuer = os.environ.get("BFF_OIDC_ISSUER", "").strip()
    override = os.environ.get("BFF_OIDC_LOGOUT_ENDPOINT", "").strip()
    return override or (f"{issuer}/logout" if issuer else "")


def _client_id() -> str:
    return os.environ.get("BFF_OIDC_CLIENT_ID", "").strip()


def _redirect_uri() -> str:
    return os.environ.get("BFF_OIDC_REDIRECT_URI", "").strip()


def _api_call_timeout() -> int:
    raw = os.environ.get("BFF_API_CALL_TIMEOUT_SECONDS", str(_DEFAULT_API_CALL_TIMEOUT))
    try:
        v = int(raw)
        return max(1, v)
    except (ValueError, TypeError):
        return _DEFAULT_API_CALL_TIMEOUT


# ---------------------------------------------------------------------------
# Logging redaction
# ---------------------------------------------------------------------------


def safe_log(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with token fields replaced by ``[REDACTED]``.

    Only operates on the top-level keys; nested structures are not recursed
    into (tokens should never appear nested).
    """
    return {k: (_REDACTED if k in _TOKEN_FIELDS else v) for k, v in data.items()}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class BffTokenError(Exception):
    """Raised when a valid access token cannot be obtained.

    Callers should translate this to HTTP 401 and clear the session cookie.

    Attributes:
        http_status: Always 401 for token errors.
        error_code: Machine-readable code.
        message: Human-readable description (safe to log, no tokens).
    """

    http_status: int = 401
    error_code: str

    def __init__(self, message: str, *, error_code: str = "token_error") -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class BffApiCallError(Exception):
    """Raised when ``bff_api_call`` cannot complete the downstream request.

    Attributes:
        http_status: HTTP status to propagate to the client (502 / 401 / ...).
        error_code: Machine-readable code.
        message: Human-readable description.
    """

    def __init__(
        self,
        message: str,
        *,
        http_status: int = 502,
        error_code: str = "api_call_error",
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.error_code = error_code
        self.message = message


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


def _do_token_refresh(
    token_endpoint_url: str,
    client_id: str,
    refresh_token: str,
    *,
    client_secret: str = "",
    timeout: int = _REFRESH_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST a ``refresh_token`` grant to *token_endpoint_url*.

    Returns parsed JSON response dict.
    Raises :class:`BffTokenError` on network errors or non-200 responses.

    Token values in the response are **not** logged; callers must handle them
    carefully.
    """
    params: dict[str, str] = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    if client_secret:
        params["client_secret"] = client_secret

    body = urlencode(params).encode("ascii")
    req = Request(
        token_endpoint_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            err_body = "(unreadable)"
        raise BffTokenError(
            f"token refresh endpoint returned HTTP {exc.code}: {err_body}",
            error_code="refresh_http_error",
        ) from exc
    except URLError as exc:
        raise BffTokenError(
            f"token refresh endpoint unreachable: {exc.reason}",
            error_code="refresh_network_error",
        ) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BffTokenError(
            "token refresh endpoint returned non-JSON response",
            error_code="refresh_invalid_response",
        ) from exc


# ---------------------------------------------------------------------------
# Public helper: bff_get_valid_access_token
# ---------------------------------------------------------------------------


def bff_get_valid_access_token(
    session: BffSession,
    session_store: BffSessionStore,
    *,
    # Injectable for unit tests
    _token_endpoint_override: str = "",
    _client_id_override: str = "",
    _client_secret: str = "",
    _refresh_fn: Any = None,
) -> str:
    """Return a valid access token for *session*, refreshing if necessary.

    This is the central helper that all internal API calls must use so that
    tokens are always current. It implements the following logic:

    1. If ``session.access_token_expires_at`` is unknown (0), return the
       stored token as-is (assume valid).
    2. If the token is **not** expired, return it directly.
    3. If the token is expired (or will expire within 30 s):
       a. Call the token endpoint with ``grant_type=refresh_token``.
       b. On success: update ``session.access_token``,
          ``session.access_token_expires_at``, and optionally
          ``session.refresh_token`` (rotation) in-place.
       c. On failure: delete the session from *session_store*, raise
          :class:`BffTokenError` → caller must return HTTP 401.

    Args:
        session: The current BFF session (modified in-place on refresh).
        session_store: Session store used to delete the session on failure.

    Returns:
        A non-empty access token string.

    Raises:
        :class:`BffTokenError`: When the session has no access token or the
            refresh grant failed.
    """
    if not session.access_token:
        session_store.delete(session.session_id)
        raise BffTokenError(
            "session has no access token",
            error_code="no_access_token",
        )

    if not session.is_access_token_expired():
        return session.access_token

    # Need to refresh ---------------------------------------------------
    refresh_token = session.refresh_token
    if not refresh_token:
        session_store.delete(session.session_id)
        raise BffTokenError(
            "access token expired and no refresh token available",
            error_code="no_refresh_token",
        )

    ep = _token_endpoint_override or _token_endpoint()
    cid = _client_id_override or _client_id()
    if not ep or not cid:
        session_store.delete(session.session_id)
        raise BffTokenError(
            "BFF_OIDC_TOKEN_ENDPOINT / BFF_OIDC_CLIENT_ID not configured",
            error_code="missing_oidc_config",
        )

    refresh_fn = _refresh_fn or _do_token_refresh
    try:
        token_response = refresh_fn(
            ep,
            cid,
            refresh_token,
            client_secret=_client_secret,
        )
    except BffTokenError:
        session_store.delete(session.session_id)
        raise

    if "error" in token_response:
        session_store.delete(session.session_id)
        raise BffTokenError(
            f"token refresh failed: {token_response.get('error_description', token_response['error'])}",
            error_code="refresh_grant_error",
        )

    new_access_token = str(token_response.get("access_token", ""))
    if not new_access_token:
        session_store.delete(session.session_id)
        raise BffTokenError(
            "token refresh response missing access_token",
            error_code="refresh_missing_token",
        )

    # Update session in-place (no log of token values)
    session.access_token = new_access_token
    expires_in = token_response.get("expires_in")
    if isinstance(expires_in, (int, float)) and expires_in > 0:
        session.access_token_expires_at = time.time() + float(expires_in)
    else:
        session.access_token_expires_at = 0.0  # unknown; assume valid

    # Refresh token rotation (optional; Cognito may return a new RT)
    new_refresh_token = token_response.get("refresh_token")
    if new_refresh_token and isinstance(new_refresh_token, str):
        session.refresh_token = new_refresh_token

    return session.access_token


# ---------------------------------------------------------------------------
# Public helper: bff_api_call
# ---------------------------------------------------------------------------


@dataclass
class BffApiResponse:
    """Result of a ``bff_api_call``."""

    status_code: int
    body: bytes
    content_type: str


def bff_api_call(
    session: BffSession,
    session_store: BffSessionStore,
    method: str,
    url: str,
    *,
    body: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
    _token_endpoint_override: str = "",
    _client_id_override: str = "",
    _client_secret: str = "",
    _refresh_fn: Any = None,
    _urlopen_fn: Any = None,
    _timeout: int | None = None,
) -> BffApiResponse:
    """Make an authenticated downstream HTTP call on behalf of the user.

    Obtains a valid access token via :func:`bff_get_valid_access_token`,
    then performs the request with ``Authorization: Bearer <token>``. The
    token is **never** logged.

    Args:
        session: Active BFF session.
        session_store: Session store (needed for refresh/delete on error).
        method: HTTP method (``GET``, ``POST``, etc.).
        url: Absolute URL of the downstream API endpoint.
        body: Optional request body bytes.
        extra_headers: Additional HTTP headers to include (merged; cannot
            override ``Authorization``).

    Returns:
        :class:`BffApiResponse` with status code, body bytes, and content-type.

    Raises:
        :class:`BffTokenError`: If a valid access token cannot be obtained
            (expired + refresh failed). Callers should return HTTP 401.
        :class:`BffApiCallError`: On network errors reaching the downstream
            API. Callers should return HTTP 502.
    """
    access_token = bff_get_valid_access_token(
        session,
        session_store,
        _token_endpoint_override=_token_endpoint_override,
        _client_id_override=_client_id_override,
        _client_secret=_client_secret,
        _refresh_fn=_refresh_fn,
    )

    headers: dict[str, str] = dict(extra_headers or {})
    # Authorization must come from the token; disallow override
    headers["Authorization"] = f"Bearer {access_token}"

    req = Request(url, data=body, method=method.upper(), headers=headers)
    timeout = _timeout if _timeout is not None else _api_call_timeout()
    urlopen_fn = _urlopen_fn or urlopen
    try:
        with urlopen_fn(req, timeout=timeout) as resp:
            raw_body = resp.read()
            status = resp.status
            ct = resp.headers.get("Content-Type", "")
    except HTTPError as exc:
        # Propagate HTTP errors from downstream API as-is
        try:
            raw_body = exc.read()
        except Exception:  # noqa: BLE001
            raw_body = b""
        ct = exc.headers.get("Content-Type", "") if exc.headers else ""
        return BffApiResponse(
            status_code=exc.code,
            body=raw_body,
            content_type=ct,
        )
    except URLError as exc:
        raise BffApiCallError(
            f"downstream API unreachable: {exc.reason}",
            http_status=502,
            error_code="api_network_error",
        ) from exc

    return BffApiResponse(status_code=status, body=raw_body, content_type=ct)


# ---------------------------------------------------------------------------
# Handler: /auth/logout
# ---------------------------------------------------------------------------


@dataclass
class LogoutResult:
    """Result of :func:`handle_logout`."""

    # HTTP status for the response (302 with redirect, or 200/204 if no IdP redirect)
    http_status: int
    # Location header value; empty string if no redirect
    redirect_url: str
    # Set-Cookie header to clear the session cookie
    set_cookie_header: str


def handle_logout(
    session_store: BffSessionStore,
    cookie_header: str | None,
    *,
    _logout_endpoint_override: str = "",
    _client_id_override: str = "",
    _redirect_uri_override: str = "",
) -> LogoutResult:
    """Invalidate the BFF session and optionally redirect to IdP logout.

    Steps:
    1. Read session ID from cookie.
    2. Delete session from store (idempotent; ok if already gone).
    3. Build clear-cookie header.
    4. If Cognito logout endpoint is configured, build redirect URL.

    This method is intentionally lenient: if the session cookie is absent or
    the session is already expired, it still returns a valid clear-cookie
    header (idempotent logout).

    Args:
        session_store: Session store.
        cookie_header: Raw ``Cookie`` header value from the request.

    Returns:
        :class:`LogoutResult` with HTTP status (302 or 204), optional
        ``Location`` header, and a ``Set-Cookie`` header to clear the cookie.
    """
    # Delete session (idempotent)
    session_id = parse_session_id_from_cookie(cookie_header)
    if session_id:
        session_store.delete(session_id)

    clear_cookie = build_clear_cookie_header()

    # Build IdP logout redirect if configured
    logout_ep = _logout_endpoint_override or _logout_endpoint()
    cid = _client_id_override or _client_id()
    post_logout_uri = _redirect_uri_override or _redirect_uri()

    if logout_ep and cid:
        params: dict[str, str] = {"client_id": cid}
        if post_logout_uri:
            params["logout_uri"] = post_logout_uri
        redirect_url = f"{logout_ep}?{urlencode(params)}"
        return LogoutResult(
            http_status=302,
            redirect_url=redirect_url,
            set_cookie_header=clear_cookie,
        )

    # No IdP endpoint configured — local logout only
    return LogoutResult(
        http_status=204,
        redirect_url="",
        set_cookie_header=clear_cookie,
    )


# ---------------------------------------------------------------------------
# Handler: /me
# ---------------------------------------------------------------------------


@dataclass
class MeResult:
    """Result of :func:`handle_me`."""

    http_status: int  # 200 or 401
    # Parsed user_claims dict (without internal _next key, without tokens)
    user_claims: dict[str, Any]
    error: str  # empty string on success


def handle_me(
    session_store: BffSessionStore,
    cookie_header: str | None,
) -> MeResult:
    """Return user_claims for the current session.

    Reads the session ID from the cookie header, looks up the session store,
    and returns a sanitised view of user_claims (no tokens, no internal _next
    key).

    Args:
        session_store: Session store.
        cookie_header: Raw ``Cookie`` header value from the request.

    Returns:
        :class:`MeResult` with ``http_status=200`` and ``user_claims`` on
        success, or ``http_status=401`` and empty claims when the session is
        absent/expired.
    """
    session_id = parse_session_id_from_cookie(cookie_header)
    if not session_id:
        return MeResult(http_status=401, user_claims={}, error="no_session_cookie")

    session = session_store.get(session_id)
    if session is None:
        return MeResult(http_status=401, user_claims={}, error="session_not_found")

    # Return only safe claims — never tokens, never internal _next key
    safe_claims = {
        k: v
        for k, v in session.user_claims.items()
        if k not in _TOKEN_FIELDS and not k.startswith("_")
    }
    return MeResult(http_status=200, user_claims=safe_claims, error="")
