from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "gui-dev-live-auth-analyze-smoke.yml"
ROUTE_SET_SCRIPT = (
    REPO_ROOT / "scripts" / "smoke" / "run_gui_live_auth_analyze_route_set.sh"
)
ROUTE_HELPER = REPO_ROOT / "scripts" / "smoke" / "gui_smoke_routes.sh"


def test_workflow_runs_single_job_route_set_with_shared_artifact_upload() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    assert "strategy:" not in content
    assert "Run DEV live UI auth+analyze smoke route set" in content
    assert "cmd=(./scripts/smoke/run_gui_live_auth_analyze_route_set.sh)" in content
    assert "inputs:" in content
    assert "routes:" in content
    assert "route_presets:" in content
    assert "timeout_ms:" in content
    assert "fallback_login_start_on_preflight_fail:" in content
    assert (
        "inputs.routes und inputs.route_presets dürfen nicht gleichzeitig gesetzt werden"
        in content
    )
    assert "gui-dev-live-auth-analyze-smoke-artifacts" in content
    assert (
        "gui-dev-live-auth-analyze-smoke-artifacts-${{ matrix.path_slug }}"
        not in content
    )


def test_route_set_script_uses_shared_route_helper_and_route_specific_run_ids() -> None:
    content = ROUTE_SET_SCRIPT.read_text(encoding="utf-8")

    assert 'source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"' in content
    assert "GUI_SMOKE_ROUTES" in content
    assert 'DEV_UI_SMOKE_GUI_PATH="${route}"' in content
    assert 'DEV_UI_SMOKE_RUN_ID="${run_id}"' in content
    assert 'run_id="${base_run_id}-${ordinal}"' in content
    assert "--fallback-login-start-on-preflight-fail" in content
    assert "DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_PREFLIGHT_FAIL" in content
    assert "run_login_start_smoke_bundle.sh" in content


def test_shared_route_helper_contains_required_gui_paths() -> None:
    content = ROUTE_HELPER.read_text(encoding="utf-8")

    assert '"/"' in content
    assert '"/gui"' in content
    assert '"/gui/history"' in content
    assert '"/gui?view=trace&request_id=req-smoke"' in content
    assert '"/history"' in content
    assert '"/gui/jobs"' in content
    assert '"/gui/jobs?source=smoke"' in content
    assert '"/jobs"' in content
    assert '"/jobs?source=smoke"' in content
    assert '"/gui/jobs/demo-job"' in content
    assert '"/jobs/demo-job"' in content
    assert '"/jobs/demo-job?source=smoke"' in content
    assert '"/gui/jobs/demo-job?source=smoke"' in content
    assert '"/results"' in content
    assert '"/results/demo-result"' in content
    assert '"/gui/results"' in content
    assert '"/results/demo-result?tab=raw&source=smoke"' in content
    assert '"/gui/results/demo-result"' in content
    assert '"/gui/results/demo-result?tab=raw&source=smoke"' in content
