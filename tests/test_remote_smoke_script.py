import json
import os
import subprocess
import threading
import unittest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "run_remote_api_smoketest.sh"


class _AnalyzeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A003
        return

    def _send_json(self, payload, status=HTTPStatus.OK):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/health"):
            self._send_json({"ok": True})
            return
        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):  # noqa: N802
        if not self.path.startswith("/analyze"):
            self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        require_auth = getattr(self.server, "require_auth", False)
        token = getattr(self.server, "expected_token", "")
        if require_auth:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {token}":
                self._send_json({"ok": False, "error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        request_id = self.headers.get("X-Request-Id", "")

        self._send_json(
            {
                "ok": True,
                "request_id": request_id,
                "result": {
                    "query": payload.get("query"),
                    "mode": payload.get("intelligence_mode"),
                    "source": "local-test-server",
                },
            },
            status=HTTPStatus.OK,
        )


def _start_server(*, require_auth: bool):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _AnalyzeHandler)
    server.require_auth = require_auth
    server.expected_token = "test-token"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class TestRemoteSmokeScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_no_auth = _start_server(require_auth=False)
        cls.server_auth = _start_server(require_auth=True)
        cls.base_no_auth = f"http://127.0.0.1:{cls.server_no_auth.server_port}"
        cls.base_auth = f"http://127.0.0.1:{cls.server_auth.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server_no_auth.shutdown()
        cls.server_auth.shutdown()
        cls.server_no_auth.server_close()
        cls.server_auth.server_close()

    def _run_smoke(self, env_updates: dict[str, str]):
        env = os.environ.copy()
        env.update(env_updates)
        return subprocess.run(
            [str(SMOKE_SCRIPT)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )

    def test_smoke_passes_and_writes_json_report(self):
        with TemporaryDirectory() as td:
            out_json = Path(td) / "smoke.json"
            cp = self._run_smoke(
                {
                    "DEV_BASE_URL": self.base_no_auth,
                    "SMOKE_QUERY": "Musterstrasse 1, 9000 St. Gallen",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                }
            )

            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
            self.assertIn("PASS", cp.stdout)
            self.assertTrue(out_json.exists())

            report = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["reason"], "ok")
            self.assertEqual(report["http_status"], 200)
            self.assertIn("query", report["result_keys"])

    def test_smoke_normalizes_health_suffix(self):
        cp = self._run_smoke(
            {
                "DEV_BASE_URL": self.base_no_auth + "/health",
                "SMOKE_QUERY": "Bahnhofstrasse 1, Zürich",
            }
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertIn("PASS", cp.stdout)

    def test_smoke_fails_when_base_url_missing(self):
        env = os.environ.copy()
        env.pop("DEV_BASE_URL", None)
        cp = subprocess.run(
            [str(SMOKE_SCRIPT)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp.returncode, 2)
        self.assertIn("DEV_BASE_URL ist nicht gesetzt", cp.stderr)

    def test_smoke_fails_on_unauthorized_when_token_missing(self):
        cp = self._run_smoke(
            {
                "DEV_BASE_URL": self.base_auth,
                "SMOKE_QUERY": "Musterweg 3, Bern",
            }
        )
        self.assertEqual(cp.returncode, 1)
        self.assertIn("Erwartet HTTP 200, erhalten 401", cp.stdout)

    def test_smoke_passes_with_trimmed_auth_token(self):
        cp = self._run_smoke(
            {
                "DEV_BASE_URL": self.base_auth,
                "DEV_API_AUTH_TOKEN": "  test-token\t",
                "SMOKE_MODE": "  ExTenDeD  ",
            }
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertIn("PASS", cp.stdout)


if __name__ == "__main__":
    unittest.main()
