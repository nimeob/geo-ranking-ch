from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_ui_auth_analyze_smoke.mjs"


class _LoginFallbackHandler(BaseHTTPRequestHandler):
    def _build_redirect_uri(self) -> str:
        host = str(self.headers.get("host") or "127.0.0.1")
        return f"http://{host}/auth/callback"

    def _build_authorize_location(self) -> str:
        redirect_uri = quote(self._build_redirect_uri(), safe="")
        return (
            "http://auth.local.test/oauth2/authorize?"
            f"response_type=code&client_id=contract&redirect_uri={redirect_uri}"
        )

    def do_GET(self) -> None:  # noqa: N802
        if not self.path.startswith("/login"):
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(302)
        self.send_header("Location", self._build_authorize_location())
        self.end_headers()

    def log_message(self, *_args, **_kwargs) -> None:
        return


class _LoginFallbackBadRedirectUriHandler(_LoginFallbackHandler):
    def _build_redirect_uri(self) -> str:
        return "https://evil.example/auth/callback"


class _LoginFallbackAuthThenCanonicalHandler(_LoginFallbackHandler):
    def _extract_next_reason(self) -> tuple[str, str]:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        next_path = str((query.get("next") or ["/gui"])[0])
        reason = str((query.get("reason") or ["manual_login"])[0])
        return next_path, reason

    def _build_auth_login_location(self, *, next_path: str, reason: str) -> str:
        return "/auth/login?" + urlencode({"next": next_path, "reason": reason})

    def _build_canonical_login_location(self, *, next_path: str, reason: str) -> str:
        return "/login?" + urlencode(
            {
                "next": next_path,
                "reason": reason,
                "start": "1",
                "canonical": "1",
            }
        )

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/auth/login":
            next_path, reason = self._extract_next_reason()
            self.send_response(302)
            self.send_header(
                "Location",
                self._build_canonical_login_location(
                    next_path=next_path,
                    reason=reason,
                ),
            )
            self.end_headers()
            return

        if path == "/login":
            next_path, reason = self._extract_next_reason()
            query = parse_qs(parsed.query, keep_blank_values=True)
            canonical_value = str((query.get("canonical") or [""])[0])
            if canonical_value == "1":
                self.send_response(302)
                self.send_header("Location", self._build_authorize_location())
                self.end_headers()
                return

            self.send_response(302)
            self.send_header(
                "Location",
                self._build_auth_login_location(next_path=next_path, reason=reason),
            )
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()


class _LoginFallbackServer:
    def __init__(self, handler: type[BaseHTTPRequestHandler] | None = None) -> None:
        handler_cls = handler or _LoginFallbackHandler
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
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


def _reserve_unused_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


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
        "const allowedOriginOverrides = String(process.env.DEV_UI_SMOKE_ALLOWED_ORIGINS || '').trim();"
        in content
    )
    assert "const allowedOrigins = resolveAllowedOrigins(baseOrigin, allowedOriginOverrides);" in content
    assert "function resolveAllowedOrigins(primaryOrigin, rawOverrides)" in content
    assert "function isAllowedOrigin(value)" in content
    assert (
        "if (target.pathname === '/gui/jobs') return `/jobs${target.search}`;"
        in content
    )
    assert "function isExpectedPostLoginUrl(value)" in content
    assert "if (!isAllowedOrigin(parsed.origin)) return false;" in content
    assert "const loginReturnedToRequestedGuiPath =" in content
    assert "(url) => isExpectedPostLoginUrl(url)" in content
    assert "loginReturnedToRequestedGuiPath," in content
    assert "loginReturnedToGui: loginReturnedToRequestedGuiPath" in content
    assert "function isExpectedAuthCallbackRedirect(value)" in content
    assert "function parseAuthAuthorizeRedirect(value)" in content
    assert "startRedirectUriMatchesAuthCallback" in content
    assert "entryRedirectUriMatchesAuthCallback" in content


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


def test_help_flag_exits_zero_without_emitting_evidence(tmp_path: Path) -> None:
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
    assert "Usage: node scripts/run_dev_ui_auth_analyze_smoke.mjs" in result.stdout
    assert "--fallback-login-start" in result.stdout
    assert "--allow-login-start-fallback" in result.stdout

    evidence_files = sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )
    assert evidence_files == []


