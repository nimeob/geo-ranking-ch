from __future__ import annotations

import json
import os
import subprocess
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


def test_script_uses_dynamic_playwright_import_with_actionable_hint() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "import { chromium } from 'playwright';" not in content
    assert "async function loadChromium()" in content
    assert "await import('playwright')" in content
    assert "npx playwright install --with-deps chromium" in content


def test_missing_credentials_emit_json_evidence_even_without_playwright(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-missing-creds"

    result = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1

    evidence_files = sorted((tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json"))
    assert evidence_files, f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["error"]["name"] == "Error"
    assert "Fehlende Credentials" in payload["error"]["message"]
