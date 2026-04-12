from __future__ import annotations

import json
import os
import shlex
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

    assert (
        "async function ensureAnalyzeShellReady(page, baseOrigin, timeout)" in content
    )
    assert "strategy: 'menuitem_to_gui'" in content
    assert "strategy: 'direct_goto_gui'" in content
    assert "analyzeShellRecovery" in content


def test_script_tracks_post_login_target_path_and_keeps_legacy_check_alias() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert (
        "const expectedPostLoginPath = resolveCanonicalGuiSuccessor(guiPath);"
        in content
    )
    assert "function resolveCanonicalGuiSuccessor(pathname)" in content
    assert (
        "const expectedPostLoginTarget = parseRelativeUrl(expectedPostLoginPath);"
        in content
    )
    assert "function parseRelativeUrl(rawPath)" in content
    assert (
        "if (target.pathname === '/gui/jobs') return `/jobs${target.search}`;"
        in content
    )
    assert "function isExpectedPostLoginUrl(value)" in content
    assert "const loginReturnedToRequestedGuiPath =" in content
    assert "(url) => isExpectedPostLoginUrl(url)" in content
    assert "loginReturnedToRequestedGuiPath," in content
    assert "loginReturnedToGui: loginReturnedToRequestedGuiPath" in content


def test_script_uses_dynamic_playwright_import_with_actionable_hint() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "import { chromium } from 'playwright';" not in content
    assert "async function loadChromium()" in content
    assert "await import('playwright')" in content
    assert "npx playwright install --with-deps chromium" in content


def test_script_emits_actionable_console_summary_markers() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "function emitSmokeSummary(payload, evidencePath)" in content
    assert "[dev-ui-auth-analyze-smoke] PASS" in content
    assert "[dev-ui-auth-analyze-smoke] FAIL" in content
    assert "[dev-ui-auth-analyze-smoke] ERROR" in content
    assert "failed_checks=" in content
    assert "evidence=" in content


def test_missing_credentials_emit_json_evidence_even_without_playwright(
    tmp_path: Path,
) -> None:
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

    evidence_files = sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )
    assert (
        evidence_files
    ), f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["blocked"] is True
    assert payload["reason"] == "missing_required_github_secrets"
    assert payload["missing"] == ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]
    assert payload["fallback_login_start_smoke"]["command"]
    assert payload["error"]["name"] == "Error"
    assert "Fehlende Credentials" in payload["error"]["message"]

    # Console contract: failures should surface actionable one-line diagnostics in stderr.
    assert "[dev-ui-auth-analyze-smoke] ERROR" in result.stderr
    assert "evidence=" in result.stderr
    assert "Fehlende_Credentials" in result.stderr


def test_run_id_is_sanitized_in_evidence_filename(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "run id: nightly/2026-03-23#01"

    result = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1

    evidence_files = sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )
    assert (
        evidence_files
    ), f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"

    evidence_name = evidence_files[-1].name
    assert "run-id-nightly-2026-03-23-01" in evidence_name


