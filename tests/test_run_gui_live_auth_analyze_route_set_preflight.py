from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "run_gui_live_auth_analyze_route_set.sh"


def test_route_set_runner_fails_fast_on_missing_secrets_without_route_fanout(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["GITHUB_RUN_ID"] = "98765"
    env["GITHUB_RUN_ATTEMPT"] = "4"
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)

    proc = subprocess.run(
        [str(SCRIPT)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert "route 1/8" not in proc.stdout
    assert "route 1/8" not in proc.stderr

    blocked_file = blocker_dir / "dev-ui-auth-analyze-smoke-blocked-98765-4.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["reason"] == "missing_required_github_secrets"
    assert payload["missing"] == ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]
