import json
import os
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_issue_1039_mobile_overflow_smoke.cjs"


class TestIssue1039MobileOverflowSmokeScript(unittest.TestCase):
    def test_unreachable_local_base_url_emits_structured_hint(self) -> None:
        env = os.environ.copy()
        env["BASE_URL"] = "http://127.0.0.1:9/gui"
        env["BASE_URL_PROBE_TIMEOUT_MS"] = "1200"

        result = subprocess.run(
            ["node", str(SCRIPT_PATH)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=45,
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + "\n" + result.stderr)
        output_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        self.assertTrue(output_lines, msg=f"script stdout leer; stderr={result.stderr}")

        evidence_rel_path = output_lines[-1]
        evidence_path = REPO_ROOT / evidence_rel_path
        self.assertTrue(evidence_path.is_file(), msg=f"Evidence fehlt: {evidence_rel_path}")

        payload = json.loads(evidence_path.read_text(encoding="utf-8"))

        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("runError", {}).get("kind"), "base_url_unreachable")
        self.assertIn(
            payload.get("runError", {}).get("reasonCode"),
            {"connection_refused", "timeout", "unreachable", "connection_reset", "dns_not_found"},
        )

        hint = payload.get("runError", {}).get("hint", "")
        self.assertIn("HOST=127.0.0.1", hint)
        self.assertIn("python3 -m src.web_service", hint)

        runtime = payload.get("runtime", {})
        self.assertFalse(runtime.get("baseUrlReachable", True))
        self.assertIn("playwrightDependencyMissing", runtime)


if __name__ == "__main__":
    unittest.main()
