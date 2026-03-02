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
        status_a, body_a = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            headers={**self._auth_headers(self.user_a["token"]), "X-Org-Id": "evil-org"},
            payload={
                "query": "Bahnhofstrasse 1, 8001 Zürich",
                "intelligence_mode": "basic",
                "options": {"async_mode": {"requested": True}},
            },
        )
        self.assertEqual(status_a, 202)
        self.assertTrue(body_a.get("ok"))
        job_id_a = str(body_a.get("job", {}).get("job_id") or "")
        self.assertTrue(job_id_a)

        status_job_a, body_job_a = self._poll_job_completed(job_id=job_id_a, token=self.user_a["token"])
        self.assertEqual(status_job_a, 200)
        result_id_a = str(body_job_a.get("job", {}).get("result_id") or "")
        self.assertTrue(result_id_a)

        # Create async job as user B.
        status_b, body_b = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            headers=self._auth_headers(self.user_b["token"]),
            payload={
                "query": "Limmatquai 12, 8001 Zürich",
                "intelligence_mode": "basic",
                "options": {"async_mode": {"requested": True}},
            },
        )
        self.assertEqual(status_b, 202)
        self.assertTrue(body_b.get("ok"))
        job_id_b = str(body_b.get("job", {}).get("job_id") or "")
        self.assertTrue(job_id_b)

        status_job_b, body_job_b = self._poll_job_completed(job_id=job_id_b, token=self.user_b["token"])
        self.assertEqual(status_job_b, 200)
        result_id_b = str(body_job_b.get("job", {}).get("result_id") or "")
        self.assertTrue(result_id_b)

        # Store must reflect server-side owner resolution (client cannot choose X-Org-Id).
        store = AsyncJobStore(store_file=self._store_file)
        job_record_a = store.get_job(job_id_a)
        job_record_b = store.get_job(job_id_b)
        self.assertIsInstance(job_record_a, dict)
        self.assertIsInstance(job_record_b, dict)

        self.assertEqual(job_record_a.get("org_id"), self.user_a["org_id"])
        self.assertEqual(job_record_a.get("owner_org_id"), self.user_a["org_id"])
        self.assertEqual(job_record_a.get("owner_user_id"), self.user_a["user_id"])

        self.assertEqual(job_record_b.get("org_id"), self.user_b["org_id"])
        self.assertEqual(job_record_b.get("owner_org_id"), self.user_b["org_id"])
        self.assertEqual(job_record_b.get("owner_user_id"), self.user_b["user_id"])

        result_record_a = store.get_result(result_id_a)
        result_record_b = store.get_result(result_id_b)
        self.assertIsInstance(result_record_a, dict)
        self.assertIsInstance(result_record_b, dict)
        self.assertEqual(result_record_a.get("owner_user_id"), self.user_a["user_id"])
        self.assertEqual(result_record_a.get("owner_org_id"), self.user_a["org_id"])
        self.assertEqual(result_record_b.get("owner_user_id"), self.user_b["user_id"])
        self.assertEqual(result_record_b.get("owner_org_id"), self.user_b["org_id"])

        # /analyze/history: 401 without token
        status_history_anon, body_history_anon = _http_json("GET", f"{self.base_url}/analyze/history")
        self.assertEqual(status_history_anon, 401)
        self.assertFalse(body_history_anon.get("ok"))
        self.assertEqual(body_history_anon.get("error"), "unauthorized")

        # User A sees only their own result_id.
        status_history_a, body_history_a = _http_json(
            "GET",
            f"{self.base_url}/analyze/history",
            headers=self._auth_headers(self.user_a["token"]),
        )
        self.assertEqual(status_history_a, 200)
        history_rows_a = body_history_a.get("history", [])
        self.assertTrue(any(str(row.get("result_id") or "") == result_id_a for row in history_rows_a))
        self.assertFalse(any(str(row.get("result_id") or "") == result_id_b for row in history_rows_a))

        # User B sees only their own result_id.
        status_history_b, body_history_b = _http_json(
            "GET",
            f"{self.base_url}/analyze/history",
            headers=self._auth_headers(self.user_b["token"]),
        )
        self.assertEqual(status_history_b, 200)
        history_rows_b = body_history_b.get("history", [])
        self.assertTrue(any(str(row.get("result_id") or "") == result_id_b for row in history_rows_b))
        self.assertFalse(any(str(row.get("result_id") or "") == result_id_a for row in history_rows_b))

        # Cross-access must be blocked.
        status_result_a_as_b, _ = _http_json(
            "GET",
            f"{self.base_url}/analyze/results/{result_id_a}",
            headers=self._auth_headers(self.user_b["token"]),
        )
        self.assertEqual(status_result_a_as_b, 404)

        status_result_b_as_a, _ = _http_json(
            "GET",
            f"{self.base_url}/analyze/results/{result_id_b}",
            headers=self._auth_headers(self.user_a["token"]),
        )
        self.assertEqual(status_result_b_as_a, 404)

        # Owner can access.
        status_result_a, body_result_a = _http_json(
            "GET",
            f"{self.base_url}/analyze/results/{result_id_a}",
            headers=self._auth_headers(self.user_a["token"]),
        )
        self.assertEqual(status_result_a, 200)
        self.assertTrue(body_result_a.get("ok"))

        status_result_b, body_result_b = _http_json(
            "GET",
            f"{self.base_url}/analyze/results/{result_id_b}",
            headers=self._auth_headers(self.user_b["token"]),
        )
        self.assertEqual(status_result_b, 200)
        self.assertTrue(body_result_b.get("ok"))


if __name__ == "__main__":
    unittest.main()
