#!/usr/bin/env python3
"""Unified smoke-runner entry point with PR/Deploy/Nightly profiles.

Issue: #991

This runner consolidates smoke execution routing and keeps legacy wrappers as
thin profile selectors.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PlannedCommand:
    name: str
    command: list[str]
    env: dict[str, str]


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


def _plan_commands(args: argparse.Namespace, environ: Mapping[str, str]) -> list[PlannedCommand]:
    profile = args.profile
    flow = args.flow
    target = args.target

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
        planned.append(
            PlannedCommand(
                name=f"{profile}-{target}-sync",
                command=["./scripts/run_remote_api_smoketest.sh"],
                env=env,
            )
        )

    if normalized_flow in {"async", "both"}:
        env = {"DEV_BASE_URL": base_url}
        if token:
            env["DEV_API_AUTH_TOKEN"] = token
        if "ASYNC_SMOKE_OUTPUT_JSON" not in environ and async_defaults:
            env.update(async_defaults)
        planned.append(
            PlannedCommand(
                name=f"{profile}-{target}-async",
                command=["./scripts/run_remote_async_jobs_smoketest.sh"],
                env=env,
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    try:
        planned = _plan_commands(args, os.environ)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        payload = [
            {
                "name": item.name,
                "command": item.command,
                "env": item.env,
            }
            for item in planned
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for item in planned:
        print(f"[deploy-smoke] running {item.name}: {' '.join(item.command)}")
        env = os.environ.copy()
        env.update(item.env)
        completed = subprocess.run(item.command, cwd=str(REPO_ROOT), env=env)
        if completed.returncode != 0:
            print(
                f"[deploy-smoke] command failed ({item.name}) with exit={completed.returncode}",
                file=sys.stderr,
            )
            return int(completed.returncode)

    print("[deploy-smoke] all planned smoke commands passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
