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
        self.assertEqual(headers.get("location"), "/auth/login?next=%2Fgui")

    def test_history_redirect_preserves_next_query(self):
        status, _, headers = _http_get(
            f"{self.base_url}/history?limit=5",
            follow_redirects=False,
        )
        self.assertEqual(status, 302)
        self.assertEqual(
            headers.get("location"),
            "/auth/login?next=%2Fhistory%3Flimit%3D5",
        )

    def test_gui_redirects_to_login_when_session_cookie_is_invalid(self):
        status, _, headers = _http_get(
            f"{self.base_url}/gui",
            follow_redirects=False,
            headers={"Cookie": "__Host-session=missing-session-id"},
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/auth/login?next=%2Fgui")

    def test_auth_me_returns_401_without_session(self):
        status, body, headers = _http_get(f"{self.base_url}/auth/me", follow_redirects=False)
        self.assertEqual(status, 401)
        self.assertEqual(headers.get("cache-control"), "no-store")

        payload = json.loads(body)
        self.assertFalse(payload.get("ok"))
        self.assertFalse(payload.get("authenticated"))
        self.assertEqual(payload.get("error"), "no_session_cookie")

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

    def test_history_redirects_to_login_when_session_cookie_is_invalid(self):
        status, _, headers = _http_get(
            f"{self.base_url}/history?limit=5",
            follow_redirects=False,
            headers={"Cookie": "__Host-session=missing-session-id"},
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("location"), "/auth/login?next=%2Fhistory%3Flimit%3D5")

    def test_logout_endpoint_clears_cookie_and_redirects_to_idp(self):
        status, _, headers = _http_get(f"{self.base_url}/auth/logout", follow_redirects=False)
        self.assertEqual(status, 302)
        self.assertIn(
            "https://issuer.example.test/pool/logout?client_id=test-client-id",
            headers.get("location", ""),
        )
        cookie_header = headers.get("set-cookie", "")
        self.assertIn("Max-Age=0", cookie_header)
        self.assertIn("HttpOnly", cookie_header)
        self.assertIn("SameSite=Lax", cookie_header)


if __name__ == "__main__":
    unittest.main()
