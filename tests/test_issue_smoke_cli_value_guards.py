from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
NODE_BIN = shutil.which("node")


@pytest.mark.skipif(NODE_BIN is None, reason="node runtime fehlt")
@pytest.mark.parametrize(
    ("script_rel", "flag"),
    [
        ("scripts/run_issue_981_mobile_smoke.mjs", "--base-url"),
        ("scripts/run_issue_986_webkit_smoke.mjs", "--base-url"),
        ("scripts/run_issue_1016_mobile_ux_smoke.mjs", "--base-url"),
        ("scripts/run_issue_1039_mobile_overflow_smoke.cjs", "--base-url"),
        ("scripts/run_issue_1142_mobile_table_overflow_smoke.cjs", "--baseline-ref"),
    ],
)
def test_issue_smoke_cli_rejects_missing_values(script_rel: str, flag: str) -> None:
    script = REPO_ROOT / script_rel
    assert script.is_file(), f"Script fehlt: {script_rel}"

    for argv in ([flag, "-h"], [f"{flag}="], [f"{flag}=   "]):
        result = subprocess.run(
            [str(NODE_BIN), str(script), *argv],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=25,
            check=False,
        )

        assert result.returncode == 2, (
            f"expected CLI usage failure for {script_rel} argv={argv}, "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert f"Missing value for {flag}" in result.stderr
        assert "Usage: node " in result.stderr
