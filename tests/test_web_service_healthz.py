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


def _wait_for(url: str, timeout_seconds: float = 12.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Endpoint nicht erreichbar: {url}")


def _http_json(method: str, url: str) -> tuple[int, dict[str, str], dict]:
    req = request.Request(url, method=method, headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return int(resp.status), dict(resp.headers), json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        payload = json.loads(body) if body else {}
        return int(exc.code), dict(exc.headers), payload


class TestWebServiceHealthz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "PYTHONPATH": str(REPO_ROOT),
                # Ensure no outbound calls are needed.
                "ENABLE_E2E_FAULT_INJECTION": "1",
                "APP_VERSION": "dev-test",
                "GIT_SHA": "deadbeef",
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

        _wait_for(f"{cls.base_url}/health")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
            cls.proc.wait(timeout=5)
        finally:
            if cls.proc.stdout is not None:
                cls.proc.stdout.close()
            if cls.proc.stderr is not None:
                cls.proc.stderr.close()

    def test_healthz_schema_and_cache_control(self):
        status, headers, payload = _http_json("GET", f"{self.base_url}/healthz")
        self.assertEqual(status, 200)
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("status"), "ok")
        self.assertEqual(payload.get("service"), "geo-ranking-ch")
        self.assertIsInstance(payload.get("timestamp"), str)
        self.assertTrue(str(payload.get("timestamp")).strip())

        build = payload.get("build")
        self.assertIsInstance(build, dict)
        assert isinstance(build, dict)
        self.assertEqual(build.get("version"), "dev-test")
        self.assertEqual(build.get("commit"), "deadbeef")

        self.assertIsInstance(payload.get("request_id"), str)
        self.assertTrue(str(payload.get("request_id")).strip())

        # /healthz is dev-only and should not be cached.
        self.assertEqual(headers.get("Cache-Control"), "no-store")

    def test_healthz_tolerates_query_params(self):
        status, _, payload = _http_json("GET", f"{self.base_url}/healthz/?probe=1")
        self.assertEqual(status, 200)
        self.assertTrue(payload.get("ok"))
