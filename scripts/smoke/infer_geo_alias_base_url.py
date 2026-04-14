#!/usr/bin/env python3
"""Infer an alias base URL for geo-ranking/georanking host smoke probes.

This helper is intentionally side-effect free by default and prints an empty
string when no usable alias host can be derived.
"""

from __future__ import annotations

import argparse
import socket
import ssl
import sys
from collections.abc import Callable
from urllib.parse import urlparse


def _normalize_host(value: str) -> str:
    raw_value = str(value or "").split(",", 1)[0].strip()
    if not raw_value:
        return ""
    parsed = urlparse(raw_value if "://" in raw_value else f"//{raw_value}")
    return str(parsed.hostname or "").strip().lower()


def _expand_geo_aliases(host: str) -> list[str]:
    normalized = str(host or "").strip().lower()
    if not normalized:
        return []

    candidates: list[str] = []
    if "geo-ranking" in normalized:
        candidates.append(normalized.replace("geo-ranking", "georanking"))
    if "georanking" in normalized:
        candidates.append(normalized.replace("georanking", "geo-ranking"))

    aliases: list[str] = []
    seen: set[str] = {normalized}
    for candidate in candidates:
        if candidate and candidate not in seen:
            aliases.append(candidate)
            seen.add(candidate)
    return aliases


def _parse_canonical_hosts(raw_hosts: str) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for part in str(raw_hosts or "").split(","):
        host = _normalize_host(part)
        if host and host not in seen:
            ordered.append(host)
            seen.add(host)
    return ordered


def _tls_hostname_matches_certificate(host: str, timeout_seconds: float = 5.0) -> bool:
    normalized_host = _normalize_host(host)
    if not normalized_host:
        return False

    context = ssl.create_default_context()
    with socket.create_connection((normalized_host, 443), timeout=timeout_seconds) as conn:
        with context.wrap_socket(conn, server_hostname=normalized_host):
            return True


def _prioritize_alias_candidates(candidates: list[str]) -> list[str]:
    preferred = [candidate for candidate in candidates if "geo-ranking" in candidate]
    fallback = [candidate for candidate in candidates if "geo-ranking" not in candidate]
    return preferred + fallback


def infer_geo_alias_base_url(
    *,
    service_app_base_url: str,
    canonical_origin: str = "",
    canonical_hosts: str = "",
    require_tls_hostname_match: bool = False,
    probe_timeout_seconds: float = 5.0,
    tls_hostname_validator: Callable[[str, float], bool] | None = None,
) -> str:
    parsed_base = urlparse(str(service_app_base_url or "").strip())
    if not parsed_base.scheme or not parsed_base.netloc:
        raise ValueError("invalid_service_app_base_url")

    parsed_canonical = (
        urlparse(str(canonical_origin or "").strip())
        if str(canonical_origin or "").strip()
        else parsed_base
    )

    canonical_host = _normalize_host(parsed_canonical.netloc)
    scheme = str(parsed_canonical.scheme or parsed_base.scheme or "https").strip().lower()

    if not canonical_host:
        return ""

    candidates = _parse_canonical_hosts(canonical_hosts)
    if canonical_host not in candidates:
        candidates.insert(0, canonical_host)

    alias_candidates: list[str] = []
    seen_alias: set[str] = {canonical_host}

    for candidate in candidates:
        if candidate and candidate != canonical_host and candidate not in seen_alias:
            alias_candidates.append(candidate)
            seen_alias.add(candidate)

    for inferred in _expand_geo_aliases(canonical_host):
        if inferred and inferred not in seen_alias:
            alias_candidates.append(inferred)
            seen_alias.add(inferred)

    if not alias_candidates:
        return ""

    validator = tls_hostname_validator or _tls_hostname_matches_certificate
    for candidate in _prioritize_alias_candidates(alias_candidates):
        if require_tls_hostname_match and scheme == "https":
            try:
                if not validator(candidate, probe_timeout_seconds):
                    print(
                        f"[infer-geo-alias] skip alias '{candidate}': tls_hostname_mismatch",
                        file=sys.stderr,
                    )
                    continue
            except Exception as exc:  # pragma: no cover - defensive for CI/runtime
                print(
                    f"[infer-geo-alias] skip alias '{candidate}': tls_probe_failed ({exc})",
                    file=sys.stderr,
                )
                continue

        return f"{scheme}://{candidate}"

    return ""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Infer alias base URL for geo-ranking/georanking smoke checks"
    )
    parser.add_argument(
        "--service-app-base-url",
        "--base-url",
        dest="service_app_base_url",
        required=True,
        help="Canonical service app base URL (alias: --base-url)",
    )
    parser.add_argument("--canonical-origin", default="")
    parser.add_argument("--canonical-hosts", default="")
    parser.add_argument(
        "--require-tls-hostname-match",
        action="store_true",
        help="Require selected HTTPS alias host to pass TLS hostname validation",
    )
    parser.add_argument(
        "--probe-timeout",
        type=float,
        default=5.0,
        help="TLS probe timeout in seconds when --require-tls-hostname-match is set",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    alias_base_url = infer_geo_alias_base_url(
        service_app_base_url=args.service_app_base_url,
        canonical_origin=args.canonical_origin,
        canonical_hosts=args.canonical_hosts,
        require_tls_hostname_match=bool(args.require_tls_hostname_match),
        probe_timeout_seconds=float(args.probe_timeout),
    )
    print(alias_base_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
