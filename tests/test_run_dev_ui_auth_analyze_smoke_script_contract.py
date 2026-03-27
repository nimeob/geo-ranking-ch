from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_ui_auth_analyze_smoke.mjs"


class _LoginFallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if not self.path.startswith("/login"):
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(302)
        self.send_header(
            "Location",
            "http://auth.local.test/oauth2/authorize?response_type=code&client_id=contract",
        )
        self.end_headers()

    def log_message(self, *_args, **_kwargs) -> None:
        return


class _LoginFallbackServer:
    def __init__(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _LoginFallbackHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "_LoginFallbackServer":
        self.thread.start()
        return self

    def __exit__(self, *_args) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


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
    assert payload["error"]["name"] == "Error"
    assert "Fehlende Credentials" in payload["error"]["message"]

    # Console contract: failures should surface actionable one-line diagnostics in stderr.
    assert "[dev-ui-auth-analyze-smoke] ERROR" in result.stderr
    assert "evidence=" in result.stderr
    assert "Fehlende_Credentials" in result.stderr
    assert "DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1" in result.stderr


def test_missing_credentials_can_use_login_start_fallback_when_enabled(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-fallback"
    env["DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS"] = "1"

    with _LoginFallbackServer() as server:
        env["BASE_URL"] = server.base_url
        result = subprocess.run(
            ["node", str(SCRIPT)],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0

    evidence_files = sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )
    assert evidence_files, (
        f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"
    )

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["degradedMode"]["active"] is True
    assert payload["degradedMode"]["reason"] == "missing_live_credentials"
    assert payload["checks"]["startRedirectToAuthAuthorize"] is True
    assert payload["checks"]["entryRedirectToAuthAuthorize"] is True
    assert payload["runtime"]["browser"] == "none-login-start-fallback"

    assert "[dev-ui-auth-analyze-smoke] PASS" in result.stdout
    assert "mode=login_start_fallback" in result.stdout


def test_default_timestamp_run_marker_does_not_duplicate_filename_token(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env.pop("DEV_UI_SMOKE_RUN_ID", None)
    env.pop("GITHUB_RUN_NUMBER", None)
    env.pop("GITHUB_RUN_ATTEMPT", None)
    env.pop("GITHUB_RUN_ID", None)

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
    body = evidence_stem.removeprefix("dev-ui-auth-analyze-smoke-")

    # Default run marker (=timestamp) should not be duplicated in the artifact filename.
    assert "-" not in body, evidence_stem



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
