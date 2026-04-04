from __future__ import annotations

import json
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
    assert "is_transport_failure_reason" in content
    assert "request_failed_*" in content
    assert "Aborting remaining routes (fail-fast)" in content
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


def test_canonical_redirect_bundle_fail_fast_marks_unprobed_routes_as_skipped(tmp_path) -> None:
    output_dir = tmp_path / "artifacts"

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--alias-host",
            "127.0.0.1",
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
    assert "UI canonical redirect smoke: route='/gui'" in proc.stdout
    assert "UI canonical redirect smoke: route='/jobs'" not in proc.stdout
    assert "Aborting remaining routes (fail-fast)" in proc.stderr

    summary_path = output_dir / "stub-fail-fast-canonical-host-redirect-smoke-bundle-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["status"] == "failed"
    assert summary["failed_routes"] == ["/gui"]
    assert summary["skipped_routes"] == ["/jobs"]

    routes = {row["route"]: row for row in summary["routes"]}
    assert routes["/gui"]["status"] == "failed"
    assert routes["/gui"]["rc"] == 1
    assert routes["/jobs"]["status"] == "skipped"
    assert routes["/jobs"]["rc"] is None
