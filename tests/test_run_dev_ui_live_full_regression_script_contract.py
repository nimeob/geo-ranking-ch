from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_ui_live_full_regression.mjs"


def test_wait_for_function_uses_options_as_third_argument() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert 'const el = document.getElementById("phase-pill");' in content
    assert '/success/i.test(String(el.textContent || ""));' in content

    assert 'const el = document.getElementById("status");' in content
    assert '/Status:\\s*(loaded|success|ok)/i.test(String(el.textContent || ""));' in content

    # Regression guard: keep Playwright waitForFunction options as 3rd arg
    assert content.count('}, undefined, { timeout: MAX_WAIT_MS });') >= 2


def test_auth_me_fetch_uses_ui_base_origin_not_current_page_origin() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert 'targetUrl: new URL("/auth/me", baseOrigin).toString()' in content
    assert "async function waitForLoggedOutState(page, timeoutMs)" in content
    assert "const logoutState = await waitForLoggedOutState(page, LOGOUT_SETTLE_MS);" in content


def test_result_tabs_keyboard_navigation_guard_present() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "async function waitForActiveResultTab(page, tabKey, timeoutMs)" in content
    assert 'await overviewTabButton.press("ArrowRight");' in content
    assert 'await locationTabButton.press("End");' in content
    assert 'await rawTabButton.press("Home");' in content
    assert '"result_tabs_keyboard_navigation"' in content
