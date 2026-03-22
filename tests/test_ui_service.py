import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
from http import HTTPStatus
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

    def _log_request(self, parsed_path, *, body: str = "") -> None:
        self.server.request_log.append(
            {
                "path": parsed_path.path,
                "query": parsed_path.query,
                "cookie": self.headers.get("Cookie", ""),
                "proxy_marker": self.headers.get("X-Geo-Auth-Proxy", ""),
                "body": body,
                "method": self.command,
            }
        )

    def log_message(self, fmt, *args):  # noqa: D401 - test silence
        return

    def do_GET(self):  # noqa: N802 - stdlib callback
        parsed = urlparse(self.path)
        self._log_request(parsed)

        if parsed.path == "/auth/login":
            next_value = parse_qs(parsed.query).get("next", ["/gui"])[0]
            if next_value == "/blocked":
                payload = json.dumps(
                    {
                        "ok": False,
                        "error": "external_direct_login_disabled",
                        "message": "direct login is disabled on API",
                    }
                ).encode("utf-8")
                self.send_response(HTTPStatus.FORBIDDEN)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

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

        if parsed.path == "/debug/trace":
            payload = json.dumps({"ok": True, "events": [{"kind": "demo"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if parsed.path == "/analyze/history":
            payload = json.dumps({"ok": True, "rows": []}).encode("utf-8")
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

    def do_POST(self):  # noqa: N802 - stdlib callback
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
        self._log_request(parsed, body=raw_body)

        if parsed.path == "/analyze":
            payload = json.dumps(
                {
                    "ok": True,
                    "result": {
                        "matched_address": "Bahnhofstrasse 1, 8001 Zürich",
                        "suitability_score": 0.71,
                        "module_scores": [{"module": "competition", "score": 0.62}],
                    },
                    "request_id": "req-ui-proxy-test",
                }
            ).encode("utf-8")
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

    def test_gui_endpoint_keeps_same_origin_api_endpoints_when_configured(self):
        status, body, headers = _http(f"{self.base_url}//gui///?probe=1")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("geo-ranking.ch GUI MVP", body)
        self.assertIn("Version ui-test-v1", body)
        self.assertIn('fetch("/analyze"', body)
        self.assertIn('const TRACE_DEBUG_ENDPOINT = "/debug/trace";', body)
        self.assertIn('function projectTraceEvent(rawEvent, index)', body)
        self.assertIn('function normalizeTraceEvents(rawEvents)', body)
        self.assertIn('function buildTraceDetailPayload(rawPayload, projectedEvents)', body)
        self.assertIn('const projectedResponse = buildTraceDetailPayload(parsed, events);', body)
        self.assertIn('const ANALYZE_JOBS_ENDPOINT_BASE = "/analyze/jobs";', body)
        self.assertIn('const ANALYZE_HISTORY_ENDPOINT = "/analyze/history";', body)
        self.assertIn('const AUTH_LOGIN_ENDPOINT = "/login";', body)
        self.assertIn('const AUTH_LOGOUT_ENDPOINT = "/auth/logout";', body)
        self.assertIn('const AUTH_ME_ENDPOINT = "/auth/me";', body)
        self.assertIn('href="/login"', body)
        self.assertIn('href="/auth/logout"', body)
        self.assertIn('credentials: "include"', body)

    def test_job_permalink_page_renders_and_targets_same_origin_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/jobs/job-123")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Async Job", body)
        self.assertIn("job-123", body)
        self.assertIn('const JOBS_ENDPOINT_BASE = "/analyze/jobs";', body)
        self.assertNotIn(f'{self.api_base_url}/analyze/jobs', body)

    def test_jobs_list_page_renders_and_targets_same_origin_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/jobs")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Jobs (dev)", body)
        self.assertIn('id="jobs-status"', body)
        self.assertIn('id="jobs-q"', body)
        self.assertIn('id="jobs-add-id"', body)
        self.assertIn('const JOBS_ENDPOINT_BASE = "/analyze/jobs";', body)
        self.assertNotIn(f'{self.api_base_url}/analyze/jobs', body)
        self.assertIn("jobs_status", body)
        self.assertIn("jobs_q", body)
        self.assertIn('url.searchParams.get("jobs_status") || url.searchParams.get("status")', body)
        self.assertIn('url.searchParams.get("jobs_q") || url.searchParams.get("q")', body)
        self.assertIn('<option value="succeeded">succeeded</option>', body)
        self.assertIn("function canonicalJobStatus", body)
        self.assertIn('normalized === "completed" || normalized === "success"', body)

    def test_legacy_gui_jobs_route_redirects_to_jobs_list_and_preserves_query(self):
        status, _, headers = _http(
            f"{self.base_url}/gui/jobs?jobs_status=running&jobs_q=job-123",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(headers.get("location"), "/jobs?jobs_status=running&jobs_q=job-123")

    def test_legacy_gui_job_permalink_redirects_to_jobs_permalink(self):
        status, _, headers = _http(
            f"{self.base_url}/gui/jobs/job-123?channel=in_app",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(headers.get("location"), "/jobs/job-123?channel=in_app")

    def test_history_page_renders_and_targets_same_origin_api_endpoints(self):
        status, body, headers = _http(f"{self.base_url}/history")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Historische Abfragen", body)
        self.assertIn('const ANALYZE_HISTORY_ENDPOINT = "/analyze/history"', body)
        self.assertNotIn(f'{self.api_base_url}/analyze/history', body)
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

        # IA: thematische Tabs + Legacy-Schlüssel (sources/derived/raw) bleiben stabil.
        for tab_key in [
            "overview",
            "location",
            "demographics",
            "safety",
            "housing",
            "education",
            "transport",
            "environment",
            "sources",
            "derived",
            "raw",
        ]:
            self.assertIn(f'data-tab="{tab_key}"', body)

        for label in [
            "Übersicht",
            "Lage",
            "Demografie",
            "Sicherheit",
            "Preise &amp; Miete",
            "Bildung",
            "Verkehr",
            "Umwelt",
            "Quellen &amp; Methodik",
            "Signale / Derived",
            "Raw JSON",
        ]:
            self.assertIn(label, body)

        # Initial state: Overview sichtbar, weitere Panels hidden.
        self.assertIn('<div id="tab-overview" class="tab-panel" role="tabpanel"', body)
        self.assertIn('<div id="tab-location" class="tab-panel" role="tabpanel"', body)
        self.assertIn('<div id="tab-sources" class="tab-panel" role="tabpanel"', body)
        self.assertIn('<div id="tab-derived" class="tab-panel" role="tabpanel"', body)
        self.assertIn('<div id="tab-raw" class="tab-panel" role="tabpanel"', body)
        self.assertIn('id="tab-location" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-location" tabindex="0" hidden', body)

        # Accessibility-Basics für Tabs.
        self.assertIn('role="tablist" aria-label="Resultat-Tabs"', body)
        self.assertIn('role="tab" data-tab="overview" aria-selected="true"', body)
        self.assertIn('aria-controls="tab-overview"', body)
        self.assertIn('function onTabKeyDown(event)', body)
        self.assertIn('if (key === "ArrowRight")', body)
        self.assertIn('if (key === "ArrowLeft")', body)
        self.assertIn('if (key === "Home")', body)
        self.assertIn('if (key === "End")', body)

        # Result-Permalink muss same-origin bleiben (Cookie-/CORS-sicher).
        self.assertIn('const RESULTS_ENDPOINT_BASE = "/analyze/results";', body)
        self.assertNotIn(f'{self.api_base_url}/analyze/results', body)

        # Robustheit: uneinheitliche / optionale Daten dürfen nicht crashen.
        self.assertIn('function asObject(value)', body)
        self.assertIn('function formatFallback(value, fallback = "—")', body)
        self.assertIn('function normalizeGroupedResult(groupedResult)', body)
        self.assertIn('function renderSafe(renderer, targetEl, groupedResult, fallbackLabel)', body)
        self.assertIn('Leere Datenbereiche werden robust abgefedert.', body)

        # Regression guard: latest-view result loading retries transient 404/not_found before failing hard.
        self.assertIn('const RESULT_LOAD_MAX_RETRIES = 8;', body)
        self.assertIn('const RESULT_LOAD_RETRY_DELAY_MS = 1500;', body)
        self.assertIn('function isTransientResultNotFound(response, parsed)', body)
        self.assertIn('const maxRetries = normalizedViewMode() === "latest" ? RESULT_LOAD_MAX_RETRIES : 0;', body)
        self.assertIn('setStatus(`retrying(${nextAttempt}/${maxRetries})`);', body)

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

    def test_login_entry_route_auto_starts_provider_flow(self):
        status, _, headers = _http(
            f"{self.base_url}/login?next=%2Fgui&reason=manual_login",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/oidc/authorize?next=/gui")
        self.assertNotIn("/auth/login", str(headers.get("location") or ""))
        self.assertIn("bff-state=state-123", headers.get("set-cookie", ""))

    def test_login_start_flow_is_proxied_without_browser_redirect_to_auth_login(self):
        self.upstream_server.request_log.clear()

        status, _, headers = _http(
            f"{self.base_url}/login?next=%2Fgui&reason=manual_login&start=1",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/oidc/authorize?next=/gui")
        self.assertNotIn("/auth/login", str(headers.get("location") or ""))
        self.assertIn("bff-state=state-123", headers.get("set-cookie", ""))

        auth_login_calls = [
            entry for entry in self.upstream_server.request_log if entry.get("path") == "/auth/login"
        ]
        self.assertTrue(auth_login_calls)
        self.assertEqual(str(auth_login_calls[-1].get("proxy_marker") or ""), "1")

    def test_login_start_flow_redirects_back_to_ui_mask_when_upstream_blocks_direct_login(self):
        self.upstream_server.request_log.clear()

        status, _, headers = _http(
            f"{self.base_url}/login?next=%2Fblocked&reason=manual_login&start=1",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/login?next=%2Fblocked&reason=login_unavailable")

        status, body, headers = _http(f"{self.base_url}{headers.get('location')}", follow_redirects=False)
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn('id="login-username"', body)
        self.assertIn('id="login-password"', body)
        self.assertIn("Die Anmeldung ist aktuell nicht verfügbar", body)
        self.assertNotIn('"error": "external_direct_login_disabled"', body)

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

    def test_same_origin_analyze_post_is_proxied_to_upstream_api(self):
        self.upstream_server.request_log.clear()

        payload = json.dumps({"query": "Bahnhofstrasse 1, 8001 Zürich"}).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/analyze",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json", "Cookie": "demo=1"},
        )
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            self.assertEqual(resp.status, 200)
            self.assertIn("application/json", resp.headers.get("Content-Type", ""))

        response_payload = json.loads(body)
        self.assertTrue(response_payload.get("ok"))
        self.assertEqual(response_payload.get("request_id"), "req-ui-proxy-test")

        analyze_calls = [entry for entry in self.upstream_server.request_log if entry.get("path") == "/analyze"]
        self.assertTrue(analyze_calls)
        self.assertEqual(analyze_calls[-1].get("method"), "POST")
        self.assertIn("Bahnhofstrasse", str(analyze_calls[-1].get("body") or ""))

    def test_same_origin_trace_get_is_proxied_to_upstream_api(self):
        self.upstream_server.request_log.clear()

        status, body, headers = _http(f"{self.base_url}/debug/trace?request_id=req-123")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        payload = json.loads(body)
        self.assertTrue(payload.get("ok"))

        trace_calls = [entry for entry in self.upstream_server.request_log if entry.get("path") == "/debug/trace"]
        self.assertTrue(trace_calls)
        self.assertEqual(trace_calls[-1].get("method"), "GET")

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

    def test_results_page_uses_session_auth_and_login_recovery(self):
        """GET /results/<id>: kein Token-Input, same-origin Session-Flow und Login-Recovery bei 401."""
        status, body, _ = _http(f"{self.base_url}/results/result-xyz")
        self.assertEqual(status, 200)
        self.assertNotIn('id="api-token"', body, "/results darf kein Token-Input #api-token haben")
        self.assertNotIn('Bitte Bearer-Token setzen', body, "/results darf keinen Bearer-Hinweis zeigen")
        self.assertIn('credentials: "include"', body)
        self.assertIn('window.setTimeout(() => redirectToLogin("session_expired"), 250);', body)
        self.assertIn('return `/auth/login?', body)
        self.assertIn('headers["X-Request-Id"] = normalizedRequestId;', body)
        self.assertIn('headers["X-Correlation-Id"] = normalizedRequestId;', body)

    def test_job_page_uses_session_auth_and_login_recovery(self):
        """GET /jobs/<id>: kein Token-Input, same-origin Session-Flow und Login-Recovery bei 401."""
        status, body, _ = _http(f"{self.base_url}/jobs/job-xyz")
        self.assertEqual(status, 200)
        self.assertNotIn('id="api-token"', body, "/jobs/<id> darf kein Token-Input #api-token haben")
        self.assertNotIn('Bitte Bearer-Token setzen', body, "/jobs/<id> darf keinen Bearer-Hinweis zeigen")
        self.assertIn('credentials: "include"', body)
        self.assertIn('window.setTimeout(() => redirectToLogin("session_expired"), 250);', body)
        self.assertIn('return `/auth/login?', body)


if __name__ == "__main__":
    unittest.main()
