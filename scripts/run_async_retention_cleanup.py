#!/usr/bin/env python3
"""Periodischer Retention-Cleanup für Async-Job-Ergebnis- und Eventdaten."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.api.async_jobs import AsyncJobStore
from src.api.duration_parsing import parse_duration_seconds


DEFAULT_RESULTS_TTL_SECONDS = 7 * 24 * 3600
DEFAULT_EVENTS_TTL_SECONDS = 3 * 24 * 3600


def _read_ttl_from_env(var_name: str, default_value: float) -> float:
    raw = os.getenv(var_name)
    if raw is None or not str(raw).strip():
        return float(default_value)
    # Fail-fast on invalid config: avoid accidentally deleting too much or too little.
    return parse_duration_seconds(raw, field_name=var_name)


def _build_parser(*, default_results_ttl: float, default_events_ttl: float) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Räumt veraltete Async-Job-Result-/Event-Daten für terminale Jobs aus dem "
            "File-Store auf."
        )
    )
    parser.add_argument(
        "--store-file",
        default=os.getenv("ASYNC_JOBS_STORE_FILE", "runtime/async_jobs/store.v1.json"),
        help="Pfad zur Async-Store-Datei (default: ASYNC_JOBS_STORE_FILE oder runtime/async_jobs/store.v1.json)",
    )
    parser.add_argument(
        "--results-ttl-seconds",
        type=str,
        default=default_results_ttl,
        help=(
            "TTL für job_results (Sekunden oder Duration wie `7d`/`24h`/`15m`). "
            "Default: ENV ASYNC_JOB_RESULTS_RETENTION_SECONDS oder "
            f"{int(default_results_ttl)}"
        ),
    )
    parser.add_argument(
        "--events-ttl-seconds",
        type=str,
        default=default_events_ttl,
        help=(
            "TTL für job_events (Sekunden oder Duration wie `7d`/`24h`/`15m`). "
            "Default: ENV ASYNC_JOB_EVENTS_RETENTION_SECONDS oder "
            f"{int(default_events_ttl)}"
        ),
    )
    parser.add_argument(
        "--disable-results-retention",
        action="store_true",
        help="Retention für job_results deaktivieren (keine Löschung).",
    )
    parser.add_argument(
        "--disable-events-retention",
        action="store_true",
        help="Retention für job_events deaktivieren (keine Löschung).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur zählen, keine Persistenzänderung schreiben.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optionaler Dateipfad für JSON-Output.",
    )
    return parser



def _run(argv: list[str]) -> int:
    default_results_ttl = _read_ttl_from_env(
        "ASYNC_JOB_RESULTS_RETENTION_SECONDS",
        float(DEFAULT_RESULTS_TTL_SECONDS),
    )
    default_events_ttl = _read_ttl_from_env(
        "ASYNC_JOB_EVENTS_RETENTION_SECONDS",
        float(DEFAULT_EVENTS_TTL_SECONDS),
    )
    parser = _build_parser(
        default_results_ttl=default_results_ttl,
        default_events_ttl=default_events_ttl,
    )
    args = parser.parse_args(argv)

    try:
        results_ttl_seconds = (
            None
            if args.disable_results_retention
            else parse_duration_seconds(
                args.results_ttl_seconds,
                field_name="results_ttl_seconds",
            )
        )
        events_ttl_seconds = (
            None
            if args.disable_events_retention
            else parse_duration_seconds(
                args.events_ttl_seconds,
                field_name="events_ttl_seconds",
            )
        )

        store_file = Path(args.store_file)
        store = AsyncJobStore(store_file=store_file)
        cleanup_summary = store.cleanup_retention(
            results_ttl_seconds=results_ttl_seconds,
            events_ttl_seconds=events_ttl_seconds,
            dry_run=bool(args.dry_run),
        )

        payload: dict[str, Any] = {
            "runner": "run_async_retention_cleanup.py",
            "store_file": str(store_file),
            "results_ttl_seconds": results_ttl_seconds,
            "events_ttl_seconds": events_ttl_seconds,
            **cleanup_summary,
        }

        if args.output_json:
            output_path = Path(args.output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
                encoding="utf-8",
            )

        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    return _run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
