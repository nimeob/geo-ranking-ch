import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from src.api import web_service


class TestWebServiceDebugTraceApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls.log_path = Path(cls._temp_dir.name) / "debug-trace.jsonl"
        now_utc = datetime.now(timezone.utc)
        cls.log_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "ts": (now_utc.replace(microsecond=0)).isoformat().replace("+00:00", "Z"),
                            "level": "info",
                            "event": "api.request.start",
                            "request_id": "trace-req-1",
                            "session_id": "sess-1",
                            "route": "/analyze",
                            "method": "POST",
                        }
                    ),
                    json.dumps(
                        {
                            "ts": (now_utc.replace(microsecond=0)).isoformat().replace("+00:00", "Z"),
                            "level": "info",
                            "event": "api.upstream.request.end",
                            "request_id": "trace-req-1",
                            "session_id": "sess-1",
                            "status": "ok",
                            "status_code": 200,
                            "source": "geoadmin",
                        }
                    ),
                    json.dumps(
                        {
                            "ts": (now_utc.replace(microsecond=0)).isoformat().replace("+00:00", "Z"),
                            "level": "info",
                            "event": "api.request.end",
                            "request_id": "trace-req-1",
                            "session_id": "sess-1",
                            "status": "ok",
                            "status_code": 200,
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        cls._server = ThreadingHTTPServer(("127.0.0.1", 0), web_service.Handler)
        cls._port = int(cls._server.server_address[1])
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()
        cls._server.server_close()
        cls._thread.join(timeout=2)
        cls._temp_dir.cleanup()

    def _request(self, path: str) -> tuple[int, dict[str, object]]:
        conn = HTTPConnection("127.0.0.1", self._port, timeout=15)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            return int(response.status), payload
        finally:
            conn.close()

    def test_debug_trace_requires_feature_flag(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TRACE_DEBUG_ENABLED", None)
            status, payload = self._request("/debug/trace?request_id=trace-req-1")

        self.assertEqual(status, 403)
        self.assertEqual(payload.get("error"), "debug_trace_disabled")

    def test_debug_trace_requires_request_id(self):
        with patch.dict(
            os.environ,
            {
                "TRACE_DEBUG_ENABLED": "1",
                "TRACE_DEBUG_LOG_PATH": str(self.log_path),
            },
            clear=False,
        ):
            status, payload = self._request("/debug/trace")

        self.assertEqual(status, 400)
        self.assertEqual(payload.get("error"), "invalid_request_id")

    def test_debug_trace_returns_timeline(self):
        with patch.dict(
            os.environ,
            {
                "TRACE_DEBUG_ENABLED": "1",
                "TRACE_DEBUG_LOG_PATH": str(self.log_path),
                "TRACE_DEBUG_LOOKBACK_SECONDS": str(48 * 3600),
                "TRACE_DEBUG_MAX_EVENTS": "50",
            },
            clear=False,
        ):
            status, payload = self._request("/debug/trace?request_id=trace-req-1")

        self.assertEqual(status, 200)
        self.assertTrue(payload.get("ok"))
        trace_payload = payload.get("trace")
        self.assertIsInstance(trace_payload, dict)
        self.assertEqual(trace_payload.get("state"), "ready")
        self.assertEqual(trace_payload.get("event_count"), 3)

    def test_debug_trace_reports_source_unavailable(self):
        with patch.dict(
            os.environ,
            {
                "TRACE_DEBUG_ENABLED": "1",
                "TRACE_DEBUG_LOG_PATH": "/tmp/trace-missing-file.jsonl",
            },
            clear=False,
        ):
            status, payload = self._request("/debug/trace?request_id=trace-req-1")

        self.assertEqual(status, 503)
        self.assertEqual(payload.get("error"), "trace_source_unavailable")


if __name__ == "__main__":
    unittest.main()
