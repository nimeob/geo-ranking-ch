import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.api.debug_trace import build_trace_timeline, normalize_request_id


class TestDebugTraceHelpers(unittest.TestCase):
    def test_normalize_request_id_rejects_invalid_values(self):
        self.assertEqual(normalize_request_id(""), "")
        self.assertEqual(normalize_request_id("  "), "")
        self.assertEqual(normalize_request_id("abc def"), "")
        self.assertEqual(normalize_request_id("abc,def"), "")
        self.assertEqual(normalize_request_id("über"), "")
        self.assertEqual(normalize_request_id("a" * 129), "")
        self.assertEqual(normalize_request_id("req-123"), "req-123")

    def test_build_trace_timeline_happy_path_with_redaction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "trace.jsonl"
            events = [
                {
                    "ts": "2026-03-01T00:00:01Z",
                    "level": "info",
                    "event": "api.request.start",
                    "request_id": "req-123",
                    "session_id": "sess-1",
                    "route": "/analyze",
                    "method": "POST",
                    "authorization": "Bearer very-secret",
                },
                {
                    "ts": "2026-03-01T00:00:02Z",
                    "level": "info",
                    "event": "api.upstream.request.end",
                    "request_id": "req-123",
                    "session_id": "sess-1",
                    "status": "ok",
                    "status_code": 200,
                    "source": "geoadmin",
                    "headers": {"Authorization": "Bearer nested-secret"},
                },
                {
                    "ts": "2026-03-01T00:00:03Z",
                    "level": "info",
                    "event": "api.request.end",
                    "request_id": "req-123",
                    "session_id": "sess-1",
                    "status": "ok",
                    "status_code": 200,
                    "duration_ms": 123.4,
                },
                {
                    "ts": "2026-03-01T00:00:04Z",
                    "level": "info",
                    "event": "api.request.end",
                    "request_id": "other-req",
                    "session_id": "sess-1",
                    "status": "ok",
                    "status_code": 200,
                },
            ]
            log_path.write_text("\n".join(json.dumps(item) for item in events) + "\n", encoding="utf-8")

            result = build_trace_timeline(
                request_id="req-123",
                log_path=str(log_path),
                lookback_seconds=48 * 3600,
                max_events=20,
                now_utc=datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "ready")
        self.assertTrue(result["found"])
        self.assertEqual(result["event_count"], 3)

        timeline = result["events"]
        self.assertEqual(timeline[0]["event"], "api.request.start")
        self.assertEqual(timeline[1]["event"], "api.upstream.request.end")
        self.assertEqual(timeline[2]["event"], "api.request.end")

        self.assertEqual(timeline[0]["details"]["authorization"], "[REDACTED]")
        self.assertEqual(timeline[1]["details"]["headers"]["Authorization"], "[REDACTED]")

    def test_build_trace_timeline_returns_empty_for_outside_window(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "trace.jsonl"
            log_path.write_text(
                json.dumps(
                    {
                        "ts": "2026-02-20T00:00:00Z",
                        "event": "api.request.start",
                        "request_id": "req-old",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = build_trace_timeline(
                request_id="req-old",
                log_path=str(log_path),
                lookback_seconds=3600,
                max_events=20,
                now_utc=datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "empty")
        self.assertEqual(result["reason"], "request_id_outside_window")
        self.assertEqual(result["events"], [])

    def test_build_trace_timeline_reports_missing_source(self):
        result = build_trace_timeline(
            request_id="req-123",
            log_path="/tmp/does-not-exist-debug-trace.jsonl",
            lookback_seconds=3600,
            max_events=20,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "trace_source_unavailable")

    def test_build_trace_timeline_from_cloudwatch(self):
        class _FakeLogsClient:
            def filter_log_events(self, **kwargs):
                self.kwargs = kwargs
                return {
                    "events": [
                        {
                            "message": json.dumps(
                                {
                                    "ts": "2026-03-01T00:00:01Z",
                                    "level": "info",
                                    "event": "api.request.start",
                                    "request_id": "req-cw-1",
                                    "session_id": "sess-1",
                                    "route": "/analyze",
                                    "method": "POST",
                                }
                            )
                        },
                        {
                            "message": json.dumps(
                                {
                                    "ts": "2026-03-01T00:00:02Z",
                                    "level": "info",
                                    "event": "api.request.end",
                                    "request_id": "req-cw-1",
                                    "session_id": "sess-1",
                                    "status": "ok",
                                    "status_code": 200,
                                }
                            )
                        },
                    ]
                }

        fake_client = _FakeLogsClient()
        result = build_trace_timeline(
            request_id="req-cw-1",
            log_path="",
            cloudwatch_log_group="/ecs/dev/swisstopo-api",
            cloudwatch_client=fake_client,
            lookback_seconds=3600,
            max_events=20,
            now_utc=datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["source"]["kind"], "cloudwatch_logs")
        self.assertEqual(result["event_count"], 2)


if __name__ == "__main__":
    unittest.main()
