import json
import os
import threading
import time
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from src.api import web_service


class TestWebServiceRequestLifecycleLogging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events: list[dict[str, object]] = []

        def _capture(*args, **kwargs):
            if kwargs:
                cls.events.append(dict(kwargs))

        cls._log_patcher = patch("src.api.web_service._emit_structured_log", side_effect=_capture)
        cls._log_patcher.start()

        cls._server = ThreadingHTTPServer(("127.0.0.1", 0), web_service.Handler)
        cls._port = int(cls._server.server_address[1])
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()
        cls._server.server_close()
        cls._thread.join(timeout=2)
        cls._log_patcher.stop()

    def setUp(self):
        self.events.clear()

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str, dict[str, str]]:
        conn = HTTPConnection("127.0.0.1", self._port, timeout=15)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            payload = response.read().decode("utf-8")
            response_headers = {key.lower(): value for key, value in response.getheaders()}
            return int(response.status), payload, response_headers
        finally:
            conn.close()

    def _events_by_name(self, event_name: str) -> list[dict[str, object]]:
        return [event for event in self.events if event.get("event") == event_name]

    def _wait_for_event_count(self, event_name: str, count: int, *, timeout_seconds: float = 0.5) -> list[dict[str, object]]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            events = self._events_by_name(event_name)
            if len(events) >= count:
                return events
            time.sleep(0.01)
        return self._events_by_name(event_name)

    def test_get_health_emits_start_and_end_lifecycle_events(self):
        status, _, _ = self._request(
            "GET",
            "/health",
            headers={
                "X-Request-Id": "bl340-req-health",
                "X-Session-Id": "sess-health",
            },
        )

        self.assertEqual(status, 200)

        starts = self._wait_for_event_count("api.request.start", 1)
        ends = self._wait_for_event_count("api.request.end", 1)

        self.assertEqual(len(starts), 1)
        self.assertEqual(len(ends), 1)

        start_event = starts[0]
        end_event = ends[0]

        self.assertEqual(start_event.get("method"), "GET")
        self.assertEqual(start_event.get("route"), "/health")
        self.assertEqual(start_event.get("request_id"), "bl340-req-health")
        self.assertEqual(start_event.get("session_id"), "sess-health")

        self.assertEqual(end_event.get("status_code"), 200)
        self.assertEqual(end_event.get("status"), "ok")
        self.assertGreaterEqual(float(end_event.get("duration_ms", 0.0)), 0.0)

    def test_post_analyze_unauthorized_is_logged_as_client_error(self):
        with patch.dict(os.environ, {"API_AUTH_TOKEN": "expected-token"}, clear=False):
            status, body, _ = self._request(
                "POST",
                "/analyze",
                body=json.dumps({"query": "St. Gallen"}),
                headers={
                    "Content-Type": "application/json",
                    "X-Request-Id": "bl340-req-unauthorized",
                },
            )

        self.assertEqual(status, 401)
        self.assertIn("unauthorized", body)

        ends = self._wait_for_event_count("api.request.end", 1)
        self.assertEqual(len(ends), 1)

        end_event = ends[0]
        self.assertEqual(end_event.get("status_code"), 401)
        self.assertEqual(end_event.get("status"), "client_error")
        self.assertEqual(end_event.get("error_class"), "unauthorized")
        self.assertEqual(end_event.get("error_code"), "unauthorized")

    def test_post_analyze_timeout_is_logged_with_timeout_class(self):
        with patch.dict(os.environ, {"ENABLE_E2E_FAULT_INJECTION": "1"}, clear=False):
            status, body, _ = self._request(
                "POST",
                "/analyze",
                body=json.dumps({"query": "__timeout__"}),
                headers={
                    "Content-Type": "application/json",
                    "X-Request-Id": "bl340-req-timeout",
                },
            )

        self.assertEqual(status, 504)
        self.assertIn("timeout", body)

        ends = self._wait_for_event_count("api.request.end", 1)
        self.assertEqual(len(ends), 1)

        end_event = ends[0]
        self.assertEqual(end_event.get("status_code"), 504)
        self.assertEqual(end_event.get("status"), "timeout")
        self.assertEqual(end_event.get("error_class"), "timeout")
        self.assertEqual(end_event.get("error_code"), "timeout")


if __name__ == "__main__":
    unittest.main()
