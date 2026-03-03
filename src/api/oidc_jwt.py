"""OIDC/JWT validation helpers (stdlib-only).

This module intentionally avoids external crypto dependencies by implementing
RSASSA-PKCS1-v1_5 (RS256) verification directly from JWK (n,e).

Security notes:
- Only RS256 is supported.
- "alg":"none" and unknown algorithms are rejected.
- Signature verification uses PKCS#1 v1.5 DigestInfo(SHA-256) structure checks.
- Comparisons use hmac.compare_digest when applicable.

This is meant as a building block for issue #817 (OIDC-0.wp1).

-----------------------------------------------------------------------
Required configuration / environment variables
-----------------------------------------------------------------------
OIDC_ISSUER
    Token issuer URL that must match the ``iss`` claim.
    Example: ``https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_XXXXX``

OIDC_AUDIENCE
    Expected ``aud`` claim (client-id or API resource identifier).
    Example: ``abc123clientid``  or  ``geo-ranking-api``

OIDC_JWKS_URL
    JWKS endpoint exposed by the Identity Provider.
    Cognito example:
    ``https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_XXXXX/.well-known/jwks.json``

OIDC_CLOCK_SKEW   (optional, default: 60)
    Allowed clock drift in seconds for ``exp``/``nbf`` checks.

Usage example::

    import os
    from src.api.oidc_jwt import JwksCache, OidcJwtConfig, OidcJwtValidator

    _validator = OidcJwtValidator(
        config=OidcJwtConfig(
            issuer=os.environ["OIDC_ISSUER"],
            audience=os.environ["OIDC_AUDIENCE"],
            clock_skew_seconds=int(os.getenv("OIDC_CLOCK_SKEW", "60")),
        ),
        jwks=JwksCache(jwks_url=os.environ["OIDC_JWKS_URL"]),
    )

    # Inside a FastAPI dependency:
    #   claims = _validator.validate(bearer_token)
    #   user_sub = claims["sub"]
-----------------------------------------------------------------------
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlsplit
from urllib.request import urlopen


class JwtValidationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = str(code or "invalid_token")
        super().__init__(str(message or code or "invalid token"))


def _b64url_decode(data: str) -> bytes:
    raw = str(data or "").strip()
    if not raw:
        return b""
    # Add base64 padding.
    pad_len = (-len(raw)) % 4
    raw_padded = raw + ("=" * pad_len)
    try:
        return base64.urlsafe_b64decode(raw_padded.encode("ascii"))
    except Exception as exc:
        raise JwtValidationError("invalid_base64", "invalid base64url encoding") from exc


def _b64url_decode_int(data: str) -> int:
    decoded = _b64url_decode(data)
    if not decoded:
        return 0
    return int.from_bytes(decoded, byteorder="big", signed=False)


def _decode_json_segment(segment_b64: str, *, label: str) -> dict[str, Any]:
    decoded = _b64url_decode(segment_b64)
    try:
        parsed = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise JwtValidationError("invalid_json", f"invalid {label} json") from exc
    if not isinstance(parsed, dict):
        raise JwtValidationError("invalid_json", f"{label} must be a json object")
    return parsed


_SHA256_DIGESTINFO_PREFIX = bytes.fromhex(
    # DigestInfo ::= SEQUENCE { AlgorithmIdentifier sha256, OCTET STRING <hash> }
    # sha256 OID = 2.16.840.1.101.3.4.2.1
    "3031300d060960864801650304020105000420"
)


@dataclass(frozen=True)
class RsaPublicKey:
    n: int
    e: int
    kid: str = ""

    @property
    def size_bytes(self) -> int:
        if self.n <= 0:
            return 0
        return max(1, (self.n.bit_length() + 7) // 8)


def _rsa_verify_pkcs1v15_sha256(
    *,
    key: RsaPublicKey,
    signing_input: bytes,
    signature: bytes,
) -> bool:
    if key.n <= 0 or key.e <= 0:
        return False

    k = key.size_bytes
    if k < 64:
        # Too small to be realistic; treat as invalid.
        return False
    if len(signature) != k:
        return False

    sig_int = int.from_bytes(signature, byteorder="big", signed=False)
    if sig_int <= 0 or sig_int >= key.n:
        return False

    em_int = pow(sig_int, key.e, key.n)
    em = em_int.to_bytes(k, byteorder="big", signed=False)

    # EM = 0x00 || 0x01 || PS (0xff...) || 0x00 || T
    if not (len(em) >= 11 and em[0] == 0x00 and em[1] == 0x01):
        return False

    try:
        sep_index = em.index(b"\x00", 2)
    except ValueError:
        return False

    ps = em[2:sep_index]
    if len(ps) < 8:
        return False
    if any(b != 0xFF for b in ps):
        return False

    t = em[sep_index + 1 :]
    expected_hash = hashlib.sha256(signing_input).digest()
    expected_t = _SHA256_DIGESTINFO_PREFIX + expected_hash

    if len(t) != len(expected_t):
        return False

    return hmac.compare_digest(t, expected_t)


@dataclass
class JwksCache:
    jwks_url: str
    ttl_seconds: float = 300.0
    timeout_seconds: float = 5.0
    fetch_json: Callable[[str, float], dict[str, Any]] | None = None

    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _cached_until: float = field(default=0.0, init=False)
    _cached_keys: list[RsaPublicKey] = field(default_factory=list, init=False, repr=False)

    def _default_fetch_json(self, url: str, timeout_seconds: float) -> dict[str, Any]:
        target = urlsplit(url)
        if target.scheme.lower() not in {"https", "http"}:
            raise JwtValidationError("invalid_jwks_url", "jwks_url must be http(s)")
        with urlopen(url, timeout=max(1.0, float(timeout_seconds))) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
        if not isinstance(parsed, dict):
            raise JwtValidationError("invalid_jwks", "jwks root must be an object")
        return parsed

    def _parse_jwks(self, payload: dict[str, Any]) -> list[RsaPublicKey]:
        keys_raw = payload.get("keys")
        if not isinstance(keys_raw, list):
            raise JwtValidationError("invalid_jwks", "jwks must contain keys:[]")

        keys: list[RsaPublicKey] = []
        for row in keys_raw:
            if not isinstance(row, dict):
                continue
            if str(row.get("kty") or "").upper() != "RSA":
                continue
            n = _b64url_decode_int(str(row.get("n") or ""))
            e = _b64url_decode_int(str(row.get("e") or ""))
            if n <= 0 or e <= 0:
                continue
            kid = str(row.get("kid") or "").strip()
            keys.append(RsaPublicKey(n=n, e=e, kid=kid))

        if not keys:
            raise JwtValidationError("invalid_jwks", "jwks contains no usable RSA keys")
        return keys

    def get_rsa_keys(self, *, now: float | None = None) -> list[RsaPublicKey]:
        ts = time.time() if now is None else float(now)
        with self._lock:
            if ts < self._cached_until and self._cached_keys:
                return list(self._cached_keys)

        fetcher = self.fetch_json or self._default_fetch_json
        payload = fetcher(self.jwks_url, float(self.timeout_seconds))
        keys = self._parse_jwks(payload)
        ttl = max(0.0, float(self.ttl_seconds))

        with self._lock:
            self._cached_keys = list(keys)
            self._cached_until = ts + ttl
        return list(keys)


@dataclass(frozen=True)
class OidcJwtConfig:
    issuer: str = ""
    audience: str = ""
    clock_skew_seconds: int = 60
    require_exp: bool = True


@dataclass
class OidcJwtValidator:
    config: OidcJwtConfig
    jwks: JwksCache

    def _parse_compact_jws(self, token: str) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
        raw = str(token or "").strip()
        parts = raw.split(".")
        if len(parts) != 3:
            raise JwtValidationError("invalid_format", "token must have 3 dot-separated parts")

        header = _decode_json_segment(parts[0], label="header")
        claims = _decode_json_segment(parts[1], label="payload")
        signature = _b64url_decode(parts[2])
        signing_input = (parts[0] + "." + parts[1]).encode("ascii")
        return header, claims, signing_input, signature

    def _validate_claims(self, claims: dict[str, Any], *, now: float) -> None:
        issuer = str(self.config.issuer or "").strip()
        if issuer:
            iss = str(claims.get("iss") or "").strip()
            if not iss:
                raise JwtValidationError("invalid_issuer", "missing iss")
            if iss != issuer:
                raise JwtValidationError("invalid_issuer", "issuer mismatch")

        audience = str(self.config.audience or "").strip()
        if audience:
            aud_claim = claims.get("aud")
            aud_ok = False
            if isinstance(aud_claim, str):
                aud_ok = aud_claim == audience
            elif isinstance(aud_claim, list):
                aud_ok = any(isinstance(item, str) and item == audience for item in aud_claim)
            if not aud_ok:
                raise JwtValidationError("invalid_audience", "audience mismatch")

        skew = max(0, int(self.config.clock_skew_seconds))

        exp = claims.get("exp")
        if exp is None:
            if self.config.require_exp:
                raise JwtValidationError("missing_exp", "missing exp")
        else:
            try:
                exp_int = int(exp)
            except Exception as exc:
                raise JwtValidationError("invalid_exp", "exp must be an integer") from exc
            if now > float(exp_int + skew):
                raise JwtValidationError("token_expired", "token expired")

        nbf = claims.get("nbf")
        if nbf is not None:
            try:
                nbf_int = int(nbf)
            except Exception as exc:
                raise JwtValidationError("invalid_nbf", "nbf must be an integer") from exc
            if now < float(nbf_int - skew):
                raise JwtValidationError("token_not_yet_valid", "token not yet valid")

    def validate(self, token: str, *, now: float | None = None) -> dict[str, Any]:
        header, claims, signing_input, signature = self._parse_compact_jws(token)

        alg = str(header.get("alg") or "").strip()
        if alg != "RS256":
            raise JwtValidationError("unsupported_alg", "only RS256 is supported")

        keys = self.jwks.get_rsa_keys(now=now)
        kid = str(header.get("kid") or "").strip()
        if kid:
            matches = [candidate for candidate in keys if candidate.kid == kid]
            if len(matches) == 1:
                key = matches[0]
            elif not matches:
                raise JwtValidationError("invalid_kid", "kid not found in jwks")
            else:
                raise JwtValidationError("invalid_kid", "kid is not unique in jwks")
        else:
            if len(keys) == 1:
                key = keys[0]
            else:
                raise JwtValidationError("kid_required", "kid required")

        if not _rsa_verify_pkcs1v15_sha256(key=key, signing_input=signing_input, signature=signature):
            raise JwtValidationError("invalid_signature", "signature verification failed")

        ts = time.time() if now is None else float(now)
        self._validate_claims(claims, now=ts)
        return claims
