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

from src.api.async_jobs import AsyncJobStore


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


class TestAuthPhase1Core(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="auth-phase1-")
        cls._store_file = Path(cls._tmpdir.name) / "store.v1.json"

        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.user_a = {"token": "token-user-a", "user_id": "user-a", "org_id": "org-a"}
        cls.user_b = {"token": "token-user-b", "user_id": "user-b", "org_id": "org-b"}

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "PYTHONPATH": str(REPO_ROOT),
                # Auth phase 1 (Core)
                "PHASE1_AUTH_USERS_JSON": json.dumps({"users": [cls.user_a, cls.user_b]}),
                # Async runtime
                "ASYNC_JOBS_STORE_FILE": str(cls._store_file),
                "ASYNC_WORKER_STAGE_DELAY_MS": "250",
                "ENABLE_E2E_FAULT_INJECTION": "1",
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

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _poll_job_completed(self, *, job_id: str, token: str, timeout_seconds: float = 12.0):
        deadline = time.time() + timeout_seconds
        last_status = 0
        last_body = {}
        while time.time() < deadline:
            status, body = _http_json(
                "GET",
                f"{self.base_url}/analyze/jobs/{job_id}",
                headers=self._auth_headers(token),
            )
            last_status = status
            last_body = body
            if status == 200 and str(body.get("job", {}).get("status") or "") == "completed":
                return status, body
            time.sleep(0.15)
        return last_status, last_body

    def test_phase1_auth_guards_and_per_user_isolation(self):
        # Create async job as user A. X-Org-Id must be ignored when token is mapped.
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            headers={**self._auth_headers(self.user_a["token"]), "X-Org-Id": "evil-org"},
            payload={
                "query": "Bahnhofstrasse 1, 8001 Zürich",
                "intelligence_mode": "basic",
                "options": {"async_mode": {"requested": True}},
            },
        )
        self.assertEqual(status, 202)
        self.assertTrue(body.get("ok"))
        job_id = str(body.get("job", {}).get("job_id") or "")
        self.assertTrue(job_id)

        # Store must reflect server-side org resolution (client cannot choose).
        store = AsyncJobStore(store_file=self._store_file)
        job_record = store.get_job(job_id)
        self.assertIsInstance(job_record, dict)
        self.assertEqual(job_record.get("org_id"), self.user_a["org_id"])

        status_job, body_job = self._poll_job_completed(job_id=job_id, token=self.user_a["token"])
        self.assertEqual(status_job, 200)
        result_id = str(body_job.get("job", {}).get("result_id") or "")
        self.assertTrue(result_id)

        # /analyze/history: 401 without token
        status_history_anon, body_history_anon = _http_json(
            "GET", f"{self.base_url}/analyze/history"
        )
        self.assertEqual(status_history_anon, 401)
        self.assertFalse(body_history_anon.get("ok"))
        self.assertEqual(body_history_anon.get("error"), "unauthorized")

        # User A can see their own history.
        status_history_a, body_history_a = _http_json(
            "GET",
            f"{self.base_url}/analyze/history",
            headers=self._auth_headers(self.user_a["token"]),
        )
        self.assertEqual(status_history_a, 200)
        self.assertTrue(body_history_a.get("ok"))
        history_rows_a = body_history_a.get("history", [])
        self.assertTrue(
            any(str(row.get("result_id") or "") == result_id for row in history_rows_a),
            "User A history sollte das soeben erzeugte result_id enthalten",
        )

        # User B cannot enumerate/access User A's job/result.
        status_result_b, _ = _http_json(
            "GET",
            f"{self.base_url}/analyze/results/{result_id}",
            headers=self._auth_headers(self.user_b["token"]),
        )
        self.assertEqual(status_result_b, 404)

        status_job_b, _ = _http_json(
            "GET",
            f"{self.base_url}/analyze/jobs/{job_id}",
            headers=self._auth_headers(self.user_b["token"]),
        )
        self.assertEqual(status_job_b, 404)

        status_notifications_b, _ = _http_json(
            "GET",
            f"{self.base_url}/analyze/jobs/{job_id}/notifications?channel=in_app",
            headers=self._auth_headers(self.user_b["token"]),
        )
        self.assertEqual(status_notifications_b, 404)

        # User A can access result.
        status_result_a, body_result_a = _http_json(
            "GET",
            f"{self.base_url}/analyze/results/{result_id}",
            headers=self._auth_headers(self.user_a["token"]),
        )
        self.assertEqual(status_result_a, 200)
        self.assertTrue(body_result_a.get("ok"))
        self.assertEqual(body_result_a.get("result_id"), result_id)


if __name__ == "__main__":
    unittest.main()
