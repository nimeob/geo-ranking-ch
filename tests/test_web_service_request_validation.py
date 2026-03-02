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


def _http_raw(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], dict | None]:
    merged_headers = {"Accept": "application/json"}
    if headers:
        merged_headers.update(headers)

    req = request.Request(url, data=body, headers=merged_headers, method=method)
    try:
        with request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8") if resp.length not in (None, 0) else ""
            payload = json.loads(raw) if raw else None
            return int(resp.status), dict(resp.headers), payload
    except error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
            return int(exc.code), dict(exc.headers), payload
        finally:
            exc.close()


class TestWebServiceRequestValidation(unittest.TestCase):
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
                # No external calls needed; invalid requests fail fast.
                "ENABLE_E2E_FAULT_INJECTION": "1",
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

    def _assert_bad_request(self, status: int, payload: dict | None, *, message_contains: str):
        self.assertEqual(status, 400)
        self.assertIsInstance(payload, dict)
        assert isinstance(payload, dict)
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("error"), "bad_request")
        self.assertIn(message_contains, str(payload.get("message")))
        self.assertIsInstance(payload.get("request_id"), str)
        self.assertTrue(str(payload.get("request_id")).strip())

    def test_rejects_empty_body(self):
        status, _, payload = _http_raw(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Content-Type": "application/json"},
            body=b"",
        )
        self._assert_bad_request(status, payload, message_contains="empty body")

    def test_rejects_invalid_json(self):
        status, _, payload = _http_raw(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Content-Type": "application/json"},
            body=b"{",
        )
        self._assert_bad_request(status, payload, message_contains="invalid json")

    def test_rejects_non_object_json_body(self):
        status, _, payload = _http_raw(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Content-Type": "application/json"},
            body=json.dumps([{"query": "X"}]).encode("utf-8"),
        )
        self._assert_bad_request(status, payload, message_contains="json body must be an object")

    def test_rejects_missing_query_when_no_coordinates(self):
        status, _, payload = _http_raw(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Content-Type": "application/json"},
            body=json.dumps({}).encode("utf-8"),
        )
        self._assert_bad_request(status, payload, message_contains="query is required")

    def test_rejects_invalid_intelligence_mode(self):
        status, _, payload = _http_raw(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"query": "St. Gallen", "intelligence_mode": "unknown"}).encode("utf-8"),
        )
        self._assert_bad_request(status, payload, message_contains="intelligence_mode must be one of")


if __name__ == "__main__":
    unittest.main()
