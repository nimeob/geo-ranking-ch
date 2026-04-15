from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_smoke_bundle.sh"


def test_dev_smoke_bundle_help_exits_without_running_steps() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0
    assert "Usage: scripts/run_dev_smoke_bundle.sh" in proc.stdout
    assert "[dev:smoke] lint: start" not in proc.stdout
    assert "[dev:smoke] lint: start" not in proc.stderr


def test_dev_smoke_bundle_rejects_unknown_option() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--definitely-unknown"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Unknown option" in proc.stderr
    assert "Usage:" in proc.stderr


def test_dev_smoke_bundle_rejects_empty_step_selection() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--skip-lint", "--skip-typecheck", "--skip-smoke"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "no steps selected" in proc.stderr
    assert "Usage:" in proc.stderr


def test_dev_smoke_bundle_rejects_unknown_only_step() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--only", "lint,definitely-not-a-step"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Unsupported step in --only" in proc.stderr
    assert "supported values are lint,typecheck,smoke" in proc.stderr


def test_dev_smoke_bundle_rejects_short_flag_as_missing_only_value() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--only", "-h"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing value for --only" in proc.stderr
    assert "Usage:" in proc.stderr
