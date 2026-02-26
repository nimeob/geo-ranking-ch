import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib import request


REPO_ROOT = Path(__file__).resolve().parents[1]
STABILITY_SCRIPT = REPO_ROOT / "scripts" / "run_remote_api_stability_check.sh"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_health(base_url: str, timeout_seconds: float = 12.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with request.urlopen(f"{base_url}/health", timeout=2):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("web_service wurde lokal nicht rechtzeitig erreichbar")


class TestRemoteStabilityScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "API_AUTH_TOKEN": "bl18-token",
                "ENABLE_E2E_FAULT_INJECTION": "1",
                "PYTHONPATH": str(REPO_ROOT),
            }
        )
        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _wait_for_health(cls.base_url)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def _run_stability(
        self,
        *,
        include_token: bool,
        runs: int,
        max_failures: int,
        stop_on_first_fail: int,
    ) -> tuple[subprocess.CompletedProcess[str], list[dict]]:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "stability.ndjson"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "CURL_MAX_TIME": "10",
                    "CURL_RETRY_COUNT": "1",
                    "CURL_RETRY_DELAY": "1",
                    "STABILITY_RUNS": str(runs),
                    "STABILITY_INTERVAL_SECONDS": "0",
                    "STABILITY_MAX_FAILURES": str(max_failures),
                    "STABILITY_STOP_ON_FIRST_FAIL": str(stop_on_first_fail),
                    "STABILITY_REPORT_PATH": str(report_path),
                }
            )
            if include_token:
                env["DEV_API_AUTH_TOKEN"] = "bl18-token"
            else:
                env.pop("DEV_API_AUTH_TOKEN", None)

            cp = subprocess.run(
                [str(STABILITY_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            entries = []
            if report_path.exists():
                entries = [
                    json.loads(line)
                    for line in report_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            return cp, entries

    def test_stability_runner_passes_for_two_successful_runs(self):
        cp, entries = self._run_stability(
            include_token=True, runs=2, max_failures=0, stop_on_first_fail=0
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(len(entries), 2)
        for idx, row in enumerate(entries, start=1):
            self.assertEqual(row.get("run_no"), idx)
            self.assertEqual(row.get("status"), "pass")
            self.assertEqual(row.get("reason"), "ok")
            self.assertEqual(row.get("http_status"), 200)
            self.assertTrue(str(row.get("request_id", "")).startswith(f"bl18-stability-{idx}-"))
            self.assertEqual(row.get("response_request_id"), row.get("request_id"))
            self.assertEqual(row.get("response_header_request_id"), row.get("request_id"))

    def test_stability_runner_stops_on_first_failure_when_configured(self):
        cp, entries = self._run_stability(
            include_token=False, runs=4, max_failures=0, stop_on_first_fail=1
        )

        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("Abbruch nach erstem Fehlrun", cp.stdout)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].get("run_no"), 1)
        self.assertEqual(entries[0].get("status"), "fail")
        self.assertEqual(entries[0].get("reason"), "http_status")
        self.assertEqual(entries[0].get("http_status"), 401)

    def test_stability_runner_rejects_invalid_stop_on_first_fail_flag(self):
        cp, entries = self._run_stability(
            include_token=True, runs=2, max_failures=0, stop_on_first_fail=2
        )

        self.assertEqual(cp.returncode, 2)
        self.assertIn("STABILITY_STOP_ON_FIRST_FAIL muss 0 oder 1 sein", cp.stderr)
        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
