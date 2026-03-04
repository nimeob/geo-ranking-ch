from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, request
from urllib.parse import parse_qs, urlencode, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _make_id_token(claims: dict[str, str]) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode("ascii")
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode("utf-8")).rstrip(b"=").decode("ascii")
    return f"{header}.{payload}.sig"


def _http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
    follow_redirects: bool = True,
    timeout: float = 10.0,
) -> tuple[int, str, dict[str, str]]:
    body = None
    req_headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
        req_headers.setdefault("Accept", "application/json")

    req = request.Request(url, method=method, headers=req_headers, data=body)
    opener = request.build_opener() if follow_redirects else request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as resp:
            return (
                resp.status,
                resp.read().decode("utf-8", errors="replace"),
                {k.lower(): v for k, v in resp.headers.items()},
            )
    except error.HTTPError as exc:
        return (
            exc.code,
            exc.read().decode("utf-8", errors="replace"),
            {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])},
        )


def _parse_cookie_value(set_cookie_header: str) -> str:
    raw = str(set_cookie_header or "").strip()
    if not raw:
        return ""
    first = raw.split(";", 1)[0].strip()
    return first


class _MockOidcHandler(BaseHTTPRequestHandler):
    server_version = "MockOIDC/1.0"

    def do_POST(self):  # noqa: N802
        if self.path != "/issuer/oauth2/token":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(max(0, length)).decode("utf-8", errors="replace")
        params = parse_qs(raw, keep_blank_values=True)

        if not params.get("code") or not params.get("code_verifier"):
            payload = {"error": "invalid_request"}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        id_token = _make_id_token(
            {
                "sub": "u-smoke-1019",
                "email": "smoke-1019@example.test",
                "aud": "test-client-id",
            }
        )
        payload = {
            "access_token": "AT-smoke-1019",
            "refresh_token": "RT-smoke-1019",
            "id_token": id_token,
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args):  # noqa: D401
        return


