#!/usr/bin/env python3
"""Run the PR dev-smoke gate with a centralized retry policy.

Issue: #1041
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "dev-smoke-required-retry-report/v1"


@dataclass
class AttemptResult:
    attempt: int
    started_at_utc: str
    ended_at_utc: str
    duration_seconds: float
    exit_code: int
    report_path: str
    report_loaded: bool
    checks: list[dict[str, Any]]

    @property
    def status(self) -> str:
        return "pass" if self.exit_code == 0 else "fail"

    @property
    def failed_checks(self) -> list[str]:
        failed: list[str] = []
        for check in self.checks:
            if str(check.get("status", "")).lower() != "pass":
                name = str(check.get("name") or "unnamed-check").strip() or "unnamed-check"
                failed.append(name)
        return failed


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_positive_int(value: str, flag: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{flag} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{flag} must be >= 1")
    return parsed


def _parse_non_negative_float(value: str, flag: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{flag} must be a number") from exc
    if parsed < 0:
        raise ValueError(f"{flag} must be >= 0")
    return parsed


def _attempt_output_path(base_output: Path, attempt: int) -> Path:
    suffix = "".join(base_output.suffixes)
    stem = base_output.name[: -len(suffix)] if suffix else base_output.name
    attempt_name = f"{stem}-attempt-{attempt}{suffix}"
    return base_output.with_name(attempt_name)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _run_attempt(args: argparse.Namespace, attempt: int, base_output_json: Path) -> AttemptResult:
    attempt_output = _attempt_output_path(base_output_json, attempt)
    attempt_output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        args.python_bin,
        str((REPO_ROOT / args.runner_script).resolve()),
        "--profile",
        "pr",
        "--flow",
        "sync",
        "--output-json",
        str(attempt_output),
    ]

    started = _timestamp_utc()
    started_perf = time.perf_counter()
    proc = subprocess.run(command, cwd=str(REPO_ROOT), text=True)
    duration = round(time.perf_counter() - started_perf, 3)
    ended = _timestamp_utc()

    payload = _load_json(attempt_output)
    checks = []
    if isinstance(payload, dict) and isinstance(payload.get("checks"), list):
        checks = [item for item in payload["checks"] if isinstance(item, dict)]

    return AttemptResult(
        attempt=attempt,
        started_at_utc=started,
        ended_at_utc=ended,
        duration_seconds=duration,
        exit_code=int(proc.returncode),
        report_path=str(attempt_output),
        report_loaded=payload is not None,
        checks=checks,
    )


def _aggregate_tests(attempts: list[AttemptResult]) -> list[dict[str, Any]]:
    timeline: dict[str, list[dict[str, Any]]] = {}

    for attempt in attempts:
        check_statuses = {
            str(check.get("name") or "unnamed-check").strip() or "unnamed-check": str(check.get("status") or "unknown").lower()
            for check in attempt.checks
        }

        if not check_statuses:
            synthetic_name = "pr-split-smoke"
            check_statuses = {synthetic_name: "pass" if attempt.exit_code == 0 else "fail"}

        for name, status in check_statuses.items():
            timeline.setdefault(name, []).append(
                {
                    "attempt": attempt.attempt,
                    "status": status,
                }
            )

    tests: list[dict[str, Any]] = []
    for name in sorted(timeline.keys()):
        entries = timeline[name]
        statuses = [entry["status"] for entry in entries]
        saw_fail_before_last = any(status != "pass" for status in statuses[:-1])
        final_status = statuses[-1]
        flaky_hint = None
        if final_status == "pass" and saw_fail_before_last:
            flaky_hint = f"failed on attempt(s) before final pass (attempt {entries[-1]['attempt']})"

        tests.append(
            {
                "name": name,
                "final_status": final_status,
                "attempts": entries,
                "flaky_hint": flaky_hint,
            }
        )

    return tests


def _build_summary_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    retry_policy = report.get("retry_policy", {})

    lines = [
        "## dev-smoke-required Retry Summary",
        "",
        f"- Final status: **{report.get('status', 'unknown')}**",
        f"- Retry policy: `max_attempts={retry_policy.get('max_attempts')}`, `retry_delay_seconds={retry_policy.get('retry_delay_seconds')}`",
        f"- Attempts used: **{summary.get('attempts_used', 0)}**",
        f"- Retried checks: **{summary.get('retried_checks', 0)}**",
        f"- Flaky candidates: **{summary.get('flaky_candidates', 0)}**",
        "",
        "### Check details",
    ]

    tests = report.get("tests", [])
    if not tests:
        lines.append("- (no checks reported)")
    else:
        for test in tests:
            attempts = ", ".join(
                f"A{entry.get('attempt')}={entry.get('status')}" for entry in test.get("attempts", [])
            )
            line = f"- `{test.get('name')}` → **{test.get('final_status')}** ({attempts})"
            if test.get("flaky_hint"):
                line += f" ⚠️ flaky: {test['flaky_hint']}"
            lines.append(line)

    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retry wrapper for dev-smoke-required gate")
    parser.add_argument("--python-bin", default="python3")
    parser.add_argument(
        "--runner-script",
        default="scripts/run_deploy_smoke.py",
        help="Path to the underlying smoke runner script (repo-relative)",
    )
    parser.add_argument(
        "--output-json",
        default="artifacts/pr-dev-smoke-required.json",
        help="Canonical output JSON path for the final deploy-smoke report",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/pr-dev-smoke-required-retry-report.json",
        help="Retry telemetry report path",
    )
    parser.add_argument(
        "--summary-markdown",
        default="artifacts/pr-dev-smoke-required-summary.md",
        help="Markdown summary path for CI step summary",
    )
    parser.add_argument(
        "--max-attempts",
        default=None,
        help="Override retry attempts (defaults to DEV_SMOKE_MAX_ATTEMPTS or 2)",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        default=None,
        help="Override retry delay seconds (defaults to DEV_SMOKE_RETRY_DELAY_SECONDS or 5)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    try:
        max_attempts = _parse_positive_int(
            args.max_attempts or os.environ.get("DEV_SMOKE_MAX_ATTEMPTS", "2"),
            "--max-attempts/DEV_SMOKE_MAX_ATTEMPTS",
        )
        retry_delay_seconds = _parse_non_negative_float(
            args.retry_delay_seconds or os.environ.get("DEV_SMOKE_RETRY_DELAY_SECONDS", "5"),
            "--retry-delay-seconds/DEV_SMOKE_RETRY_DELAY_SECONDS",
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    base_output_json = (REPO_ROOT / args.output_json).resolve()
    report_json = (REPO_ROOT / args.report_json).resolve()
    summary_markdown = (REPO_ROOT / args.summary_markdown).resolve()

    attempts: list[AttemptResult] = []

    for attempt in range(1, max_attempts + 1):
        result = _run_attempt(args, attempt, base_output_json)
        attempts.append(result)

        if result.exit_code == 0:
            break

        if attempt < max_attempts and retry_delay_seconds > 0:
            print(
                f"[dev-smoke-required] attempt {attempt}/{max_attempts} failed; retrying in {retry_delay_seconds}s",
                file=sys.stderr,
            )
            time.sleep(retry_delay_seconds)

    last = attempts[-1]
    last_attempt_path = Path(last.report_path)
    if last_attempt_path.exists():
        base_output_json.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(last_attempt_path, base_output_json)

    tests = _aggregate_tests(attempts)
    retried_checks = sum(1 for test in tests if len(test.get("attempts", [])) > 1)
    flaky_candidates = sum(1 for test in tests if test.get("flaky_hint"))

    status = "pass" if last.exit_code == 0 else "fail"
    reason = "ok" if last.exit_code == 0 else "retries_exhausted"

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reason": reason,
        "retry_policy": {
            "max_attempts": max_attempts,
            "retry_delay_seconds": retry_delay_seconds,
        },
        "attempts": [
            {
                "attempt": attempt.attempt,
                "status": attempt.status,
                "exit_code": attempt.exit_code,
                "started_at_utc": attempt.started_at_utc,
                "ended_at_utc": attempt.ended_at_utc,
                "duration_seconds": attempt.duration_seconds,
                "report_path": attempt.report_path,
                "report_loaded": attempt.report_loaded,
                "failed_checks": attempt.failed_checks,
            }
            for attempt in attempts
        ],
        "tests": tests,
        "summary": {
            "attempts_used": len(attempts),
            "retried_checks": retried_checks,
            "flaky_candidates": flaky_candidates,
        },
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = _build_summary_markdown(payload)
    summary_markdown.parent.mkdir(parents=True, exist_ok=True)
    summary_markdown.write_text(summary, encoding="utf-8")

    if status != "pass":
        return int(last.exit_code or 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
