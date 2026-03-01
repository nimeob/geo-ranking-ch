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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


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


class TestAsyncJobsRuntimeSkeleton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory(prefix="async-jobs-runtime-")
        cls._store_file = Path(cls._tmpdir.name) / "store.v1.json"

        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "PYTHONPATH": str(REPO_ROOT),
                "API_AUTH_TOKEN": "async-token",
                "ASYNC_JOBS_STORE_FILE": str(cls._store_file),
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

    def test_async_analyze_creates_persistent_job_and_result(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Authorization": "Bearer async-token"},
            payload={
                "query": "Bahnhofstrasse 1, 8001 Zürich",
                "intelligence_mode": "basic",
                "options": {
                    "async_mode": {"requested": True},
                },
            },
        )
        self.assertEqual(status, 202)
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("accepted"))

        job = body.get("job", {})
        job_id = str(job.get("job_id") or "")
        result_id = str(job.get("result_id") or "")
        self.assertTrue(job_id)
        self.assertTrue(result_id)
        self.assertEqual(job.get("status"), "completed")
        self.assertEqual(job.get("progress_percent"), 100)

        status_job, body_job = _http_json("GET", f"{self.base_url}/analyze/jobs/{job_id}")
        self.assertEqual(status_job, 200)
        self.assertTrue(body_job.get("ok"))
        self.assertEqual(body_job.get("job", {}).get("job_id"), job_id)
        self.assertEqual(body_job.get("job", {}).get("status"), "completed")
        self.assertGreaterEqual(len(body_job.get("job", {}).get("events", [])), 3)

        status_result, body_result = _http_json(
            "GET", f"{self.base_url}/analyze/results/{result_id}"
        )
        self.assertEqual(status_result, 200)
        self.assertTrue(body_result.get("ok"))
        self.assertEqual(body_result.get("result_id"), result_id)

        runtime_module = (
            body_result.get("result", {})
            .get("result", {})
            .get("data", {})
            .get("modules", {})
            .get("runtime", {})
        )
        self.assertEqual(runtime_module.get("status"), "stub")

    def test_unknown_job_and_result_return_not_found(self):
        status_job, body_job = _http_json(
            "GET", f"{self.base_url}/analyze/jobs/does-not-exist"
        )
        self.assertEqual(status_job, 404)
        self.assertEqual(body_job.get("error"), "not_found")

        status_result, body_result = _http_json(
            "GET", f"{self.base_url}/analyze/results/does-not-exist"
        )
        self.assertEqual(status_result, 404)
        self.assertEqual(body_result.get("error"), "not_found")


class TestAsyncJobStoreTransitions(unittest.TestCase):
    def test_invalid_transition_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="async-job-store-") as tmpdir:
            store_path = Path(tmpdir) / "store.json"
            store = AsyncJobStore(store_file=store_path)

            job = store.create_job(
                request_payload={"query": "test", "options": {}},
                request_id="req-1",
                query="test",
                intelligence_mode="basic",
            )

            with self.assertRaises(ValueError):
                store.transition_job(
                    job_id=str(job["job_id"]),
                    to_status="completed",
                    progress_percent=100,
                )


if __name__ == "__main__":
    unittest.main()
