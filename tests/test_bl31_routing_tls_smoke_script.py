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
SCRIPT = REPO_ROOT / "scripts" / "run_bl31_routing_tls_smoke.sh"


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


class TestBl31RoutingTlsSmokeScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_port = _free_port()
        cls.ui_port = _free_port()
        cls.api_base_url = f"http://127.0.0.1:{cls.api_port}"
        cls.ui_base_url = f"http://127.0.0.1:{cls.ui_port}"

        api_env = os.environ.copy()
        api_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.api_port),
                "PYTHONPATH": str(REPO_ROOT),
                "CORS_ALLOW_ORIGINS": cls.ui_base_url,
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
                "UI_API_BASE_URL": cls.api_base_url,
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

    def _run_smoke(self, *, strict_cors: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bl31-smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "BL31_API_BASE_URL": self.api_base_url,
                    "BL31_APP_BASE_URL": self.ui_base_url,
                    "BL31_CORS_ORIGIN": self.ui_base_url,
                    "BL31_STRICT_CORS": strict_cors,
                    "BL31_OUTPUT_JSON": str(output_path),
                    "BL31_CURL_MAX_TIME": "5",
                }
            )
            cp = subprocess.run(
                [str(SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            return cp, payload

    def test_smoke_baseline_mode_is_reproducible_with_structured_output(self):
        cp, payload = self._run_smoke(strict_cors="0")

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(payload["overall"]["status"], "pass")
        self.assertEqual(payload["checks"]["api_health"]["status"], "pass")
        self.assertEqual(payload["checks"]["app_reachability"]["status"], "pass")
        self.assertEqual(payload["checks"]["cors_baseline"]["status"], "pass")
        self.assertIn("[BL-31] API health", cp.stdout)
        self.assertIn("[BL-31] CORS baseline", cp.stdout)

    def test_strict_mode_is_green_with_configured_allowlist(self):
        cp, payload = self._run_smoke(strict_cors="1")

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(payload["overall"]["status"], "pass")
        self.assertEqual(payload["checks"]["cors_baseline"]["status"], "pass")

    def test_invalid_api_base_url_fails_fast(self):
        env = os.environ.copy()
        env.update(
            {
                "BL31_API_BASE_URL": "not-a-url",
                "BL31_APP_BASE_URL": self.ui_base_url,
            }
        )

        cp = subprocess.run(
            [str(SCRIPT)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(cp.returncode, 2)
        self.assertIn("BL31_API_BASE_URL muss eine gültige http(s)-Base-URL", cp.stderr)


if __name__ == "__main__":
    unittest.main()
