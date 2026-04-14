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
    assert "--run-id <token>" in result.stdout
    assert "DEV_UI_FULL_RUN_ID" in result.stdout
    assert "DEV_UI_SMOKE_RUN_ID" in result.stdout
    assert "DEV_UI_SMOKE_RUN_TOKEN" in result.stdout
    assert "--summary-json <path>" in result.stdout
    assert "--json-out <path>" in result.stdout
    assert "--out <path>" in result.stdout
    assert result.stderr == ""


def test_help_lists_full_and_legacy_fallback_env_aliases(tmp_path: Path) -> None:
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
    assert "DEV_UI_FULL_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1" in result.stdout
    assert "DEV_UI_FULL_FALLBACK_LOGIN_START_ON_PREFLIGHT_FAIL=1" in result.stdout
    assert "DEV_UI_FULL_ALLOW_LOGIN_START_FALLBACK=1" in result.stdout
    assert "DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1" in result.stdout
    assert "DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_PREFLIGHT_FAIL=1" in result.stdout
    assert "DEV_UI_SMOKE_ALLOW_LOGIN_START_FALLBACK=1" in result.stdout
    assert result.stderr == ""


def test_script_checks_legacy_preflight_fallback_env_aliases() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert '"DEV_UI_FULL_FALLBACK_LOGIN_START_ON_PREFLIGHT_FAIL"' in content
    assert '"DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_PREFLIGHT_FAIL"' in content


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


def test_cli_overrides_base_url_and_evidence_path_without_credentials(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_BASE_URL", None)
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract-cli.json"

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--base-url",
            "https://dev.example.test",
            "--evidence-json",
            str(evidence_path),
        ],
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
    assert payload["baseUrl"] == "https://dev.example.test"
    assert payload["error"] == "Missing DEV_UI_SMOKE_USERNAME"


@pytest.mark.parametrize("alias_flag", ["--out", "--summary-json", "--json-out"])
def test_cli_accepts_legacy_evidence_aliases(tmp_path: Path, alias_flag: str) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_BASE_URL", None)
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract-out-alias.json"

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--base-url",
            "https://dev.example.test",
            alias_flag,
            str(evidence_path),
        ],
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
    assert payload["baseUrl"] == "https://dev.example.test"
    assert payload["error"] == "Missing DEV_UI_SMOKE_USERNAME"


