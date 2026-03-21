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
