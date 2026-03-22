from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_ui_auth_analyze_smoke.mjs"


def test_wait_for_function_uses_options_as_third_argument() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "async function waitForTerminalUiSignal(page, timeout)" in content
    assert "reason: 'results_rows_rendered'" in content

    # Regression guard: Playwright waitForFunction options must stay in the 3rd argument.
    assert "  }, undefined, { timeout });" in content


def test_script_contains_analyze_shell_recovery_for_non_gui_default_paths() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "async function ensureAnalyzeShellReady(page, baseOrigin, timeout)" in content
    assert "strategy: 'menuitem_to_gui'" in content
    assert "strategy: 'direct_goto_gui'" in content
    assert "analyzeShellRecovery" in content


def test_script_tracks_post_login_target_path_and_keeps_legacy_check_alias() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "const expectedPostLoginPath = resolveCanonicalGuiSuccessor(guiPath);" in content
    assert "function resolveCanonicalGuiSuccessor(pathname)" in content
    assert "if (value === '/gui/jobs') return '/jobs';" in content
    assert "const loginReturnedToRequestedGuiPath =" in content
    assert "loginReturnedToRequestedGuiPath," in content
    assert "loginReturnedToGui: loginReturnedToRequestedGuiPath" in content
