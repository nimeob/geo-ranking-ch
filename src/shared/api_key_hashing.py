"""API key hashing + fingerprint helpers.

This module provides dependency-free helpers to ensure *secret API keys are
never persisted in plaintext*.

Design goals:
- **fingerprint**: short, stable identifier derived from the key material.
  Used for lookup / rotation UX, but not a secret.
- **hash**: server-side derived value used for verification. Must not allow
  recovery of the original key without access to the server secret.

Current supported scheme:
- ``hmac_sha256_v1`` using a server-side secret ("pepper")

Once the DB layer is implemented, the expected storage pattern is:
- store ``key_fingerprint`` + ``key_hash`` + ``hash_scheme``
- never store the plaintext key
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

DEFAULT_HASH_SCHEME = "hmac_sha256_v1"
DEFAULT_FINGERPRINT_HEX_CHARS = 12


def _normalize_api_key(token: str) -> bytes:
    token_str = str(token or "").strip()
    if not token_str:
        raise ValueError("api key token must be non-empty")
    return token_str.encode("utf-8")


def build_key_fingerprint(token: str, *, hex_chars: int = DEFAULT_FINGERPRINT_HEX_CHARS) -> str:
    """Return a short stable SHA-256 fingerprint of a token.

    The fingerprint is intended for *identification only* (e.g. displaying the
    last 12 hex characters). It must not be treated as a secret.
    """

    if hex_chars <= 0:
        raise ValueError("hex_chars must be > 0")

    token_bytes = _normalize_api_key(token)
    digest = hashlib.sha256(token_bytes).hexdigest()
    return digest[:hex_chars]


def hash_api_key(
    token: str,
    *,
    secret: bytes,
    scheme: str = DEFAULT_HASH_SCHEME,
) -> str:
    """Hash the api key using the configured scheme.

    ``secret`` is a server-side configuration value (pepper). Keep it out of
    logs and never persist it.
    """

    if not isinstance(secret, (bytes, bytearray)) or not secret:
        raise ValueError("secret must be non-empty bytes")

    token_bytes = _normalize_api_key(token)
    scheme_normalized = str(scheme or "").strip().lower()

    if scheme_normalized == "hmac_sha256_v1":
        return hmac.new(bytes(secret), token_bytes, hashlib.sha256).hexdigest()

    raise ValueError(f"unsupported hash scheme: {scheme}")


def verify_api_key(
    token: str,
    *,
    secret: bytes,
    expected_hash: str,
    scheme: str = DEFAULT_HASH_SCHEME,
) -> bool:
    """Verify a plaintext api key against a stored hash (constant-time compare)."""

    computed = hash_api_key(token, secret=secret, scheme=scheme)
    return hmac.compare_digest(str(computed), str(expected_hash or ""))


def build_api_key_storage_fields(
    token: str,
    *,
    secret: bytes,
    label: str | None = None,
    scheme: str = DEFAULT_HASH_SCHEME,
) -> dict[str, Any]:
    """Build storage-ready fields for an ``api_keys`` row (no plaintext key)."""

    return {
        "label": str(label).strip() or None if label is not None else None,
        "key_fingerprint": build_key_fingerprint(token),
        "key_hash": hash_api_key(token, secret=secret, scheme=scheme),
        "hash_scheme": str(scheme or DEFAULT_HASH_SCHEME).strip().lower() or DEFAULT_HASH_SCHEME,
    }
