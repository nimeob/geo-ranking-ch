from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_BIN = shutil.which("node")


@pytest.mark.skipif(NODE_BIN is None, reason="node runtime fehlt")
@pytest.mark.parametrize(
    ("script_rel", "usage_prefix", "help_marker"),
    [
        (
            "scripts/run_issue_1016_mobile_ux_smoke.mjs",
            "Usage: node scripts/run_issue_1016_mobile_ux_smoke.mjs",
            "Issue #1016 Mobile-UX-Smoke.",
        ),
        (
            "scripts/run_issue_981_mobile_smoke.mjs",
            "Usage: node scripts/run_issue_981_mobile_smoke.mjs",
            "Issue #981 Mobile E2E Smoke.",
        ),
        (
            "scripts/run_issue_986_webkit_smoke.mjs",
            "Usage: node scripts/run_issue_986_webkit_smoke.mjs",
            "Issue #986 WebKit Smoke.",
        ),
        (
            "scripts/run_issue_1039_mobile_overflow_smoke.cjs",
            "Usage: node scripts/run_issue_1039_mobile_overflow_smoke.cjs",
            "Issue #1039 Mobile Overflow Smoke.",
        ),
        (
            "scripts/run_issue_1142_mobile_table_overflow_smoke.cjs",
            "Usage: node scripts/run_issue_1142_mobile_table_overflow_smoke.cjs",
            "Issue #1142 Mobile Table Overflow Harness.",
        ),
    ],
)
def test_issue_smoke_help_exits_zero_without_side_effects(
    tmp_path: Path,
    script_rel: str,
    usage_prefix: str,
    help_marker: str,
) -> None:
    script = REPO_ROOT / script_rel
    assert script.is_file(), f"Smoke-Skript fehlt: {script_rel}"

    result = subprocess.run(
        [str(NODE_BIN), str(script), "--help"],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0
    assert usage_prefix in result.stdout
    assert help_marker in result.stdout

    evidence_root = tmp_path / "reports" / "evidence"
    assert not evidence_root.exists(), (
        f"--help darf keine Evidence erzeugen: stdout={result.stdout!r} stderr={result.stderr!r}"
    )


@pytest.mark.skipif(NODE_BIN is None, reason="node runtime fehlt")
@pytest.mark.parametrize(
    ("script_rel", "usage_prefix"),
    [
        (
            "scripts/run_issue_1016_mobile_ux_smoke.mjs",
            "Usage: node scripts/run_issue_1016_mobile_ux_smoke.mjs",
        ),
        (
            "scripts/run_issue_981_mobile_smoke.mjs",
            "Usage: node scripts/run_issue_981_mobile_smoke.mjs",
        ),
        (
            "scripts/run_issue_986_webkit_smoke.mjs",
            "Usage: node scripts/run_issue_986_webkit_smoke.mjs",
        ),
        (
            "scripts/run_issue_1039_mobile_overflow_smoke.cjs",
            "Usage: node scripts/run_issue_1039_mobile_overflow_smoke.cjs",
        ),
        (
            "scripts/run_issue_1142_mobile_table_overflow_smoke.cjs",
            "Usage: node scripts/run_issue_1142_mobile_table_overflow_smoke.cjs",
        ),
    ],
)
def test_issue_smoke_unknown_option_exits_with_usage_and_no_side_effects(
    tmp_path: Path,
    script_rel: str,
    usage_prefix: str,
) -> None:
    script = REPO_ROOT / script_rel
    assert script.is_file(), f"Smoke-Skript fehlt: {script_rel}"

    result = subprocess.run(
        [str(NODE_BIN), str(script), "--unknown-option"],
        cwd=str(tmp_path),
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 2
    assert "unknown_cli_args=--unknown-option" in result.stderr
    assert usage_prefix in result.stderr
    assert "    at " not in result.stderr

    evidence_root = tmp_path / "reports" / "evidence"
    assert not evidence_root.exists(), (
        f"Unknown CLI args dürfen keine Evidence erzeugen: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