class TestAuthRegressionSmokeIssue1019(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()

        cls.idp_port = _free_port()
        cls.idp_base_url = f"http://127.0.0.1:{cls.idp_port}"
        cls.idp_server = ThreadingHTTPServer(("127.0.0.1", cls.idp_port), _MockOidcHandler)
        cls.idp_thread = threading.Thread(target=cls.idp_server.serve_forever, daemon=True)
        cls.idp_thread.start()

        cls.api_port = _free_port()
        cls.api_base_url = f"http://127.0.0.1:{cls.api_port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.api_port),
                "APP_VERSION": "test-auth-regression-1019",
                "PYTHONPATH": str(REPO_ROOT),
                "ENABLE_E2E_FAULT_INJECTION": "1",
                "ENABLE_QUERY_HISTORY": "1",
                "ASYNC_JOBS_STORE_FILE": str(Path(cls.tmp.name) / "async_jobs_store.json"),
                "BFF_OIDC_ISSUER": f"{cls.idp_base_url}/issuer",
                "BFF_OIDC_AUTH_ENDPOINT": f"{cls.idp_base_url}/issuer/oauth2/authorize",
                "BFF_OIDC_TOKEN_ENDPOINT": f"{cls.idp_base_url}/issuer/oauth2/token",
                "BFF_OIDC_CLIENT_ID": "test-client-id",
                "BFF_OIDC_REDIRECT_URI": f"{cls.api_base_url}/auth/callback",
                "BFF_OIDC_POST_LOGOUT_REDIRECT_URI": f"{cls.api_base_url}/auth/login",
            }
        )

        cls.api_proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _, _ = _http_request("GET", f"{cls.api_base_url}/health")
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("web_service wurde lokal nicht rechtzeitig erreichbar")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "api_proc", None) is not None:
            cls.api_proc.terminate()
            try:
                cls.api_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.api_proc.kill()

        if getattr(cls, "idp_server", None) is not None:
            cls.idp_server.shutdown()
            cls.idp_server.server_close()

        if getattr(cls, "tmp", None) is not None:
            cls.tmp.cleanup()

    def test_login_search_ranking_logout_regression_smoke(self):
        # 1) unauth GUI must redirect to login
        status, _, headers = _http_request(
            "GET",
            f"{self.api_base_url}/gui",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/auth/login?next=%2Fgui")

        # 1b) direct API login path is deprecated and points to UI-owned /auth/login
        status, body, headers = _http_request(
            "GET",
            f"{self.api_base_url}/login",
            follow_redirects=False,
        )
        self.assertEqual(status, 403)
        deprecated_payload = json.loads(body)
        self.assertEqual(deprecated_payload.get("error"), "external_direct_login_disabled")
        self.assertEqual(headers.get("deprecation"), "true")
        self.assertTrue((headers.get("sunset") or "").strip())
        self.assertIn('rel="deprecation"', str(headers.get("link") or ""))
        self.assertIn("/auth/login", str(headers.get("link") or ""))
        dep = deprecated_payload.get("deprecation") or {}
        self.assertEqual(dep.get("successor"), "/auth/login")
        self.assertEqual(dep.get("sunset"), headers.get("sunset"))

        # 2) explicit login endpoint sets session cookie and redirects to IdP authorize URL
        status, _, headers = _http_request(
            "GET",
            f"{self.api_base_url}/auth/login?next=%2Fgui",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        login_redirect = str(headers.get("location") or "")
        self.assertIn(f"{self.idp_base_url}/issuer/oauth2/authorize", login_redirect)
        self.assertIn("state=", login_redirect)
        session_cookie = _parse_cookie_value(headers.get("set-cookie", ""))
        self.assertTrue(session_cookie.startswith("__Host-session="))

        state = parse_qs(urlparse(login_redirect).query).get("state", [""])[0]
        self.assertTrue(state)

        # 3) callback establishes authenticated session
        callback_query = urlencode({"code": "smoke-code-1019", "state": state})
        status, _, headers = _http_request(
            "GET",
            f"{self.api_base_url}/auth/callback?{callback_query}",
            headers={"Cookie": session_cookie},
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/gui")

        callback_cookie = _parse_cookie_value(headers.get("set-cookie", ""))
        self.assertTrue(callback_cookie.startswith("__Host-session="))

        # 4) authenticated session visible via /auth/me
        status, body, _ = _http_request(
            "GET",
            f"{self.api_base_url}/auth/me",
            headers={"Cookie": callback_cookie},
            follow_redirects=False,
        )
        self.assertEqual(status, 200)
        me_payload = json.loads(body)
        self.assertTrue(me_payload.get("ok"))
        self.assertTrue(me_payload.get("authenticated"))

        # 5) authenticated /gui shell exposes deterministic selectors for core flow
        status, body, _ = _http_request(
            "GET",
            f"{self.api_base_url}/gui",
            headers={"Cookie": callback_cookie},
            follow_redirects=False,
        )
        self.assertEqual(status, 200)
        self.assertIn('id="analyze-form"', body)
        self.assertIn('id="query"', body)
        self.assertIn('id="submit-btn"', body)
        self.assertIn('id="results-list"', body)
        self.assertIn('id="results-body"', body)

        # 6) search/analyze call succeeds with deterministic smoke fixture query
        status, body, _ = _http_request(
            "POST",
            f"{self.api_base_url}/analyze",
            headers={
                "Cookie": callback_cookie,
                "X-Session-Id": "smoke-issue-1019",
                "X-Request-Id": "smoke-issue-1019-analyze",
            },
            payload={"query": "__ok__", "intelligence_mode": "basic"},
            follow_redirects=False,
            timeout=20,
        )
        self.assertEqual(status, 200)
        analyze_payload = json.loads(body)
        self.assertTrue(analyze_payload.get("ok"))
        self.assertIn("result", analyze_payload)

        # 7) history endpoint returns at least one entry incl. result_id for ranking view
        status, body, _ = _http_request(
            "GET",
            f"{self.api_base_url}/analyze/history?limit=5",
            headers={"Cookie": callback_cookie},
            follow_redirects=False,
        )
        self.assertEqual(status, 200)
        history_payload = json.loads(body)
        self.assertTrue(history_payload.get("ok"))
        history_entries = history_payload.get("history") or []
        self.assertTrue(history_entries)
        result_id = str(history_entries[0].get("result_id") or "").strip()
        self.assertTrue(result_id)

        # 8) ranking/detail view opens for the newest result and keeps stable selectors
        status, result_body, result_headers = _http_request(
            "GET",
            f"{self.api_base_url}/results/{result_id}",
            headers={"Cookie": callback_cookie},
            follow_redirects=False,
        )
        self.assertEqual(status, 200)
        self.assertIn("text/html", result_headers.get("content-type", ""))
        self.assertIn('id="result-id"', result_body)
        self.assertIn(f'data-result-id="{result_id}"', result_body)
        self.assertIn('id="tab-overview"', result_body)
        self.assertIn('id="tab-sources"', result_body)
        self.assertIn('id="tab-derived"', result_body)
        self.assertIn('id="tab-raw"', result_body)

        # 9) logout returns redirect + cookie clear and session becomes unauthorized
        status, _, headers = _http_request(
            "GET",
            f"{self.api_base_url}/auth/logout",
            headers={"Cookie": callback_cookie},
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        logout_location = str(headers.get("location") or "")
        self.assertIn(f"{self.idp_base_url}/issuer/logout", logout_location)
        self.assertIn("client_id=test-client-id", logout_location)
        self.assertIn("logout_uri=", logout_location)
        self.assertIn("Max-Age=0", str(headers.get("set-cookie") or ""))

        status, body, _ = _http_request(
            "GET",
            f"{self.api_base_url}/auth/me",
            follow_redirects=False,
        )
        self.assertEqual(status, 401)
        me_after_logout = json.loads(body)
        self.assertFalse(me_after_logout.get("ok"))


if __name__ == "__main__":
    unittest.main()
