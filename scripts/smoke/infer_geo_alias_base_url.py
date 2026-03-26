#!/usr/bin/env python3
"""Infer an alias base URL for geo-ranking/georanking host smoke probes.

This helper is intentionally side-effect free and prints an empty string when no
usable alias host can be derived.
"""

from __future__ import annotations

import argparse
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


def infer_geo_alias_base_url(
    *,
    service_app_base_url: str,
    canonical_origin: str = "",
    canonical_hosts: str = "",
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

    selected_alias = ""
    for candidate in alias_candidates:
        if "geo-ranking" in candidate:
            selected_alias = candidate
            break

    if not selected_alias and alias_candidates:
        selected_alias = alias_candidates[0]

    if not selected_alias:
        return ""

    return f"{scheme}://{selected_alias}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Infer alias base URL for geo-ranking/georanking smoke checks"
    )
    parser.add_argument("--service-app-base-url", required=True)
    parser.add_argument("--canonical-origin", default="")
    parser.add_argument("--canonical-hosts", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    alias_base_url = infer_geo_alias_base_url(
        service_app_base_url=args.service_app_base_url,
        canonical_origin=args.canonical_origin,
        canonical_hosts=args.canonical_hosts,
    )
    print(alias_base_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
