from __future__ import annotations

import math
import os
from typing import Any, Callable

from src.api.oidc_jwt import JwksCache, OidcJwtConfig, OidcJwtValidator

_OIDC_JWKS_URL_ENV = "OIDC_JWKS_URL"
_OIDC_JWT_ISSUER_ENV = "OIDC_JWT_ISSUER"
_OIDC_JWT_AUDIENCE_ENV = "OIDC_JWT_AUDIENCE"
_LEGACY_OIDC_ISSUER_ENV = "OIDC_ISSUER"
_LEGACY_OIDC_AUDIENCE_ENV = "OIDC_AUDIENCE"
_OIDC_JWKS_TTL_SECONDS_ENV = "OIDC_JWKS_TTL_SECONDS"
_OIDC_JWKS_TIMEOUT_SECONDS_ENV = "OIDC_JWKS_TIMEOUT_SECONDS"
_OIDC_CLOCK_SKEW_SECONDS_ENV = "OIDC_CLOCK_SKEW_SECONDS"


def _read_float_from_env(
    *,
    env_getter: Callable[[str, str], str | Any],
    name: str,
    default: str,
    predicate: Callable[[float], bool],
    requirement_hint: str,
) -> float:
    raw_value = str(env_getter(name, default) or default).strip()
    try:
        parsed = float(raw_value)
    except Exception as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(parsed) or not predicate(parsed):
        raise ValueError(f"{name} must be finite and {requirement_hint}")
    return parsed


def _read_env_with_optional_legacy_fallback(
    *,
    env_getter: Callable[[str, str], str | Any],
    primary_name: str,
    legacy_name: str,
) -> str:
    """Read *primary_name* and fallback to *legacy_name* when unset.

    The fallback keeps existing deployments working that still use the original
    ``OIDC_ISSUER``/``OIDC_AUDIENCE`` naming from early runbooks.
    """
    primary = str(env_getter(primary_name, "") or "").strip()
    if primary:
        return primary
    return str(env_getter(legacy_name, "") or "").strip()


def load_oidc_jwt_validator_from_env(
    *,
    env_getter: Callable[[str, str], str | Any] = os.getenv,
) -> OidcJwtValidator | None:
    """Build an OIDC JWT validator from environment configuration.

    OIDC auth is enabled when `OIDC_JWKS_URL` is set.

    Notes:
    - This function must be safe at import time: it must not fetch the JWKS.
    - If configured but invalid, we fail-fast (better crash than silently disable auth).
    - ``OIDC_JWT_ISSUER``/``OIDC_JWT_AUDIENCE`` have precedence; for backward
      compatibility we fallback to ``OIDC_ISSUER``/``OIDC_AUDIENCE`` when needed.
    """
    jwks_url = str(env_getter(_OIDC_JWKS_URL_ENV, "") or "").strip()
    if not jwks_url:
        return None

    issuer = _read_env_with_optional_legacy_fallback(
        env_getter=env_getter,
        primary_name=_OIDC_JWT_ISSUER_ENV,
        legacy_name=_LEGACY_OIDC_ISSUER_ENV,
    )
    audience = _read_env_with_optional_legacy_fallback(
        env_getter=env_getter,
        primary_name=_OIDC_JWT_AUDIENCE_ENV,
        legacy_name=_LEGACY_OIDC_AUDIENCE_ENV,
    )

    ttl_seconds = _read_float_from_env(
        env_getter=env_getter,
        name=_OIDC_JWKS_TTL_SECONDS_ENV,
        default="300",
        predicate=lambda value: value >= 0,
        requirement_hint=">= 0",
    )
    timeout_seconds = _read_float_from_env(
        env_getter=env_getter,
        name=_OIDC_JWKS_TIMEOUT_SECONDS_ENV,
        default="5",
        predicate=lambda value: value > 0,
        requirement_hint="> 0",
    )
    clock_skew_seconds = _read_float_from_env(
        env_getter=env_getter,
        name=_OIDC_CLOCK_SKEW_SECONDS_ENV,
        default="60",
        predicate=lambda value: value >= 0,
        requirement_hint=">= 0",
    )

    config = OidcJwtConfig(
        issuer=issuer,
        audience=audience,
        clock_skew_seconds=clock_skew_seconds,
        require_exp=True,
    )
    jwks_cache = JwksCache(
        jwks_url=jwks_url,
        ttl_seconds=ttl_seconds,
        timeout_seconds=timeout_seconds,
    )
    return OidcJwtValidator(config=config, jwks=jwks_cache)
