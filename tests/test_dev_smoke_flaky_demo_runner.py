from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "dev_smoke_flaky_demo_runner.py"


def _run_demo(tmpdir: str) -> subprocess.CompletedProcess[str]:
    output_json = Path(tmpdir) / "demo.json"
    state_file = Path(tmpdir) / "state.txt"

    env = {"PATH": os.environ.get("PATH", "")}
    env["DEV_SMOKE_FLAKY_DEMO_STATE_FILE"] = str(state_file)

    return subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--profile",
            "pr",
            "--flow",
            "sync",
            "--output-json",
            str(output_json),
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        env=env,
    )


def test_demo_runner_fails_first_attempt_then_passes() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        first = _run_demo(tmpdir)
        assert first.returncode == 1

        second = _run_demo(tmpdir)
        assert second.returncode == 0

        payload = json.loads((Path(tmpdir) / "demo.json").read_text(encoding="utf-8"))
        assert payload["runner"] == "dev-smoke-flaky-demo"
        assert payload["checks"][0]["name"] == "flaky-demo-check"
        assert payload["checks"][0]["status"] == "pass"
