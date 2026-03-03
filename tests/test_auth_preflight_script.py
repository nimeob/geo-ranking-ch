from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "auth_preflight.sh"


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(
        [str(SCRIPT)],
        cwd=str(REPO_ROOT),
        env=merged_env,
        text=True,
        capture_output=True,
    )


def _read_env_file(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        payload[key] = value
    return payload


class _TokenHandler(BaseHTTPRequestHandler):
    expected_client_id = ""
    expected_client_secret = ""
    token_value = ""

    def do_POST(self) -> None:  # noqa: N802
        raw_body = self.rfile.read(int(self.headers.get("content-length", "0"))).decode("utf-8")
        data = parse_qs(raw_body)

        client_id = (data.get("client_id") or [""])[0]
        client_secret = (data.get("client_secret") or [""])[0]
        grant_type = (data.get("grant_type") or [""])[0]

        if (
            grant_type != "client_credentials"
            or client_id != self.expected_client_id
            or client_secret != self.expected_client_secret
        ):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "invalid_client"}).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "access_token": self.token_value,
                    "token_type": "Bearer",
                    "expires_in": 300,
                }
            ).encode("utf-8")
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


class _TokenServer:
    def __init__(self, *, client_id: str, client_secret: str, token_value: str) -> None:
        handler_cls = type(
            "TokenHandler",
            (_TokenHandler,),
            {
                "expected_client_id": client_id,
                "expected_client_secret": client_secret,
                "token_value": token_value,
            },
        )
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def token_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/oauth/token"

    def __enter__(self) -> "_TokenServer":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def test_auth_preflight_oidc_mode_writes_smoke_bearer_token_contract() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "auth.env"
        client_id = "deploy-smoke-client"
        client_secret = "topsecret"
        token = "eyJhbGciOiJIUzI1NiJ9.payload.sig"

        with _TokenServer(client_id=client_id, client_secret=client_secret, token_value=token) as oidc:
            proc = _run(
                {
                    "SMOKE_AUTH_MODE": "oidc_client_credentials",
                    "OIDC_TOKEN_URL": oidc.token_url,
                    "OIDC_CLIENT_ID": client_id,
                    "OIDC_CLIENT_SECRET": client_secret,
                    "SMOKE_AUTH_OUTPUT_FILE": str(output_file),
                }
            )

        assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
        assert output_file.exists()
        payload = _read_env_file(output_file)
        assert payload["SMOKE_AUTH_MODE"] == "oidc_client_credentials"
        assert payload["SMOKE_BEARER_TOKEN"] == token
        assert "SMOKE_AUTH_OUTPUT_FILE=" in proc.stdout


def test_auth_preflight_supports_client_secret_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "auth.env"
        secret_file = Path(tmpdir) / "oidc.secret"
        secret_file.write_text("  from-file-secret  ", encoding="utf-8")

        with _TokenServer(
            client_id="deploy-smoke-client",
            client_secret="from-file-secret",
            token_value="token-from-file",
        ) as oidc:
            proc = _run(
                {
                    "SMOKE_AUTH_MODE": "oidc_client_credentials",
                    "OIDC_TOKEN_URL": oidc.token_url,
                    "OIDC_CLIENT_ID": "deploy-smoke-client",
                    "OIDC_CLIENT_SECRET_FILE": str(secret_file),
                    "SMOKE_AUTH_OUTPUT_FILE": str(output_file),
                }
            )

        assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
        payload = _read_env_file(output_file)
        assert payload["SMOKE_BEARER_TOKEN"] == "token-from-file"


def test_auth_preflight_none_mode_writes_empty_token() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "auth.env"
        proc = _run(
            {
                "SMOKE_AUTH_MODE": "none",
                "SMOKE_AUTH_OUTPUT_FILE": str(output_file),
            }
        )

        assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
        payload = _read_env_file(output_file)
        assert payload["SMOKE_AUTH_MODE"] == "none"
        assert payload["SMOKE_BEARER_TOKEN"] == ""


def test_auth_preflight_fails_fast_when_required_env_is_missing() -> None:
    proc = _run(
        {
            "SMOKE_AUTH_MODE": "oidc_client_credentials",
            "OIDC_CLIENT_ID": "deploy-smoke-client",
            "OIDC_CLIENT_SECRET": "topsecret",
        }
    )

    assert proc.returncode == 42
    assert "auth-preflight-failed" in proc.stderr
    assert "OIDC_TOKEN_URL fehlt" in proc.stderr
