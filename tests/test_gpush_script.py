import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GPUSH_SCRIPT = REPO_ROOT / "scripts" / "gpush"


class TestGPushScript(unittest.TestCase):
    def _run_gpush(self, remote_url: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts_dir = tmp_path / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)

            gpush_copy = scripts_dir / "gpush"
            gpush_copy.write_text(GPUSH_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            gpush_copy.chmod(gpush_copy.stat().st_mode | stat.S_IXUSR)

            token_script = scripts_dir / "gh_app_token.sh"
            token_script.write_text("#!/usr/bin/env bash\necho test-token\n", encoding="utf-8")
            token_script.chmod(token_script.stat().st_mode | stat.S_IXUSR)

            mock_git = bin_dir / "git"
            mock_git.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" -ge 3 && "$1" == "remote" && "$2" == "get-url" && "$3" == "origin" ]]; then
  printf '%s\\n' "${MOCK_REMOTE_URL:?}"
  exit 0
fi
if [[ "$#" -ge 3 && "$1" == "rev-parse" && "$2" == "--abbrev-ref" && "$3" == "HEAD" ]]; then
  printf '%s\\n' "main"
  exit 0
fi
if [[ "$#" -ge 1 && "$1" == "push" ]]; then
  printf '%s\\n' "$@" > "${MOCK_PUSH_LOG:?}"
  exit 0
fi
printf 'unexpected git args: %s\\n' "$*" >&2
exit 2
""",
                encoding="utf-8",
            )
            mock_git.chmod(mock_git.stat().st_mode | stat.S_IXUSR)

            push_log = tmp_path / "push.log"
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env["MOCK_REMOTE_URL"] = remote_url
            env["MOCK_PUSH_LOG"] = str(push_log)

            subprocess.run(
                [str(gpush_copy)],
                cwd=str(tmp_path),
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )

            return push_log.read_text(encoding="utf-8").splitlines()

    def test_push_uses_tokenized_url_for_plain_https_origin(self):
        args = self._run_gpush("https://github.com/acme/geo-ranking-ch.git")

        self.assertEqual(
            args,
            [
                "push",
                "https://x-access-token:test-token@github.com/acme/geo-ranking-ch.git",
                "main",
            ],
        )

    def test_push_normalizes_existing_tokenized_origin_without_double_auth(self):
        args = self._run_gpush(
            "https://x-access-token:already-present@github.com/acme/geo-ranking-ch.git"
        )

        self.assertEqual(
            args,
            [
                "push",
                "https://x-access-token:test-token@github.com/acme/geo-ranking-ch.git",
                "main",
            ],
        )


if __name__ == "__main__":
    unittest.main()
