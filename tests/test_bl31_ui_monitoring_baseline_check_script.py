import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_bl31_ui_monitoring_baseline.sh"
SETUP_SCRIPT = REPO_ROOT / "scripts" / "setup_bl31_ui_monitoring_baseline.sh"


class TestBl31UiMonitoringBaselineScripts(unittest.TestCase):
    def _write_executable(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def _run_check(self, *, alarm_mode: str = "ok", health_rc: str = "0") -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_aws = tmp / "aws"
            fake_health = tmp / "fake_check_health_probe.sh"

            self._write_executable(
                fake_aws,
                """#!/usr/bin/env bash
set -euo pipefail
command_key=\"${1:-} ${2:-}\"
case \"${command_key}\" in
  \"sts get-caller-identity\")
    echo '{"Account":"523234426229"}'
    ;;
  \"ecs describe-services\")
    echo 'arn:aws:ecs:eu-central-1:523234426229:service/swisstopo-dev/swisstopo-dev-ui'
    ;;
  \"cloudwatch describe-alarms\")
    mode=\"${AWS_FAKE_UI_ALARM_MODE:-ok}\"
    alarm_name=\"${UI_RUNNING_TASK_ALARM:-swisstopo-dev-ui-running-taskcount-low}\"
    sns=\"${SNS_TOPIC_ARN:-arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts}\"
    if [[ \"${mode}\" == \"ok\" ]]; then
      printf '{"Name":"%s","Actions":["%s"]}\n' \"${alarm_name}\" \"${sns}\"
    elif [[ \"${mode}\" == \"missing-action\" ]]; then
      printf '{"Name":"%s","Actions":[]}\n' \"${alarm_name}\"
    else
      echo '{}'
    fi
    ;;
  *)
    echo \"unexpected aws call: ${command_key}\" >&2
    exit 99
    ;;
esac
""",
            )

            self._write_executable(
                fake_health,
                """#!/usr/bin/env bash
set -euo pipefail
echo 'fake health probe check'
exit "${FAKE_HEALTH_RC:-0}"
""",
            )

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{tmp}:{env.get('PATH', '')}",
                    "CHECK_HEALTH_PROBE_SCRIPT": str(fake_health),
                    "AWS_FAKE_UI_ALARM_MODE": alarm_mode,
                    "FAKE_HEALTH_RC": health_rc,
                }
            )

            return subprocess.run(
                [str(CHECK_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

    def test_check_script_ok_when_ui_alarm_and_probe_are_green(self):
        cp = self._run_check(alarm_mode="ok", health_rc="0")
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertIn("Ergebnis: OK", cp.stdout)

    def test_check_script_warn_when_probe_returns_warning(self):
        cp = self._run_check(alarm_mode="ok", health_rc="10")
        self.assertEqual(cp.returncode, 10, msg=cp.stdout + "\n" + cp.stderr)
        self.assertIn("Ergebnis: WARN", cp.stdout)

    def test_check_script_fails_when_ui_alarm_missing(self):
        cp = self._run_check(alarm_mode="missing", health_rc="0")
        self.assertEqual(cp.returncode, 20, msg=cp.stdout + "\n" + cp.stderr)
        self.assertIn("UI RunningTaskCount-Alarm fehlt", cp.stdout)

    def test_setup_script_is_syntax_valid(self):
        cp = subprocess.run(
            ["bash", "-n", str(SETUP_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)


if __name__ == "__main__":
    unittest.main()
