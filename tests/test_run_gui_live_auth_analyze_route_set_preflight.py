from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "run_gui_live_auth_analyze_route_set.sh"


class _LoginStartStubHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/login":
            self.send_response(404)
            self.end_headers()
            return

        query = parse_qs(parsed.query, keep_blank_values=True)
        reason = query.get("reason", [""])[0]
        location = (
            "https://auth.127.0.0.1/oauth2/authorize"
            f"?response_type=code&client_id=stub-client&state=stub&reason={reason}"
        )

        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def test_route_set_runner_fails_fast_on_missing_secrets_without_route_fanout(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env.pop("GITHUB_RUN_NUMBER", None)
    env["GITHUB_RUN_ID"] = "98765"
    env["GITHUB_RUN_ATTEMPT"] = "4"
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)

    proc = subprocess.run(
        [str(SCRIPT)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert "route 1/" not in proc.stdout
    assert "route 1/" not in proc.stderr

    blocked_file = blocker_dir / "dev-ui-auth-analyze-smoke-blocked-98765-4.json"
    assert blocked_file.exists()

    payload = json.loads(blocked_file.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["reason"] == "missing_required_github_secrets"
    assert payload["missing"] == ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]

    summary_file = blocker_dir / "dev-ui-auth-analyze-route-set-summary.json"
    assert summary_file.exists()

    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_payload["status"] == "blocked"
    assert summary_payload["mode"] == "none"
    assert summary_payload["preflight_status"] == "failed"
    assert summary_payload["fallback_status"] == "not_requested"
    assert summary_payload["run_id_base"] == "98765-4"


def test_route_set_runner_rejects_unknown_cli_option_before_preflight(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(tmp_path / "blocked")

    proc = subprocess.run(
        [str(SCRIPT), "--definitely-unknown-option"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Unknown option" in proc.stderr
    assert "Usage:" in proc.stderr


def test_route_set_runner_accepts_ui_base_url_alias_and_reaches_preflight(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--ui-base-url",
            "https://www.dev.georanking.ch",
            "--run-id-base",
            "manual-ui-base-url-alias",
            "--output-dir",
            str(blocker_dir),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert "Unknown option" not in proc.stderr
    assert (
        "run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev"
        in proc.stderr
    )

    blocked_file = (
        blocker_dir / "dev-ui-auth-analyze-smoke-blocked-manual-ui-base-url-alias.json"
    )
    assert blocked_file.exists()


@pytest.mark.parametrize(
    ("missing_option", "next_flag"),
    [
        ("--base-url", "--headless"),
        ("--ui-base-url", "--headless"),
        ("--output-dir", "--headless"),
        ("--timeout-ms", "--headless"),
        ("--address-file", "--headless"),
        ("--login-reason", "--headless"),
        ("--run-id-base", "--headless"),
        ("--routes", "--headless"),
        ("--route-presets", "--headless"),
    ],
)
def test_route_set_runner_rejects_missing_option_value_when_next_token_is_flag(
    tmp_path: Path,
    missing_option: str,
    next_flag: str,
) -> None:
    env = os.environ.copy()
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(tmp_path / "blocked")

    proc = subprocess.run(
        [str(SCRIPT), missing_option, next_flag],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert f"Missing value for {missing_option}" in proc.stderr
    assert "Usage:" in proc.stderr


def test_route_set_runner_prints_login_start_hint_on_secret_blocker(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--run-id-base",
            "manual-hint",
            "--output-dir",
            str(blocker_dir),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert (
        "run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev"
        in proc.stderr
    )

    blocked_file = blocker_dir / "dev-ui-auth-analyze-smoke-blocked-manual-hint.json"
    assert blocked_file.exists()


def test_route_set_runner_hint_preserves_normalized_route_subset_on_secret_blocker(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--run-id-base",
            "manual-hint-routes",
            "--output-dir",
            str(blocker_dir),
            "--routes",
            " /gui , /jobs?source=smoke , /gui ",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert (
        "run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch "
        '--env-name dev --routes "/gui,/jobs?source=smoke"'
    ) in proc.stderr
    assert (
        "run_gui_live_auth_analyze_route_set.sh --base-url https://www.dev.georanking.ch "
        '--fallback-login-start-on-preflight-fail --routes "/gui,/jobs?source=smoke"'
    ) in proc.stderr

    blocked_file = (
        blocker_dir / "dev-ui-auth-analyze-smoke-blocked-manual-hint-routes.json"
    )
    assert blocked_file.exists()


def test_route_set_runner_hint_quotes_route_subset_with_query_ampersand(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--run-id-base",
            "manual-hint-routes-query",
            "--output-dir",
            str(blocker_dir),
            "--routes",
            " /gui?view=trace&request_id=req-smoke , /jobs ",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    expected_routes_csv = "/gui?view=trace&request_id=req-smoke,/jobs"
    assert f'--routes "{expected_routes_csv}"' in proc.stderr

    blocked_file = (
        blocker_dir / "dev-ui-auth-analyze-smoke-blocked-manual-hint-routes-query.json"
    )
    assert blocked_file.exists()


def test_route_set_runner_hint_preserves_normalized_route_presets_on_secret_blocker(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--run-id-base",
            "manual-hint-presets",
            "--output-dir",
            str(blocker_dir),
            "--route-presets",
            " CORE , trace , core ",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert '--route-presets "core,trace"' in proc.stderr

    blocked_file = (
        blocker_dir / "dev-ui-auth-analyze-smoke-blocked-manual-hint-presets.json"
    )
    assert blocked_file.exists()


def test_route_set_runner_fallback_uses_env_reason_and_evidence_dir(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"
    evidence_dir = tmp_path / "evidence"

    server = ThreadingHTTPServer(("127.0.0.1", 0), _LoginStartStubHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{server.server_port}"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)
    env["DEV_UI_SMOKE_EVIDENCE_DIR"] = str(evidence_dir)
    env["DEV_UI_SMOKE_LOGIN_REASON"] = "env_reason_contract"
    env["DEV_UI_SMOKE_TIMEOUT_MS"] = "2501"

    try:
        proc = subprocess.run(
            [
                str(SCRIPT),
                "--base-url",
                base_url,
                "--run-id-base",
                "manual-fallback-env",
                "--fallback-login-start-on-preflight-fail",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert proc.returncode == 0
    assert "login-start fallback passed" in proc.stderr
    assert (
        "fallback_login_start_smoke=./scripts/smoke/run_login_start_smoke_bundle.sh"
        in proc.stderr
    )
    assert f"--output-dir {evidence_dir}" in proc.stderr
    assert "--reason env_reason_contract" in proc.stderr
    assert "--timeout 3" in proc.stderr

    blocked_file = (
        blocker_dir / "dev-ui-auth-analyze-smoke-blocked-manual-fallback-env.json"
    )
    assert blocked_file.exists()

    fallback_artifact = evidence_dir / "dev-login-start-smoke-root.json"
    assert fallback_artifact.exists()

    payload = json.loads(fallback_artifact.read_text(encoding="utf-8"))
    assert "reason=env_reason_contract" in str(payload.get("request_url", ""))

    summary_file = evidence_dir / "dev-ui-auth-analyze-route-set-summary.json"
    assert summary_file.exists()

    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_payload["status"] == "passed"
    assert summary_payload["mode"] == "fallback_login_start"
    assert summary_payload["preflight_status"] == "failed"
    assert summary_payload["fallback_status"] == "passed"
    assert len(summary_payload["routes"]) > 0
    assert summary_payload["routes"][0]["run_id"].startswith(
        "manual-fallback-env-fallback-"
    )
    assert summary_payload["fallback_bundle_summary"].endswith(
        "dev-login-start-smoke-bundle-summary.json"
    )


def test_route_set_runner_fallback_propagates_cli_route_subset(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"
    evidence_dir = tmp_path / "evidence"

    server = ThreadingHTTPServer(("127.0.0.1", 0), _LoginStartStubHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{server.server_port}"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)
    env["DEV_UI_SMOKE_EVIDENCE_DIR"] = str(evidence_dir)

    try:
        proc = subprocess.run(
            [
                str(SCRIPT),
                "--base-url",
                base_url,
                "--run-id-base",
                "manual-fallback-routes",
                "--fallback-login-start-on-preflight-fail",
                "--routes",
                "/gui,/jobs?source=smoke",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert proc.returncode == 0
    assert "login-start fallback passed" in proc.stderr
    assert (
        "fallback_login_start_smoke=./scripts/smoke/run_login_start_smoke_bundle.sh"
        in proc.stderr
    )
    assert '--routes "/gui,/jobs?source=smoke"' in proc.stderr

    assert (evidence_dir / "dev-login-start-smoke.json").exists()
    assert (evidence_dir / "dev-login-start-smoke-jobs-query.json").exists()
    assert not (evidence_dir / "dev-login-start-smoke-root.json").exists()

    summary_file = evidence_dir / "dev-ui-auth-analyze-route-set-summary.json"
    assert summary_file.exists()

    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_payload["status"] == "passed"
    assert summary_payload["mode"] == "fallback_login_start"
    assert [item["route"] for item in summary_payload["routes"]] == [
        "/gui",
        "/jobs?source=smoke",
    ]
    assert [item["run_id"] for item in summary_payload["routes"]] == [
        "manual-fallback-routes-fallback-1",
        "manual-fallback-routes-fallback-2",
    ]


def test_route_set_runner_fallback_propagates_quiet_flag(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"
    evidence_dir = tmp_path / "evidence"

    server = ThreadingHTTPServer(("127.0.0.1", 0), _LoginStartStubHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{server.server_port}"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)
    env["DEV_UI_SMOKE_EVIDENCE_DIR"] = str(evidence_dir)

    try:
        proc = subprocess.run(
            [
                str(SCRIPT),
                "--base-url",
                base_url,
                "--run-id-base",
                "manual-fallback-quiet",
                "--fallback-login-start-on-preflight-fail",
                "--quiet",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert proc.returncode == 0
    assert "--quiet" in proc.stderr
    assert proc.stdout.strip() == ""

    assert (evidence_dir / "dev-login-start-smoke-root.json").exists()


def test_route_set_runner_fallback_can_be_enabled_via_env_alias(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"
    evidence_dir = tmp_path / "evidence"

    server = ThreadingHTTPServer(("127.0.0.1", 0), _LoginStartStubHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{server.server_port}"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)
    env["DEV_UI_SMOKE_EVIDENCE_DIR"] = str(evidence_dir)
    env["DEV_UI_SMOKE_ALLOW_LOGIN_START_FALLBACK"] = "1"

    try:
        proc = subprocess.run(
            [
                str(SCRIPT),
                "--base-url",
                base_url,
                "--run-id-base",
                "manual-fallback-env-alias",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert proc.returncode == 0
    assert "running login-start fallback (degraded mode)" in proc.stderr
    assert (evidence_dir / "dev-login-start-smoke-root.json").exists()

    summary_file = evidence_dir / "dev-ui-auth-analyze-route-set-summary.json"
    assert summary_file.exists()

    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_payload["mode"] == "fallback_login_start"
    assert summary_payload["fallback_status"] == "passed"


def test_route_set_runner_fallback_can_be_enabled_via_cli_alias(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"
    evidence_dir = tmp_path / "evidence"

    server = ThreadingHTTPServer(("127.0.0.1", 0), _LoginStartStubHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{server.server_port}"

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)
    env["DEV_UI_SMOKE_EVIDENCE_DIR"] = str(evidence_dir)

    try:
        proc = subprocess.run(
            [
                str(SCRIPT),
                "--base-url",
                base_url,
                "--run-id-base",
                "manual-fallback-cli-alias",
                "--allow-login-start-fallback",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert proc.returncode == 0
    assert "running login-start fallback (degraded mode)" in proc.stderr
    assert (evidence_dir / "dev-login-start-smoke-root.json").exists()

    summary_file = evidence_dir / "dev-ui-auth-analyze-route-set-summary.json"
    assert summary_file.exists()

    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_payload["mode"] == "fallback_login_start"
    assert summary_payload["fallback_status"] == "passed"


def test_route_set_runner_fallback_surfaces_bundle_exit_code_from_override(
    tmp_path: Path,
) -> None:
    blocker_dir = tmp_path / "blocked"
    evidence_dir = tmp_path / "evidence"

    fake_bundle = tmp_path / "fake-login-start-bundle.sh"
    fake_bundle.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "exit 9\n",
        encoding="utf-8",
    )
    fake_bundle.chmod(0o755)

    env = os.environ.copy()
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)
    env["DEV_UI_SMOKE_BLOCKER_DIR"] = str(blocker_dir)
    env["DEV_UI_SMOKE_EVIDENCE_DIR"] = str(evidence_dir)
    env["DEV_UI_SMOKE_LOGIN_START_FALLBACK_BUNDLE_SCRIPT"] = str(fake_bundle)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--run-id-base",
            "manual-fallback-bundle-exit-code",
            "--fallback-login-start-on-preflight-fail",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 9
    assert "login-start fallback failed after live-auth preflight failure (exit=9)." in proc.stderr
    assert str(fake_bundle) in proc.stderr

    summary_file = evidence_dir / "dev-ui-auth-analyze-route-set-summary.json"
    assert summary_file.exists()

    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_payload["status"] == "failed"
    assert summary_payload["mode"] == "fallback_login_start"
    assert summary_payload["preflight_status"] == "failed"
    assert summary_payload["fallback_status"] == "failed"


def test_route_set_runner_accepts_cli_route_subset_and_uses_ordinal_run_ids(
    tmp_path: Path,
) -> None:
    node_bin_dir = tmp_path / "bin"
    node_bin_dir.mkdir(parents=True, exist_ok=True)
    route_log = tmp_path / "route-runs.log"
    evidence_dir = tmp_path / "evidence"

    fake_node = node_bin_dir / "node"
    fake_node.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'echo "${DEV_UI_SMOKE_GUI_PATH}|${DEV_UI_SMOKE_RUN_ID}|$*" >> "${ROUTE_LOG_FILE}"\n',
        encoding="utf-8",
    )
    fake_node.chmod(0o755)

    env = os.environ.copy()
    env["DEV_UI_SMOKE_USERNAME"] = "stub-user"
    env["DEV_UI_SMOKE_PASSWORD"] = "stub-password"
    env["PATH"] = f"{node_bin_dir}:{env.get('PATH', '')}"
    env["ROUTE_LOG_FILE"] = str(route_log)
    env["DEV_UI_SMOKE_EVIDENCE_DIR"] = str(evidence_dir)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--run-id-base",
            "manual-route-subset",
            "--routes",
            "/gui,/jobs?source=smoke",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0
    assert "route 1/2: /gui (run_id=manual-route-subset-1)" in proc.stdout
    assert "route 2/2: /jobs?source=smoke (run_id=manual-route-subset-2)" in proc.stdout

    rows = [
        line.strip()
        for line in route_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert rows[0].split("|", 2)[:2] == ["/gui", "manual-route-subset-1"]
    assert rows[1].split("|", 2)[:2] == ["/jobs?source=smoke", "manual-route-subset-2"]

    summary_file = evidence_dir / "dev-ui-auth-analyze-route-set-summary.json"
    assert summary_file.exists()

    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary_payload["status"] == "passed"
    assert summary_payload["mode"] == "live_auth_analyze"
    assert summary_payload["preflight_status"] == "passed"
    assert summary_payload["selected_routes"] == ["/gui", "/jobs?source=smoke"]
    assert [item["run_id"] for item in summary_payload["routes"]] == [
        "manual-route-subset-1",
        "manual-route-subset-2",
    ]


def test_route_set_runner_quiet_suppresses_live_route_progress_stdout(
    tmp_path: Path,
) -> None:
    node_bin_dir = tmp_path / "bin"
    node_bin_dir.mkdir(parents=True, exist_ok=True)
    route_log = tmp_path / "route-runs.log"

    fake_node = node_bin_dir / "node"
    fake_node.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'echo "${DEV_UI_SMOKE_GUI_PATH}|${DEV_UI_SMOKE_RUN_ID}|$*" >> "${ROUTE_LOG_FILE}"\n',
        encoding="utf-8",
    )
    fake_node.chmod(0o755)

    env = os.environ.copy()
    env["DEV_UI_SMOKE_USERNAME"] = "stub-user"
    env["DEV_UI_SMOKE_PASSWORD"] = "stub-password"
    env["PATH"] = f"{node_bin_dir}:{env.get('PATH', '')}"
    env["ROUTE_LOG_FILE"] = str(route_log)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--run-id-base",
            "manual-route-quiet",
            "--routes",
            "/gui,/jobs?source=smoke",
            "--quiet",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0
    assert "route 1/2" not in proc.stdout
    assert "PASS /gui" not in proc.stdout
    assert "route set passed" not in proc.stdout

    rows = [
        line.strip()
        for line in route_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    assert rows[0].split("|", 2)[:2] == ["/gui", "manual-route-quiet-1"]
    assert rows[1].split("|", 2)[:2] == ["/jobs?source=smoke", "manual-route-quiet-2"]


def test_route_set_runner_accepts_route_presets_and_uses_ordinal_run_ids(
    tmp_path: Path,
) -> None:
    node_bin_dir = tmp_path / "bin"
    node_bin_dir.mkdir(parents=True, exist_ok=True)
    route_log = tmp_path / "route-runs.log"

    fake_node = node_bin_dir / "node"
    fake_node.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'echo "${DEV_UI_SMOKE_GUI_PATH}|${DEV_UI_SMOKE_RUN_ID}|$*" >> "${ROUTE_LOG_FILE}"\n',
        encoding="utf-8",
    )
    fake_node.chmod(0o755)

    env = os.environ.copy()
    env["DEV_UI_SMOKE_USERNAME"] = "stub-user"
    env["DEV_UI_SMOKE_PASSWORD"] = "stub-password"
    env["PATH"] = f"{node_bin_dir}:{env.get('PATH', '')}"
    env["ROUTE_LOG_FILE"] = str(route_log)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--run-id-base",
            "manual-route-presets",
            "--route-presets",
            "trace,minimal",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0
    assert (
        "route 1/3: /gui?view=trace&request_id=req-smoke (run_id=manual-route-presets-1)"
        in proc.stdout
    )
    assert "route 2/3: / (run_id=manual-route-presets-2)" in proc.stdout
    assert "route 3/3: /gui (run_id=manual-route-presets-3)" in proc.stdout

    rows = [
        line.strip()
        for line in route_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 3
    assert rows[0].split("|", 2)[:2] == [
        "/gui?view=trace&request_id=req-smoke",
        "manual-route-presets-1",
    ]
    assert rows[1].split("|", 2)[:2] == ["/", "manual-route-presets-2"]
    assert rows[2].split("|", 2)[:2] == ["/gui", "manual-route-presets-3"]


def test_route_set_runner_rejects_invalid_route_token(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_SMOKE_USERNAME"] = "stub-user"
    env["DEV_UI_SMOKE_PASSWORD"] = "stub-password"

    proc = subprocess.run(
        [str(SCRIPT), "--routes", "gui,/jobs"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Invalid route token: gui" in proc.stderr
    assert "routes must start with '/'" in proc.stderr
    assert "HINT: Supported routes:" in proc.stderr
    assert "/gui" in proc.stderr


def test_route_set_runner_rejects_unsupported_route_token(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_SMOKE_USERNAME"] = "stub-user"
    env["DEV_UI_SMOKE_PASSWORD"] = "stub-password"

    proc = subprocess.run(
        [str(SCRIPT), "--routes", "/definitely-not-in-smoke-matrix"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Unsupported route token: /definitely-not-in-smoke-matrix" in proc.stderr
    assert "HINT: Supported routes:" in proc.stderr
    assert "/gui" in proc.stderr


def test_route_set_runner_rejects_unsupported_route_preset(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEV_UI_SMOKE_USERNAME"] = "stub-user"
    env["DEV_UI_SMOKE_PASSWORD"] = "stub-password"

    proc = subprocess.run(
        [str(SCRIPT), "--route-presets", "unknown-preset"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Unsupported route preset: unknown-preset" in proc.stderr
    assert "HINT: Supported route presets:" in proc.stderr


def test_route_set_runner_rejects_routes_and_presets_combination(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env["DEV_UI_SMOKE_USERNAME"] = "stub-user"
    env["DEV_UI_SMOKE_PASSWORD"] = "stub-password"

    proc = subprocess.run(
        [str(SCRIPT), "--routes", "/gui", "--route-presets", "core"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert (
        "--routes und --route-presets dürfen nicht gleichzeitig gesetzt werden"
        in proc.stderr
    )
    assert "Usage:" in proc.stderr
