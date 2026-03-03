#!/usr/bin/env python3
"""Unified smoke-runner entry point with PR/Deploy/Nightly profiles.

Issue: #991
Issue: #992 (JSON schema/classification alignment)

This runner consolidates smoke execution routing and keeps legacy wrappers as
thin profile selectors.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "deploy-smoke-report/v1"
ENTRYPOINT_RUNNER = "deploy-smoke-entrypoint"


@dataclass(frozen=True)
class PlannedCommand:
    name: str
    command: list[str]
    env: dict[str, str]
    classification: str


def _pick_env(environ: Mapping[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = (environ.get(key) or "").strip()
        if value:
            return value
    return ""


def _resolve_target_config(target: str, environ: Mapping[str, str]) -> tuple[str, str, dict[str, str], dict[str, str]]:
    target_normalized = target.strip().lower()

    if target_normalized == "staging":
        base_url = _pick_env(environ, ("STAGING_BASE_URL", "SERVICE_API_BASE_URL"))
        token = _pick_env(environ, ("STAGING_API_AUTH_TOKEN", "SERVICE_API_AUTH_TOKEN"))
        if not base_url:
            raise ValueError(
                "Missing STAGING_BASE_URL (or SERVICE_API_BASE_URL) for deploy/nightly smoke target 'staging'."
            )
        sync_defaults = {"SMOKE_OUTPUT_JSON": "artifacts/staging-smoke-analyze.json"}
        async_defaults = {"ASYNC_SMOKE_OUTPUT_JSON": "artifacts/staging-smoke-async-jobs.json"}
        return base_url, token, sync_defaults, async_defaults

    if target_normalized == "prod":
        base_url = _pick_env(environ, ("PROD_BASE_URL", "SERVICE_API_BASE_URL"))
        token = _pick_env(environ, ("PROD_API_AUTH_TOKEN", "SERVICE_API_AUTH_TOKEN"))
        if not base_url:
            raise ValueError(
                "Missing PROD_BASE_URL (or SERVICE_API_BASE_URL) for deploy/nightly smoke target 'prod'."
            )
        sync_defaults = {"SMOKE_OUTPUT_JSON": "artifacts/prod-smoke-analyze.json"}
        async_defaults = {"ASYNC_SMOKE_OUTPUT_JSON": "artifacts/prod-smoke-async-jobs.json"}
        return base_url, token, sync_defaults, async_defaults

    if target_normalized in {"dev", "remote"}:
        base_url = _pick_env(environ, ("DEV_BASE_URL", "SERVICE_API_BASE_URL"))
        token = _pick_env(environ, ("DEV_API_AUTH_TOKEN", "SERVICE_API_AUTH_TOKEN"))
        if not base_url:
            raise ValueError(
                "Missing DEV_BASE_URL (or SERVICE_API_BASE_URL) for deploy/nightly smoke target 'dev|remote'."
            )
        return base_url, token, {}, {}

    raise ValueError("Invalid --target. Allowed values: dev, remote, staging, prod.")


def _classification_for_profile(profile: str) -> str:
    if profile == "nightly":
        return "informational"
    return "must-pass"


def _plan_commands(args: argparse.Namespace, environ: Mapping[str, str]) -> list[PlannedCommand]:
    profile = args.profile
    flow = args.flow
    target = args.target
    classification = _classification_for_profile(profile)

    if profile == "pr":
        if target is not None:
            raise ValueError("--target is not used with --profile pr.")
        if flow not in {None, "sync"}:
            raise ValueError("--profile pr only supports --flow sync (or omitted).")
        return [
            PlannedCommand(
                name="pr-split-smoke",
                command=["./scripts/check_bl334_split_smokes.sh"],
                env={},
                classification=classification,
            )
        ]

    if profile == "deploy":
        if not target:
            raise ValueError("--profile deploy requires --target (dev|remote|staging|prod).")
        normalized_flow = flow or "sync"
    else:
        # nightly
        normalized_flow = flow or "both"
        target = target or "dev"

    if normalized_flow not in {"sync", "async", "both"}:
        raise ValueError("Invalid --flow. Allowed values: sync, async, both.")

    base_url, token, sync_defaults, async_defaults = _resolve_target_config(target, environ)

    planned: list[PlannedCommand] = []

    if normalized_flow in {"sync", "both"}:
        env = {"DEV_BASE_URL": base_url}
        if token:
            env["DEV_API_AUTH_TOKEN"] = token
        if "SMOKE_OUTPUT_JSON" not in environ and sync_defaults:
            env.update(sync_defaults)
        if "SMOKE_CLASSIFICATION" not in environ:
            env["SMOKE_CLASSIFICATION"] = classification
        planned.append(
            PlannedCommand(
                name=f"{profile}-{target}-sync",
                command=["./scripts/run_remote_api_smoketest.sh"],
                env=env,
                classification=classification,
            )
        )

    if normalized_flow in {"async", "both"}:
        env = {"DEV_BASE_URL": base_url}
        if token:
            env["DEV_API_AUTH_TOKEN"] = token
        if "ASYNC_SMOKE_OUTPUT_JSON" not in environ and async_defaults:
            env.update(async_defaults)
        if "ASYNC_SMOKE_CLASSIFICATION" not in environ:
            env["ASYNC_SMOKE_CLASSIFICATION"] = classification
        planned.append(
            PlannedCommand(
                name=f"{profile}-{target}-async",
                command=["./scripts/run_remote_async_jobs_smoketest.sh"],
                env=env,
                classification=classification,
            )
        )

    return planned


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unified smoke runner for PR/Deploy/Nightly profiles",
    )
    parser.add_argument("--profile", choices=("pr", "deploy", "nightly"), required=True)
    parser.add_argument("--target", choices=("dev", "remote", "staging", "prod"))
    parser.add_argument("--flow", choices=("sync", "async", "both"))
    parser.add_argument("--dry-run", action="store_true", help="Print resolved command plan and exit")
    parser.add_argument(
        "--output-json",
        help="Optional JSON report output path (schema: deploy-smoke-report/v1)",
    )
    return parser.parse_args(argv)


def _write_json_report(path: str, payload: dict[str, object]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    try:
        planned = _plan_commands(args, os.environ)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    started = datetime.now(timezone.utc)
    started_perf = time.perf_counter()

    if args.dry_run:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "runner": ENTRYPOINT_RUNNER,
            "profile": args.profile,
            "target": args.target,
            "flow": args.flow or ("sync" if args.profile == "deploy" else "both" if args.profile == "nightly" else "sync"),
            "classification": _classification_for_profile(args.profile),
            "status": "planned",
            "reason": "dry_run",
            "checks": [
                {
                    "name": item.name,
                    "command": item.command,
                    "env": item.env,
                    "classification": item.classification,
                    "status": "planned",
                }
                for item in planned
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if args.output_json:
            _write_json_report(args.output_json, payload)
        return 0

    checks: list[dict[str, object]] = []
    overall_status = "pass"
    overall_reason = "ok"
    failure_code = 0

    for item in planned:
        print(f"[deploy-smoke] running {item.name}: {' '.join(item.command)}")
        env = os.environ.copy()
        env.update(item.env)
        completed = subprocess.run(item.command, cwd=str(REPO_ROOT), env=env)
        item_status = "pass" if completed.returncode == 0 else "fail"
        checks.append(
            {
                "name": item.name,
                "classification": item.classification,
                "status": item_status,
                "exit_code": int(completed.returncode),
                "command": item.command,
            }
        )
        if completed.returncode != 0:
            print(
                f"[deploy-smoke] command failed ({item.name}) with exit={completed.returncode}",
                file=sys.stderr,
            )
            overall_status = "fail"
            overall_reason = "command_failed"
            failure_code = int(completed.returncode)
            break

    ended = datetime.now(timezone.utc)
    duration_seconds = round(time.perf_counter() - started_perf, 3)

    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "runner": ENTRYPOINT_RUNNER,
        "profile": args.profile,
        "target": args.target,
        "flow": args.flow or ("sync" if args.profile == "deploy" else "both" if args.profile == "nightly" else "sync"),
        "classification": _classification_for_profile(args.profile),
        "status": overall_status,
        "reason": overall_reason,
        "started_at_utc": started.isoformat().replace("+00:00", "Z"),
        "ended_at_utc": ended.isoformat().replace("+00:00", "Z"),
        "duration_seconds": duration_seconds,
        "checks": checks,
    }

    if args.output_json:
        _write_json_report(args.output_json, report)

    if failure_code != 0:
        return failure_code

    print("[deploy-smoke] all planned smoke commands passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
