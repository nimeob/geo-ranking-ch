import io
import json
import unittest
from unittest.mock import patch

from src.api import web_service
from src.shared.structured_logging import build_event, emit_event, redact_mapping


class TestStructuredLoggingHelpers(unittest.TestCase):
    def test_build_event_contains_required_keys(self):
        payload = build_event(
            "api.test",
            level="INFO",
            trace_id="trace-1",
            request_id="req-1",
            session_id="sess-1",
            component="api.web_service",
        )

        self.assertEqual(payload["event"], "api.test")
        self.assertEqual(payload["level"], "info")
        self.assertEqual(payload["trace_id"], "trace-1")
        self.assertEqual(payload["request_id"], "req-1")
        self.assertEqual(payload["session_id"], "sess-1")
        self.assertIn("ts", payload)

    def test_redact_mapping_masks_sensitive_fields(self):
        payload = {
            "authorization": "Bearer super-secret-token",
            "nested": {
                "api_token": "abc123",
                "email": "person@example.com",
            },
            "notes": "contact person@example.com",
        }

        redacted = redact_mapping(payload)

        self.assertEqual(redacted["authorization"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["api_token"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["email"], "p***@example.com")
        self.assertIn("p***@example.com", redacted["notes"])

    def test_emit_event_writes_json_line(self):
        stream = io.StringIO()
        payload = {
            "event": "service.startup",
            "level": "info",
            "trace_id": "",
            "request_id": "",
            "session_id": "",
            "authorization": "Bearer secret-token",
            "ts": "2026-03-01T00:00:00Z",
        }

        emitted = emit_event(payload, stream=stream)
        line = stream.getvalue().strip()
        parsed = json.loads(line)

        self.assertEqual(parsed["event"], "service.startup")
        self.assertEqual(parsed["authorization"], "[REDACTED]")
        self.assertEqual(emitted["authorization"], "[REDACTED]")


class TestWebServiceLoggingBridge(unittest.TestCase):
    def test_emit_structured_log_uses_helper_payload(self):
        with patch("src.api.web_service.emit_event") as mock_emit:
            web_service._emit_structured_log(
                event="api.health.response",
                trace_id="req-123",
                request_id="req-123",
                session_id="",
                component="api.web_service",
                status="ok",
            )

        mock_emit.assert_called_once()
        emitted_payload = mock_emit.call_args.args[0]
        self.assertEqual(emitted_payload["event"], "api.health.response")
        self.assertEqual(emitted_payload["request_id"], "req-123")
        self.assertEqual(emitted_payload["component"], "api.web_service")

    def test_emit_structured_log_never_raises_on_emit_failure(self):
        with patch("src.api.web_service.emit_event", side_effect=RuntimeError("boom")):
            web_service._emit_structured_log(event="service.startup")


if __name__ == "__main__":
    unittest.main()
