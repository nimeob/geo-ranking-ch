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
SCRIPT = REPO_ROOT / "scripts" / "check_bl335_frontdoor_runtime.py"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for(url: str, timeout_seconds: float = 12.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Endpoint nicht erreichbar: {url}")


class TestCheckBl335FrontdoorRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_port = _free_port()
        cls.ui_port = _free_port()

        cls.api_base_url = f"http://127.0.0.1:{cls.api_port}"
        cls.ui_base_url = f"http://127.0.0.1:{cls.ui_port}"
        cls.extra_allowed_origin = "https://www.dev.georanking.ch"

        api_env = os.environ.copy()
        api_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.api_port),
                "PYTHONPATH": str(REPO_ROOT),
                "CORS_ALLOW_ORIGINS": f"{cls.ui_base_url},{cls.extra_allowed_origin}",
            }
        )
        cls.api_proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=api_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        ui_env = os.environ.copy()
        ui_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.ui_port),
                "UI_API_BASE_URL": "https://api.dev.georanking.ch",
                "PYTHONPATH": str(REPO_ROOT),
            }
        )
        cls.ui_proc = subprocess.Popen(
            [sys.executable, "-m", "src.ui_service"],
            cwd=str(REPO_ROOT),
            env=ui_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        _wait_for(f"{cls.api_base_url}/health")
        _wait_for(f"{cls.ui_base_url}/healthz")

    @classmethod
    def tearDownClass(cls):
        for proc in (cls.api_proc, cls.ui_proc):
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _run_guardrail(self, *args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bl335-runtime-check.json"
            cmd = [
                sys.executable,
                str(SCRIPT),
                "--ui-health-url",
                f"{self.ui_base_url}/healthz",
                "--api-analyze-url",
                f"{self.api_base_url}/analyze",
                "--output-json",
                str(output_path),
                *args,
            ]
            cp = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            return cp, payload

    def test_guardrail_passes_for_expected_frontdoor_and_cors_origins(self):
        cp, payload = self._run_guardrail(
            "--expected-api-base-url",
            "https://api.dev.georanking.ch",
            "--expected-ui-origin",
            self.ui_base_url,
            "--expected-ui-origin",
            self.extra_allowed_origin,
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(payload["overall"]["status"], "pass")
        self.assertEqual(payload["checks"]["ui_health"]["status"], "pass")
        self.assertEqual(payload["checks"]["cors_preflight"]["status"], "pass")

    def test_guardrail_fails_when_ui_uses_unexpected_api_base_url(self):
        cp, payload = self._run_guardrail(
            "--expected-api-base-url",
            "https://api.dev.geo-ranking.ch",
            "--expected-ui-origin",
            self.ui_base_url,
        )

        self.assertEqual(cp.returncode, 1, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(payload["overall"]["status"], "fail")
        self.assertEqual(payload["checks"]["ui_health"]["reason"], "api_base_url_mismatch")

    def test_guardrail_fails_when_cors_origin_is_missing(self):
        cp, payload = self._run_guardrail(
            "--expected-api-base-url",
            "https://api.dev.georanking.ch",
            "--expected-ui-origin",
            self.ui_base_url,
            "--expected-ui-origin",
            "https://www.dev.geo-ranking.ch",
        )

        self.assertEqual(cp.returncode, 1, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(payload["overall"]["status"], "fail")
        self.assertEqual(payload["checks"]["cors_preflight"]["reason"], "cors_preflight_failed")

    def test_invalid_timeout_returns_exit_code_2(self):
        cp = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--ui-health-url",
                f"{self.ui_base_url}/healthz",
                "--api-analyze-url",
                f"{self.api_base_url}/analyze",
                "--expected-api-base-url",
                "https://api.dev.georanking.ch",
                "--expected-ui-origin",
                self.ui_base_url,
                "--timeout-seconds",
                "0",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )

        self.assertEqual(cp.returncode, 2)
        self.assertIn("timeout-seconds must be > 0", cp.stdout)


if __name__ == "__main__":
    unittest.main()
