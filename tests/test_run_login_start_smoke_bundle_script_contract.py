from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "run_login_start_smoke_bundle.sh"


def test_login_start_bundle_script_covers_canonical_and_legacy_routes() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required = [
        'run_probe "/gui"',
        'run_probe "/gui/history"',
        'run_probe "/jobs"',
        'run_probe "/gui/jobs"',
        'run_probe "/gui/jobs/demo-job"',
        'LOGIN_GUI_RC',
        'LOGIN_HISTORY_RC',
        'LOGIN_JOBS_RC',
        'LOGIN_GUI_JOBS_LEGACY_RC',
        'LOGIN_GUI_JOBS_LEGACY_DETAIL_RC',
    ]

    missing = [snippet for snippet in required if snippet not in content]
    assert not missing, f"run_login_start_smoke_bundle.sh fehlt Smoke-Contract-Snippets: {missing}"


def test_login_start_bundle_script_requires_base_url_and_env_name() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "--base-url" in content
    assert "--env-name" in content
    assert "Missing required --base-url" in content
    assert "Missing required --env-name" in content
