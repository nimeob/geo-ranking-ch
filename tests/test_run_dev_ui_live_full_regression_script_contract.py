from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_ui_live_full_regression.mjs"


def test_wait_for_function_uses_options_as_third_argument() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert """await page.waitForFunction(() => {
      const el = document.getElementById(\"phase-pill\");
      return el && /success/i.test(String(el.textContent || \"\"));
    }, undefined, { timeout: MAX_WAIT_MS });""" in content

    assert """await page.waitForFunction(() => {
      const el = document.getElementById(\"status\");
      return el && /Status:\\s*(loaded|success|ok)/i.test(String(el.textContent || \"\"));
    }, undefined, { timeout: MAX_WAIT_MS });""" in content


def test_auth_me_fetch_uses_ui_base_origin_not_current_page_origin() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert 'targetUrl: new URL("/auth/me", baseOrigin).toString()' in content
    assert "async function waitForLoggedOutState(page, timeoutMs)" in content
    assert "const logoutState = await waitForLoggedOutState(page, LOGOUT_SETTLE_MS);" in content
