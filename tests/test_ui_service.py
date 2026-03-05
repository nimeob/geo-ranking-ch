import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, request
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http(url: str, *, timeout: float = 10.0, follow_redirects: bool = True):
    req = request.Request(url, method="GET")

    if follow_redirects:
        opener = request.build_opener()
    else:
        class _NoRedirect(request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, hdrs, newurl):
                return None

        opener = request.build_opener(_NoRedirect)

    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body, {k.lower(): v for k, v in resp.headers.items()}
    except error.HTTPError as exc:
        return (
            exc.code,
            exc.read().decode("utf-8"),
            {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])},
        )


class _UpstreamAuthStubHandler(BaseHTTPRequestHandler):
    server_version = "auth-stub/1.0"

    def log_message(self, fmt, *args):  # noqa: D401 - test silence
        return

    def do_GET(self):  # noqa: N802 - stdlib callback
        parsed = urlparse(self.path)
        self.server.request_log.append(
            {
                "path": parsed.path,
                "query": parsed.query,
                "cookie": self.headers.get("Cookie", ""),
                "proxy_marker": self.headers.get("X-Geo-Auth-Proxy", ""),
            }
        )

        if parsed.path == "/auth/login":
            next_value = parse_qs(parsed.query).get("next", ["/gui"])[0]
            self.send_response(302)
            self.send_header("Location", f"/oidc/authorize?next={next_value}")
            self.send_header("Set-Cookie", "bff-state=state-123; HttpOnly; Path=/")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if parsed.path == "/auth/logout":
            self.send_response(302)
            self.send_header(
                "Location",
                "https://issuer.example.test/logout?client_id=cid&logout_uri="
                "http%3A%2F%2F127.0.0.1%3A"
                f"{self.server.api_port}%2Fauth%2Flogin",
            )
            self.send_header("Set-Cookie", "__Host-session=deleted; Max-Age=0; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if parsed.path == "/auth/me":
            payload = json.dumps({"ok": True, "subject": "demo-user"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


class TestUiService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream_port = _free_port()
        cls.upstream_server = ThreadingHTTPServer(("127.0.0.1", cls.upstream_port), _UpstreamAuthStubHandler)
        cls.upstream_server.request_log = []
        cls.upstream_server.api_port = cls.upstream_port
        cls.upstream_thread = threading.Thread(target=cls.upstream_server.serve_forever, daemon=True)
        cls.upstream_thread.start()

        cls.api_base_url = f"http://127.0.0.1:{cls.upstream_port}"

        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "APP_VERSION": "ui-test-v1",
                "UI_API_BASE_URL": cls.api_base_url,
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

        cls.upstream_server.shutdown()
        cls.upstream_server.server_close()
        cls.upstream_thread.join(timeout=5)

    def test_healthz_exposes_ui_service_metadata(self):
        status, body, headers = _http(f"{self.base_url}/healthz")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))

        payload = json.loads(body)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "geo-ranking-ch-ui")
        self.assertEqual(payload["version"], "ui-test-v1")
        self.assertEqual(payload["api_base_url"], self.api_base_url)

    def test_gui_endpoint_uses_absolute_api_base_when_configured(self):
        status, body, headers = _http(f"{self.base_url}//gui///?probe=1")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("geo-ranking.ch GUI MVP", body)
        self.assertIn("Version ui-test-v1", body)
        self.assertIn(f'fetch("{self.api_base_url}/analyze"', body)
        self.assertIn(f'const TRACE_DEBUG_ENDPOINT = "{self.api_base_url}/debug/trace";', body)
        self.assertIn(f'const ANALYZE_JOBS_ENDPOINT_BASE = "{self.api_base_url}/analyze/jobs";', body)
        self.assertIn(f'const ANALYZE_HISTORY_ENDPOINT = "{self.api_base_url}/analyze/history";', body)
        self.assertIn('const AUTH_LOGIN_ENDPOINT = "/login";', body)
        self.assertIn('const AUTH_LOGOUT_ENDPOINT = "/auth/logout";', body)
        self.assertIn('const AUTH_ME_ENDPOINT = "/auth/me";', body)
        self.assertIn('href="/login"', body)
        self.assertIn('href="/auth/logout"', body)
        self.assertIn('credentials: "include"', body)

    def test_job_permalink_page_renders_and_targets_absolute_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/jobs/job-123")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Async Job", body)
        self.assertIn("job-123", body)
        self.assertIn(f'const JOBS_ENDPOINT_BASE = "{self.api_base_url}/analyze/jobs";', body)

    def test_jobs_list_page_renders_and_targets_absolute_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/jobs")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Jobs (dev)", body)
        self.assertIn('id="jobs-status"', body)
        self.assertIn('id="jobs-q"', body)
        self.assertIn('id="jobs-add-id"', body)
        self.assertIn(f'const JOBS_ENDPOINT_BASE = "{self.api_base_url}/analyze/jobs";', body)
        self.assertIn("jobs_status", body)
        self.assertIn("jobs_q", body)
        self.assertIn('url.searchParams.get("jobs_status") || url.searchParams.get("status")', body)
        self.assertIn('url.searchParams.get("jobs_q") || url.searchParams.get("q")', body)
        self.assertIn('<option value="succeeded">succeeded</option>', body)
        self.assertIn("function canonicalJobStatus", body)
        self.assertIn('normalized === "completed" || normalized === "success"', body)

    def test_history_page_renders_and_targets_absolute_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/history")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Historische Abfragen", body)
        self.assertIn(f'const ANALYZE_HISTORY_ENDPOINT = "{self.api_base_url}/analyze/history"', body)
        self.assertIn('const AUTH_LOGIN_ENDPOINT = "/login"', body)
        self.assertIn('credentials: "include"', body)
        self.assertIn("/results/", body)
        self.assertIn('id="history-status-filter"', body)
        self.assertIn('id="history-query-filter"', body)
        self.assertIn('id="history-page-prev"', body)
        self.assertIn('id="history-page-next"', body)
        self.assertIn("history_status", body)
        self.assertIn("history_q", body)
        self.assertIn("history_page", body)
        self.assertIn("history_limit", body)
        self.assertIn('function applyClientFilters(rows)', body)
        self.assertIn('function buildHistoryRequestUrl()', body)
        self.assertIn('const offset = Math.max(0, (historyState.page - 1) * historyState.limit);', body)

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
        self.assertIn(f'const RESULTS_ENDPOINT_BASE = "{self.api_base_url}/analyze/results";', body)

        # Regression guard (Issue #1123): missing optional metadata must not hard-crash rendering.
        self.assertIn('function asObject(value)', body)
        self.assertIn('function formatFallback(value, fallback = "—")', body)
        self.assertIn('function renderSafe(renderer, targetEl, groupedResult, fallbackLabel)', body)
        self.assertIn('Overview konnte wegen fehlender optionaler Metadaten nicht vollständig gerendert werden.', body)
        self.assertIn('Sources konnten wegen fehlender optionaler Metadaten nicht vollständig gerendert werden.', body)
        self.assertIn('Derived konnte wegen fehlender optionaler Metadaten nicht vollständig gerendert werden.', body)
        self.assertIn('rows.push(kvRow("IDs", formatFallback(ids, "nicht verfügbar")));', body)
        self.assertIn('rows.push(kvRow("Administrative", formatFallback(admin, "nicht verfügbar")));', body)

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

    def test_login_entry_route_stays_ui_owned(self):
        status, _, headers = _http(
            f"{self.base_url}/login?next=%2Fgui&reason=manual_login",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/auth/login?next=%2Fgui&reason=manual_login")

    def test_auth_routes_are_proxied_without_api_host_redirect(self):
        self.upstream_server.request_log.clear()

        status, _, headers = _http(
            f"{self.base_url}/auth/login?next=%2Fgui&reason=manual_login",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/oidc/authorize?next=/gui")
        self.assertIn("bff-state=state-123", headers.get("set-cookie", ""))

        status, body, headers = _http(f"{self.base_url}/auth/me")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        self.assertEqual(json.loads(body), {"ok": True, "subject": "demo-user"})

        logged_paths = [entry["path"] for entry in self.upstream_server.request_log]
        self.assertIn("/auth/login", logged_paths)
        self.assertIn("/auth/me", logged_paths)

        markers = {
            entry["path"]: str(entry.get("proxy_marker") or "")
            for entry in self.upstream_server.request_log
            if entry.get("path") in {"/auth/login", "/auth/me"}
        }
        self.assertEqual(markers.get("/auth/login"), "1")
        self.assertEqual(markers.get("/auth/me"), "1")

    def test_auth_logout_proxy_rewrites_nested_logout_uri_to_ui_login(self):
        self.upstream_server.request_log.clear()
        status, _, headers = _http(
            f"{self.base_url}/auth/logout",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        location = str(headers.get("location") or "")
        self.assertIn("https://issuer.example.test/logout?client_id=cid", location)
        self.assertIn("logout_uri=http%3A%2F%2F127.0.0.1%3A", location)
        self.assertIn(f"%3A{self.port}%2Flogin", location)
        self.assertNotIn(f"%3A{self.upstream_port}%2Fauth%2Flogin", location)
        self.assertIn("Max-Age=0", str(headers.get("set-cookie") or ""))

        auth_logout_calls = [
            entry for entry in self.upstream_server.request_log if entry.get("path") == "/auth/logout"
        ]
        self.assertTrue(auth_logout_calls)
        self.assertEqual(str(auth_logout_calls[-1].get("proxy_marker") or ""), "1")

    # --- GUI Auth UX wp2: Session-Flow statt Bearer-Paste für /analyze + /analyze/history ---

    def test_gui_page_uses_session_flow_without_token_input(self):
        """GET /gui: kein Bearer-Token-Input, keine Authorization-Header-Injektion, Session-UX-Texte vorhanden."""
        status, body, _ = _http(f"{self.base_url}/gui")
        self.assertEqual(status, 200)
        self.assertNotIn('id="api-token"', body, "/gui darf kein manuelles Token-Input mehr enthalten")
        self.assertNotIn('headers["Authorization"]', body, "/gui darf keinen Browser-Authorization-Header setzen")
        self.assertIn('Session ungültig oder abgelaufen — bitte erneut einloggen.', body)
        self.assertIn('Session konnte nicht erneuert werden — bitte erneut einloggen.', body)
        self.assertIn('Login-Status ungültig oder abgelaufen — bitte Anmeldung neu starten.', body)
        self.assertIn('Anmeldung abgebrochen oder verweigert — bitte erneut einloggen.', body)
        self.assertIn('Zugriff verweigert — bitte Berechtigungen/Session prüfen.', body)
        self.assertIn('function isSessionRecoveryRequired(statusCode, errorCode)', body)
        self.assertIn('function resolveAuthRecoveryReason(statusCode, errorCode)', body)
        self.assertIn('"invalid_state"', body)
        self.assertIn('function resolveAuthFailure(statusCode, errorCode, fallbackMessage)', body)
        self.assertIn('if (normalizedStatus === 401 || normalizedStatus === 403)', body)
        self.assertIn('"403": "session_expired"', body)
        self.assertIn('const ANALYZE_DRAFT_STORAGE_KEY = "geo-ranking-ui-analyze-draft-v1";', body)
        self.assertIn('function updateSessionExpiryWarning(payload)', body)
        self.assertIn('session_expires_at', body)
        self.assertIn('id="session-expiry-warning"', body)
        self.assertIn('params.set("reason", normalizedReason);', body)
        self.assertIn('refresh_grant_error', body)
        self.assertIn('window.location.assign(loginUrl);', body)

    def test_history_page_uses_session_flow_without_token_storage(self):
        """GET /history: kein Token-Input/-Storage, 401/403 UX verweist auf Session/Login."""
        status, body, _ = _http(f"{self.base_url}/history")
        self.assertEqual(status, 200)
        self.assertNotIn('id="api-token"', body, "/history darf kein manuelles Token-Input mehr enthalten")
        self.assertNotIn('geo-ranking-ui-api-token', body, "/history darf keinen Access-Token-Storage-Key enthalten")
        self.assertNotIn('headers["Authorization"]', body, "/history darf keinen Browser-Authorization-Header setzen")
        self.assertIn('headers["X-Request-Id"] = normalizedRequestId;', body)
        self.assertIn('headers["X-Correlation-Id"] = normalizedRequestId;', body)
        self.assertIn('Session ungültig oder abgelaufen — bitte erneut einloggen.', body)
        self.assertIn('Session konnte nicht erneuert werden — bitte erneut einloggen.', body)
        self.assertIn('Login-Status ungültig oder abgelaufen — bitte Anmeldung neu starten.', body)
        self.assertIn('Anmeldung abgebrochen oder verweigert — bitte erneut einloggen.', body)
        self.assertIn('Zugriff verweigert — bitte Berechtigungen/Session prüfen.', body)
        self.assertIn('function isSessionRecoveryRequired(statusCode, errorCode)', body)
        self.assertIn('function resolveAuthRecoveryReason(statusCode, errorCode)', body)
        self.assertIn('"invalid_state"', body)
        self.assertIn('function resolveAuthFailure(statusCode, errorCode, fallbackMessage)', body)
        self.assertIn('if (normalizedStatus === 401 || normalizedStatus === 403)', body)
        self.assertIn('"403": "session_expired"', body)
        self.assertIn('window.location.hash || ""', body)
        self.assertIn('params.set("reason", normalizedReason);', body)
        self.assertIn('refresh_grant_error', body)
        self.assertIn('window.location.assign(loginUrl);', body)
        self.assertIn('function canonicalHistoryStatus(value)', body)
        self.assertIn('function applyClientFilters(rows)', body)
        self.assertIn('function renderPageMeta(filteredCount)', body)

    def test_results_page_has_token_input_and_sets_authorization_header(self):
        """GET /results/<id>: Token input vorhanden + JS setzt Authorization: Bearer <token> Header."""
        status, body, _ = _http(f"{self.base_url}/results/result-xyz")
        self.assertEqual(status, 200)
        self.assertIn('id="api-token"', body, "/results muss Token-Input #api-token haben")
        self.assertIn('type="password"', body, "Token-Input muss type=password sein")
        self.assertIn('Authorization', body, "/results muss Authorization Header-Code enthalten")
        self.assertIn('Bearer', body, "/results muss Bearer-Token-Code enthalten")
        self.assertIn('headers["X-Request-Id"] = normalizedRequestId;', body)
        self.assertIn('headers["X-Correlation-Id"] = normalizedRequestId;', body)
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
