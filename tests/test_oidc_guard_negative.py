import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(method: str, url: str, payload=None, headers=None, timeout: float = 10.0):
    data = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, method=method, data=data, headers=req_headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return exc.code, parsed


class TestOidcGuardNegative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="oidc-guard-")
        cls._store_file = Path(cls._tmpdir.name) / "store.v1.json"

        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "PYTHONPATH": str(REPO_ROOT),
                # Enable OIDC auth mode (no JWKS fetch should occur for missing/malformed tokens).
                "OIDC_JWKS_URL": "https://example.invalid/.well-known/jwks.json",
                # Async runtime store isolation.
                "ASYNC_JOBS_STORE_FILE": str(cls._store_file),
            }
        )

        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _ = _http_json("GET", f"{cls.base_url}/health")
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
        cls._tmpdir.cleanup()

    def test_analyze_requires_bearer_token_when_oidc_enabled(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            payload={"query": "St. Leonhard-Strasse 40, St. Gallen", "intelligence_mode": "basic"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(body.get("error"), "unauthorized")

    def test_analyze_history_requires_bearer_token_when_oidc_enabled(self):
        status, body = _http_json("GET", f"{self.base_url}/analyze/history")
        self.assertEqual(status, 401)
        self.assertEqual(body.get("error"), "unauthorized")

    def test_malformed_bearer_token_is_rejected(self):
        headers = {"Authorization": "Bearer not-a-jwt"}

        status_history, body_history = _http_json(
            "GET",
            f"{self.base_url}/analyze/history",
            headers=headers,
        )
        self.assertEqual(status_history, 401)
        self.assertEqual(body_history.get("error"), "unauthorized")

        status_analyze, body_analyze = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            headers=headers,
            payload={"query": "St. Leonhard-Strasse 40, St. Gallen", "intelligence_mode": "basic"},
        )
        self.assertEqual(status_analyze, 401)
        self.assertEqual(body_analyze.get("error"), "unauthorized")

    def test_jobs_requires_bearer_token_when_oidc_enabled(self):
        """GET /analyze/jobs/<id> without token must return 401, not 404, when OIDC auth is enabled."""
        status, body = _http_json("GET", f"{self.base_url}/analyze/jobs/nonexistent-job-id")
        self.assertEqual(status, 401)
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("error"), "unauthorized")

    def test_results_requires_bearer_token_when_oidc_enabled(self):
        """GET /analyze/results/<id> without token must return 401, not 404, when OIDC auth is enabled."""
        status, body = _http_json("GET", f"{self.base_url}/analyze/results/nonexistent-result-id")
        self.assertEqual(status, 401)
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("error"), "unauthorized")

    def test_notifications_requires_bearer_token_when_oidc_enabled(self):
        """GET /analyze/jobs/<id>/notifications without token must return 401 when OIDC auth is enabled."""
        status, body = _http_json(
            "GET", f"{self.base_url}/analyze/jobs/nonexistent-job-id/notifications"
        )
        self.assertEqual(status, 401)
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("error"), "unauthorized")

    def test_cancel_requires_bearer_token_when_oidc_enabled(self):
        """POST /analyze/jobs/<id>/cancel without token must return 401 when OIDC auth is enabled."""
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze/jobs/nonexistent-job-id/cancel",
            payload={"reason": "test"},
        )
        self.assertEqual(status, 401)
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("error"), "unauthorized")

    def test_health_remains_public_when_oidc_enabled(self):
        """GET /health and /healthz must remain accessible without token even with OIDC enabled."""
        for path in ("/health", "/healthz"):
            status, body = _http_json("GET", f"{self.base_url}{path}")
            self.assertEqual(status, 200, f"{path} should return 200 without auth")
            self.assertTrue(body.get("ok"), f"{path} body should be ok")


if __name__ == "__main__":
    unittest.main()
