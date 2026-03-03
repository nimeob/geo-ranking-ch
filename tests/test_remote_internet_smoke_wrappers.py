from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _assert_executable(path: Path) -> None:
    assert path.exists(), f"missing: {path}"
    mode = path.stat().st_mode
    assert (mode & stat.S_IXUSR) != 0, f"not executable: {path}"


def test_smoke_wrapper_scripts_exist_and_are_executable() -> None:
    bash_scripts = [
        REPO_ROOT / "scripts" / "run_remote_async_jobs_smoketest.sh",
        REPO_ROOT / "scripts" / "run_staging_api_smoketest.sh",
        REPO_ROOT / "scripts" / "run_staging_async_jobs_smoketest.sh",
        REPO_ROOT / "scripts" / "run_prod_api_smoketest.sh",
        REPO_ROOT / "scripts" / "run_prod_async_jobs_smoketest.sh",
    ]
    for script in bash_scripts:
        _assert_executable(script)
        first_line = script.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("#!/usr/bin/env bash")

    python_entrypoint = REPO_ROOT / "scripts" / "run_deploy_smoke.py"
    _assert_executable(python_entrypoint)
    first_line = python_entrypoint.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!/usr/bin/env python3")


def test_smoke_wrappers_fail_fast_without_required_env() -> None:
    scripts = [
        (REPO_ROOT / "scripts" / "run_remote_async_jobs_smoketest.sh", "Missing DEV_BASE_URL"),
        (REPO_ROOT / "scripts" / "run_staging_api_smoketest.sh", "Missing STAGING_BASE_URL"),
        (REPO_ROOT / "scripts" / "run_staging_async_jobs_smoketest.sh", "Missing STAGING_BASE_URL"),
        (REPO_ROOT / "scripts" / "run_prod_api_smoketest.sh", "Missing PROD_BASE_URL"),
        (REPO_ROOT / "scripts" / "run_prod_async_jobs_smoketest.sh", "Missing PROD_BASE_URL"),
    ]

    for script, expected in scripts:
        proc = subprocess.run(
            [str(script)],
            cwd=str(REPO_ROOT),
            env={"PATH": os.environ.get("PATH", "")},
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 2, (script, proc.returncode, proc.stdout, proc.stderr)
        combined = (proc.stdout + proc.stderr).strip()
        assert expected in combined


def test_environment_wrappers_delegate_to_unified_runner() -> None:
    expected_fragments = {
        REPO_ROOT / "scripts" / "run_staging_api_smoketest.sh": "run_deploy_smoke.py --profile deploy --target staging --flow sync",
        REPO_ROOT / "scripts" / "run_staging_async_jobs_smoketest.sh": "run_deploy_smoke.py --profile deploy --target staging --flow async",
        REPO_ROOT / "scripts" / "run_prod_api_smoketest.sh": "run_deploy_smoke.py --profile deploy --target prod --flow sync",
        REPO_ROOT / "scripts" / "run_prod_async_jobs_smoketest.sh": "run_deploy_smoke.py --profile deploy --target prod --flow async",
    }

    for script_path, expected in expected_fragments.items():
        content = script_path.read_text(encoding="utf-8")
        assert expected in content
