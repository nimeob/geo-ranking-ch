from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "validate_gui_live_auth_analyze_secrets.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "gui-dev-live-auth-analyze-smoke.yml"


def _run(tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(
        [str(SCRIPT)],
        cwd=str(tmp_path),
        env=merged_env,
        capture_output=True,
        text=True,
    )


def test_preflight_writes_blocker_evidence_when_secrets_are_missing(tmp_path: Path) -> None:
    proc = _run(tmp_path, {"GITHUB_RUN_ID": "4242"})

    assert proc.returncode == 1
    blocked_file = tmp_path / "reports" / "evidence" / "dev-ui-auth-analyze-smoke-blocked-4242.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["blocked"] is True
    assert payload["reason"] == "missing_required_github_secrets"
    assert payload["required"] == ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]
    assert payload["missing"] == ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]
    assert payload["next_step"].startswith("Set both repository secrets")


def test_preflight_reports_exactly_which_secret_is_missing(tmp_path: Path) -> None:
    proc = _run(
        tmp_path,
        {
            "DEV_UI_SMOKE_RUN_ID": " 9001 ",
            "DEV_UI_SMOKE_USERNAME": "smoke-user",
            "DEV_UI_SMOKE_PASSWORD": "   ",
        },
    )

    assert proc.returncode == 1
    blocked_file = tmp_path / "reports" / "evidence" / "dev-ui-auth-analyze-smoke-blocked-9001.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    assert payload["run_id"] == "9001"
    assert payload["missing"] == ["DEV_UI_SMOKE_PASSWORD"]


def test_preflight_passes_when_all_required_secrets_exist(tmp_path: Path) -> None:
    proc = _run(
        tmp_path,
        {
            "GITHUB_RUN_ID": "7331",
            "DEV_UI_SMOKE_USERNAME": "smoke-user",
            "DEV_UI_SMOKE_PASSWORD": "super-secret",
        },
    )

    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    blocked_file = tmp_path / "reports" / "evidence" / "dev-ui-auth-analyze-smoke-blocked-7331.json"
    assert not blocked_file.exists()
    assert "required secrets present" in proc.stdout


def test_workflow_uses_preflight_script_and_uploads_blocker_artifact() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "run: ./scripts/smoke/validate_gui_live_auth_analyze_secrets.sh" in content
    assert "dev-ui-auth-analyze-smoke-blocked-*.json" in content
    assert "DEV_UI_SMOKE_RUN_ID: ${{ github.run_number }}-${{ github.run_attempt }}" in content
