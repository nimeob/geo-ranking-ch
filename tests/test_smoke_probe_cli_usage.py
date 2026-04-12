from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_BIN = shutil.which("node")


@pytest.mark.skipif(NODE_BIN is None, reason="node runtime fehlt")
@pytest.mark.parametrize(
    ("script_rel", "required_flag", "usage_prefix"),
    [
        (
            "scripts/smoke/run_jobs_filter_search_e2e_probe.mjs",
            "--jobs-url",
            "Usage: node scripts/smoke/run_jobs_filter_search_e2e_probe.mjs",
        ),
        (
            "scripts/smoke/run_result_tabs_keyboard_probe.mjs",
            "--result-url",
            "Usage: node scripts/smoke/run_result_tabs_keyboard_probe.mjs",
        ),
    ],
)
def test_smoke_probe_help_contract(script_rel: str, required_flag: str, usage_prefix: str) -> None:
    script = REPO_ROOT / script_rel
    assert script.is_file(), f"Probe-Skript fehlt: {script_rel}"

    help_run = subprocess.run(
        [str(NODE_BIN), str(script), "--help"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert help_run.returncode == 0
    assert usage_prefix in help_run.stdout
    assert required_flag in help_run.stdout

    missing_required = subprocess.run(
        [str(NODE_BIN), str(script)],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert missing_required.returncode == 2
    assert f"missing {required_flag}" in missing_required.stderr
    assert usage_prefix in missing_required.stderr
    assert "    at " not in missing_required.stderr

    unknown_option = subprocess.run(
        [str(NODE_BIN), str(script), "--unknown-option"],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert unknown_option.returncode == 2
    assert "unknown option: --unknown-option" in unknown_option.stderr
    assert usage_prefix in unknown_option.stderr
    assert "    at " not in unknown_option.stderr
