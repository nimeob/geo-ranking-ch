from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GHA_SCRIPT = REPO_ROOT / "scripts" / "gha"


def _run_gha(args: list[str]) -> tuple[int, str, list[str], str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        gha_copy = scripts_dir / "gha"
        gha_copy.write_text(GHA_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        gha_copy.chmod(gha_copy.stat().st_mode | stat.S_IXUSR)

        token_script = scripts_dir / "gh_app_token.sh"
        token_script.write_text("#!/usr/bin/env bash\necho test-token\n", encoding="utf-8")
        token_script.chmod(token_script.stat().st_mode | stat.S_IXUSR)

        mock_gh = bin_dir / "gh"
        mock_gh.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" > "${MOCK_GH_ARGS_LOG:?}"
printf '%s' "${GH_TOKEN:-}" > "${MOCK_GH_TOKEN_LOG:?}"
if [[ "$1" == "auth" && "$2" == "status" ]]; then
  for arg in "$@"; do
    if [[ "$arg" == "--active" ]]; then
      exit 0
    fi
  done
  exit 1
fi
exit 0
""",
            encoding="utf-8",
        )
        mock_gh.chmod(mock_gh.stat().st_mode | stat.S_IXUSR)

        gh_args_log = tmp_path / "gh-args.log"
        gh_token_log = tmp_path / "gh-token.log"

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["MOCK_GH_ARGS_LOG"] = str(gh_args_log)
        env["MOCK_GH_TOKEN_LOG"] = str(gh_token_log)

        result = subprocess.run(
            [str(gha_copy), *args],
            cwd=str(tmp_path),
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        forwarded_args = gh_args_log.read_text(encoding="utf-8").splitlines()
        forwarded_token = gh_token_log.read_text(encoding="utf-8")
        return result.returncode, result.stderr, forwarded_args, forwarded_token


def test_auth_status_auto_appends_active_flag() -> None:
    code, _, args, token = _run_gha(["auth", "status", "-h", "github.com"])

    assert code == 0
    assert args == ["auth", "status", "-h", "github.com", "--active"]
    assert token == "test-token"


def test_auth_status_keeps_existing_active_flag_without_duplication() -> None:
    code, _, args, token = _run_gha(["auth", "status", "--active", "-h", "github.com"])

    assert code == 0
    assert args == ["auth", "status", "--active", "-h", "github.com"]
    assert token == "test-token"


def test_non_auth_status_commands_are_forwarded_verbatim() -> None:
    code, _, args, token = _run_gha(["run", "list", "--limit", "5"])

    assert code == 0
    assert args == ["run", "list", "--limit", "5"]
    assert token == "test-token"
