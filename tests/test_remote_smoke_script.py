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
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "run_remote_api_smoketest.sh"


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


class TestRemoteSmokeScript(unittest.TestCase):
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

    def _run_smoke(
        self, *, include_token: bool
    ) -> tuple[subprocess.CompletedProcess[str], dict, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            request_id = f"bl18-smoke-test-{int(time.time() * 1000)}"
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
                    "SMOKE_REQUEST_ID": request_id,
                    "SMOKE_OUTPUT_JSON": str(out_json),
                }
            )
            if include_token:
                env["DEV_API_AUTH_TOKEN"] = "bl18-token"
            else:
                env.pop("DEV_API_AUTH_TOKEN", None)

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            data = json.loads(out_json.read_text(encoding="utf-8"))
            return cp, data, request_id

    def test_smoke_script_passes_with_valid_token(self):
        cp, data, request_id = self._run_smoke(include_token=True)
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertIn("query", data.get("result_keys", []))
        self.assertTrue(data.get("request_id_echo_enforced"))
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_fails_without_token_when_auth_enabled(self):
        cp, data, _ = self._run_smoke(include_token=False)
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(data.get("status"), "fail")
        self.assertEqual(data.get("reason"), "http_status")
        self.assertEqual(data.get("http_status"), 401)


if __name__ == "__main__":
    unittest.main()
