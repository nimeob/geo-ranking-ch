import json
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


def _http_get(url: str, *, timeout: float = 10.0):
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return (
                resp.status,
                resp.read().decode("utf-8"),
                {k.lower(): v for k, v in resp.headers.items()},
            )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, body, headers


class TestTraceLegacyDeprecation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "APP_VERSION": "test-trace-legacy-deprecation-v1",
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
                status, _, _ = _http_get(f"{cls.base_url}/health")
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

    def test_trace_legacy_alias_returns_gone_with_deprecation_headers(self):
        status, body, headers = _http_get(f"{self.base_url}/trace?request_id=req-legacy-1")
        self.assertEqual(status, 410)

        payload = json.loads(body)
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("error"), "gone")
        self.assertEqual(payload.get("next"), "/debug/trace?request_id=<id>")

        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(headers.get("deprecation"), "true")
        self.assertTrue((headers.get("sunset") or "").strip())
        self.assertIn("deprecated", str(headers.get("warning") or "").lower())
        self.assertIn('rel="deprecation"', str(headers.get("link") or ""))
        self.assertIn('rel="successor-version"', str(headers.get("link") or ""))
        self.assertIn("/debug/trace", str(headers.get("link") or ""))

        dep = payload.get("deprecation") or {}
        self.assertEqual(dep.get("successor"), "/debug/trace?request_id=<id>")
        self.assertEqual(dep.get("scope"), "trace-debug-legacy-alias")
        self.assertEqual(dep.get("sunset"), headers.get("sunset"))


if __name__ == "__main__":
    unittest.main()
