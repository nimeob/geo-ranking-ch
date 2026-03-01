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

    def _poll_job(
        self,
        *,
        job_id: str,
        expected_statuses: set[str],
        timeout_seconds: float = 8.0,
    ) -> tuple[int, dict]:
        deadline = time.time() + timeout_seconds
        last_status = 0
        last_body: dict = {}

        while time.time() < deadline:
            status, body = _http_json("GET", f"{self.base_url}/analyze/jobs/{job_id}")
            last_status = status
            last_body = body
            if status == 200:
                current_status = str(body.get("job", {}).get("status") or "")
                if current_status in expected_statuses:
                    return status, body
            time.sleep(0.1)

        return last_status, last_body

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

        created_job = body.get("job", {})
        job_id = str(created_job.get("job_id") or "")
        self.assertTrue(job_id)
        self.assertIn(created_job.get("status"), {"queued", "running", "partial"})

        status_job, body_job = self._poll_job(
            job_id=job_id,
            expected_statuses={"completed"},
            timeout_seconds=12,
        )
        self.assertEqual(status_job, 200)
        self.assertTrue(body_job.get("ok"))

        completed_job = body_job.get("job", {})
        result_id = str(completed_job.get("result_id") or "")
        self.assertEqual(completed_job.get("status"), "completed")
        self.assertEqual(completed_job.get("progress_percent"), 100)
        self.assertTrue(result_id)

        events = completed_job.get("events", [])
        event_types = [str(row.get("event_type") or "") for row in events]
        self.assertIn("job.queued", event_types)
        self.assertIn("job.running", event_types)
        self.assertIn("job.partial", event_types)
        self.assertIn("job.completed", event_types)

        # Konsistenz zwischen Partial-Events und persisted Snapshots.
        store = AsyncJobStore(store_file=self._store_file)
        results = store.list_results(job_id)
        partial_results = [row for row in results if row.get("result_kind") == "partial"]
        final_results = [row for row in results if row.get("result_kind") == "final"]

        self.assertGreaterEqual(len(partial_results), 1)
        self.assertEqual(len(final_results), 1)
        self.assertEqual(completed_job.get("partial_count"), len(partial_results))
        self.assertEqual(result_id, final_results[0].get("result_id"))

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
        self.assertEqual(runtime_module.get("status"), "completed")

    def test_cancel_endpoint_stops_running_job_idempotently(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Authorization": "Bearer async-token"},
            payload={
                "query": "Kornhausstrasse 3, 9000 St. Gallen",
                "intelligence_mode": "basic",
                "options": {
                    "async_mode": {"requested": True},
                },
            },
        )
        self.assertEqual(status, 202)
        self.assertTrue(body.get("ok"))
        job_id = str(body.get("job", {}).get("job_id") or "")
        self.assertTrue(job_id)

        # Zielpfad DoD: running -> canceled
        self._poll_job(job_id=job_id, expected_statuses={"running", "partial"}, timeout_seconds=8)

        cancel_status, cancel_body = _http_json(
            "POST",
            f"{self.base_url}/analyze/jobs/{job_id}/cancel",
            headers={"Authorization": "Bearer async-token"},
            payload={"reason": "test-cancel"},
        )
        self.assertIn(cancel_status, {200, 202})
        self.assertTrue(cancel_body.get("ok"))

        status_canceled, body_canceled = self._poll_job(
            job_id=job_id,
            expected_statuses={"canceled"},
            timeout_seconds=8,
        )
        self.assertEqual(status_canceled, 200)
        self.assertEqual(body_canceled.get("job", {}).get("status"), "canceled")

        status_repeat, body_repeat = _http_json(
            "POST",
            f"{self.base_url}/analyze/jobs/{job_id}/cancel",
            headers={"Authorization": "Bearer async-token"},
            payload={"reason": "repeat-cancel"},
        )
        self.assertIn(status_repeat, {200, 202})
        self.assertTrue(body_repeat.get("ok"))
        self.assertEqual(body_repeat.get("job", {}).get("status"), "canceled")

        event_types = [
            str(row.get("event_type") or "")
            for row in body_repeat.get("job", {}).get("events", [])
        ]
        self.assertIn("job.cancel_requested", event_types)
        self.assertIn("job.canceled", event_types)
        self.assertNotIn("job.completed", event_types)

    def test_async_error_path_persists_retry_hint(self):
        status, body = _http_json(
            "POST",
            f"{self.base_url}/analyze",
            headers={"Authorization": "Bearer async-token"},
            payload={
                "query": "__internal__",
                "intelligence_mode": "basic",
                "options": {
                    "async_mode": {"requested": True},
                },
            },
        )
        self.assertEqual(status, 202)
        self.assertTrue(body.get("ok"))

        job_id = str(body.get("job", {}).get("job_id") or "")
        self.assertTrue(job_id)

        status_failed, body_failed = self._poll_job(
            job_id=job_id,
            expected_statuses={"failed"},
            timeout_seconds=8,
        )
        self.assertEqual(status_failed, 200)
        failed_job = body_failed.get("job", {})
        self.assertEqual(failed_job.get("status"), "failed")
        self.assertEqual(failed_job.get("error_code"), "internal")
        self.assertIn("forced internal error", str(failed_job.get("error_message") or ""))
        self.assertTrue(failed_job.get("retryable"))
        self.assertEqual(failed_job.get("retry_hint"), "retry_with_backoff")

        event_types = [str(row.get("event_type") or "") for row in failed_job.get("events", [])]
        self.assertIn("job.failed", event_types)

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
