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
        '"/gui"',
        '"/gui/history"',
        '"/history"',
        '"/jobs"',
        '"/jobs?source=smoke"',
        '"/jobs/demo-job"',
        '"/results/demo-result"',
        '"/gui/jobs"',
        '"/gui/jobs?source=smoke"',
        '"/gui/jobs/demo-job"',
    ]

    missing = [snippet for snippet in required_routes if snippet not in content]
    assert not missing, f"gui_smoke_routes.sh fehlt Routen-Snippets: {missing}"

    assert "gui_login_start_artifact_suffix_for_route" in content
    assert "login-start-smoke-history-legacy" in content
    assert "login-start-smoke-jobs-query" in content
    assert "login-start-smoke-gui-jobs-legacy-query" in content
    assert "login-start-smoke-results-detail" in content


def test_login_start_bundle_script_uses_shared_route_helper_and_probe_loop() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert 'source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"' in content
    assert "GUI_SMOKE_ROUTES" in content
    assert "gui_login_start_artifact_suffix_for_route" in content
    assert 'run_probe "$route" "$output_json"' in content


def test_login_start_bundle_script_requires_base_url_and_env_name() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "--base-url" in content
    assert "--env-name" in content
    assert "--expected-authorize-host" in content
    assert "Missing required --base-url" in content
    assert "Missing required --env-name" in content


def test_login_start_bundle_defaults_include_auth_host_for_non_www_base_urls() -> None:
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
