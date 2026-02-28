from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_bl337_api_frontdoor_e2e.py"

spec = importlib.util.spec_from_file_location("run_bl337_api_frontdoor_e2e", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _ApiHandler(BaseHTTPRequestHandler):
    health_status_code = 200

    def _write_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            if self.health_status_code == 200:
                self._write_json(200, {"ok": True, "status": "healthy"})
            else:
                self._write_json(self.health_status_code, {"ok": False, "error": "boom"})
            return

        if self.path == "/analyze":
            self._write_json(405, {"ok": False, "error": "method_not_allowed"})
            return

        self._write_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/analyze":
            self._write_json(404, {"ok": False, "error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._write_json(400, {"ok": False, "error": "bad_request"})
            return

        if not isinstance(payload, dict) or "query" not in payload:
            self._write_json(400, {"ok": False, "error": "bad_request"})
            return

        self._write_json(200, {"ok": True, "request_id": "test-req", "result": {"score": 1}})

    def log_message(self, fmt, *args):  # noqa: A003
        return


class TestRunBl337ApiFrontdoorE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _free_port()
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), _ApiHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _build_matrix(self, target_api: str, path: Path) -> None:
        payload = {
            "schemaVersion": "bl337.internet-e2e.v1",
            "generatedAtUtc": "2026-03-01T00:00:00Z",
            "targets": {
                "apiBaseUrl": target_api,
                "appBaseUrl": "https://www.dev.georanking.ch",
            },
            "summary": {"total": 8, "planned": 8, "pass": 0, "fail": 0, "blocked": 0},
            "tests": [
                {
                    "testId": "API.HEALTH.200",
                    "area": "api",
                    "title": "health",
                    "preconditions": [],
                    "steps": ["GET"],
                    "expectedResult": "HTTP 200",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "API.ANALYZE.POST.200",
                    "area": "api",
                    "title": "analyze",
                    "preconditions": [],
                    "steps": ["POST"],
                    "expectedResult": "HTTP 200",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "API.ANALYZE.INVALID_PAYLOAD.400",
                    "area": "api",
                    "title": "invalid",
                    "preconditions": [],
                    "steps": ["POST invalid"],
                    "expectedResult": "HTTP 400",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "API.ANALYZE.METHOD_MISMATCH.405",
                    "area": "api",
                    "title": "method mismatch",
                    "preconditions": [],
                    "steps": ["GET"],
                    "expectedResult": "HTTP 405",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "UI.LOAD.HOME.200",
                    "area": "ui",
                    "title": "ui load",
                    "preconditions": [],
                    "steps": ["GET"],
                    "expectedResult": "HTTP 200",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "UI.NAV.CORE_FLOW.VISIBLE",
                    "area": "ui",
                    "title": "ui nav",
                    "preconditions": [],
                    "steps": ["ui"],
                    "expectedResult": "visible",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "UI.INVALID_INPUT.ERROR_SURFACE",
                    "area": "ui",
                    "title": "ui invalid",
                    "preconditions": [],
                    "steps": ["ui"],
                    "expectedResult": "error",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "UI.API_ERROR.CONSISTENCY",
                    "area": "ui",
                    "title": "ui consistency",
                    "preconditions": [],
                    "steps": ["ui"],
                    "expectedResult": "consistent",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_main_updates_matrix_and_evidence_when_all_pass(self) -> None:
        _ApiHandler.health_status_code = 200
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = Path(tmpdir) / "matrix.json"
            evidence = Path(tmpdir) / "evidence.json"
            self._build_matrix(f"http://127.0.0.1:{self.port}", matrix)

            rc = module.main(["--matrix", str(matrix), "--evidence-json", str(evidence)])
            self.assertEqual(rc, 0)
            self.assertTrue(evidence.exists())

            matrix_payload = json.loads(matrix.read_text(encoding="utf-8"))
            summary = matrix_payload["summary"]
            self.assertEqual(summary["pass"], 4)
            self.assertEqual(summary["planned"], 4)
            self.assertEqual(summary["fail"], 0)

            api_rows = [
                case
                for case in matrix_payload["tests"]
                if case.get("testId", "").startswith("API.")
            ]
            self.assertEqual(len(api_rows), 4)
            for row in api_rows:
                self.assertEqual(row["status"], "pass")
                self.assertEqual(row["evidenceLinks"], [str(evidence)])
                self.assertIsInstance(row["actualResult"], str)
                self.assertTrue(row["actualResult"].strip())

            evidence_payload = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(evidence_payload["summary"]["pass"], 4)
            self.assertEqual(evidence_payload["summary"]["fail"], 0)

    def test_main_returns_nonzero_when_expectation_fails(self) -> None:
        _ApiHandler.health_status_code = 503
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = Path(tmpdir) / "matrix.json"
            evidence = Path(tmpdir) / "evidence.json"
            self._build_matrix(f"http://127.0.0.1:{self.port}", matrix)

            rc = module.main(["--matrix", str(matrix), "--evidence-json", str(evidence)])
            self.assertEqual(rc, 1)

            matrix_payload = json.loads(matrix.read_text(encoding="utf-8"))
            first_api = next(case for case in matrix_payload["tests"] if case.get("testId") == "API.HEALTH.200")
            self.assertEqual(first_api["status"], "fail")
            self.assertIn("WP2 runtime reason", first_api["notes"])


if __name__ == "__main__":
    unittest.main()
