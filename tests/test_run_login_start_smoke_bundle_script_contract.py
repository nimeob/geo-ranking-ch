from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "run_login_start_smoke_bundle.sh"
ROUTE_HELPER = REPO_ROOT / "scripts" / "smoke" / "gui_smoke_routes.sh"


class _BundleStubHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/login"):
            self.send_response(302)
            self.send_header("Location", "/oauth2/authorize?state=smoke")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


class _BundleStubServer:
    def __init__(self) -> None:
        self.httpd = HTTPServer(("127.0.0.1", 0), _BundleStubHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.httpd.server_address
        return f"http://{host}:{port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        self.httpd.server_close()


def test_shared_route_helper_covers_canonical_and_legacy_routes() -> None:
    content = ROUTE_HELPER.read_text(encoding="utf-8")

    required_routes = [
        '"/"',
        '"/gui"',
        '"/gui/history"',
        '"/gui?view=trace&request_id=req-smoke"',
        '"/history"',
        '"/jobs"',
        '"/jobs?source=smoke"',
        '"/jobs/demo-job"',
        '"/jobs/demo-job?source=smoke"',
        '"/results"',
        '"/results/demo-result"',
        '"/results/demo-result?tab=raw&source=smoke"',
        '"/gui/results"',
        '"/gui/results/demo-result"',
        '"/gui/results/demo-result?tab=raw&source=smoke"',
        '"/gui/jobs"',
        '"/gui/jobs?source=smoke"',
        '"/gui/jobs/demo-job"',
        '"/gui/jobs/demo-job?source=smoke"',
    ]

    missing = [snippet for snippet in required_routes if snippet not in content]
    assert not missing, f"gui_smoke_routes.sh fehlt Routen-Snippets: {missing}"

    assert "gui_login_start_artifact_suffix_for_route" in content
    assert "gui_canonical_redirect_artifact_suffix_for_route" in content
    assert "gui_smoke_parse_route_csv" in content
    assert "gui_smoke_parse_route_presets_csv" in content
    assert "gui_smoke_supported_route_presets_csv" in content
    assert "gui_smoke_route_is_supported" in content
    assert "${login_suffix/login-start-smoke/canonical-host-redirect-smoke}" in content
    assert "login-start-smoke-root" in content
    assert "login-start-smoke-gui-trace-view" in content
    assert "login-start-smoke-history-legacy" in content
    assert "login-start-smoke-jobs-query" in content
    assert "login-start-smoke-jobs-detail-query" in content
    assert "login-start-smoke-gui-jobs-legacy-query" in content
    assert "login-start-smoke-gui-jobs-legacy-detail-query" in content
    assert "login-start-smoke-results" in content
    assert "login-start-smoke-results-detail" in content
    assert "login-start-smoke-results-detail-query" in content
    assert "login-start-smoke-gui-results-legacy" in content
    assert "login-start-smoke-gui-results-legacy-detail" in content
    assert "login-start-smoke-gui-results-legacy-detail-query" in content
    assert "canonical-host-redirect-smoke" in content


def test_login_start_bundle_script_uses_shared_route_helper_and_probe_loop() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert 'source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"' in content
    assert "GUI_SMOKE_ROUTES" in content
    assert "gui_login_start_artifact_suffix_for_route" in content
    assert 'run_probe "$route" "$output_json"' in content
    assert "--quiet" in content
    assert "write_bundle_summary" in content
    assert "read_route_artifact_meta" in content
    assert "duration_seconds" in content
    assert "is_transport_failure_reason" in content
    assert "request_failed_*" in content
    assert "Aborting remaining routes (fail-fast)" in content
    assert "login-start-smoke-bundle-summary.json" in content
    assert "dev.georanking.ch" in content
    assert "dev.geo-ranking.ch" in content
    assert "Base URL '" in content
    assert "base_url_canonicalized" in content
    assert "requested_base_url" in content


def test_login_start_bundle_script_requires_base_url_and_env_name() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "--base-url" in content
    assert "--ui-base-url" in content
    assert "--env-name" in content
    assert "--routes" in content
    assert "--route-presets" in content
    assert "--expected-authorize-host" in content
    assert "Missing required --base-url" in content
    assert "Missing required --env-name" in content


def test_login_start_bundle_accepts_ui_base_url_alias() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--ui-base-url",
            "https://www.dev.georanking.ch",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing required --env-name" in proc.stderr


def test_login_start_bundle_canonicalizes_legacy_dev_non_www_origin_before_validation() -> (
    None
):
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://dev.georanking.ch",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing required --env-name" in proc.stderr
    assert "kanonisiere auf 'https://www.dev.georanking.ch'" in proc.stderr


def test_login_start_bundle_canonicalizes_legacy_dev_non_www_origin_with_trailing_dot_before_validation() -> (
    None
):
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://dev.georanking.ch./",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing required --env-name" in proc.stderr
    assert "kanonisiere auf 'https://www.dev.georanking.ch/'" in proc.stderr


def test_login_start_bundle_canonicalizes_trailing_dot_www_origin_before_validation() -> (
    None
):
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch./",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing required --env-name" in proc.stderr
    assert "enthält einen Host mit trailing dot" in proc.stderr
    assert "kanonisiere auf 'https://www.dev.georanking.ch/'" in proc.stderr


def test_login_start_bundle_defaults_harden_www_origins_against_legacy_bare_host() -> (
    None
):
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "import ipaddress",
        'host = host.rstrip(".")',
        'if host.startswith("www.") and len(host) > 4:',
        'seed_hosts.append(f"auth.{bare_host}")',
        "seed_hosts.append(host)",
        "expand_geo_host_variants",
        'host.replace("geo-ranking", "georanking")',
        'host.replace("georanking", "geo-ranking")',
        'if host in {"localhost", "localhost.localdomain"}:',
        "ipaddress.ip_address(host)",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"Default authorize-host Herleitung fehlt Snippets: {missing}"
    assert "seed_hosts.append(bare_host)" not in content


def test_login_start_bundle_derives_no_default_authorize_host_for_local_ip_origin(
    tmp_path,
) -> None:
    output_dir = tmp_path / "artifacts"

    with _BundleStubServer() as stub:
        proc = subprocess.run(
            [
                str(SCRIPT),
                "--base-url",
                stub.base_url,
                "--env-name",
                "stub-local",
                "--output-dir",
                str(output_dir),
                "--routes",
                "/gui",
                "--timeout",
                "5",
                "--max-attempts",
                "1",
                "--retry-delay",
                "0",
            ],
            cwd=str(REPO_ROOT),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )

    assert proc.returncode == 0, proc.stderr

    summary_path = output_dir / "stub-local-login-start-smoke-bundle-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["expected_authorize_host"] == ""


def test_login_start_bundle_rejects_missing_option_value_for_base_url() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--base-url"],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing value for --base-url" in proc.stderr
    assert "Usage:" in proc.stderr


def test_login_start_bundle_rejects_missing_option_value_for_timeout() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "dev",
            "--timeout",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing value for --timeout" in proc.stderr
    assert "Usage:" in proc.stderr


def test_login_start_bundle_rejects_missing_option_value_for_routes() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "dev",
            "--routes",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing value for --routes" in proc.stderr
    assert "Usage:" in proc.stderr


def test_login_start_bundle_rejects_missing_option_value_for_route_presets() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "dev",
            "--route-presets",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing value for --route-presets" in proc.stderr
    assert "Usage:" in proc.stderr


def test_login_start_bundle_rejects_unsupported_routes_csv() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "dev",
            "--routes",
            "/gui,/not-in-matrix",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Unsupported route token: /not-in-matrix" in proc.stderr
    assert "HINT: Supported routes:" in proc.stderr
    assert "/gui" in proc.stderr
    assert "Usage:" in proc.stderr


def test_login_start_bundle_rejects_unsupported_route_preset() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "dev",
            "--route-presets",
            "unknown-preset",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Unsupported route preset: unknown-preset" in proc.stderr
    assert "HINT: Supported route presets:" in proc.stderr
    assert "Usage:" in proc.stderr


def test_login_start_bundle_rejects_routes_and_presets_combination() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "dev",
            "--routes",
            "/gui",
            "--route-presets",
            "core",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
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


def test_login_start_bundle_summary_includes_route_reason_phase_status_and_duration(
    tmp_path,
) -> None:
    output_dir = tmp_path / "artifacts"

    with _BundleStubServer() as stub:
        proc = subprocess.run(
            [
                str(SCRIPT),
                "--base-url",
                stub.base_url,
                "--env-name",
                "stub",
                "--output-dir",
                str(output_dir),
                "--routes",
                "/gui,/jobs",
                "--timeout",
                "5",
                "--max-attempts",
                "1",
                "--retry-delay",
                "0",
            ],
            cwd=str(REPO_ROOT),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )

    assert proc.returncode == 0, proc.stderr
    assert "UI login-start smoke: probing route='/gui'" in proc.stdout
    assert (
        "UI login-start smoke: route='/jobs' rc=0 phase=start reason=ok" in proc.stdout
    )

    summary_path = output_dir / "stub-login-start-smoke-bundle-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["status"] == "passed"
    assert summary["requested_base_url"] == stub.base_url
    assert summary["base_url"] == stub.base_url
    assert summary["base_url_canonicalized"] is False
    assert summary["selected_routes"] == ["/gui", "/jobs"]
    assert summary["failed_routes"] == []

    routes = summary["routes"]
    assert len(routes) == 2

    for row in routes:
        assert row["status"] == "passed"
        assert row["rc"] == 0
        assert row["phase"] == "start"
        assert row["reason"] == "ok"
        assert row["status_code"] == 302
        assert isinstance(row["duration_seconds"], int)
        assert row["duration_seconds"] >= 0


def test_login_start_bundle_fail_fast_stops_after_first_transport_error(tmp_path) -> None:
    output_dir = tmp_path / "artifacts"

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://127.0.0.1:1",
            "--env-name",
            "stub-fail-fast",
            "--output-dir",
            str(output_dir),
            "--routes",
            "/gui,/jobs",
            "--timeout",
            "2",
            "--max-attempts",
            "1",
            "--retry-delay",
            "0",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert "UI login-start smoke: probing route='/gui'" in proc.stdout
    assert "UI login-start smoke: probing route='/jobs'" not in proc.stdout
    assert "Aborting remaining routes (fail-fast)" in proc.stderr