def test_empty_sanitized_run_id_falls_back_to_stable_run_token(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "::::"

    result = subprocess.run(
        ["node", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1

    evidence_files = sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )
    assert (
        evidence_files
    ), f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"

    evidence_stem = evidence_files[-1].stem
    assert evidence_stem.endswith("-run"), evidence_stem


def test_cli_overrides_base_url_and_gui_path_even_without_credentials(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--base-url",
            "https://dev.example.test/",
            "--gui-path",
            "/gui/jobs?from=cli",
            "--run-id",
            "cli-override-check",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1

    evidence_files = sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )
    assert evidence_files, result.stderr

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["target"]["baseOrigin"] == "https://dev.example.test"
    assert payload["target"]["guiPath"] == "/gui/jobs?from=cli"
    assert payload["target"]["expectedPostLoginPath"] == "/jobs?from=cli"


def test_cli_base_url_is_normalized_to_origin_when_path_or_query_is_passed(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--base-url",
            "https://dev.example.test/gui?from=ci#frag",
            "--gui-path",
            "/gui/history",
            "--run-id",
            "cli-origin-normalization-check",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1

    evidence_files = sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )
    assert evidence_files, result.stderr

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["target"]["baseOrigin"] == "https://dev.example.test"
    assert payload["target"]["loginStartUrl"].startswith(
        "https://dev.example.test/login?next=%2Fgui%2Fhistory"
    )


def test_cli_output_dir_override_writes_evidence_outside_default_path(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    output_dir = tmp_path / "artifacts" / "ui-smoke"

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "cli-output-dir-check",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert sorted(output_dir.glob("dev-ui-auth-analyze-smoke-*.json"))
    assert not sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )


def test_help_flag_exits_successfully_without_live_credentials(tmp_path: Path) -> None:
    env = os.environ.copy()
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
    assert "Usage: node scripts/run_dev_ui_auth_analyze_smoke.mjs [options]" in result.stdout
    assert "--allow-login-start-fallback" in result.stdout


def test_allow_login_start_fallback_runs_command_override_when_live_credentials_missing(
    tmp_path: Path,
) -> None:
    marker_file = tmp_path / "fallback-marker.txt"
    evidence_dir = tmp_path / "evidence"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_LOGIN_START_FALLBACK_COMMAND"] = (
        f"printf fallback-ok > {shlex.quote(str(marker_file))}"
    )

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--allow-login-start-fallback",
            "--run-id",
            "contract-fallback-ok",
            "--output-dir",
            str(evidence_dir),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert marker_file.read_text(encoding="utf-8") == "fallback-ok"

    evidence_files = sorted(evidence_dir.glob("dev-ui-auth-analyze-smoke-*.json"))
    assert evidence_files, result.stderr

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["fallback_login_start_smoke"]["executed"] is True
    assert payload["fallback_login_start_smoke"]["result"]["ok"] is True
    assert "running login-start fallback" in result.stderr


def test_allow_login_start_fallback_emits_evidence_when_bundle_script_is_missing(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_LOGIN_START_FALLBACK_BUNDLE_SCRIPT"] = (
        "./scripts/smoke/does-not-exist.sh"
    )

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--allow-login-start-fallback",
            "--run-id",
            "contract-fallback-missing-script",
            "--output-dir",
            str(evidence_dir),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Unhandled 'error' event" not in result.stderr

    evidence_files = sorted(evidence_dir.glob("dev-ui-auth-analyze-smoke-*.json"))
    assert evidence_files, result.stderr

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["checks"]["missingLiveCredentials"] is True
    assert payload["checks"]["fallbackLoginStartBundlePassed"] is False
    assert payload["fallback_login_start_smoke"]["executed"] is True
    assert payload["fallback_login_start_smoke"]["result"]["ok"] is False
    assert payload["fallback_login_start_smoke"]["result"]["code"] == -1
    assert payload["fallback_login_start_smoke"]["result"]["error"]["name"] == "Error"
    assert "ENOENT" in payload["fallback_login_start_smoke"]["result"]["error"]["message"]


def test_allow_login_start_fallback_resolves_relative_bundle_script_from_repo_when_cwd_differs(
    tmp_path: Path,
) -> None:
    evidence_dir = tmp_path / "evidence"
    marker_file = tmp_path / "bundle-cwd.txt"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_LOGIN_START_FALLBACK_BUNDLE_SCRIPT"] = (
        "./tests/data/fake_login_start_bundle_ok.sh"
    )
    env["DEV_UI_SMOKE_FALLBACK_MARKER_PATH"] = str(marker_file)

    result = subprocess.run(
        [
            "node",
            str(SCRIPT),
            "--allow-login-start-fallback",
            "--run-id",
            "contract-fallback-repo-relative-bundle",
            "--output-dir",
            str(evidence_dir),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert marker_file.read_text(encoding="utf-8").strip() == str(REPO_ROOT)

    evidence_files = sorted(evidence_dir.glob("dev-ui-auth-analyze-smoke-*.json"))
    assert evidence_files, result.stderr

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["fallback_login_start_smoke"]["executed"] is True
    assert payload["fallback_login_start_smoke"]["result"]["ok"] is True
    assert payload["fallback_login_start_smoke"]["bundle_cwd"] == str(REPO_ROOT)
    assert payload["fallback_login_start_smoke"]["bundle_script"].endswith(
        "/tests/data/fake_login_start_bundle_ok.sh"
    )
