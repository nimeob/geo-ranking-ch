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


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_get(
    url: str,
    *,
    timeout: float = 10.0,
    follow_redirects: bool = True,
    headers: dict[str, str] | None = None,
):
    req = request.Request(url, method="GET", headers=headers or {})
    opener = request.build_opener() if follow_redirects else request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as resp:
            return (
                resp.status,
                resp.read().decode("utf-8"),
                {k.lower(): v for k, v in resp.headers.items()},
            )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, body, headers


def _ui_proxy_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "X-Geo-Auth-Proxy": "1",
        "X-Forwarded-Host": "www.dev.georanking.ch",
        "X-Forwarded-Proto": "https",
    }
    if extra:
        headers.update(extra)
    return headers


class TestWebServiceBffGuiGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "APP_VERSION": "test-bff-guard-v1",
                "PYTHONPATH": str(REPO_ROOT),
                # Enable BFF OIDC mode for guard behavior
                "BFF_OIDC_ISSUER": "https://issuer.example.test/pool",
                "BFF_OIDC_CLIENT_ID": "test-client-id",
                "BFF_OIDC_REDIRECT_URI": f"{cls.base_url}/auth/callback",
            }
        )

        cls.proc = subprocess.Popen(
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
                status, _, _ = _http_get(f"{cls.base_url}/health")
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("web_service wurde lokal nicht rechtzeitig erreichbar")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def test_gui_redirects_to_login_when_no_session(self):
        status, _, headers = _http_get(f"{self.base_url}/gui", follow_redirects=False)
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(headers.get("location"), "/login?next=%2Fgui&reason=no_session")

    def test_legacy_history_redirect_preserves_next_query_with_canonical_successor(self):
        status, _, headers = _http_get(
            f"{self.base_url}/history?limit=5",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(
            headers.get("location"),
            "/login?next=%2Fgui%2Fhistory%3Flimit%3D5&reason=no_session",
        )

    def test_gui_history_redirect_preserves_next_query(self):
        status, _, headers = _http_get(
            f"{self.base_url}/gui/history?limit=5",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(
            headers.get("location"),
            "/login?next=%2Fgui%2Fhistory%3Flimit%3D5&reason=no_session",
        )

    def test_gui_redirects_to_login_when_session_cookie_is_invalid(self):
        status, _, headers = _http_get(
            f"{self.base_url}/gui",
            follow_redirects=False,
            headers={"Cookie": "__Host-session=missing-session-id"},
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/login?next=%2Fgui&reason=no_session")

    def test_login_entry_renders_ui_mask_with_username_password_fields(self):
        status, body, headers = _http_get(
            f"{self.base_url}/login?next=%2Fgui&reason=manual_login",
            follow_redirects=False,
        )
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn('id="login-username"', body)
        self.assertIn('id="login-password"', body)
        self.assertIn('id="login-start-link"', body)
        self.assertIn('/login?next=%2Fgui&amp;reason=manual_login&amp;start=1', body)

    def test_login_start_redirects_to_idp_without_browser_visible_auth_login_hop(self):
        status, _, headers = _http_get(
            f"{self.base_url}/login?next=%2Fgui&reason=manual_login&start=1",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        location = str(headers.get("location") or "")
        self.assertIn("/oauth2/authorize", location)
        self.assertNotIn("/auth/login", location)
        self.assertIn("state=", location)
        self.assertIn("code_challenge=", location)

    def test_auth_login_route_is_fail_closed_without_ui_proxy_marker(self):
        status, body, headers = _http_get(
            f"{self.base_url}/auth/login?next=%2Fgui",
            follow_redirects=False,
            headers={"Accept": "application/json"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(headers.get("deprecation"), "true")
        self.assertIn('rel="successor-version"', str(headers.get("link") or ""))
        self.assertIn("/login", str(headers.get("link") or ""))

        payload = json.loads(body)
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("error"), "external_direct_login_disabled")
        dep = payload.get("deprecation") or {}
        self.assertEqual(dep.get("successor"), "/login")

    def test_auth_login_route_redirects_to_ui_entry_when_ui_host_hits_api_without_proxy_marker(self):
        status, _, headers = _http_get(
            f"{self.base_url}/auth/login?next=%2Fgui&reason=manual_login",
            follow_redirects=False,
            headers={
                "Accept": "text/html",
                "Host": "127.0.0.1",
                "X-Forwarded-Host": "127.0.0.1",
                "X-Forwarded-Proto": "https",
            },
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(headers.get("location"), "/login?next=%2Fgui&reason=manual_login")

    def test_auth_me_returns_401_without_session(self):
        status, body, headers = _http_get(f"{self.base_url}/auth/me", follow_redirects=False)
        self.assertEqual(status, 401)
        self.assertEqual(headers.get("cache-control"), "no-store")

        payload = json.loads(body)
        self.assertFalse(payload.get("ok"))
        self.assertFalse(payload.get("authenticated"))
        self.assertEqual(payload.get("error"), "no_session_cookie")
        self.assertEqual(payload.get("code"), "unauthorized")
        self.assertEqual(payload.get("auth_reason"), "no_session_cookie")
        self.assertIsInstance(payload.get("request_id"), str)
        self.assertTrue(str(payload.get("request_id")).strip())

    def test_auth_me_returns_401_for_invalid_session_cookie(self):
        status, body, _ = _http_get(
            f"{self.base_url}/auth/me",
            follow_redirects=False,
            headers={"Cookie": "__Host-session=missing-session-id"},
        )
        self.assertEqual(status, 401)

        payload = json.loads(body)
        self.assertFalse(payload.get("ok"))
        self.assertFalse(payload.get("authenticated"))
        self.assertEqual(payload.get("error"), "session_not_found")
        self.assertEqual(payload.get("code"), "unauthorized")
        self.assertEqual(payload.get("auth_reason"), "session_not_found")
        self.assertIsInstance(payload.get("request_id"), str)
        self.assertTrue(str(payload.get("request_id")).strip())

    def test_auth_callback_error_renders_single_relogin_page_without_redirect_loop(self):
        status, body, headers = _http_get(
            f"{self.base_url}/auth/callback?code=fake-code&state=fake-state",
            follow_redirects=False,
            headers=_ui_proxy_headers(
                {
                    "Host": "callback-mismatch.local",
                    "X-Forwarded-Host": "callback-mismatch.local",
                }
            ),
        )
        self.assertEqual(status, 400)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertNotIn("location", headers)

        self.assertIn("Anmeldung konnte nicht abgeschlossen werden", body)
        self.assertIn("id=\"auth-callback-relogin\"", body)
        self.assertIn("/login?next=%2Fgui&amp;reason=invalid_state", body)
        self.assertIn("id=\"auth-callback-error-code\">missing_session_cookie<", body)
        self.assertIn("id=\"auth-callback-request-id\">", body)

        # Redirect diagnostics remain visible for reproducible debugging.
        self.assertIn('&quot;host&quot;: &quot;127.0.0.1&quot;', body)
        self.assertIn('&quot;path&quot;: &quot;/auth/callback&quot;', body)
        self.assertIn('&quot;host&quot;: &quot;callback-mismatch.local&quot;', body)

    def test_callback_state_mismatch_clears_cookie_and_shows_relogin_cta(self):
        login_status, _, login_headers = _http_get(
            f"{self.base_url}/auth/login",
            follow_redirects=False,
            headers=_ui_proxy_headers(),
        )
        self.assertEqual(login_status, 302)
        cookie_header = str(login_headers.get("set-cookie") or "")
        self.assertTrue(cookie_header)
        cookie_pair = cookie_header.split(";", 1)[0]

        status, body, headers = _http_get(
            f"{self.base_url}/auth/callback?code=fake-code&state=wrong-state",
            follow_redirects=False,
            headers=_ui_proxy_headers({"Cookie": cookie_pair}),
        )
        self.assertEqual(status, 400)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertNotIn("location", headers)
        self.assertIn("Max-Age=0", str(headers.get("set-cookie") or ""))
        self.assertIn("id=\"auth-callback-relogin\"", body)
        self.assertIn("reason=invalid_state", body)

    def test_callback_consent_denied_reason_stays_deterministic(self):
        status, body, headers = _http_get(
            f"{self.base_url}/auth/callback?error=access_denied&error_description=cancelled",
            follow_redirects=False,
            headers=_ui_proxy_headers(),
        )
        self.assertEqual(status, 400)
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertNotIn("location", headers)
        self.assertIn("id=\"auth-callback-relogin\"", body)
        self.assertIn("reason=consent_denied", body)

    def test_history_redirects_to_login_when_session_cookie_is_invalid(self):
        status, _, headers = _http_get(
            f"{self.base_url}/history?limit=5",
            follow_redirects=False,
            headers={"Cookie": "__Host-session=missing-session-id"},
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/login?next=%2Fgui%2Fhistory%3Flimit%3D5&reason=no_session")

    def test_logout_endpoint_clears_cookie_and_redirects_to_idp_with_defined_return_path(self):
        status, _, headers = _http_get(
            f"{self.base_url}/auth/logout",
            follow_redirects=False,
            headers=_ui_proxy_headers(),
        )
        self.assertEqual(status, 302)
        location = headers.get("location", "")
        self.assertIn(
            "https://issuer.example.test/pool/logout?client_id=test-client-id",
            location,
        )
        self.assertIn(
            "logout_uri=http%3A%2F%2F127.0.0.1",
            location,
        )
        self.assertIn("%2Flogin", location)
        self.assertNotIn("%2Fauth%2Fcallback", location)
        cookie_header = headers.get("set-cookie", "")
        self.assertIn("Max-Age=0", cookie_header)
        self.assertIn("HttpOnly", cookie_header)
        self.assertIn("SameSite=Lax", cookie_header)


if __name__ == "__main__":
    unittest.main()
