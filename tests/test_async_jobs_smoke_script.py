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
SCRIPT = REPO_ROOT / "scripts" / "run_async_jobs_smoketest.py"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for(url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Endpoint nicht erreichbar: {url}")


class TestAsyncJobsSmokeScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_port = _free_port()
        cls.api_base_url = f"http://127.0.0.1:{cls.api_port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.api_port),
                "PYTHONPATH": str(REPO_ROOT),
                "ENABLE_E2E_FAULT_INJECTION": "1",
                "ASYNC_WORKER_STAGE_DELAY_MS": "0",
            }
        )

        cls.api_proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        _wait_for(f"{cls.api_base_url}/health")

    @classmethod
    def tearDownClass(cls):
        cls.api_proc.terminate()
        try:
            cls.api_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.api_proc.kill()

    def test_script_can_submit_poll_and_fetch_result_locally(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "async-jobs-smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "PYTHONPATH": str(REPO_ROOT),
                }
            )

            cp = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--api-base-url",
                    self.api_base_url,
                    "--query",
                    "__ok__",
                    "--poll-timeout-seconds",
                    "15",
                    "--poll-interval-seconds",
                    "0.05",
                    "--output-json",
                    str(output_path),
                ],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIs(payload.get("ok"), True)
            self.assertEqual(payload["job"]["status"], "completed")
            self.assertTrue(payload["job"]["job_id"])
            self.assertTrue(payload["job"]["result_id"])


if __name__ == "__main__":
    unittest.main()
