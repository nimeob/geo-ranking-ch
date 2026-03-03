from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_deploy_smoke.py"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = {"PATH": os.environ.get("PATH", "")}
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        env=merged_env,
    )


def test_pr_profile_dry_run_routes_to_split_smoke() -> None:
    proc = _run(["--profile", "pr", "--dry-run"])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload == [
        {
            "name": "pr-split-smoke",
            "command": ["./scripts/check_bl334_split_smokes.sh"],
            "env": {},
        }
    ]


def test_deploy_profile_requires_target() -> None:
    proc = _run(["--profile", "deploy", "--dry-run"])
    assert proc.returncode == 2
    assert "requires --target" in proc.stderr


def test_deploy_staging_sync_dry_run_uses_staging_env_defaults() -> None:
    proc = _run(
        ["--profile", "deploy", "--target", "staging", "--flow", "sync", "--dry-run"],
        env={
            "STAGING_BASE_URL": "https://api.staging.example.test",
            "STAGING_API_AUTH_TOKEN": "secret-token",
        },
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert len(payload) == 1
    planned = payload[0]
    assert planned["command"] == ["./scripts/run_remote_api_smoketest.sh"]
    assert planned["env"]["DEV_BASE_URL"] == "https://api.staging.example.test"
    assert planned["env"]["DEV_API_AUTH_TOKEN"] == "secret-token"
    assert planned["env"]["SMOKE_OUTPUT_JSON"] == "artifacts/staging-smoke-analyze.json"


def test_nightly_profile_defaults_to_dev_both_flows() -> None:
    proc = _run(
        ["--profile", "nightly", "--dry-run"],
        env={"DEV_BASE_URL": "https://api.dev.example.test"},
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert [item["command"] for item in payload] == [
        ["./scripts/run_remote_api_smoketest.sh"],
        ["./scripts/run_remote_async_jobs_smoketest.sh"],
    ]
    for item in payload:
        assert item["env"]["DEV_BASE_URL"] == "https://api.dev.example.test"