def test_unknown_cli_argument_exits_with_usage_and_no_evidence(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    result = subprocess.run(
        ["node", str(SCRIPT), "--unknown-flag"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "unknown_cli_args=--unknown-flag" in result.stderr
    assert "Usage: node scripts/run_dev_ui_auth_analyze_smoke.mjs" in result.stderr

    evidence_files = sorted(
        (tmp_path / "reports" / "evidence").glob("dev-ui-auth-analyze-smoke-*.json")
    )
    assert evidence_files == []


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


def test_missing_credentials_payload_includes_default_origin_alias_allowlist(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-origin-alias-default"
    env["BASE_URL"] = "https://www.dev.georanking.ch/"

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
    assert payload["target"]["baseOrigin"] == "https://www.dev.georanking.ch"
    assert sorted(payload["target"]["allowedOrigins"]) == [
        "https://www.dev.geo-ranking.ch",
        "https://www.dev.georanking.ch",
    ]


def test_missing_credentials_payload_normalizes_allowed_origin_overrides(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-origin-overrides"
    env["BASE_URL"] = "https://dev.georanking.ch"
    env["DEV_UI_SMOKE_ALLOWED_ORIGINS"] = (
        "https://preview.dev.georanking.ch, https://dev.georanking.ch:443, not-a-url"
    )

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
    assert payload["target"]["baseOrigin"] == "https://www.dev.georanking.ch"
    assert sorted(payload["target"]["allowedOrigins"]) == [
        "https://preview.dev.geo-ranking.ch",
        "https://preview.dev.georanking.ch",
        "https://www.dev.geo-ranking.ch",
        "https://www.dev.georanking.ch",
        "https://www.preview.dev.geo-ranking.ch",
        "https://www.preview.dev.georanking.ch",
    ]
    assert "dev.georanking.ch" not in payload["target"]["allowedAuthorizeHosts"]
    assert "dev.geo-ranking.ch" not in payload["target"]["allowedAuthorizeHosts"]
    assert "auth.dev.georanking.ch" in payload["target"]["allowedAuthorizeHosts"]


def test_missing_credentials_can_use_login_start_fallback_when_enabled(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-fallback"
    env["DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS"] = "1"
    env["DEV_UI_SMOKE_ALLOWED_AUTHORIZE_HOSTS"] = "auth.local.test"

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
    assert (
        evidence_files
    ), f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["degradedMode"]["active"] is True
    assert payload["degradedMode"]["reason"] == "missing_live_credentials"
    assert payload["checks"]["startRedirectToAuthAuthorize"] is True
    assert payload["checks"]["entryRedirectToAuthAuthorize"] is True
    assert payload["checks"]["startRedirectResponseTypeCode"] is True
    assert payload["checks"]["entryRedirectResponseTypeCode"] is True
    assert payload["checks"]["startRedirectClientIdPresent"] is True
    assert payload["checks"]["entryRedirectClientIdPresent"] is True
    assert payload["checks"]["startRedirectUriMatchesAuthCallback"] is True
    assert payload["checks"]["entryRedirectUriMatchesAuthCallback"] is True
    assert payload["runtime"]["browser"] == "none-login-start-fallback"

    assert "[dev-ui-auth-analyze-smoke] PASS" in result.stdout
    assert "mode=login_start_fallback" in result.stdout


def test_missing_credentials_can_use_login_start_fallback_via_cli_flag(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-fallback-cli"
    env["DEV_UI_SMOKE_ALLOWED_AUTHORIZE_HOSTS"] = "auth.local.test"

    with _LoginFallbackServer() as server:
        env["BASE_URL"] = server.base_url
        result = subprocess.run(
            ["node", str(SCRIPT), "--fallback-login-start"],
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
    assert (
        evidence_files
    ), f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["degradedMode"]["active"] is True
    assert payload["degradedMode"]["reason"] == "missing_live_credentials"
    assert payload["checks"]["entryRedirectToAuthAuthorize"] is True
    assert payload["checks"]["entryRedirectResponseTypeCode"] is True
    assert payload["checks"]["entryRedirectClientIdPresent"] is True
    assert payload["checks"]["entryRedirectUriMatchesAuthCallback"] is True

    assert "[dev-ui-auth-analyze-smoke] PASS" in result.stdout
    assert "mode=login_start_fallback" in result.stdout


def test_missing_credentials_can_use_login_start_fallback_via_legacy_cli_flag(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-fallback-cli-legacy"
    env["DEV_UI_SMOKE_ALLOWED_AUTHORIZE_HOSTS"] = "auth.local.test"

    with _LoginFallbackServer() as server:
        env["BASE_URL"] = server.base_url
        result = subprocess.run(
            ["node", str(SCRIPT), "--allow-login-start-fallback"],
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
    assert (
        evidence_files
    ), f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["degradedMode"]["active"] is True
    assert payload["degradedMode"]["reason"] == "missing_live_credentials"
    assert payload["checks"]["entryRedirectToAuthAuthorize"] is True
    assert payload["checks"]["entryRedirectResponseTypeCode"] is True
    assert payload["checks"]["entryRedirectClientIdPresent"] is True
    assert payload["checks"]["entryRedirectUriMatchesAuthCallback"] is True

    assert "[dev-ui-auth-analyze-smoke] PASS" in result.stdout
    assert "mode=login_start_fallback" in result.stdout


def test_login_start_fallback_tolerates_auth_login_then_canonical_login_hop(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-fallback-canonical-hop"
    env["DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS"] = "1"
    env["DEV_UI_SMOKE_ALLOWED_AUTHORIZE_HOSTS"] = "auth.local.test"

    with _LoginFallbackServer(handler=_LoginFallbackAuthThenCanonicalHandler) as server:
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
    assert (
        evidence_files
    ), f"expected evidence json, got stdout={result.stdout!r} stderr={result.stderr!r}"

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["checks"]["startRedirectToAuthAuthorize"] is True
    assert payload["checks"]["entryRedirectToAuthAuthorize"] is True

    start_probe = payload["loginStartFallback"]["startProbe"]
    entry_probe = payload["loginStartFallback"]["entryProbe"]
    assert start_probe["redirectHopCount"] >= 2
    assert entry_probe["redirectHopCount"] >= 2
    assert any("/auth/login" in hop["location"] for hop in start_probe["redirectChain"])
    assert any("canonical=1" in hop["location"] for hop in entry_probe["redirectChain"])


def test_login_start_fallback_fails_when_redirect_uri_does_not_match_base_origin(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-fallback-bad-redirect-uri"
    env["DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS"] = "1"
    env["DEV_UI_SMOKE_ALLOWED_AUTHORIZE_HOSTS"] = "auth.local.test"

    with _LoginFallbackServer(handler=_LoginFallbackBadRedirectUriHandler) as server:
        env["BASE_URL"] = server.base_url
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
    assert payload["checks"]["startRedirectToAuthAuthorize"] is False
    assert payload["checks"]["entryRedirectToAuthAuthorize"] is False
    assert payload["checks"]["startRedirectResponseTypeCode"] is True
    assert payload["checks"]["entryRedirectResponseTypeCode"] is True
    assert payload["checks"]["startRedirectClientIdPresent"] is True
    assert payload["checks"]["entryRedirectClientIdPresent"] is True
    assert payload["checks"]["startRedirectUriMatchesAuthCallback"] is False
    assert payload["checks"]["entryRedirectUriMatchesAuthCallback"] is False

    assert "[dev-ui-auth-analyze-smoke] FAIL" in result.stderr
    assert "startRedirectUriMatchesAuthCallback" in result.stderr


def test_login_start_fallback_records_connection_failure_as_contract_fail(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_RUN_ID"] = "contract-fallback-connection-failure"
    env["DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS"] = "1"

    unused_port = _reserve_unused_local_port()
    env["BASE_URL"] = f"http://127.0.0.1:{unused_port}"

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
    assert "error" not in payload

    start_probe = payload["loginStartFallback"]["startProbe"]
    entry_probe = payload["loginStartFallback"]["entryProbe"]

    assert start_probe["ok"] is False
    assert entry_probe["ok"] is False
    assert start_probe["reason"].startswith("request_failed_connection_")
    assert entry_probe["reason"].startswith("request_failed_connection_")
    assert start_probe["requestError"]["reason"] == start_probe["reason"]
    assert entry_probe["requestError"]["reason"] == entry_probe["reason"]
    assert payload["checks"]["startRedirectToAuthAuthorize"] is False
    assert payload["checks"]["entryRedirectToAuthAuthorize"] is False

    assert "[dev-ui-auth-analyze-smoke] FAIL" in result.stderr
    assert "start_reason=request_failed_connection_" in result.stderr


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


def test_cli_run_token_alias_sets_run_marker_and_artifact_suffix(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    result = subprocess.run(
        ["node", str(SCRIPT), "--run-token", "legacy-cli-run-token"],
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

    evidence_name = evidence_files[-1].name
    assert "legacy-cli-run-token" in evidence_name

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["runtime"]["runMarker"] == "legacy-cli-run-token"


def test_env_run_token_alias_sets_run_marker_and_artifact_suffix(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env.pop("DEV_UI_SMOKE_RUN_ID", None)
    env["DEV_UI_SMOKE_RUN_TOKEN"] = "legacy-env-run-token"

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
    assert evidence_files, result.stderr

    evidence_name = evidence_files[-1].name
    assert "legacy-env-run-token" in evidence_name

    payload = json.loads(evidence_files[-1].read_text(encoding="utf-8"))
    assert payload["runtime"]["runMarker"] == "legacy-env-run-token"


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
