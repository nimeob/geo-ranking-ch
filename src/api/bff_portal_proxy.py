"""BFF Portal Proxy Endpoints + CSRF + Security Hardening.

Implements the portal-facing proxy layer for the Backend-for-Frontend:

- ``handle_portal_proxy(session_store, cookie_header, method, path, ...)``
    Session-cookie-gated pass-through proxy for ``/portal/api/*`` requests.
    Delegates to :func:`~src.api.bff_token_delegation.bff_api_call` after
    reading a valid session.

- CSRF protection
    ``require_csrf_header(method, headers)`` enforces the ``X-BFF-CSRF: 1``
    custom-header check for all state-changing methods (POST, PUT, PATCH,
    DELETE). Cross-origin requests cannot set custom headers, so this provides
    a lightweight CSRF guard without server-side state. SPA clients must set
    this header explicitly.

- Cookie security helpers
    ``get_secure_cookie_flag(request_headers)`` inspects
    ``X-Forwarded-Proto`` / ``X-Forwarded-Ssl`` to determine whether the
    connection is HTTPS and the ``Secure`` cookie flag should be set.

    ``build_strict_set_cookie_header(session_id, ...)`` builds a
    ``SameSite=Strict`` variant for CSRF-sensitive cookies (complement to the
    ``SameSite=Lax`` cookie used during the OIDC auth redirect flow).

- Logging redaction extension
    ``redact_authorization_header(headers)`` ensures the ``Authorization``
    header (containing the Bearer token) is never logged verbatim.

Security design
---------------
- ``X-BFF-CSRF: 1`` Custom-Header-Check (RFC 6454 same-origin restriction):
    A cross-origin attacker cannot set custom HTTP headers from a browser
    (blocked by CORS pre-flight). An SPA served from the same origin can.
    This is a defence-in-depth measure; the ``SameSite`` cookie attribute
    already prevents credential forwarding in most browsers.
- ``Secure`` flag is set based on TLS detection (``X-Forwarded-Proto: https``
    or ``X-Forwarded-Ssl: on``); can be forced off via
    ``BFF_SESSION_SECURE_COOKIE=0`` (local dev).
- ``SameSite=Lax`` on the auth-redirect cookie; ``SameSite=Strict`` for
    CSRF-sensitive portal cookies (configurable).
- Tokens never appear in log output; ``redact_authorization_header`` must be
    called before logging any outgoing request headers.

Environment variables
---------------------
BFF_PORTAL_API_BASE_URL
    Base URL of the internal API to proxy to.
    Example: ``http://localhost:8080``
    Required for ``handle_portal_proxy``.
BFF_CSRF_HEADER_NAME
    Custom header to check for CSRF protection.
    Default: ``X-BFF-CSRF``.
BFF_CSRF_HEADER_VALUE
    Expected value of the CSRF header.
    Default: ``1``.

Issue: #853 (BFF-0.wp4)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from src.api.bff_session import (
    BffSessionStore,
    build_set_cookie_header,
    parse_session_id_from_cookie,
)
from src.api.bff_token_delegation import (
    BffApiCallError,
    BffApiResponse,
    BffTokenError,
    bff_api_call,
)

# ---------------------------------------------------------------------------
# Constants / env helpers
# ---------------------------------------------------------------------------

_CSRF_HEADER_ENV = "BFF_CSRF_HEADER_NAME"
_CSRF_VALUE_ENV = "BFF_CSRF_HEADER_VALUE"
_PORTAL_API_BASE_ENV = "BFF_PORTAL_API_BASE_URL"

_DEFAULT_CSRF_HEADER = "X-BFF-CSRF"
_DEFAULT_CSRF_VALUE = "1"
_DEFAULT_SECURE_COOKIE_NAME = "__Host-session"
_DEFAULT_INSECURE_COOKIE_NAME = "bff-session"
_MAX_SESSION_ID_LENGTH = 256
_COOKIE_NAME_ALLOWED_CHARS = frozenset(
    "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
_SESSION_ID_ALLOWED_CHARS = frozenset("-._~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

# Methods that require CSRF protection
_CSRF_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Headers that must never appear in logs verbatim
_SENSITIVE_HEADER_KEYS = frozenset({"authorization", "x-api-key", "cookie", "set-cookie"})

_REDACTED = "[REDACTED]"


def _csrf_header_name() -> str:
    return os.environ.get(_CSRF_HEADER_ENV, _DEFAULT_CSRF_HEADER)


def _csrf_header_value() -> str:
    return os.environ.get(_CSRF_VALUE_ENV, _DEFAULT_CSRF_VALUE)


def _portal_api_base() -> str:
    return os.environ.get(_PORTAL_API_BASE_ENV, "").rstrip("/")


# ---------------------------------------------------------------------------
# CSRF helpers
# ---------------------------------------------------------------------------


class CsrfError(Exception):
    """Raised when the CSRF header check fails.

    Attributes:
        http_status: Always 403.
        error_code: Machine-readable code.
        message: Human-readable description.
    """

    http_status: int = 403
    error_code: str = "csrf_check_failed"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def require_csrf_header(
    method: str,
    headers: dict[str, str],
    *,
    _header_name_override: str = "",
    _header_value_override: str = "",
) -> None:
    """Assert that the CSRF custom header is present for state-changing requests.

    For GET/HEAD/OPTIONS no check is performed.
    For POST/PUT/PATCH/DELETE the header ``X-BFF-CSRF: 1`` (configurable) must
    be present with the expected value.

    Args:
        method: HTTP method (case-insensitive).
        headers: Request headers dict (keys may be any casing).

    Raises:
        :class:`CsrfError`: When the CSRF header is missing or has the wrong
            value on a state-changing method.
    """
    if method.upper() not in _CSRF_METHODS:
        return  # no check for safe methods

    expected_name = _header_name_override or _csrf_header_name()
    expected_value = _header_value_override or _csrf_header_value()

    # Case-insensitive header lookup
    actual_value = _get_header_ci(headers, expected_name)
    if actual_value != expected_value:
        raise CsrfError(
            f"CSRF check failed: expected header {expected_name!r}={expected_value!r}, "
            f"got {'(missing)' if actual_value is None else repr(actual_value)}"
        )


# ---------------------------------------------------------------------------
# Cookie security helpers
# ---------------------------------------------------------------------------


def is_https_request(request_headers: dict[str, str]) -> bool:
    """Return True if the request arrived over HTTPS.

    Checks (in order):
    1. ``X-Forwarded-Proto: https``
    2. ``X-Forwarded-Ssl: on``

    These headers are set by load balancers / reverse proxies (ALB, nginx).
    Returns False if neither header is present (conservative default).
    """
    proto = _get_header_ci(request_headers, "X-Forwarded-Proto") or ""
    ssl = _get_header_ci(request_headers, "X-Forwarded-Ssl") or ""
    return proto.lower() == "https" or ssl.lower() == "on"


def get_secure_cookie_flag(request_headers: dict[str, str]) -> bool:
    """Return whether the ``Secure`` cookie flag should be set.

    Combines :func:`is_https_request` with the ``BFF_SESSION_SECURE_COOKIE``
    env var override (``0`` disables Secure regardless of TLS).
    """
    override = os.environ.get("BFF_SESSION_SECURE_COOKIE", "1")
    if override in ("0", "false", "False", "no"):
        return False
    return is_https_request(request_headers)


def _resolve_cookie_name(*, secure: bool, cookie_name: str | None = None) -> str:
    raw_name = str(cookie_name or os.environ.get("BFF_SESSION_COOKIE_NAME", _DEFAULT_SECURE_COOKIE_NAME) or "").strip()
    if not raw_name or any(ch not in _COOKIE_NAME_ALLOWED_CHARS for ch in raw_name):
        raw_name = _DEFAULT_SECURE_COOKIE_NAME
    if raw_name.startswith("__Host-") and not secure:
        return _DEFAULT_INSECURE_COOKIE_NAME
    return raw_name


def _assert_valid_session_id(session_id: str) -> None:
    value = str(session_id or "")
    if not value or value != value.strip() or len(value) > _MAX_SESSION_ID_LENGTH:
        raise ValueError("invalid session_id for Set-Cookie header")
    if any(ch not in _SESSION_ID_ALLOWED_CHARS for ch in value):
        raise ValueError("invalid session_id for Set-Cookie header")


def build_strict_set_cookie_header(
    session_id: str,
    *,
    ttl_seconds: int | None = None,
    secure: bool = True,
    cookie_name: str | None = None,
) -> str:
    """Build a ``SameSite=Strict`` Set-Cookie header for CSRF-sensitive cookies.

    This is the stricter variant of :func:`~src.api.bff_session.build_set_cookie_header`
    (which uses ``SameSite=Lax`` for the auth redirect flow). Portal proxy
    endpoints use ``Strict`` to prevent the session cookie from being sent in
    any cross-site context.

    Args:
        session_id: The opaque session identifier.
        ttl_seconds: Optional max-age override.
        secure: Whether to set the ``Secure`` flag (default True).
        cookie_name: Optional override for the cookie name. If None, reads
            ``BFF_SESSION_COOKIE_NAME`` from env (default: ``__Host-session``).

    Returns:
        A ``Set-Cookie`` header value string.
    """
    _assert_valid_session_id(session_id)
    name = _resolve_cookie_name(secure=secure, cookie_name=cookie_name)
    max_age = ttl_seconds if ttl_seconds is not None else int(
        os.environ.get("BFF_SESSION_TTL_SECONDS", "3600") or "3600"
    )
    parts = [
        f"{name}={session_id}",
        f"Max-Age={max_age}",
        "Path=/",
        "HttpOnly",
        "SameSite=Strict",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Logging redaction
# ---------------------------------------------------------------------------


def redact_authorization_header(
    headers: dict[str, str],
    *,
    _sensitive_keys: frozenset[str] = _SENSITIVE_HEADER_KEYS,
) -> dict[str, str]:
    """Return a copy of *headers* with sensitive values replaced by ``[REDACTED]``.

    Redacts (case-insensitively):
    - ``Authorization``
    - ``X-Api-Key``
    - ``Cookie``
    - ``Set-Cookie``

    Args:
        headers: HTTP headers dict (keys may be any casing).

    Returns:
        New dict with sensitive values redacted; original is not modified.
    """
    return {
        k: (_REDACTED if k.lower() in _sensitive_keys else v)
        for k, v in headers.items()
    }


# ---------------------------------------------------------------------------
# Portal Proxy result
# ---------------------------------------------------------------------------


@dataclass
class PortalProxyResult:
    """Result of :func:`handle_portal_proxy`."""

    http_status: int
    body: bytes
    content_type: str
    # Error code (empty on success)
    error: str


# ---------------------------------------------------------------------------
# Portal Proxy handler
# ---------------------------------------------------------------------------


def handle_portal_proxy(
    session_store: BffSessionStore,
    cookie_header: str | None,
    method: str,
    proxy_path: str,
    *,
    request_body: bytes | None = None,
    request_headers: dict[str, str] | None = None,
    _portal_api_base_override: str = "",
    _token_endpoint_override: str = "",
    _client_id_override: str = "",
    _client_secret: str = "",
    _refresh_fn: Any = None,
    _urlopen_fn: Any = None,
) -> PortalProxyResult:
    """Session-cookie-gated proxy handler for ``/portal/api/*``.

    Steps:
    1. Read session from cookie → 401 if missing/expired.
    2. For state-changing methods: validate ``X-BFF-CSRF`` header → 403 on failure.
    3. Call the downstream API via :func:`~src.api.bff_token_delegation.bff_api_call`
       with ``Authorization: Bearer <access_token>``.
    4. Pass through the response body + status to the caller.

    The downstream URL is constructed as::

        {BFF_PORTAL_API_BASE_URL}/{proxy_path.lstrip('/')}

    Args:
        session_store: Session store.
        cookie_header: Raw ``Cookie`` header from the incoming request.
        method: HTTP method of the incoming request.
        proxy_path: Path to forward (e.g. ``/portal/api/analyze/history``).
        request_body: Optional request body bytes.
        request_headers: Optional request headers dict (used for CSRF + passed
            to downstream after stripping ``Cookie`` and adding ``Authorization``).

    Returns:
        :class:`PortalProxyResult` with the upstream status code, body, and
        content-type. On auth/CSRF error, returns the appropriate error status.
    """
    rh = dict(request_headers or {})

    # --- 1. Session check ---
    session_id = parse_session_id_from_cookie(cookie_header)
    if not session_id:
        return PortalProxyResult(
            http_status=401,
            body=b'{"error": "no_session_cookie"}',
            content_type="application/json",
            error="no_session_cookie",
        )

    session = session_store.get(session_id)
    if session is None:
        return PortalProxyResult(
            http_status=401,
            body=b'{"error": "session_not_found"}',
            content_type="application/json",
            error="session_not_found",
        )

    # --- 2. CSRF check (state-changing methods) ---
    try:
        require_csrf_header(method, rh)
    except CsrfError as exc:
        return PortalProxyResult(
            http_status=403,
            body=f'{{"error": "csrf_check_failed", "detail": "{exc.message}"}}'.encode(),
            content_type="application/json",
            error="csrf_check_failed",
        )

    # --- 3. Build downstream URL ---
    base = _portal_api_base_override or _portal_api_base()
    if not base:
        return PortalProxyResult(
            http_status=502,
            body=b'{"error": "BFF_PORTAL_API_BASE_URL not configured"}',
            content_type="application/json",
            error="missing_portal_api_base",
        )

    clean_path = proxy_path.lstrip("/")
    downstream_url = f"{base}/{clean_path}"

    # Strip Cookie header from forwarded headers (the downstream receives Bearer, not session cookie)
    forward_headers = {k: v for k, v in rh.items() if k.lower() != "cookie"}

    # --- 4. Proxy call ---
    try:
        api_resp = bff_api_call(
            session,
            session_store,
            method,
            downstream_url,
            body=request_body,
            extra_headers=forward_headers,
            _token_endpoint_override=_token_endpoint_override,
            _client_id_override=_client_id_override,
            _client_secret=_client_secret,
            _refresh_fn=_refresh_fn,
            _urlopen_fn=_urlopen_fn,
        )
    except BffTokenError as exc:
        return PortalProxyResult(
            http_status=401,
            body=f'{{"error": "{exc.error_code}"}}'.encode(),
            content_type="application/json",
            error=exc.error_code,
        )
    except BffApiCallError as exc:
        return PortalProxyResult(
            http_status=exc.http_status,
            body=f'{{"error": "{exc.error_code}"}}'.encode(),
            content_type="application/json",
            error=exc.error_code,
        )

    return PortalProxyResult(
        http_status=api_resp.status_code,
        body=api_resp.body,
        content_type=api_resp.content_type,
        error="",
    )


# ---------------------------------------------------------------------------
# Utility: case-insensitive header lookup
# ---------------------------------------------------------------------------


def _get_header_ci(headers: dict[str, str], key: str) -> str | None:
    """Case-insensitive lookup in a headers dict. Returns None if not found."""
    key_lower = key.lower()
    for k, v in headers.items():
        if k.lower() == key_lower:
            return v
    return None
