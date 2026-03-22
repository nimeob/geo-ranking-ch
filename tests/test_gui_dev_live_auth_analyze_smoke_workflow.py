from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "gui-dev-live-auth-analyze-smoke.yml"


def test_workflow_runs_deeplink_matrix_serially_with_route_specific_artifacts() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    assert "strategy:" in content
    assert "max-parallel: 1" in content
    assert "gui_path: /gui" in content
    assert "gui_path: /gui/history" in content
    assert "gui_path: /gui/jobs" in content
    assert "DEV_UI_SMOKE_GUI_PATH: ${{ matrix.gui_path }}" in content
    assert (
        "DEV_UI_SMOKE_RUN_ID: ${{ github.run_number }}-${{ github.run_attempt }}-${{ matrix.path_ordinal }}"
        in content
    )
    assert "Run DEV live UI auth+analyze smoke (${{ matrix.gui_path }})" in content
    assert (
        "gui-dev-live-auth-analyze-smoke-artifacts-${{ matrix.path_slug }}" in content
    )
