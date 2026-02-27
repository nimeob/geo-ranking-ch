import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_text(url: str, *, timeout: float = 10.0):
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return (
                resp.status,
                resp.read().decode("utf-8"),
                {k.lower(): v for k, v in resp.headers.items()},
            )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, body, headers


class TestWebServiceGuiMvp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "APP_VERSION": "test-gui-v1",
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

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _, _ = _http_text(f"{cls.base_url}/health")
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("web_service wurde lokal nicht rechtzeitig erreichbar")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def test_gui_shell_is_served_with_html_content_type(self):
        status, body, headers = _http_text(f"{self.base_url}/gui")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("geo-ranking.ch GUI MVP", body)
        self.assertIn('id="gui-shell-nav"', body)
        self.assertIn('id="analyze-form"', body)
        self.assertIn("Version test-gui-v1", body)

    def test_gui_shell_exposes_state_machine_markers(self):
        status, body, _ = _http_text(f"{self.base_url}/gui")
        self.assertEqual(status, 200)
        self.assertIn('Status: idle', body)
        self.assertIn('idle -> loading -> success/error', body)
        self.assertIn('id="error-box"', body)
        self.assertIn('id="map-click-surface"', body)
        self.assertIn('id="map-click-marker"', body)
        self.assertIn('id="core-factors"', body)
        self.assertIn('coordinates.lat/lon', body)

    def test_gui_route_accepts_trailing_slash_query_and_double_slash(self):
        status, body, _ = _http_text(f"{self.base_url}//gui///?probe=1")
        self.assertEqual(status, 200)
        self.assertIn("Result-Panel", body)


if __name__ == "__main__":
    unittest.main()
