import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_docs_quality_gate.sh"


class TestCheckDocsQualityGateScript(unittest.TestCase):
    def _prepare_fixture(self) -> tuple[Path, Path, Path, Path, Path]:
        tmpdir = Path(tempfile.mkdtemp(prefix="docs-gate-script-"))
        scripts_dir = tmpdir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        script_copy = scripts_dir / "check_docs_quality_gate.sh"
        script_copy.write_text(SCRIPT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

        # Minimal file expected by the script.
        (tmpdir / "requirements-dev.txt").write_text("\n", encoding="utf-8")

        bin_dir = tmpdir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        calls_log = tmpdir / "python-calls.log"
        fake_python = bin_dir / "python"
        fake_python.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${MOCK_CALLS_LOG:?}"

if [[ "$#" -ge 3 && "$1" == "-m" && "$2" == "venv" ]]; then
  target="$3"
  if [[ "${MOCK_VENV_FAIL:-0}" == "1" ]]; then
    echo "mock venv failed intentionally" >&2
    exit 1
  fi
  mkdir -p "$target/bin"
  cat > "$target/bin/activate" <<'ACT'
# mock activate (no-op)
ACT
  exit 0
fi

if [[ "$#" -ge 2 && "$1" == "-m" && "$2" == "pip" ]]; then
  exit 0
fi

if [[ "$#" -ge 2 && "$1" == "-m" && "$2" == "pytest" ]]; then
  exit 0
fi

echo "unexpected python args: $*" >&2
exit 2
""",
            encoding="utf-8",
        )
        fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

        return tmpdir, script_copy, fake_python, calls_log, bin_dir

    def test_fail_closed_when_venv_creation_fails(self):
        tmpdir, script_copy, fake_python, calls_log, bin_dir = self._prepare_fixture()
        env = os.environ.copy()
        env["QUALITY_GATE_PYTHON"] = str(fake_python)
        env["MOCK_CALLS_LOG"] = str(calls_log)
        env["MOCK_VENV_FAIL"] = "1"
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

        result = subprocess.run(
            [str(script_copy)],
            cwd=str(tmpdir),
            env=env,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("fail-closed", result.stderr)

        calls = calls_log.read_text(encoding="utf-8")
        self.assertIn("-m venv", calls)
        self.assertNotIn("-m pytest", calls)

    def test_runs_pytest_when_venv_setup_succeeds(self):
        tmpdir, script_copy, fake_python, calls_log, bin_dir = self._prepare_fixture()
        env = os.environ.copy()
        env["QUALITY_GATE_PYTHON"] = str(fake_python)
        env["MOCK_CALLS_LOG"] = str(calls_log)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

        result = subprocess.run(
            [str(script_copy)],
            cwd=str(tmpdir),
            env=env,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("docs quality gate: PASS", result.stdout)

        calls = calls_log.read_text(encoding="utf-8")
        self.assertIn("-m venv", calls)
        self.assertIn("-m pip install --upgrade pip", calls)
        self.assertIn("-m pip install -r", calls)
        self.assertIn("-m pytest -q tests/test_user_docs.py tests/test_markdown_links.py", calls)


if __name__ == "__main__":
    unittest.main()
