import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_ui_live_full_regression.mjs"


def test_help_lists_legacy_fallback_alias(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_BASE_URL", None)
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
    assert "--allow-login-start-fallback" in result.stdout
    assert result.stderr == ""


def test_legacy_fallback_alias_is_accepted_with_help_flag(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("DEV_UI_BASE_URL", None)
    env.pop("DEV_UI_SMOKE_USERNAME", None)
    env.pop("DEV_UI_SMOKE_PASSWORD", None)

    result = subprocess.run(
        ["node", str(SCRIPT), "--allow-login-start-fallback", "--help"],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (
        "Usage: node scripts/run_dev_ui_live_full_regression.mjs [options]"
        in result.stdout
    )
    assert result.stderr == ""
