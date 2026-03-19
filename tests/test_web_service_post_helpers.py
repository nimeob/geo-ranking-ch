import importlib
import io
import unittest
from unittest.mock import patch


web_service = importlib.import_module("src.api.web_service")


class _FakeAsyncJobStore:
    def __init__(self):
        self.create_result_calls: list[dict] = []
        self.transition_job_calls: list[dict] = []
        self.raise_on_create_result = False
        self.raise_on_transition_job = False

    def create_result(self, **kwargs):
        if self.raise_on_create_result:
            raise RuntimeError("forced create_result failure")
        self.create_result_calls.append(dict(kwargs))
        return {"result_id": "result-1"}

    def transition_job(self, **kwargs):
        if self.raise_on_transition_job:
            raise RuntimeError("forced transition_job failure")
        self.transition_job_calls.append(dict(kwargs))


class TestWebServicePostJsonBodyReader(unittest.TestCase):
    def _call(self, *, body: bytes, content_length: str, allow_empty_body: bool):
        return web_service._read_json_request_object(
            headers={"Content-Length": content_length},
            rfile=io.BytesIO(body),
            allow_empty_body=allow_empty_body,
        )

    def test_rejects_invalid_content_length(self):
        with self.assertRaisesRegex(ValueError, "invalid content length"):
            self._call(body=b"", content_length="NaN", allow_empty_body=False)

    def test_rejects_empty_body_when_not_allowed(self):
        with self.assertRaisesRegex(ValueError, "empty body"):
            self._call(body=b"", content_length="0", allow_empty_body=False)

    def test_accepts_empty_body_when_allowed(self):
        parsed = self._call(body=b"", content_length="0", allow_empty_body=True)
        self.assertEqual(parsed, {})

    def test_rejects_truncated_body_when_content_length_exceeds_payload(self):
        with self.assertRaisesRegex(ValueError, "incomplete body"):
            self._call(body=b"{}", content_length="4", allow_empty_body=False)

    def test_rejects_truncated_body_even_when_empty_body_allowed(self):
        with self.assertRaisesRegex(ValueError, "incomplete body"):
            self._call(body=b"", content_length="1", allow_empty_body=True)

    def test_rejects_non_utf8_body(self):
        with self.assertRaisesRegex(ValueError, "body must be valid utf-8 json"):
            self._call(body=b"\xff", content_length="1", allow_empty_body=False)

    def test_rejects_invalid_json(self):
        with self.assertRaisesRegex(ValueError, "invalid json"):
            self._call(body=b"{", content_length="1", allow_empty_body=False)

    def test_rejects_non_object_json(self):
        payload = b"[1,2,3]"
        with self.assertRaisesRegex(ValueError, "json body must be an object"):
            self._call(body=payload, content_length=str(len(payload)), allow_empty_body=False)

    def test_accepts_object_json(self):
        payload = b'{"query":"St. Gallen"}'
        parsed = self._call(body=payload, content_length=str(len(payload)), allow_empty_body=False)
        self.assertEqual(parsed, {"query": "St. Gallen"})


class TestWebServiceSyncHistoryPersistCallbacks(unittest.TestCase):
    def test_noop_when_job_id_missing(self):
        store = _FakeAsyncJobStore()
        success_cb, failure_cb = web_service._build_sync_history_persist_callbacks(
            state={"job_id": None}
        )

        with patch.object(web_service, "_ASYNC_JOB_STORE", store):
            success_cb({"ok": True})
            failure_cb(error_code="bad_request", error_message="boom")

        self.assertEqual(store.create_result_calls, [])
        self.assertEqual(store.transition_job_calls, [])

    def test_success_callback_persists_result_and_completes_job(self):
        store = _FakeAsyncJobStore()
        success_cb, _ = web_service._build_sync_history_persist_callbacks(
            state={"job_id": "job-123"}
        )

        with patch.object(web_service, "_ASYNC_JOB_STORE", store):
            success_cb({"status": {"ok": True}})

        self.assertEqual(len(store.create_result_calls), 1)
        self.assertEqual(store.create_result_calls[0]["job_id"], "job-123")
        self.assertEqual(store.create_result_calls[0]["result_kind"], "final")

        self.assertEqual(len(store.transition_job_calls), 1)
        transition = store.transition_job_calls[0]
        self.assertEqual(transition["job_id"], "job-123")
        self.assertEqual(transition["to_status"], "completed")
        self.assertEqual(transition["progress_percent"], 100)
        self.assertEqual(transition["result_id"], "result-1")

    def test_failure_callback_marks_job_failed(self):
        store = _FakeAsyncJobStore()
        _, failure_cb = web_service._build_sync_history_persist_callbacks(
            state={"job_id": "job-456"}
        )

        with patch.object(web_service, "_ASYNC_JOB_STORE", store):
            failure_cb(error_code="timeout", error_message="upstream timeout")

        self.assertEqual(store.create_result_calls, [])
        self.assertEqual(len(store.transition_job_calls), 1)
        transition = store.transition_job_calls[0]
        self.assertEqual(transition["job_id"], "job-456")
        self.assertEqual(transition["to_status"], "failed")
        self.assertEqual(transition["error_code"], "timeout")
        self.assertEqual(transition["error_message"], "upstream timeout")
        self.assertFalse(transition["retryable"])

    def test_callbacks_swallow_store_exceptions(self):
        store = _FakeAsyncJobStore()
        store.raise_on_create_result = True
        store.raise_on_transition_job = True
        success_cb, failure_cb = web_service._build_sync_history_persist_callbacks(
            state={"job_id": "job-789"}
        )

        with patch.object(web_service, "_ASYNC_JOB_STORE", store):
            success_cb({"status": {"ok": True}})
            failure_cb(error_code="internal", error_message="boom")


if __name__ == "__main__":
    unittest.main()
