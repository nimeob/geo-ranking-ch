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


def test_canonical_redirect_bundle_requires_base_url_and_supports_env_inference() -> (
    None
):
    content = SCRIPT.read_text(encoding="utf-8")

    assert "--base-url" in content
    assert "--ui-base-url" in content
    assert "--env-name" in content
    assert "--canonical-origin" in content
    assert "--canonical-hosts" in content
    assert "--summary-json" in content
    assert "--json-out" in content
    assert "--routes" in content
    assert "--route-presets" in content
    assert "Missing required --base-url" in content
    assert "--env-name nicht gesetzt; verwende abgeleitetes env" in content


def test_canonical_redirect_bundle_accepts_ui_base_url_alias_and_infers_env_name(
    tmp_path,
) -> None:
    output_dir = tmp_path / "artifacts"
    summary_path = tmp_path / "custom" / "canonical-summary.json"

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--ui-base-url",
            "http://127.0.0.1:9",
            "--output-dir",
            str(output_dir),
            "--routes",
            "/gui",
            "--timeout",
            "2",
            "--max-attempts",
            "1",
            "--retry-delay",
            "0",
            "--summary-json",
            str(summary_path),
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "--env-name nicht gesetzt" in proc.stderr
    assert summary_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["env_name"] == "local"
    assert (output_dir / "local-canonical-host-redirect-smoke.json").is_file()


def test_canonical_redirect_bundle_accepts_summary_json_alias(tmp_path) -> None:
    output_dir = tmp_path / "artifacts"
    custom_summary_path = tmp_path / "custom" / "canonical-summary.json"

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "http://127.0.0.1:9",
            "--env-name",
            "stub-summary",
            "--output-dir",
            str(output_dir),
            "--routes",
            "/gui",
            "--timeout",
            "2",
            "--max-attempts",
            "1",
            "--retry-delay",
            "0",
            "--json-out",
            str(custom_summary_path),
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert custom_summary_path.is_file()

    summary = json.loads(custom_summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "passed"
    assert summary["env_name"] == "stub-summary"

    route_artifact = output_dir / "stub-summary-canonical-host-redirect-smoke.json"
    assert route_artifact.is_file()


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


def test_canonical_redirect_bundle_accepts_quiet_flag_and_suppresses_progress_stdout(
    tmp_path,
) -> None:
    output_dir = tmp_path / "artifacts"

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "http://127.0.0.1:9",
            "--env-name",
            "stub-quiet",
            "--output-dir",
            str(output_dir),
            "--routes",
            "/gui",
            "--timeout",
            "2",
            "--max-attempts",
            "1",
            "--retry-delay",
            "0",
            "--quiet",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "UI canonical redirect smoke:" not in proc.stdout

    summary_path = output_dir / "stub-quiet-canonical-host-redirect-smoke-bundle-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "passed"