def test_cli_headful_override_is_reflected_in_failure_evidence(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://www.dev.georanking.ch"
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract-headful.json"
    env["DEV_UI_FULL_EVIDENCE_JSON"] = str(evidence_path)

    result = subprocess.run(
        ["node", str(SCRIPT), "--headful"],
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
    assert payload["headless"] is False
    assert payload["error"] == "Missing DEV_UI_SMOKE_USERNAME"


def test_unknown_cli_option_exits_with_usage_and_code_2(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_BASE_URL", None)
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    result = subprocess.run(
        ["node", str(SCRIPT), "--nope"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "[dev-ui-full-regression] ERROR Unknown option: --nope" in result.stderr
    assert "Usage: node scripts/run_dev_ui_live_full_regression.mjs [options]" in result.stdout


def test_script_resolves_paths_and_fallback_bundle_from_repo_root() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "const REPO_ROOT = path.resolve(SCRIPT_DIR, \"..\");" in content
    assert "const LOGIN_START_FALLBACK_SCRIPT = path.join(REPO_ROOT, \"scripts\", \"smoke\", \"run_login_start_smoke_bundle.sh\");" in content
    assert "const EVIDENCE_JSON_PATH = resolvePathAgainstRepoRoot(EVIDENCE_JSON);" in content
    assert "const SCREENSHOT_DIR_PATH = resolvePathAgainstRepoRoot(SCREENSHOT_DIR);" in content
    assert 'const FALLBACK_ARTIFACTS_BASE_DIR_PATH = path.join(path.dirname(EVIDENCE_JSON_PATH), "fallback-login-start", RUN_TOKEN);' in content
    assert "const result = spawnSync(LOGIN_START_FALLBACK_SCRIPT, args, {" in content
    assert "cwd: REPO_ROOT," in content
    assert '"--output-dir",' in content
    assert '"--summary-json",' in content
    assert "const outputDir = reserveUniqueDirectoryPath(FALLBACK_ARTIFACTS_BASE_DIR_PATH);" in content
    assert "const summaryJson = path.join(outputDir, \"login-start-smoke-bundle-summary.json\");" in content
    assert "fallbackOutputDir: fallbackResult.outputDir," in content
    assert "fallbackSummaryJson: fallbackResult.summaryJson," in content


def test_script_reserves_unique_output_paths_to_avoid_evidence_clobber() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "function reserveUniqueOutputPath(filePath)" in content
    assert 'const fd = fs.openSync(candidate, "wx");' in content
    assert "const reservedEvidenceJsonPath = reserveUniqueOutputPath(EVIDENCE_JSON_PATH);" in content
    assert "const shot = reserveUniqueOutputPath(screenshotName(label));" in content
    assert "function reserveUniqueDirectoryPath(dirPath)" in content
    assert "const outputDir = reserveUniqueDirectoryPath(FALLBACK_ARTIFACTS_BASE_DIR_PATH);" in content


def test_cli_run_id_is_recorded_in_runtime_evidence(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://www.dev.georanking.ch"
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract-run-id.json"

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--run-id",
            "contract-run-id-2026-04-14",
            "--evidence-json",
            str(evidence_path),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["runMarker"] == "contract-run-id-2026-04-14"
    assert payload["runtime"]["runMarkerSource"] == "DEV_UI_FULL_RUN_ID"
    assert payload["runtime"]["runToken"] == "contract-run-id-2026-04-14"


def test_legacy_run_token_alias_is_recorded_in_runtime_evidence(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://www.dev.georanking.ch"
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract-run-token.json"

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--run-token",
            "legacy-cli-run-token",
            "--evidence-json",
            str(evidence_path),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["runMarker"] == "legacy-cli-run-token"
    assert payload["runtime"]["runMarkerSource"] == "DEV_UI_FULL_RUN_ID"
    assert payload["runtime"]["runToken"] == "legacy-cli-run-token"


def test_legacy_smoke_run_id_env_alias_is_recorded_in_runtime_evidence(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://www.dev.georanking.ch"
    env["DEV_UI_SMOKE_RUN_ID"] = "legacy-smoke-run-id"
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract-smoke-run-id.json"

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--evidence-json",
            str(evidence_path),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["runMarker"] == "legacy-smoke-run-id"
    assert payload["runtime"]["runMarkerSource"] == "DEV_UI_SMOKE_RUN_ID"
    assert payload["runtime"]["runToken"] == "legacy-smoke-run-id"


def test_legacy_smoke_run_token_env_alias_is_recorded_in_runtime_evidence(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://www.dev.georanking.ch"
    env["DEV_UI_SMOKE_RUN_TOKEN"] = "legacy-smoke-run-token"
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract-smoke-run-token.json"

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--evidence-json",
            str(evidence_path),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["runMarker"] == "legacy-smoke-run-token"
    assert payload["runtime"]["runMarkerSource"] == "DEV_UI_SMOKE_RUN_ID"
    assert payload["runtime"]["runToken"] == "legacy-smoke-run-token"


def test_relative_evidence_path_is_resolved_against_repo_root_not_cwd(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://www.dev.georanking.ch"
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    relative_evidence = "artifacts/dev-ui-full/latest/dev-ui-full-regression-contract-relative-evidence.json"
    env["DEV_UI_FULL_EVIDENCE_JSON"] = relative_evidence

    repo_evidence_path = REPO_ROOT / relative_evidence
    cwd_evidence_path = tmp_path / relative_evidence

    if repo_evidence_path.exists():
        repo_evidence_path.unlink()

    try:
        result = subprocess.run(
            ["node", str(SCRIPT)],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert repo_evidence_path.exists(), (
            f"expected evidence under repo root, got stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert not cwd_evidence_path.exists()

        payload = json.loads(repo_evidence_path.read_text(encoding="utf-8"))
        assert payload["ok"] is False
        assert payload["error"] == "Missing DEV_UI_SMOKE_USERNAME"
    finally:
        if repo_evidence_path.exists():
            repo_evidence_path.unlink()


def test_existing_evidence_file_gets_unique_suffix_instead_of_overwrite(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_BASE_URL"] = "https://www.dev.georanking.ch"
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    evidence_path = tmp_path / "artifacts" / "dev-ui-full" / "latest" / "dev-ui-full-regression-contract-clobber.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text("existing-payload\n", encoding="utf-8")

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--evidence-json",
            str(evidence_path),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert evidence_path.read_text(encoding="utf-8") == "existing-payload\n"

    suffixed_path = evidence_path.with_name("dev-ui-full-regression-contract-clobber1.json")
    assert suffixed_path.exists(), f"expected reserved suffix evidence file, stderr={result.stderr!r}"

    payload = json.loads(suffixed_path.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["error"] == "Missing DEV_UI_SMOKE_USERNAME"
    assert f"[dev-ui-full-regression] Evidence: {suffixed_path}" in result.stderr
