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
    for key in ("DEV_UI_SMOKE_RUN_ID", "GITHUB_RUN_ID", "GITHUB_RUN_NUMBER", "GITHUB_RUN_ATTEMPT"):
        merged_env.pop(key, None)
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
    blocked_file = tmp_path / "reports" / "evidence" / "dev-ui-auth-analyze-smoke-blocked-4242-1.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["blocked"] is True
    assert payload["reason"] == "missing_required_github_secrets"
    assert payload["run_id"] == "4242-1"
    assert payload["required"] == ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]
    assert payload["missing"] == ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]
    assert payload["next_step"].startswith("Set both repository secrets")
    fallback = payload["fallback_login_start_smoke"]
    assert fallback["base_url"] == "https://www.dev.georanking.ch"
    assert fallback["env_name"] == "dev"
    assert "run_login_start_smoke_bundle.sh" in fallback["command"]


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
    blocked_file = tmp_path / "reports" / "evidence" / "dev-ui-auth-analyze-smoke-blocked-7331-1.json"
    assert not blocked_file.exists()
    assert "required secrets present" in proc.stdout


def test_preflight_prefers_github_run_number_and_attempt_when_run_id_is_missing(tmp_path: Path) -> None:
    proc = _run(
        tmp_path,
        {
            "GITHUB_RUN_NUMBER": "77",
            "GITHUB_RUN_ATTEMPT": "3",
        },
    )

    assert proc.returncode == 1
    blocked_file = tmp_path / "reports" / "evidence" / "dev-ui-auth-analyze-smoke-blocked-77-3.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    assert payload["run_id"] == "77-3"


def test_preflight_supports_custom_blocker_target_and_workflow_name(tmp_path: Path) -> None:
    proc = _run(
        tmp_path,
        {
            "GITHUB_RUN_NUMBER": "12",
            "GITHUB_RUN_ATTEMPT": "2",
            "DEV_UI_SMOKE_WORKFLOW_NAME": "gui-dev-live-full-regression",
            "DEV_UI_SMOKE_BLOCKER_PREFIX": "dev-ui-full-regression-blocked",
            "DEV_UI_SMOKE_BLOCKER_DIR": "artifacts/dev-ui-full/latest",
        },
    )

    assert proc.returncode == 1
    blocked_file = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-blocked-12-2.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    assert payload["run_id"] == "12-2"
    assert payload["workflow"] == "gui-dev-live-full-regression"
    assert payload["next_step"] == "Set both repository secrets and re-run gui-dev-live-full-regression workflow."
    assert payload["fallback_login_start_smoke"]["env_name"] == "dev"


def test_preflight_uses_staging_fallback_hint_when_base_url_contains_staging(tmp_path: Path) -> None:
    proc = _run(
        tmp_path,
        {
            "GITHUB_RUN_ID": "555",
            "DEV_UI_BASE_URL": "https://www.staging.georanking.ch",
        },
    )

    assert proc.returncode == 1
    blocked_file = tmp_path / "reports" / "evidence" / "dev-ui-auth-analyze-smoke-blocked-555-1.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    fallback = payload["fallback_login_start_smoke"]
    assert fallback["base_url"] == "https://www.staging.georanking.ch"
    assert fallback["env_name"] == "staging"
    assert fallback["command"].endswith("--env-name staging")


def test_preflight_canonicalizes_legacy_dev_non_www_base_url_in_fallback_hint(
    tmp_path: Path,
) -> None:
    proc = _run(
        tmp_path,
        {
            "GITHUB_RUN_ID": "778",
            "DEV_UI_BASE_URL": "https://dev.geo-ranking.ch.",
        },
    )

    assert proc.returncode == 1
    blocked_file = tmp_path / "reports" / "evidence" / "dev-ui-auth-analyze-smoke-blocked-778-1.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    fallback = payload["fallback_login_start_smoke"]
    assert fallback["base_url"] == "https://www.dev.geo-ranking.ch"
    assert fallback["env_name"] == "dev"
    assert (
        fallback["command"]
        == "./scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.geo-ranking.ch --env-name dev"
    )


def test_workflow_runs_route_set_and_uploads_blocker_artifact() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "dev-ui-auth-analyze-smoke-blocked-*.json" in content
    assert "./scripts/smoke/run_gui_live_auth_analyze_route_set.sh" in content
    assert "fallback_login_start_on_preflight_fail" in content
    assert "route_presets" in content
