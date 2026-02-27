#!/usr/bin/env python3
"""Run migrated OpenClaw automation jobs and persist reproducible reports.

This script is the execution anchor for BL-20.y.wp3 (#223).
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_ROOT = REPO_ROOT / "reports" / "automation"


@dataclass(frozen=True)
class JobSpec:
    description: str
    commands: tuple[tuple[str, ...], ...]


JOB_SPECS: dict[str, JobSpec] = {
    "contract-tests": JobSpec(
        description="Contract-/Field-Catalog Regression (ehemals contract-tests.yml)",
        commands=(
            ("python3", "scripts/validate_field_catalog.py"),
            (
                "python3",
                "-m",
                "pytest",
                "-q",
                "tests/test_api_contract_v1.py",
                "tests/test_api_field_catalog.py",
            ),
        ),
    ),
    "crawler-regression": JobSpec(
        description="Crawler-Regression (ehemals crawler-regression.yml)",
        commands=(("./scripts/check_crawler_regression.sh",),),
    ),
    "docs-quality": JobSpec(
        description="Docs-Qualitätsgate (ehemals docs-quality.yml)",
        commands=(("./scripts/check_docs_quality_gate.sh",),),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, choices=sorted(JOB_SPECS.keys()))
    parser.add_argument(
        "--reports-root",
        default=str(DEFAULT_REPORTS_ROOT),
        help="Root directory for automation reports (default: reports/automation)",
    )
    parser.add_argument(
        "--command-override",
        action="append",
        default=[],
        help="Optional command override(s), useful for tests. Can be repeated.",
    )
    parser.add_argument(
        "--timestamp",
        default=None,
        help="Optional UTC run timestamp as YYYYMMDDTHHMMSSZ (for deterministic runs/tests).",
    )
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=12000,
        help="Max chars per stdout/stderr block in markdown report.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write reports without executing commands.",
    )
    return parser.parse_args()


def now_utc() -> datetime:
    return datetime.now(UTC)


def format_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_run_id(explicit_timestamp: str | None) -> str:
    if explicit_timestamp:
        datetime.strptime(explicit_timestamp, "%Y%m%dT%H%M%SZ")
        return explicit_timestamp
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def trim_text(value: str, max_chars: int) -> str:
    if max_chars <= 0 or len(value) <= max_chars:
        return value
    omitted = len(value) - max_chars
    return f"{value[:max_chars]}\n\n...[truncated {omitted} chars]"


def render_markdown(report: dict, max_output_chars: int) -> str:
    lines: list[str] = []
    lines.append(f"# OpenClaw Automation Report — {report['job_id']}")
    lines.append("")
    lines.append(f"- Description: {report['description']}")
    lines.append(f"- Run ID: `{report['run_id']}`")
    lines.append(f"- Started: `{report['started_at']}`")
    lines.append(f"- Finished: `{report['finished_at']}`")
    lines.append(f"- Duration: `{report['duration_seconds']:.3f}s`")
    lines.append(f"- Status: **{report['status']}**")
    lines.append(f"- Exit code: `{report['exit_code']}`")
    lines.append("")
    lines.append("## Steps")

    for step in report["steps"]:
        lines.append("")
        lines.append(f"### Step {step['step_index']}: `{step['command']}`")
        lines.append(f"- Status: **{step['status']}**")
        lines.append(f"- Exit code: `{step['exit_code']}`")
        lines.append(f"- Duration: `{step['duration_seconds']:.3f}s`")

        stdout = trim_text(step.get("stdout", ""), max_output_chars)
        stderr = trim_text(step.get("stderr", ""), max_output_chars)

        lines.append("")
        lines.append("Stdout:")
        lines.append("```text")
        lines.append(stdout if stdout else "<empty>")
        lines.append("```")

        lines.append("")
        lines.append("Stderr:")
        lines.append("```text")
        lines.append(stderr if stderr else "<empty>")
        lines.append("```")

    lines.append("")
    return "\n".join(lines)


def run_command(command: Sequence[str], cwd: Path) -> dict:
    started = time.time()
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    ended = time.time()
    return {
        "started_at": format_utc(started),
        "finished_at": format_utc(ended),
        "duration_seconds": ended - started,
        "command": " ".join(shlex.quote(part) for part in command),
        "exit_code": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def resolve_commands(job: str, command_override: list[str]) -> list[list[str]]:
    if command_override:
        return [shlex.split(raw) for raw in command_override]
    return [list(cmd) for cmd in JOB_SPECS[job].commands]


def write_report_files(report: dict, markdown: str, reports_root: Path) -> tuple[Path, Path, Path, Path]:
    job_dir = reports_root / report["job_id"]
    history_dir = job_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    history_json = history_dir / f"{report['run_id']}.json"
    history_md = history_dir / f"{report['run_id']}.md"
    latest_json = job_dir / "latest.json"
    latest_md = job_dir / "latest.md"

    history_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    history_md.write_text(markdown, encoding="utf-8")

    shutil.copyfile(history_json, latest_json)
    shutil.copyfile(history_md, latest_md)

    return history_json, history_md, latest_json, latest_md


def main() -> int:
    args = parse_args()

    reports_root = Path(args.reports_root)
    run_id = resolve_run_id(args.timestamp)
    commands = resolve_commands(args.job, args.command_override)

    start = time.time()
    steps: list[dict] = []
    final_exit_code = 0

    if args.dry_run:
        for idx, command in enumerate(commands, start=1):
            cmd_str = " ".join(shlex.quote(part) for part in command)
            steps.append(
                {
                    "step_index": idx,
                    "command": cmd_str,
                    "started_at": format_utc(start),
                    "finished_at": format_utc(start),
                    "duration_seconds": 0.0,
                    "exit_code": 0,
                    "status": "skipped",
                    "stdout": "dry-run: command skipped",
                    "stderr": "",
                }
            )
    else:
        for idx, command in enumerate(commands, start=1):
            step = run_command(command, cwd=REPO_ROOT)
            step["step_index"] = idx
            steps.append(step)
            if step["exit_code"] != 0:
                final_exit_code = step["exit_code"]
                break

    end = time.time()

    if final_exit_code == 0 and not args.dry_run:
        status = "pass"
    elif args.dry_run:
        status = "dry-run"
    else:
        status = "fail"

    report = {
        "job_id": args.job,
        "description": JOB_SPECS[args.job].description,
        "run_id": run_id,
        "started_at": format_utc(start),
        "finished_at": format_utc(end),
        "duration_seconds": end - start,
        "status": status,
        "exit_code": final_exit_code,
        "command_override": args.command_override,
        "steps": steps,
    }

    markdown = render_markdown(report, max_output_chars=args.max_output_chars)
    history_json, history_md, latest_json, latest_md = write_report_files(report, markdown, reports_root=reports_root)

    print(
        json.dumps(
            {
                "job_id": args.job,
                "status": report["status"],
                "exit_code": report["exit_code"],
                "history_json": str(history_json),
                "history_md": str(history_md),
                "latest_json": str(latest_json),
                "latest_md": str(latest_md),
            },
            ensure_ascii=False,
        )
    )

    return final_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
