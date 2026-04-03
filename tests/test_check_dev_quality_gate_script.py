import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_dev_quality_gate.sh"


class TestCheckDevQualityGateScript(unittest.TestCase):
    def _prepare_fixture(self) -> tuple[Path, Path, Path, Path]:
        tmpdir = Path(tempfile.mkdtemp(prefix="dev-quality-gate-"))
        scripts_dir = tmpdir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        script_copy = scripts_dir / "check_dev_quality_gate.sh"
        script_copy.write_text(
            SCRIPT_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )
        script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

        bin_dir = tmpdir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        calls_log = tmpdir / "calls.log"

        fake_git = bin_dir / "git"
        fake_git.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
printf 'git %s\n' "$*" >> "${MOCK_CALLS_LOG:?}"
if [[ "$#" -ge 4 && "$1" == "diff" && "$2" == "--name-only" && "$3" == "--diff-filter=ACMR" && "$4" == "HEAD" ]]; then
  cat <<'EOF'
src/keep.py
.local/tmp/gh.1
reports/consistency_report.json
EOF
  exit 0
fi
if [[ "$#" -ge 3 && "$1" == "ls-files" && "$2" == "--others" && "$3" == "--exclude-standard" ]]; then
  cat <<'EOF'
.tmp/cache.bin
.nightlock/geo-ranking-night-worker.lock
docs/keep.md
EOF
  exit 0
fi
exit 0
""",
            encoding="utf-8",
        )
        fake_git.chmod(fake_git.stat().st_mode | stat.S_IXUSR)

        fake_pre_commit = bin_dir / "pre-commit"
        fake_pre_commit.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
printf 'pre-commit %s\n' "$*" >> "${MOCK_CALLS_LOG:?}"
exit 0
""",
            encoding="utf-8",
        )
        fake_pre_commit.chmod(fake_pre_commit.stat().st_mode | stat.S_IXUSR)

        fake_python = bin_dir / "python"
        fake_python.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
printf 'python %s\n' "$*" >> "${MOCK_CALLS_LOG:?}"
exit 0
""",
            encoding="utf-8",
        )
        fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

        # Files that the mocked git output references and that should pass the -f filter.
        (tmpdir / "src").mkdir(parents=True, exist_ok=True)
        (tmpdir / "docs").mkdir(parents=True, exist_ok=True)
        (tmpdir / ".local" / "tmp").mkdir(parents=True, exist_ok=True)
        (tmpdir / ".tmp").mkdir(parents=True, exist_ok=True)
        (tmpdir / ".nightlock").mkdir(parents=True, exist_ok=True)
        (tmpdir / "reports").mkdir(parents=True, exist_ok=True)

        (tmpdir / "src" / "keep.py").write_text("print('ok')\n", encoding="utf-8")
        (tmpdir / "docs" / "keep.md").write_text("# ok\n", encoding="utf-8")
        (tmpdir / ".local" / "tmp" / "gh.1").write_text("local\n", encoding="utf-8")
        (tmpdir / ".tmp" / "cache.bin").write_text("tmp\n", encoding="utf-8")
        (tmpdir / ".nightlock" / "geo-ranking-night-worker.lock").write_text(
            "lock\n", encoding="utf-8"
        )
        (tmpdir / "reports" / "consistency_report.json").write_text(
            "{}\n", encoding="utf-8"
        )

        return tmpdir, script_copy, bin_dir, calls_log

    def test_lint_scope_skips_local_cache_and_forbidden_wip_files(self):
        tmpdir, script_copy, bin_dir, calls_log = self._prepare_fixture()
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["PYTHON_BIN"] = str(bin_dir / "python")
        env["PRE_COMMIT_BIN"] = str(bin_dir / "pre-commit")
        env["MOCK_CALLS_LOG"] = str(calls_log)

        result = subprocess.run(
            [str(script_copy)],
            cwd=str(tmpdir),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)

        lines = calls_log.read_text(encoding="utf-8").splitlines()
        pre_commit_calls = [line for line in lines if line.startswith("pre-commit ")]
        self.assertEqual(len(pre_commit_calls), 1)

        pre_commit_call = pre_commit_calls[0]
        self.assertIn("run --files", pre_commit_call)
        self.assertIn("src/keep.py", pre_commit_call)
        self.assertIn("docs/keep.md", pre_commit_call)

        self.assertNotIn("reports/consistency_report.json", pre_commit_call)
        self.assertNotIn(".local/tmp/gh.1", pre_commit_call)
        self.assertNotIn(".tmp/cache.bin", pre_commit_call)
        self.assertNotIn(".nightlock/geo-ranking-night-worker.lock", pre_commit_call)


if __name__ == "__main__":
    unittest.main()
