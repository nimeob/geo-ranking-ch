from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "gui-dev-live-full-regression.yml"


def test_full_regression_workflow_uses_preflight_with_artifact_visible_blocker_output() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    assert "base_url:" in content
    assert "fallback_login_start_on_missing_creds:" in content
    assert "DEV_UI_BASE_URL: ${{ inputs.base_url }}" in content
    assert "run: ./scripts/smoke/validate_gui_live_auth_analyze_secrets.sh" in content
    assert "if: ${{ inputs.fallback_login_start_on_missing_creds != true }}" in content
    assert 'cmd=(node scripts/run_dev_ui_live_full_regression.mjs --base-url "${{ inputs.base_url }}")' in content
    assert "cmd+=(--fallback-login-start)" in content
    assert "DEV_UI_SMOKE_RUN_ID: ${{ github.run_number }}-${{ github.run_attempt }}" in content
    assert "DEV_UI_SMOKE_WORKFLOW_NAME: gui-dev-live-full-regression" in content
    assert "DEV_UI_SMOKE_BLOCKER_PREFIX: dev-ui-full-regression-blocked" in content
    assert "DEV_UI_SMOKE_BLOCKER_DIR: artifacts/dev-ui-full/latest" in content
    assert "artifacts/dev-ui-full/latest/**" in content
