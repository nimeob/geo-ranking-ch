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


REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(url: str, *, method: str = "GET", payload: dict | None = None, headers: dict | None = None, timeout: float = 12.0):
    body = None
    req_headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = request.Request(url, method=method, data=body, headers=req_headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            decoded = resp.read().decode("utf-8")
            return resp.status, json.loads(decoded), {k.lower(): v for k, v in resp.headers.items()}
    except error.HTTPError as exc:
        decoded = exc.read().decode("utf-8")
        return exc.code, json.loads(decoded), {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}


class TestTraceDebugSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.tmpdir = tempfile.TemporaryDirectory(prefix="bl422-smoke-")
        cls.log_path = Path(cls.tmpdir.name) / "structured-events.jsonl"
        cls.log_handle = cls.log_path.open("a", encoding="utf-8")

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "APP_VERSION": "trace-smoke-v1",
                "TRACE_DEBUG_ENABLED": "1",
                "TRACE_DEBUG_LOG_PATH": str(cls.log_path),
                "PYTHONPATH": str(REPO_ROOT),
            }
        )

        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=cls.log_handle,
            stderr=cls.log_handle,
            text=True,
        )

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _, _ = _http_json(f"{cls.base_url}/health")
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("web_service trace-smoke setup wurde nicht rechtzeitig erreichbar")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

        cls.log_handle.close()
        cls.tmpdir.cleanup()

    def test_analyze_to_trace_lookup_smoke_flow(self):
        trace_request_id = "bl422-smoke-request-id"

        status, analyze_payload, analyze_headers = _http_json(
            f"{self.base_url}/analyze",
            method="POST",
            payload={"intelligence_mode": "basic"},
            headers={
                "X-Request-Id": trace_request_id,
                "Authorization": "Bearer super-secret-token",
            },
        )

        self.assertEqual(status, 400)
        self.assertFalse(analyze_payload["ok"])
        self.assertEqual(analyze_payload.get("request_id"), trace_request_id)
        self.assertEqual(analyze_headers.get("x-request-id"), trace_request_id)

        # Give the logger a tiny moment to flush request.start/end events.
        time.sleep(0.25)

        status, trace_payload, _ = _http_json(
            f"{self.base_url}/debug/trace?request_id={trace_request_id}&lookback_seconds=600&max_events=50"
        )

        self.assertEqual(status, 200)
        self.assertTrue(trace_payload["ok"])
        self.assertEqual(trace_payload.get("trace_request_id"), trace_request_id)

        trace_data = trace_payload.get("trace") or {}
        self.assertTrue(trace_data.get("ok"))
        self.assertEqual(trace_data.get("state"), "ready")

        events = trace_data.get("events") or []
        self.assertGreaterEqual(len(events), 2)

        event_names = [str(event.get("event") or "") for event in events]
        self.assertIn("api.request.start", event_names)
        self.assertIn("api.request.end", event_names)

        self.assertNotIn("super-secret-token", json.dumps(trace_payload))


if __name__ == "__main__":
    unittest.main()
