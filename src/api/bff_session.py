"""BFF Session Store + httpOnly Cookie Middleware.

Provides a thread-safe, in-process session store for the Backend-for-Frontend
layer. Tokens are stored server-side only; the browser receives a session cookie
containing only an opaque session ID.

Security design:
- Session IDs are cryptographically random (secrets.token_hex(32)).
- Access Token / Refresh Token / ID Token are NEVER sent to the browser.
- Cookies use: httpOnly=True, Secure (when HTTPS), SameSite=Lax, Path=/.
- Session expiry is enforced on read (lazy eviction).

This module implements issue #850 (BFF-0.wp1).

Environment variables
---------------------
BFF_SESSION_COOKIE_NAME
    Cookie name. Default: ``__Host-session``.
    Note: ``__Host-`` prefix requires Secure + Path=/ (enforced here).
BFF_SESSION_TTL_SECONDS
    Session lifetime in seconds. Default: 3600 (1 hour).
BFF_SESSION_SECURE_COOKIE
    Set to ``0`` to disable Secure flag (local dev only). Default: ``1``.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Session model
# ---------------------------------------------------------------------------

_REDACTED = "[REDACTED]"
_DEFAULT_SECURE_COOKIE_NAME = "__Host-session"
_DEFAULT_INSECURE_COOKIE_NAME = "bff-session"
_MAX_SESSION_ID_LENGTH = 256
_COOKIE_NAME_ALLOWED_CHARS = frozenset(
    "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
_SESSION_ID_ALLOWED_CHARS = frozenset("-._~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")


@dataclass
class BffSession:
    """Represents a single authenticated BFF session.

    All token fields are stored in-process only. Never serialize tokens
    to logs, HTTP responses or persistent storage unless encrypted.
    """

    session_id: str
    # OIDC tokens (never leave the server)
    access_token: str = ""
    refresh_token: str = ""
    id_token: str = ""
    # Decoded user claims (safe to return to browser without tokens)
    user_claims: dict[str, Any] = field(default_factory=dict)
    # PKCE / state for in-flight auth (cleared after callback)
    pkce_code_verifier: str = ""
    oauth_state: str = ""
    # Timestamps (Unix seconds)
    created_at: float = field(default_factory=time.time)
    # absolute Unix epoch when access_token expires (0 = unknown)
    access_token_expires_at: float = 0.0
    # absolute Unix epoch when this session expires
    session_expires_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() >= self.session_expires_at

    def is_access_token_expired(self, *, clock_skew_seconds: int = 30) -> bool:
        """Return True if the access token is expired (or will expire soon)."""
        if self.access_token_expires_at <= 0:
            return False  # unknown – assume valid
        return time.time() >= (self.access_token_expires_at - clock_skew_seconds)

    def safe_repr(self) -> dict[str, Any]:
        """Return a representation safe to log / return to the browser."""
        return {
            "session_id": self.session_id,
            "user_claims": self.user_claims,
            "created_at": self.created_at,
            "session_expires_at": self.session_expires_at,
            "access_token": _REDACTED if self.access_token else "",
            "refresh_token": _REDACTED if self.refresh_token else "",
            "id_token": _REDACTED if self.id_token else "",
        }


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------


class BffSessionStore:
    """Thread-safe, in-process session store.

    Provides create / get / delete operations for :class:`BffSession`
    objects keyed by opaque session IDs.

    This implementation keeps sessions in memory (suitable for a single-
    process deployment or during development). The interface is designed
    so a DB-backed or Redis-backed implementation can replace it without
    changing call-sites.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._sessions: dict[str, BffSession] = {}
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self) -> BffSession:
        """Create a new, empty session and register it in the store."""
        session_id = secrets.token_hex(32)
        now = time.time()
        session = BffSession(
            session_id=session_id,
            created_at=now,
            session_expires_at=now + self.ttl_seconds,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> BffSession | None:
        """Return the session for *session_id*, or None if missing/expired."""
        if not _is_valid_session_id(session_id):
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_expired():
                del self._sessions[session_id]
                return None
            return session

    def delete(self, session_id: str) -> None:
        """Remove session from store (idempotent)."""
        if not _is_valid_session_id(session_id):
            return
        with self._lock:
            self._sessions.pop(session_id, None)

    def renew(self, session_id: str) -> bool:
        """Extend session lifetime by ttl_seconds from now.

        Returns True if session existed and was renewed, False otherwise.
        """
        if not _is_valid_session_id(session_id):
            return False
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.is_expired():
                return False
            session.session_expires_at = time.time() + self.ttl_seconds
            return True

    def evict_expired(self) -> int:
        """Remove all expired sessions. Returns count of removed sessions."""
        now = time.time()
        with self._lock:
            expired_keys = [k for k, s in self._sessions.items() if now >= s.session_expires_at]
            for k in expired_keys:
                del self._sessions[k]
        return len(expired_keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

import os as _os


def _bff_cookie_name() -> str:
    raw_name = str(_os.environ.get("BFF_SESSION_COOKIE_NAME", _DEFAULT_SECURE_COOKIE_NAME) or "").strip()
    if not raw_name or any(ch not in _COOKIE_NAME_ALLOWED_CHARS for ch in raw_name):
        raw_name = _DEFAULT_SECURE_COOKIE_NAME

    # ``__Host-`` cookies are only valid with Secure + Path=/ and no Domain.
    # We always enforce Path=/ and no Domain; when Secure is explicitly disabled
    # (local dev), downgrade to a non-prefixed cookie name so browsers don't
    # silently reject an invalid ``__Host-`` cookie.
    if raw_name.startswith("__Host-") and not _bff_secure_cookie():
        return _DEFAULT_INSECURE_COOKIE_NAME
    return raw_name


def _bff_ttl_seconds() -> int:
    raw = _os.environ.get("BFF_SESSION_TTL_SECONDS", "3600")
    try:
        v = int(raw)
        if v <= 0:
            raise ValueError
        return v
    except (ValueError, TypeError):
        return 3600


def _bff_secure_cookie() -> bool:
    """Return True if Secure flag should be set (default True)."""
    return _os.environ.get("BFF_SESSION_SECURE_COOKIE", "1") not in ("0", "false", "False", "no")


def _is_valid_session_id(session_id: str) -> bool:
    value = str(session_id or "")
    if not value or value != value.strip() or len(value) > _MAX_SESSION_ID_LENGTH:
        return False
    return all(ch in _SESSION_ID_ALLOWED_CHARS for ch in value)


def _assert_valid_session_id(session_id: str) -> None:
    if not _is_valid_session_id(session_id):
        raise ValueError("invalid session_id for Set-Cookie header")


def build_set_cookie_header(session_id: str, *, ttl_seconds: int | None = None) -> str:
    """Return a Set-Cookie header value for the given session ID.

    Example::

        response.headers["Set-Cookie"] = build_set_cookie_header(session.session_id)

    The cookie uses:
    - ``HttpOnly`` (prevents JS access)
    - ``SameSite=Lax`` (allows auth redirects, blocks CSRF)
    - ``Secure`` (HTTPS only; disable via BFF_SESSION_SECURE_COOKIE=0 for local dev)
    - ``Path=/`` (required for ``__Host-`` prefix)
    """
    _assert_valid_session_id(session_id)
    name = _bff_cookie_name()
    max_age = ttl_seconds if ttl_seconds is not None else _bff_ttl_seconds()
    parts = [
        f"{name}={session_id}",
        f"Max-Age={max_age}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if _bff_secure_cookie():
        parts.append("Secure")
    return "; ".join(parts)


def build_clear_cookie_header() -> str:
    """Return a Set-Cookie header value that expires / clears the session cookie."""
    name = _bff_cookie_name()
    parts = [
        f"{name}=deleted",
        "Max-Age=0",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if _bff_secure_cookie():
        parts.append("Secure")
    return "; ".join(parts)


def parse_session_id_from_cookie(cookie_header: str | None) -> str | None:
    """Extract the BFF session ID from a Cookie header value.

    Handles multiple cookies: ``name1=val1; name2=val2``.
    Returns None if the cookie is missing.
    """
    if not cookie_header:
        return None
    name = _bff_cookie_name()
    for part in cookie_header.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        if k.strip() == name:
            candidate = v.strip()
            if not _is_valid_session_id(candidate):
                return None
            return candidate
    return None


# ---------------------------------------------------------------------------
# Module-level singleton (shared across Handler threads)
# ---------------------------------------------------------------------------

_STORE_LOCK = threading.Lock()
_store_instance: BffSessionStore | None = None


def get_session_store() -> BffSessionStore:
    """Return the module-level singleton :class:`BffSessionStore`.

    Initialised lazily on first call; uses ``BFF_SESSION_TTL_SECONDS`` env var.
    """
    global _store_instance  # noqa: PLW0603
    if _store_instance is None:
        with _STORE_LOCK:
            if _store_instance is None:
                _store_instance = BffSessionStore(ttl_seconds=_bff_ttl_seconds())
    return _store_instance
