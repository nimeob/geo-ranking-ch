#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LEGACY_CLASSIFICATION = "legacy-user-swisstopo-api-deploy"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Report file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in report {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Report {path} must be a JSON object")

    generated = payload.get("generated_at_utc")
    caller = payload.get("caller")
    exit_codes = payload.get("exit_codes")

    if not isinstance(generated, str) or not generated.strip():
        raise ValueError(f"Report {path} is missing non-empty string field 'generated_at_utc'")
    if not isinstance(caller, dict):
        raise ValueError(f"Report {path} is missing object field 'caller'")
    if not isinstance(exit_codes, dict):
        raise ValueError(f"Report {path} is missing object field 'exit_codes'")

    classification = caller.get("classification")
    final_exit = exit_codes.get("final")

    if not isinstance(classification, str) or not classification.strip():
        raise ValueError(f"Report {path} is missing non-empty string field 'caller.classification'")
    if not isinstance(final_exit, int):
        raise ValueError(f"Report {path} is missing integer field 'exit_codes.final'")

    return {
        "path": str(path),
        "generated_at_utc": generated,
        "classification": classification,
        "final_exit": final_exit,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate BL-17 posture reports and classify readiness for the "
            "Legacy-only-fallback window."
        )
    )
    parser.add_argument(
        "--glob",
        dest="patterns",
        action="append",
        required=True,
        help="Glob pattern for input reports (repeatable), e.g. artifacts/bl17/*.json",
    )
    parser.add_argument(
        "--output-json",
        dest="output_json",
        default="",
        help="Optional output path for structured summary JSON",
    )
    parser.add_argument(
        "--min-reports",
        dest="min_reports",
        type=int,
        default=1,
        help="Minimum number of reports required for a readiness decision (default: 1)",
    )
    args = parser.parse_args(argv)

    if args.min_reports < 1:
        parser.error("--min-reports must be >= 1")

    return args


def main(argv: list[str]) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    report_paths: list[Path] = []
    for pattern in args.patterns:
        matches = sorted(Path(match) for match in glob.glob(pattern))
        report_paths.extend(matches)

    # Deduplicate while keeping deterministic order.
    deduped_paths: list[Path] = []
    seen: set[Path] = set()
    for p in report_paths:
        if p not in seen:
            deduped_paths.append(p)
            seen.add(p)

    if not deduped_paths:
        print("ERROR: no reports matched the provided --glob pattern(s)", file=sys.stderr)
        return 2

    try:
        reports = [_read_report(path) for path in deduped_paths]
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    timestamps = [r["generated_at_utc"] for r in reports]
    classification_counts = Counter(r["classification"] for r in reports)
    legacy_observed_count = classification_counts.get(LEGACY_CLASSIFICATION, 0)
    nonzero_final_exit_count = sum(1 for r in reports if r["final_exit"] != 0)
    max_final_exit = max(r["final_exit"] for r in reports)

    insufficient_reports = len(reports) < args.min_reports
    ready = not insufficient_reports and legacy_observed_count == 0 and nonzero_final_exit_count == 0

    if ready:
        recommended_status = "ready"
        recommended_exit_code = 0
    else:
        recommended_status = "not-ready"
        recommended_exit_code = 10

    summary = {
        "version": 1,
        "generated_at_utc": _utc_now_iso(),
        "input": {
            "patterns": args.patterns,
            "report_count": len(reports),
            "min_reports_required": args.min_reports,
        },
        "window": {
            "from_generated_at_utc": min(timestamps),
            "to_generated_at_utc": max(timestamps),
        },
        "caller_classification_counts": dict(sorted(classification_counts.items())),
        "legacy_observed_count": legacy_observed_count,
        "nonzero_final_exit_count": nonzero_final_exit_count,
        "max_final_exit": max_final_exit,
        "insufficient_reports": insufficient_reports,
        "recommended_status": recommended_status,
        "recommended_exit_code": recommended_exit_code,
        "report_files": [r["path"] for r in reports],
    }

    rendered = json.dumps(summary, indent=2, sort_keys=True)
    print(rendered)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    return recommended_exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
