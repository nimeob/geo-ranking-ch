#!/usr/bin/env python3
"""Mini-Benchmark: dev-only Geo-Query Cache (Issue #750).

Runs the coordinate->query resolution twice and prints timing.

Usage (from repo root):

  PYTHONPATH="$PWD" \
    DEV_GEO_QUERY_CACHE_TTL_SECONDS=0 \
    python3 scripts/bench_dev_geo_query_cache.py

  PYTHONPATH="$PWD" \
    DEV_GEO_QUERY_CACHE_TTL_SECONDS=120 \
    DEV_GEO_QUERY_CACHE_DISK=1 \
    python3 scripts/bench_dev_geo_query_cache.py

Notes:
- Requires outbound internet (geo.admin.ch endpoints).
- Cache is opt-in (ENV); disabled by default.
"""

from __future__ import annotations

import os
import time

from src.api import web_service


def bench_once(*, lat: float, lon: float) -> float:
    started = time.perf_counter()
    query, meta = web_service._resolve_query_from_coordinates(lat=lat, lon=lon, timeout_seconds=8.0)
    elapsed = time.perf_counter() - started
    print(f"resolved: {query} (feature_id={meta.get('feature_id')})")
    return elapsed


def main() -> None:
    lat = float(os.getenv("BENCH_LAT", "47.4245"))
    lon = float(os.getenv("BENCH_LON", "9.3767"))

    ttl = os.getenv("DEV_GEO_QUERY_CACHE_TTL_SECONDS", "")
    disk = os.getenv("DEV_GEO_QUERY_CACHE_DISK", "")
    print(
        "DEV_GEO_QUERY_CACHE_TTL_SECONDS="
        + (ttl if ttl else "<unset>")
        + " DEV_GEO_QUERY_CACHE_DISK="
        + (disk if disk else "<unset>")
    )

    web_service._DEV_GEO_QUERY_CACHE.clear()

    t1 = bench_once(lat=lat, lon=lon)
    t2 = bench_once(lat=lat, lon=lon)

    print(f"first:  {t1:.3f}s")
    print(f"second: {t2:.3f}s")


if __name__ == "__main__":
    main()
