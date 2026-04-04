from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


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


def test_check_details_encode_observed_visibility_state() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "sampleVisibilitySignal" in content
    assert "maxVisibleStreak" in content
    assert "visibleCount" in content
    assert "timeline" in content
    assert "server_error_after_reload=${serverErrorAfterReload}" in content
    assert "query_visible=${queryVisible}" in content
    assert "mode_visible=${modeVisible}" in content
    assert "submit_visible=${submitVisible}" in content
    assert "server_error_visible_after_analyze=${serverErrorAfterAnalyze}" in content
    assert "error_box_visible_after_analyze=${errorBoxAfterAnalyze}" in content


def test_script_uses_dynamic_playwright_import_with_actionable_hint() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert 'import { chromium } from "playwright";' not in content
    assert "async function loadChromium()" in content
    assert 'await import("playwright")' in content
    assert "npx playwright install --with-deps chromium" in content


def test_help_flag_prints_usage_without_env_or_playwright(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_BASE_URL", None)
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    result = subprocess.run(
        ["node", str(SCRIPT), "--help"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage: node scripts/run_dev_ui_live_full_regression.mjs" in result.stdout
    assert "DEV_UI_BASE_URL" in result.stdout
    assert "DEV_UI_SMOKE_USERNAME" in result.stdout
    assert "DEV_UI_SMOKE_PASSWORD" in result.stdout
    assert result.stderr == ""


def test_missing_credentials_emit_evidence_even_before_browser_boot(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://www.dev.georanking.ch"
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract.json"
    env["DEV_UI_FULL_EVIDENCE_JSON"] = str(evidence_path)

    result = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert evidence_path.exists(), f"expected evidence file, got stdout={result.stdout!r} stderr={result.stderr!r}"

    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["error"] == "Missing DEV_UI_SMOKE_USERNAME"
    assert payload["checks"] == []

    assert "[dev-ui-full-regression] FAILED: Missing DEV_UI_SMOKE_USERNAME" in result.stderr
    assert "[dev-ui-full-regression] Evidence:" in result.stderr
    assert "[dev-ui-full-regression] HINT: Falls Live-Credentials fehlen" in result.stderr
    assert "run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev" in result.stderr


def test_missing_credentials_hint_canonicalizes_legacy_trailing_dot_base_url(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://dev.georanking.ch."
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-canonicalized.json"
    env["DEV_UI_FULL_EVIDENCE_JSON"] = str(evidence_path)

    result = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["baseUrl"] == "https://www.dev.georanking.ch"
    assert payload["requestedBaseUrl"] == "https://dev.georanking.ch."
    assert payload["baseUrlCanonicalized"] is True
    assert set(payload["baseUrlCanonicalizationReasons"]) >= {"trailing_dot", "legacy_dev_non_www"}
    assert "Canonicalized DEV_UI_BASE_URL 'https://dev.georanking.ch.' -> 'https://www.dev.georanking.ch'" in result.stderr
    assert "run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev" in result.stderr


@pytest.mark.parametrize(
    "base_url, expected_fragment",
    [
        ("dev.georanking.ch", "must be an absolute URL"),
        ("ftp://www.dev.georanking.ch", "unsupported protocol 'ftp:'"),
    ],
)
def test_invalid_base_url_emits_actionable_hint_and_error(
    tmp_path: Path,
    base_url: str,
    expected_fragment: str,
) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = base_url
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-invalid-base-url.json"
    env["DEV_UI_FULL_EVIDENCE_JSON"] = str(evidence_path)

    result = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["error"].startswith("Invalid DEV_UI_BASE_URL:")
    assert expected_fragment in payload["error"]
    assert "[dev-ui-full-regression] HINT: Setze DEV_UI_BASE_URL" in result.stderr
