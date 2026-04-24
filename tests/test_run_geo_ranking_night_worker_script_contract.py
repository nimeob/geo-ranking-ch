import os
import stat
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_geo_ranking_night_worker.sh"


class TestRunGeoRankingNightWorkerScriptContract(unittest.TestCase):
    def _prepare_fixture(self) -> tuple[Path, Path, Path]:
        tmpdir = Path(tempfile.mkdtemp(prefix="geo-night-worker-"))

        scripts_dir = tmpdir / "scripts"
        smoke_dir = scripts_dir / "smoke"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        smoke_dir.mkdir(parents=True, exist_ok=True)

        script_copy = scripts_dir / "run_geo_ranking_night_worker.sh"
        script_copy.write_text(SCRIPT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

        fake_gha = scripts_dir / "gha"
        fake_gha.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" -ge 2 && "$1" == "issue" && "$2" == "list" ]]; then
  cat <<'JSON'
[{"number": 123, "title": "blocked", "url": "https://example.invalid/issues/123"}]
JSON
  exit 0
fi
if [[ "$#" -ge 2 && "$1" == "run" && "$2" == "list" ]]; then
  cat <<'JSON'
[{"databaseId": 1, "workflowName": "ci", "status": "completed", "conclusion": "failure", "createdAt": "__NOW__", "url": "https://example.invalid/run/1"}]
JSON
  exit 0
fi
exit 2
""".replace("__NOW__", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
            encoding="utf-8",
        )
        fake_gha.chmod(fake_gha.stat().st_mode | stat.S_IXUSR)

        fake_retry = scripts_dir / "blocker_retry_supervisor.py"
        fake_retry.write_text("print('ok')\n", encoding="utf-8")

        fake_auth_smoke = smoke_dir / "run_auth_perimeter_smoke_bundle.sh"
        fake_auth_smoke.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
summary_json=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --summary-json)
      summary_json="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
if [[ -n "$summary_json" ]]; then
  mkdir -p "$(dirname "$summary_json")"
  printf '{"ok": true}\n' > "$summary_json"
fi
exit 0
""",
            encoding="utf-8",
        )
        fake_auth_smoke.chmod(fake_auth_smoke.stat().st_mode | stat.S_IXUSR)

        bin_dir = tmpdir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        fake_gh = bin_dir / "gh"
        fake_gh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IXUSR)

        return tmpdir, script_copy, bin_dir

    def test_oneshot_cycle_writes_blocker_note_without_backtick_command_substitution(self):
        tmpdir, script_copy, bin_dir = self._prepare_fixture()

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["NIGHT_WORKER_ONESHOT"] = "1"
        env["NIGHT_WORKER_INTERVAL_SECONDS"] = "1"
        env["NIGHT_WORKER_GHA_BIN"] = str(tmpdir / "scripts" / "gha")
        env["NIGHT_WORKER_BLOCKER_RETRY_SCRIPT"] = str(
            tmpdir / "scripts" / "blocker_retry_supervisor.py"
        )
        env["NIGHT_WORKER_AUTH_SMOKE_SCRIPT"] = str(
            tmpdir / "scripts" / "smoke" / "run_auth_perimeter_smoke_bundle.sh"
        )

        result = subprocess.run(
            [str(script_copy)],
            cwd=str(tmpdir),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn("No such file or directory", result.stderr)

        blocker_notes = sorted((tmpdir / "reports" / "nightworker").glob("*-blockers.md"))
        self.assertEqual(len(blocker_notes), 1)

        note = blocker_notes[0].read_text(encoding="utf-8")
        self.assertIn("- Worktree: `", note)
        self.assertIn("- Blocked-Issues-Snapshot: `", note)
        self.assertIn("- CI-Snapshot: `", note)
        self.assertIn("- Runtime-Log: `", note)
        self.assertIn("- Auth-Summary: `", note)


if __name__ == "__main__":
    unittest.main()
