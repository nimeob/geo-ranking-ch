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
DEFAULT_MAX_RETRIES = 1
DEFAULT_MAX_ATTEMPTS = DEFAULT_MAX_RETRIES + 1
MAX_ALLOWED_RETRIES = 1


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
        return [item["name"] for item in self.failed_check_details]

    @property
    def failed_check_details(self) -> list[dict[str, str]]:
        failed: list[dict[str, str]] = []
        for check in self.checks:
            if str(check.get("status", "")).lower() == "pass":
                continue
            name = str(check.get("name") or "unnamed-check").strip() or "unnamed-check"
            reason = str(check.get("reason") or "unknown").strip() or "unknown"
            failed.append(
                {
                    "name": name,
                    "reason": reason,
                }
            )
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


def _parse_non_negative_int(value: str, flag: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{flag} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"{flag} must be >= 0")
    return parsed


def _parse_non_negative_float(value: str, flag: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{flag} must be a number") from exc
    if parsed < 0:
        raise ValueError(f"{flag} must be >= 0")
    return parsed


def _resolve_smoke_test_seed() -> str:
    raw = os.environ.get("DEV_SMOKE_TEST_SEED", "")
    seed = raw.strip()
    if raw and not seed:
        raise ValueError("DEV_SMOKE_TEST_SEED must not be empty after trimming")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in seed):
        raise ValueError("DEV_SMOKE_TEST_SEED must not contain control chars")
    return seed


def _resolve_retry_policy(args: argparse.Namespace) -> tuple[int, int]:
    max_retries_raw = args.max_retries or os.environ.get("DEV_SMOKE_MAX_RETRIES")
    max_attempts_raw = args.max_attempts or os.environ.get("DEV_SMOKE_MAX_ATTEMPTS")

    if max_retries_raw is not None:
        max_retries = _parse_non_negative_int(
            max_retries_raw,
            "--max-retries/DEV_SMOKE_MAX_RETRIES",
        )
        if max_retries > MAX_ALLOWED_RETRIES:
            raise ValueError(
                f"--max-retries/DEV_SMOKE_MAX_RETRIES must be <= {MAX_ALLOWED_RETRIES} (max 1 retry in Dev-CI)"
            )
        return max_retries + 1, max_retries

    if max_attempts_raw is not None:
        max_attempts = _parse_positive_int(
            max_attempts_raw,
            "--max-attempts/DEV_SMOKE_MAX_ATTEMPTS",
        )
        max_retries = max_attempts - 1
        if max_retries > MAX_ALLOWED_RETRIES:
            raise ValueError(
                f"--max-attempts/DEV_SMOKE_MAX_ATTEMPTS implies {max_retries} retries; max allowed is {MAX_ALLOWED_RETRIES}"
            )
        return max_attempts, max_retries

    return DEFAULT_MAX_ATTEMPTS, DEFAULT_MAX_RETRIES


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


def _build_ci_context() -> dict[str, Any]:
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    run_number = os.environ.get("GITHUB_RUN_NUMBER")
    workflow = os.environ.get("GITHUB_WORKFLOW")
    job = os.environ.get("GITHUB_JOB")
    sha = os.environ.get("GITHUB_SHA")
    repository = os.environ.get("GITHUB_REPOSITORY")
    server_url = os.environ.get("GITHUB_SERVER_URL")

    run_url = None
    if run_id and repository and server_url:
        if run_attempt:
            run_url = f"{server_url}/{repository}/actions/runs/{run_id}/attempts/{run_attempt}"
        else:
            run_url = f"{server_url}/{repository}/actions/runs/{run_id}"

    return {
        "provider": "github_actions" if run_id else "local",
        "run_id": run_id,
        "run_attempt": run_attempt,
        "run_number": run_number,
        "workflow": workflow,
        "job": job,
        "sha": sha,
        "repository": repository,
        "run_url": run_url,
    }


