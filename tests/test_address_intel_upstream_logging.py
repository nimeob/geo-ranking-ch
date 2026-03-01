import io
import json
import unittest
from unittest.mock import patch
import urllib.error

from src.api import address_intel


class _DummyJsonResponse:
    def __init__(self, payload: dict, *, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyBytesResponse:
    def __init__(self, raw: bytes, *, status: int = 200) -> None:
        self._raw = raw
        self.status = status

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestAddressIntelUpstreamLogging(unittest.TestCase):
    def _client(self, events: list[dict]) -> address_intel.HttpClient:
        def _capture(**kwargs):
            events.append(dict(kwargs))

        return address_intel.HttpClient(
            timeout=1,
            retries=1,
            backoff_seconds=0.01,
            min_request_interval_seconds=0.0,
            cache_ttl_seconds=0.0,
            enable_disk_cache=False,
            upstream_log_emitter=_capture,
            upstream_trace_id="trace-413",
            upstream_request_id="req-413",
            upstream_session_id="sess-413",
        )

    def test_get_json_success_emits_start_end_and_summary(self):
        events: list[dict] = []
        client = self._client(events)

        with patch("src.api.address_intel.urllib.request.urlopen", return_value=_DummyJsonResponse({"results": [1, 2]})):
            payload = client.get_json("https://api.example.test/search?q=abc", source="geoadmin_search")

        self.assertEqual(payload["results"], [1, 2])
        self.assertEqual([event["event"] for event in events], [
            "api.upstream.request.start",
            "api.upstream.request.end",
            "api.upstream.response.summary",
        ])

        start_event = events[0]
        end_event = events[1]
        summary_event = events[2]

        self.assertEqual(start_event.get("source"), "geoadmin_search")
        self.assertEqual(start_event.get("direction"), "api->upstream")
        self.assertEqual(start_event.get("attempt"), 1)
        self.assertEqual(start_event.get("max_attempts"), 2)
        self.assertEqual(start_event.get("request_id"), "req-413")

        self.assertEqual(end_event.get("status"), "ok")
        self.assertEqual(end_event.get("status_code"), 200)
        self.assertEqual(end_event.get("retry_count"), 0)
        self.assertGreaterEqual(float(end_event.get("duration_ms", 0.0)), 0.0)

        self.assertEqual(summary_event.get("records"), 2)
        self.assertEqual(summary_event.get("status"), "ok")
        self.assertEqual(summary_event.get("payload_kind"), "dict")

    def test_get_json_retry_then_success_logs_retry_state(self):
        events: list[dict] = []
        client = self._client(events)
        error = urllib.error.HTTPError(
            url="https://api.example.test/retry",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=io.BytesIO(b"temporary unavailable"),
        )

        with patch(
            "src.api.address_intel.urllib.request.urlopen",
            side_effect=[error, _DummyJsonResponse({"results": [{"id": 1}]})],
        ), patch("src.api.address_intel.time.sleep", return_value=None):
            payload = client.get_json("https://api.example.test/retry", source="geoadmin_search")

        self.assertEqual(payload["results"], [{"id": 1}])

        end_events = [event for event in events if event.get("event") == "api.upstream.request.end"]
        self.assertEqual(len(end_events), 2)

        first_end = end_events[0]
        second_end = end_events[1]

        self.assertEqual(first_end.get("status"), "retrying")
        self.assertEqual(first_end.get("status_code"), 503)
        self.assertEqual(first_end.get("retryable"), True)
        self.assertEqual(first_end.get("error_class"), "http_error")

        self.assertEqual(second_end.get("status"), "ok")
        self.assertEqual(second_end.get("attempt"), 2)
        self.assertEqual(second_end.get("retry_count"), 1)

    def test_get_json_network_error_emits_final_error_event(self):
        events: list[dict] = []

        def _capture(**kwargs):
            events.append(dict(kwargs))

        client = address_intel.HttpClient(
            timeout=1,
            retries=0,
            backoff_seconds=0.01,
            min_request_interval_seconds=0.0,
            cache_ttl_seconds=0.0,
            enable_disk_cache=False,
            upstream_log_emitter=_capture,
            upstream_trace_id="trace-413",
            upstream_request_id="req-413",
            upstream_session_id="sess-413",
        )

        with patch(
            "src.api.address_intel.urllib.request.urlopen",
            side_effect=urllib.error.URLError("offline"),
        ), patch("src.api.address_intel.time.sleep", return_value=None):
            with self.assertRaises(address_intel.ExternalRequestError):
                client.get_json("https://api.example.test/offline", source="geoadmin_search")

        end_events = [event for event in events if event.get("event") == "api.upstream.request.end"]
        self.assertEqual(len(end_events), 1)
        self.assertEqual(end_events[0].get("status"), "error")
        self.assertEqual(end_events[0].get("error_class"), "network_error")

    def test_google_news_rss_emits_upstream_events(self):
        events: list[dict] = []
        client = self._client(events)
        sources = address_intel.SourceRegistry()
        rss = b"""<?xml version='1.0' encoding='UTF-8'?>
        <rss><channel>
          <item>
            <title>Incident</title>
            <link>https://news.example.test/incident</link>
            <pubDate>Sun, 01 Mar 2026 00:00:00 GMT</pubDate>
            <description>Sample</description>
          </item>
        </channel></rss>
        """

        with patch("src.api.address_intel.urllib.request.urlopen", return_value=_DummyBytesResponse(rss)):
            payload = address_intel.fetch_google_news_rss(
                client,
                sources,
                query="St. Gallen",
                limit=3,
            )

        self.assertEqual(len(payload.get("events") or []), 1)
        self.assertIn("api.upstream.request.start", [event.get("event") for event in events])
        self.assertIn("api.upstream.request.end", [event.get("event") for event in events])
        self.assertIn("api.upstream.response.summary", [event.get("event") for event in events])


if __name__ == "__main__":
    unittest.main()
