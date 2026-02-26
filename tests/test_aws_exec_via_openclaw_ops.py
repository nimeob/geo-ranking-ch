import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "aws_exec_via_openclaw_ops.sh"


class TestAwsExecViaOpenclawOpsScript(unittest.TestCase):
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

            script_copy = tmp_path / "aws_exec_via_openclaw_ops.sh"
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

    def test_missing_args_exits_2_and_prints_usage(self):
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)

    def test_invalid_duration_is_rejected_before_aws_call(self):
        result = self._run_with_mock_aws(
            args=["sts", "get-caller-identity"],
            mock_aws_body="#!/usr/bin/env bash\nset -euo pipefail\necho should-not-run >&2\nexit 99\n",
            env_overrides={"OPENCLAW_OPS_SESSION_SECONDS": "abc"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("OPENCLAW_OPS_SESSION_SECONDS", result.stderr)

    def test_invalid_role_arn_is_rejected_before_aws_call(self):
        result = self._run_with_mock_aws(
            args=["sts", "get-caller-identity"],
            mock_aws_body="#!/usr/bin/env bash\nset -euo pipefail\necho should-not-run >&2\nexit 99\n",
            env_overrides={"OPENCLAW_OPS_ROLE_ARN": "not-an-arn"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("OPENCLAW_OPS_ROLE_ARN", result.stderr)

    def test_assume_role_parse_error_exits_30(self):
        result = self._run_with_mock_aws(
            args=["sts", "get-caller-identity"],
            mock_aws_body="""#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" -ge 2 && "$1" == "sts" && "$2" == "assume-role" ]]; then
  printf '{}\n'
  exit 0
fi
printf 'unexpected command: %s\n' "$*" >&2
exit 99
""",
        )

        self.assertEqual(result.returncode, 30)
        self.assertIn("Failed to parse assume-role credentials JSON", result.stderr)

    def test_happy_path_executes_requested_command_with_assumed_creds(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            args_log = tmp_path / "aws-args.log"
            env_log = tmp_path / "aws-env.log"

            result = self._run_with_mock_aws(
                args=["ecs", "list-clusters", "--region", "eu-central-1"],
                mock_aws_body="""#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" -ge 2 && "$1" == "sts" && "$2" == "assume-role" ]]; then
  printf '{"Credentials":{"AccessKeyId":"AKIA_TEST","SecretAccessKey":"SEC_TEST","SessionToken":"TOK_TEST"}}\n'
  exit 0
fi
printf '%s\n' "$@" > "${MOCK_AWS_ARGS_LOG:?}"
printf 'AK=%s\nSK=%s\nST=%s\n' "${AWS_ACCESS_KEY_ID:-}" "${AWS_SECRET_ACCESS_KEY:-}" "${AWS_SESSION_TOKEN:-}" > "${MOCK_AWS_ENV_LOG:?}"
exit 0
""",
                env_overrides={
                    "MOCK_AWS_ARGS_LOG": str(args_log),
                    "MOCK_AWS_ENV_LOG": str(env_log),
                    "OPENCLAW_OPS_SESSION_NAME": "openclaw-ops-exec-test",
                },
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(
                args_log.read_text(encoding="utf-8").splitlines(),
                ["ecs", "list-clusters", "--region", "eu-central-1"],
            )
            env_content = env_log.read_text(encoding="utf-8")
            self.assertIn("AK=AKIA_TEST", env_content)
            self.assertIn("SK=SEC_TEST", env_content)
            self.assertIn("ST=TOK_TEST", env_content)


if __name__ == "__main__":
    unittest.main()
