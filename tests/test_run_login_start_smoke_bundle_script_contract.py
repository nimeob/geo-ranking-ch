from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "run_login_start_smoke_bundle.sh"
ROUTE_HELPER = REPO_ROOT / "scripts" / "smoke" / "gui_smoke_routes.sh"


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
        '"/results"',
        '"/results/demo-result"',
        '"/results/demo-result?tab=raw&source=smoke"',
        '"/gui/results"',
        '"/gui/results/demo-result"',
        '"/gui/results/demo-result?tab=raw&source=smoke"',
        '"/gui/jobs"',
        '"/gui/jobs?source=smoke"',
        '"/gui/jobs/demo-job"',
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
    assert "login-start-smoke-gui-jobs-legacy-query" in content
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
    assert "write_bundle_summary" in content
    assert "login-start-smoke-bundle-summary.json" in content


def test_login_start_bundle_script_requires_base_url_and_env_name() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "--base-url" in content
    assert "--env-name" in content
    assert "--routes" in content
    assert "--route-presets" in content
    assert "--expected-authorize-host" in content
    assert "Missing required --base-url" in content
    assert "Missing required --env-name" in content


def test_login_start_bundle_defaults_harden_www_origins_against_legacy_bare_host() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        'if host.startswith("www.") and len(host) > 4:',
        'seed_hosts.append(f"auth.{bare_host}")',
        'seed_hosts.append(f"auth.{host}")',
        "seed_hosts.append(host)",
        "expand_geo_host_variants",
        'host.replace("geo-ranking", "georanking")',
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"Default authorize-host Herleitung fehlt Snippets: {missing}"
    assert "seed_hosts.append(bare_host)" not in content


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
    assert "--routes und --route-presets dürfen nicht gleichzeitig gesetzt werden" in proc.stderr
    assert "Usage:" in proc.stderr
