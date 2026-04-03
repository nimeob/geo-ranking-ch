from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "run_canonical_redirect_smoke_bundle.sh"


def test_canonical_redirect_bundle_script_uses_shared_route_helper_and_probe_loop() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert 'source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"' in content
    assert "GUI_SMOKE_ROUTES" in content
    assert "gui_canonical_redirect_artifact_suffix_for_route" in content
    assert "gui_smoke_parse_route_csv" in content
    assert "check_ui_canonical_redirect.py" in content
    assert '"--quiet"' in content
    assert 'run_probe "$route" "$output_json"' in content
    assert "UI canonical redirect smoke: route='" in content
    assert "write_bundle_summary" in content
    assert "canonical-host-redirect-smoke-bundle-summary.json" in content


def test_canonical_redirect_bundle_requires_base_url_and_env_name() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "--base-url" in content
    assert "--ui-base-url" in content
    assert "--env-name" in content
    assert "--canonical-origin" in content
    assert "--canonical-hosts" in content
    assert "--routes" in content
    assert "--route-presets" in content
    assert "Missing required --base-url" in content
    assert "Missing required --env-name" in content


def test_canonical_redirect_bundle_accepts_ui_base_url_alias() -> None:
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


def test_canonical_redirect_bundle_rejects_missing_option_value_for_base_url() -> None:
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


def test_canonical_redirect_bundle_rejects_missing_option_value_for_timeout() -> None:
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


def test_canonical_redirect_bundle_rejects_missing_option_value_for_routes() -> None:
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


def test_canonical_redirect_bundle_rejects_missing_option_value_for_route_presets() -> None:
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


def test_canonical_redirect_bundle_rejects_unsupported_routes_csv() -> None:
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


def test_canonical_redirect_bundle_rejects_unsupported_route_preset() -> None:
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


def test_canonical_redirect_bundle_rejects_routes_and_presets_combination() -> None:
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
