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

    def test_post_analyze_forwards_upstream_events_with_request_context(self):
        def _fake_build_report(query, **kwargs):
            emitter = kwargs.get("upstream_log_emitter")
            self.assertIsNotNone(emitter)
            emitter(
                event="api.upstream.request.start",
                level="info",
                component="api.address_intel",
                direction="api->upstream",
                status="sent",
                source="geoadmin_search",
                target_host="api3.geo.admin.ch",
                target_path="/rest/services/api/SearchServer",
                attempt=1,
                max_attempts=1,
                retry_count=0,
            )
            emitter(
                event="api.upstream.request.end",
                level="info",
                component="api.address_intel",
                direction="upstream->api",
                status="ok",
                source="geoadmin_search",
                target_host="api3.geo.admin.ch",
                target_path="/rest/services/api/SearchServer",
                status_code=200,
                duration_ms=12.5,
                attempt=1,
                max_attempts=1,
                retry_count=0,
            )
            emitter(
                event="api.upstream.response.summary",
                level="info",
                component="api.address_intel",
                direction="upstream->api",
                status="ok",
                source="geoadmin_search",
                target_host="api3.geo.admin.ch",
                target_path="/rest/services/api/SearchServer",
                records=1,
                payload_kind="dict",
                cache="miss",
                attempt=1,
                max_attempts=1,
                retry_count=0,
            )
            return {
                "query": query,
                "matched_address": query,
                "ids": {},
                "coordinates": {},
                "administrative": {},
                "suitability_light": {},
                "summary_compact": {},
            }

        with patch("src.api.web_service.build_report", side_effect=_fake_build_report):
            status, body, _ = self._request(
                "POST",
                "/analyze",
                body=json.dumps({"query": "Bahnhofstrasse 1, 9000 St. Gallen"}),
                headers={
                    "Content-Type": "application/json",
                    "X-Request-Id": "bl340-req-upstream",
                    "X-Session-Id": "sess-upstream",
                },
            )

        self.assertEqual(status, 200)
        self.assertIn('"ok": true', body.lower())

        upstream_events = [
            event
            for event in self.events
            if str(event.get("event", "")).startswith("api.upstream.")
        ]
        self.assertGreaterEqual(len(upstream_events), 3)

        start_event = next(event for event in upstream_events if event.get("event") == "api.upstream.request.start")
        end_event = next(event for event in upstream_events if event.get("event") == "api.upstream.request.end")
        summary_event = next(event for event in upstream_events if event.get("event") == "api.upstream.response.summary")

        self.assertEqual(start_event.get("request_id"), "bl340-req-upstream")
        self.assertEqual(start_event.get("session_id"), "sess-upstream")
        self.assertEqual(start_event.get("route"), "/analyze")

        self.assertEqual(end_event.get("status"), "ok")
        self.assertEqual(end_event.get("status_code"), 200)
        self.assertEqual(summary_event.get("records"), 1)


if __name__ == "__main__":
    unittest.main()
