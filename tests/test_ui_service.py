import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http(url: str, *, timeout: float = 10.0):
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body, {k.lower(): v for k, v in resp.headers.items()}
    except error.HTTPError as exc:
        return (
            exc.code,
            exc.read().decode("utf-8"),
            {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])},
        )


class TestUiService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "APP_VERSION": "ui-test-v1",
                "UI_API_BASE_URL": "https://api.example.test",
                "PYTHONPATH": str(REPO_ROOT),
            }
        )

        cls.proc = subprocess.Popen(
            [sys.executable, "-m", "src.ui_service"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _, _ = _http(f"{cls.base_url}/healthz")
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("ui_service wurde lokal nicht rechtzeitig erreichbar")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def test_healthz_exposes_ui_service_metadata(self):
        status, body, headers = _http(f"{self.base_url}/healthz")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))

        payload = json.loads(body)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "geo-ranking-ch-ui")
        self.assertEqual(payload["version"], "ui-test-v1")
        self.assertEqual(payload["api_base_url"], "https://api.example.test")

    def test_gui_endpoint_uses_absolute_api_base_when_configured(self):
        status, body, headers = _http(f"{self.base_url}//gui///?probe=1")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("geo-ranking.ch GUI MVP", body)
        self.assertIn("Version ui-test-v1", body)
        self.assertIn('fetch("https://api.example.test/analyze"', body)
        self.assertIn('const TRACE_DEBUG_ENDPOINT = "https://api.example.test/debug/trace";', body)
        self.assertIn('const ANALYZE_JOBS_ENDPOINT_BASE = "https://api.example.test/analyze/jobs";', body)
        self.assertIn('const ANALYZE_HISTORY_ENDPOINT = "https://api.example.test/analyze/history";', body)

    def test_job_permalink_page_renders_and_targets_absolute_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/jobs/job-123")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Async Job", body)
        self.assertIn("job-123", body)
        self.assertIn('const JOBS_ENDPOINT_BASE = "https://api.example.test/analyze/jobs";', body)

    def test_jobs_list_page_renders_and_targets_absolute_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/jobs")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Jobs (dev)", body)
        self.assertIn('id="jobs-status"', body)
        self.assertIn('id="jobs-q"', body)
        self.assertIn('id="jobs-add-id"', body)
        self.assertIn('const JOBS_ENDPOINT_BASE = "https://api.example.test/analyze/jobs";', body)
        self.assertIn("jobs_status", body)
        self.assertIn("jobs_q", body)
        self.assertIn('<option value="succeeded">succeeded</option>', body)
        self.assertIn("function canonicalJobStatus", body)
        self.assertIn('normalized === "completed" || normalized === "success"', body)

    def test_history_page_renders_and_targets_absolute_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/history")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Historische Abfragen", body)
        self.assertIn('const ANALYZE_HISTORY_ENDPOINT = "https://api.example.test/analyze/history"', body)
        self.assertIn("/results/", body)

    def test_result_permalink_page_renders_and_contains_tabs(self):
        status, body, headers = _http(f"{self.base_url}/results/res-123")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Result", body)
        self.assertIn("res-123", body)

        # Tabs (Order is relevant for UX; keep assertions explicit.)
        self.assertIn('data-tab="overview"', body)
        self.assertIn('data-tab="sources"', body)
        self.assertIn('data-tab="derived"', body)
        self.assertIn('data-tab="raw"', body)
        self.assertIn(">Overview<", body)
        self.assertIn(">Sources / Evidence<", body)
        self.assertIn(">Generated / Derived<", body)
        self.assertIn(">Raw JSON<", body)

        # Initial state: Overview visible, other panels hidden.
        self.assertIn('<div id="tab-overview" class="tab-panel">', body)
        self.assertIn('<div id="tab-sources" class="tab-panel" hidden>', body)
        self.assertIn('<div id="tab-derived" class="tab-panel" hidden>', body)
        self.assertIn('<div id="tab-raw" class="tab-panel" hidden>', body)

        # API base URL must be wired for UI deployments.
        self.assertIn('const RESULTS_ENDPOINT_BASE = "https://api.example.test/analyze/results";', body)

    def test_invalid_job_id_returns_not_found_payload(self):
        status, body, _ = _http(f"{self.base_url}/jobs/!!!")
        self.assertEqual(status, 404)
        payload = json.loads(body)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "not_found")

    def test_unknown_endpoint_returns_not_found_payload(self):
        status, body, _ = _http(f"{self.base_url}/not-here")
        self.assertEqual(status, 404)
        payload = json.loads(body)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "not_found")

    # --- GUI Auth UX wp2: Session-Flow statt Bearer-Paste für /analyze + /analyze/history ---

    def test_gui_page_uses_session_flow_without_token_input(self):
        """GET /gui: kein Bearer-Token-Input, keine Authorization-Header-Injektion, Session-UX-Texte vorhanden."""
        status, body, _ = _http(f"{self.base_url}/gui")
        self.assertEqual(status, 200)
        self.assertNotIn('id="api-token"', body, "/gui darf kein manuelles Token-Input mehr enthalten")
        self.assertNotIn('headers["Authorization"]', body, "/gui darf keinen Browser-Authorization-Header setzen")
        self.assertIn('Session ungültig oder abgelaufen — bitte erneut einloggen.', body)
        self.assertIn('Session konnte nicht erneuert werden — bitte erneut einloggen.', body)
        self.assertIn('Zugriff verweigert — bitte Berechtigungen/Session prüfen.', body)
        self.assertIn('function isSessionRecoveryRequired(statusCode, errorCode)', body)
        self.assertIn('refresh_grant_error', body)
        self.assertIn('window.location.assign(loginUrl);', body)

    def test_history_page_uses_session_flow_without_token_storage(self):
        """GET /history: kein Token-Input/-Storage, 401/403 UX verweist auf Session/Login."""
        status, body, _ = _http(f"{self.base_url}/history")
        self.assertEqual(status, 200)
        self.assertNotIn('id="api-token"', body, "/history darf kein manuelles Token-Input mehr enthalten")
        self.assertNotIn('geo-ranking-ui-api-token', body, "/history darf keinen Access-Token-Storage-Key enthalten")
        self.assertNotIn('headers["Authorization"]', body, "/history darf keinen Browser-Authorization-Header setzen")
        self.assertIn('Session ungültig oder abgelaufen — bitte erneut einloggen.', body)
        self.assertIn('Session konnte nicht erneuert werden — bitte erneut einloggen.', body)
        self.assertIn('Zugriff verweigert — bitte Berechtigungen/Session prüfen.', body)
        self.assertIn('function isSessionRecoveryRequired(statusCode, errorCode)', body)
        self.assertIn('refresh_grant_error', body)
        self.assertIn('window.location.assign(loginUrl);', body)

    def test_results_page_has_token_input_and_sets_authorization_header(self):
        """GET /results/<id>: Token input vorhanden + JS setzt Authorization: Bearer <token> Header."""
        status, body, _ = _http(f"{self.base_url}/results/result-xyz")
        self.assertEqual(status, 200)
        self.assertIn('id="api-token"', body, "/results muss Token-Input #api-token haben")
        self.assertIn('type="password"', body, "Token-Input muss type=password sein")
        self.assertIn('Authorization', body, "/results muss Authorization Header-Code enthalten")
        self.assertIn('Bearer', body, "/results muss Bearer-Token-Code enthalten")
        self.assertIn('Bitte Bearer-Token setzen', body, "/results muss 401-UX-Hint enthalten")

    def test_job_page_has_token_input_and_sets_authorization_header(self):
        """GET /jobs/<id>: Token input vorhanden + JS setzt Authorization: Bearer <token> Header."""
        status, body, _ = _http(f"{self.base_url}/jobs/job-xyz")
        self.assertEqual(status, 200)
        self.assertIn('id="api-token"', body, "/jobs/<id> muss Token-Input #api-token haben")
        self.assertIn('type="password"', body, "Token-Input muss type=password sein")
        self.assertIn('Authorization', body, "/jobs/<id> muss Authorization Header-Code enthalten")
        self.assertIn('Bearer', body, "/jobs/<id> muss Bearer-Token-Code enthalten")
        self.assertIn('Bitte Bearer-Token setzen', body, "/jobs/<id> muss 401-UX-Hint enthalten")


if __name__ == "__main__":
    unittest.main()