def _aggregate_tests(attempts: list[AttemptResult], build_context: dict[str, Any]) -> list[dict[str, Any]]:
    timeline: dict[str, list[dict[str, Any]]] = {}

    for attempt in attempts:
        check_entries = {
            str(check.get("name") or "unnamed-check").strip() or "unnamed-check": {
                "status": str(check.get("status") or "unknown").lower(),
                "reason": str(check.get("reason") or "unknown").strip() or "unknown",
            }
            for check in attempt.checks
        }

        if not check_entries:
            synthetic_name = "pr-split-smoke"
            check_entries = {
                synthetic_name: {
                    "status": "pass" if attempt.exit_code == 0 else "fail",
                    "reason": "ok" if attempt.exit_code == 0 else "command_failed",
                }
            }

        for name, check_entry in check_entries.items():
            timeline.setdefault(name, []).append(
                {
                    "attempt": attempt.attempt,
                    "status": check_entry["status"],
                    "reason": check_entry["reason"],
                }
            )

    tests: list[dict[str, Any]] = []
    for name in sorted(timeline.keys()):
        entries = timeline[name]
        statuses = [entry["status"] for entry in entries]
        saw_fail_before_last = any(status != "pass" for status in statuses[:-1])
        final_status = statuses[-1]
        final_reason = str(entries[-1].get("reason") or "unknown").strip() or "unknown"

        flaky_hint = None
        flaky_context = None
        if final_status == "pass" and saw_fail_before_last:
            first_failed_attempt = next(
                (entry["attempt"] for entry in entries if entry["status"] != "pass"),
                entries[0]["attempt"],
            )
            flaky_hint = f"failed before final pass (failed on attempt {first_failed_attempt}, recovered on attempt {entries[-1]['attempt']})"
            flaky_context = {
                "first_failed_attempt": first_failed_attempt,
                "recovered_on_attempt": entries[-1]["attempt"],
                "build_context": build_context,
            }

        tests.append(
            {
                "name": name,
                "final_status": final_status,
                "final_reason": final_reason,
                "attempts": entries,
                "flaky_hint": flaky_hint,
                "flaky_context": flaky_context,
            }
        )

    return tests


def _build_summary_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    retry_policy = report.get("retry_policy", {})
    build_context = report.get("build_context", {})

    run_id = build_context.get("run_id") or "n/a"
    run_attempt = build_context.get("run_attempt") or "n/a"
    run_url = build_context.get("run_url") or "n/a"

    lines = [
        "## dev-smoke-required Retry Summary",
        "",
        f"- Final status: **{report.get('status', 'unknown')}**",
        f"- Retry policy: `max_retries={retry_policy.get('max_retries')}`, `max_attempts={retry_policy.get('max_attempts')}`, `retry_delay_seconds={retry_policy.get('retry_delay_seconds')}`",
        f"- Deterministic seed: `{report.get('smoke_test_seed') or 'n/a'}`",
        f"- Build context: run_id=`{run_id}`, run_attempt=`{run_attempt}`",
        f"- Run URL: {run_url}",
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
            final_reason = str(test.get("final_reason") or "unknown").strip() or "unknown"
            if str(test.get("final_status") or "").lower() != "pass":
                line += f" — cause: `{final_reason}`"
            if test.get("flaky_hint"):
                line += f" ⚠️ flaky: {test['flaky_hint']}"
                flaky_context = test.get("flaky_context") or {}
                flaky_build = flaky_context.get("build_context") or {}
                line += (
                    f" [run_id={flaky_build.get('run_id') or 'n/a'}, "
                    f"run_attempt={flaky_build.get('run_attempt') or 'n/a'}]"
                )
            lines.append(line)

    failed_checks_final = report.get("failed_checks_final") or []
    if failed_checks_final:
        lines.extend(["", "### Failed checks (final attempt)"])
        for entry in failed_checks_final:
            name = str(entry.get("name") or "unnamed-check").strip() or "unnamed-check"
            reason = str(entry.get("reason") or "unknown").strip() or "unknown"
            lines.append(f"- `{name}` — cause: `{reason}`")

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
        "--max-retries",
        default=None,
        help="Override max retries (defaults to DEV_SMOKE_MAX_RETRIES or 1)",
    )
    parser.add_argument(
        "--max-attempts",
        default=None,
        help="Legacy override for attempts (defaults to DEV_SMOKE_MAX_ATTEMPTS or 2)",
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
        max_attempts, max_retries = _resolve_retry_policy(args)
        retry_delay_seconds = _parse_non_negative_float(
            args.retry_delay_seconds or os.environ.get("DEV_SMOKE_RETRY_DELAY_SECONDS", "5"),
            "--retry-delay-seconds/DEV_SMOKE_RETRY_DELAY_SECONDS",
        )
        smoke_test_seed = _resolve_smoke_test_seed()
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

    build_context = _build_ci_context()
    tests = _aggregate_tests(attempts, build_context=build_context)
    retried_checks = sum(1 for test in tests if len(test.get("attempts", [])) > 1)
    flaky_candidates = sum(1 for test in tests if test.get("flaky_hint"))

    status = "pass" if last.exit_code == 0 else "fail"
    reason = "ok" if last.exit_code == 0 else "retries_exhausted"
    failed_checks_final = last.failed_check_details

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reason": reason,
        "failed_checks_final": failed_checks_final,
        "smoke_test_seed": smoke_test_seed or None,
        "retry_policy": {
            "max_retries": max_retries,
            "max_attempts": max_attempts,
            "retry_delay_seconds": retry_delay_seconds,
        },
        "build_context": build_context,
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
                "failed_check_details": attempt.failed_check_details,
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
