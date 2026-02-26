from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "openclaw_runtime_assumerole_exec.sh"


class TestOpenclawRuntimeAssumeroleExecScript(unittest.TestCase):
    def _run_with_mock_aws(
        self,
        args: list[str],
        mock_aws_body: str,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)

            script_copy = tmp_path / "openclaw_runtime_assumerole_exec.sh"
            script_copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

            mock_aws = bin_dir / "aws"
            mock_aws.write_text(mock_aws_body, encoding="utf-8")
            mock_aws.chmod(mock_aws.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            if env_overrides:
                env.update(env_overrides)

            return subprocess.run(
                [str(script_copy), *args],
                cwd=tmp_path,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )

    def test_missing_args_exits_2_and_prints_usage(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)

    def test_happy_path_replaces_static_env_with_session_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env_log = tmp_path / "runtime-env.log"

            target_cmd = tmp_path / "target.sh"
            target_cmd.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf 'AK=%s\nSK=%s\nST=%s\nFLAG=%s\n' "
                "\"${AWS_ACCESS_KEY_ID:-}\" "
                "\"${AWS_SECRET_ACCESS_KEY:-}\" "
                "\"${AWS_SESSION_TOKEN:-}\" "
                "\"${OPENCLAW_ASSUME_ROLE_FIRST:-}\" "
                f"> \"{env_log}\"\n",
                encoding="utf-8",
            )
            target_cmd.chmod(target_cmd.stat().st_mode | stat.S_IXUSR)

            result = self._run_with_mock_aws(
                args=[str(target_cmd)],
                mock_aws_body="""#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" -ge 2 && "$1" == "sts" && "$2" == "assume-role" ]]; then
  printf '{"Credentials":{"AccessKeyId":"ASIA_TEST_SESSION","SecretAccessKey":"SEC_TEST_SESSION","SessionToken":"TOK_TEST_SESSION"}}\n'
  exit 0
fi
printf 'unexpected command: %s\n' "$*" >&2
exit 99
""",
                env_overrides={
                    "AWS_ACCESS_KEY_ID": "AKIAX1234567890ABCD",
                    "AWS_SECRET_ACCESS_KEY": "legacy-secret",
                },
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            env_content = env_log.read_text(encoding="utf-8")
            self.assertIn("AK=ASIA_TEST_SESSION", env_content)
            self.assertIn("SK=SEC_TEST_SESSION", env_content)
            self.assertIn("ST=TOK_TEST_SESSION", env_content)
            self.assertIn("FLAG=1", env_content)


if __name__ == "__main__":
    unittest.main()
