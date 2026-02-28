import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib import error, request

from src.web_service import _parse_cors_allow_origins


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


def _http_json(method: str, url: str, *, headers: dict[str, str] | None = None, payload: dict | None = None):
    data = None
    merged_headers = {"Accept": "application/json"}
    if headers:
        merged_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        merged_headers.setdefault("Content-Type", "application/json")
    req = request.Request(url, data=data, headers=merged_headers, method=method)
    with request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8") if resp.length not in (None, 0) else ""
        parsed = json.loads(body) if body else None
        return resp.status, resp.headers, parsed


class TestCorsAllowlistParsing(unittest.TestCase):
    def test_parses_valid_origins_and_ignores_invalid_chunks(self):
        parsed = _parse_cors_allow_origins(
            " https://app.example.test ,http://127.0.0.1:8081,not-an-origin,https://app.example.test/path "
        )
        self.assertEqual(
            parsed,
            {
                "https://app.example.test",
                "http://127.0.0.1:8081",
            },
        )


class TestWebServiceCorsBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.allowed_origin = "http://app.example.test"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "PYTHONPATH": str(REPO_ROOT),
                "ENABLE_E2E_FAULT_INJECTION": "1",
                "CORS_ALLOW_ORIGINS": cls.allowed_origin,
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

    def test_options_preflight_allows_configured_origin(self):
        status, headers, body = _http_json(
            "OPTIONS",
            f"{self.base_url}/analyze",
            headers={
                "Origin": self.allowed_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization,x-request-id",
            },
        )

        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), self.allowed_origin)
        self.assertEqual(headers.get("Access-Control-Allow-Methods"), "POST, OPTIONS")

    def test_options_preflight_rejects_disallowed_origin(self):
        req = request.Request(
            f"{self.base_url}/analyze",
            headers={
                "Accept": "application/json",
                "Origin": "https://evil.example.test",
                "Access-Control-Request-Method": "POST",
            },
            method="OPTIONS",
        )
        with self.assertRaises(error.HTTPError) as ctx:
            request.urlopen(req, timeout=10)

        resp = ctx.exception
        self.assertEqual(resp.code, 403)
        payload = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(payload.get("error"), "cors_origin_not_allowed")

    def test_post_sets_allow_origin_for_allowed_request_origin(self):
        status, headers, payload = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Origin": self.allowed_origin},
            payload={"query": "__ok__", "intelligence_mode": "basic"},
        )

        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), self.allowed_origin)
        self.assertTrue(payload.get("ok"))

    def test_post_rejects_disallowed_origin(self):
        req = request.Request(
            f"{self.base_url}/analyze",
            data=json.dumps({"query": "__ok__"}).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://evil.example.test",
            },
            method="POST",
        )
        with self.assertRaises(error.HTTPError) as ctx:
            request.urlopen(req, timeout=10)

        resp = ctx.exception
        self.assertEqual(resp.code, 403)
        payload = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(payload.get("error"), "cors_origin_not_allowed")


if __name__ == "__main__":
    unittest.main()
