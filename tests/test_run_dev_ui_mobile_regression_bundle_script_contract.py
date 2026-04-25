from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_BIN = shutil.which("node")
SCRIPT = REPO_ROOT / "scripts" / "run_dev_ui_mobile_regression_bundle.mjs"


@pytest.mark.skipif(NODE_BIN is None, reason="node runtime fehlt")
def test_help_exits_zero_and_prints_usage(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(NODE_BIN), str(SCRIPT), "--help"],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0
    assert "Usage: node scripts/run_dev_ui_mobile_regression_bundle.mjs" in result.stdout
    assert "--dry-run" in result.stdout


@pytest.mark.skipif(NODE_BIN is None, reason="node runtime fehlt")
def test_dry_run_writes_plan_json_with_expected_suite(tmp_path: Path) -> None:
    out_json = tmp_path / "bundle" / "dev-ui-mobile-regression.json"

    result = subprocess.run(
        [
            str(NODE_BIN),
            str(SCRIPT),
            "--dry-run",
            "--base-url",
            "https://dev.georanking.ch/gui",
            "--evidence-json",
            str(out_json),
            "--headless",
        ],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0
    assert out_json.exists()

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["dryRun"] is True
    assert payload["ok"] is True
    assert payload["target"]["baseUrl"] == "https://dev.georanking.ch/gui"

    step_ids = [step["id"] for step in payload["suite"]]
    assert step_ids == [
        "issue-1016-mobile-ux",
        "issue-981-mobile-e2e",
        "issue-1039-mobile-overflow",
        "issue-986-webkit",
    ]


@pytest.mark.skipif(NODE_BIN is None, reason="node runtime fehlt")
def test_dry_run_skip_webkit_removes_issue_986_step(tmp_path: Path) -> None:
    out_json = tmp_path / "bundle" / "dev-ui-mobile-regression-skip-webkit.json"

    result = subprocess.run(
        [
            str(NODE_BIN),
            str(SCRIPT),
            "--dry-run",
            "--skip-webkit",
            "--evidence-json",
            str(out_json),
        ],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(out_json.read_text(encoding="utf-8"))

    step_ids = [step["id"] for step in payload["suite"]]
    assert "issue-986-webkit" not in step_ids
    assert step_ids == [
        "issue-1016-mobile-ux",
        "issue-981-mobile-e2e",
        "issue-1039-mobile-overflow",
    ]


@pytest.mark.skipif(NODE_BIN is None, reason="node runtime fehlt")
def test_unknown_option_exits_with_usage(tmp_path: Path) -> None:
    result = subprocess.run(
        [str(NODE_BIN), str(SCRIPT), "--unknown-option"],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 2
    assert "Unknown option: --unknown-option" in result.stderr
    assert "Usage: node scripts/run_dev_ui_mobile_regression_bundle.mjs" in result.stderr
