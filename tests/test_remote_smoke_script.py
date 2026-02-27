import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib import request


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "run_remote_api_smoketest.sh"
GENERATE_DEV_TLS_CERT_SCRIPT = REPO_ROOT / "scripts" / "generate_dev_tls_cert.sh"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_health(base_url: str, timeout_seconds: float = 12.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with request.urlopen(f"{base_url}/health", timeout=2):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("web_service wurde lokal nicht rechtzeitig erreichbar")


class TestRemoteSmokeScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "API_AUTH_TOKEN": "bl18-token",
                "ENABLE_E2E_FAULT_INJECTION": "1",
                "PYTHONPATH": str(REPO_ROOT),
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
        _wait_for_health(cls.base_url)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def _run_smoke(
        self,
        *,
        include_token: bool,
        base_url: str | None = None,
        request_id: str | None = None,
        request_id_header: str | None = None,
        smoke_query: str | None = None,
        smoke_mode: str | None = None,
        smoke_timeout_seconds: str | None = None,
        curl_max_time: str | None = None,
        curl_retry_count: str | None = None,
        curl_retry_delay: str | None = None,
        dev_api_auth_token: str | None = None,
        use_default_request_id: bool = False,
        extra_env: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict, str | None]:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            request_id = request_id or f"bl18-smoke-test-{int(time.time() * 1000)}"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": base_url or self.base_url,
                    "SMOKE_QUERY": smoke_query or "__ok__",
                    "SMOKE_MODE": smoke_mode or "basic",
                    "SMOKE_TIMEOUT_SECONDS": smoke_timeout_seconds or "2",
                    "CURL_MAX_TIME": curl_max_time or "10",
                    "CURL_RETRY_COUNT": curl_retry_count or "1",
                    "CURL_RETRY_DELAY": curl_retry_delay or "1",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                }
            )
            if use_default_request_id:
                env.pop("SMOKE_REQUEST_ID", None)
                request_id = None
            else:
                env["SMOKE_REQUEST_ID"] = request_id
            if request_id_header is not None:
                env["SMOKE_REQUEST_ID_HEADER"] = request_id_header
            if dev_api_auth_token is not None:
                env["DEV_API_AUTH_TOKEN"] = dev_api_auth_token
            elif include_token:
                env["DEV_API_AUTH_TOKEN"] = "bl18-token"
            else:
                env.pop("DEV_API_AUTH_TOKEN", None)

            if extra_env:
                env.update(extra_env)

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            data = json.loads(out_json.read_text(encoding="utf-8"))
            return cp, data, request_id

    def test_smoke_script_passes_with_valid_token(self):
        cp, data, request_id = self._run_smoke(include_token=True)
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertIn("status", data.get("result_keys", []))
        self.assertIn("data", data.get("result_keys", []))
        self.assertTrue(data.get("request_id_echo_enforced"))
        self.assertEqual(data.get("request_id_header_source"), "request")
        self.assertEqual(data.get("request_id_header_name"), "X-Request-Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_passes_against_self_signed_https_with_ca_cert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_dir = Path(tmpdir) / "certs"
            cert_dir.mkdir(parents=True, exist_ok=True)
            cert_base = "tls-dev"

            gen_env = os.environ.copy()
            gen_env.update(
                {
                    "DEV_TLS_CERT_DIR": str(cert_dir),
                    "DEV_TLS_CERT_BASENAME": cert_base,
                    "DEV_TLS_CERT_DAYS": "2",
                }
            )
            gen_cp = subprocess.run(
                [str(GENERATE_DEV_TLS_CERT_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=gen_env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(gen_cp.returncode, 0, msg=gen_cp.stdout + "\n" + gen_cp.stderr)

            cert_path = cert_dir / f"{cert_base}.crt"
            key_path = cert_dir / f"{cert_base}.key"
            self.assertTrue(cert_path.is_file())
            self.assertTrue(key_path.is_file())

            tls_port = _free_port()
            tls_base_url = f"https://localhost:{tls_port}"
            env = os.environ.copy()
            env.update(
                {
                    "HOST": "127.0.0.1",
                    "PORT": str(tls_port),
                    "API_AUTH_TOKEN": "bl18-token",
                    "ENABLE_E2E_FAULT_INJECTION": "1",
                    "PYTHONPATH": str(REPO_ROOT),
                    "TLS_CERT_FILE": str(cert_path),
                    "TLS_KEY_FILE": str(key_path),
                }
            )

            tls_proc = subprocess.Popen(
                [sys.executable, "-m", "src.web_service"],
                cwd=str(REPO_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                deadline = time.time() + 12
                ssl_context = ssl.create_default_context(cafile=str(cert_path))
                while time.time() < deadline:
                    try:
                        with request.urlopen(
                            f"{tls_base_url}/health",
                            timeout=2,
                            context=ssl_context,
                        ) as resp:
                            if resp.status == 200:
                                break
                    except Exception:
                        time.sleep(0.2)
                else:
                    self.fail("TLS-web_service wurde lokal nicht rechtzeitig erreichbar")

                cp, data, request_id = self._run_smoke(
                    include_token=True,
                    base_url=tls_base_url,
                    extra_env={"DEV_TLS_CA_CERT": str(cert_path)},
                )
                self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
                self.assertEqual(data.get("status"), "pass")
                self.assertEqual(data.get("reason"), "ok")
                self.assertEqual(data.get("http_status"), 200)
                self.assertEqual(data.get("request_id"), request_id)
                self.assertEqual(data.get("response_request_id"), request_id)
                self.assertEqual(data.get("response_header_request_id"), request_id)
            finally:
                tls_proc.terminate()
                try:
                    tls_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    tls_proc.kill()

    def test_smoke_script_rejects_missing_dev_tls_ca_cert_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            missing_ca = Path(tmpdir) / "does-not-exist.crt"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "CURL_MAX_TIME": "10",
                    "CURL_RETRY_COUNT": "1",
                    "CURL_RETRY_DELAY": "1",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "SMOKE_REQUEST_ID": "bl18-smoke-missing-ca",
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                    "DEV_TLS_CA_CERT": str(missing_ca),
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2, msg=cp.stdout + "\n" + cp.stderr)
            self.assertIn("DEV_TLS_CA_CERT muss auf eine existierende Datei zeigen", cp.stderr)

    def test_smoke_script_generates_unique_default_request_id_when_system_time_is_constant(self):
        with tempfile.TemporaryDirectory() as fake_bin_dir:
            fake_date = Path(fake_bin_dir) / "date"
            fake_date.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"${1:-}\" == \"-u\" ]]; then\n"
                "  echo '2026-02-26T00:00:00Z'\n"
                "else\n"
                "  echo '1700000000'\n"
                "fi\n",
                encoding="utf-8",
            )
            fake_date.chmod(0o755)

            fake_path = f"{fake_bin_dir}:{os.environ.get('PATH', '')}"
            cp_first, data_first, _ = self._run_smoke(
                include_token=True,
                use_default_request_id=True,
                extra_env={"PATH": fake_path},
            )
            cp_second, data_second, _ = self._run_smoke(
                include_token=True,
                use_default_request_id=True,
                extra_env={"PATH": fake_path},
            )

        self.assertEqual(cp_first.returncode, 0, msg=cp_first.stdout + "\n" + cp_first.stderr)
        self.assertEqual(cp_second.returncode, 0, msg=cp_second.stdout + "\n" + cp_second.stderr)

        request_id_first = data_first.get("request_id")
        request_id_second = data_second.get("request_id")
        self.assertIsInstance(request_id_first, str)
        self.assertIsInstance(request_id_second, str)
        self.assertTrue(request_id_first.startswith("bl18-"))
        self.assertTrue(request_id_second.startswith("bl18-"))
        self.assertNotEqual(request_id_first, request_id_second)
        self.assertEqual(data_first.get("response_request_id"), request_id_first)
        self.assertEqual(data_first.get("response_header_request_id"), request_id_first)
        self.assertEqual(data_second.get("response_request_id"), request_id_second)
        self.assertEqual(data_second.get("response_header_request_id"), request_id_second)

    def test_smoke_script_trims_dev_api_auth_token_before_request(self):
        cp, data, request_id = self._run_smoke(
            include_token=False,
            dev_api_auth_token="\tbl18-token  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_trims_request_id_before_validation_and_echo_check(self):
        cp, data, _ = self._run_smoke(
            include_token=True,
            request_id="  bl18-custom-request-id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id"), "bl18-custom-request-id")
        self.assertEqual(data.get("response_request_id"), "bl18-custom-request-id")
        self.assertEqual(data.get("response_header_request_id"), "bl18-custom-request-id")

    def test_smoke_script_supports_correlation_header_mode_for_request_id_echo(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="correlation",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "correlation")
        self.assertEqual(data.get("request_id_header_name"), "X-Correlation-Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_trims_request_id_header_mode_before_validation(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  Correlation  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "correlation")
        self.assertEqual(data.get("request_id_header_name"), "X-Correlation-Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_request_header_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  X-Request-Id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "request")
        self.assertEqual(data.get("request_id_header_name"), "X-Request-Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_short_request_header_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  request-id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "request")
        self.assertEqual(data.get("request_id_header_name"), "Request-Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_correlation_header_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="\tX-Correlation-Id\t",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "correlation")
        self.assertEqual(data.get("request_id_header_name"), "X-Correlation-Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_short_correlation_header_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  correlation-id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "correlation")
        self.assertEqual(data.get("request_id_header_name"), "Correlation-Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_request_header_underscore_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  X_Request_Id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "request")
        self.assertEqual(data.get("request_id_header_name"), "X_Request_Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_short_request_header_underscore_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  request_id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "request")
        self.assertEqual(data.get("request_id_header_name"), "Request_Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_correlation_header_underscore_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="\tX_Correlation_Id\t",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "correlation")
        self.assertEqual(data.get("request_id_header_name"), "X_Correlation_Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_short_correlation_underscore_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  correlation_id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "correlation")
        self.assertEqual(data.get("request_id_header_name"), "Correlation_Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_lowercase_correlation_underscore_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  x_correlation_id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "correlation")
        self.assertEqual(data.get("request_id_header_name"), "X_Correlation_Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_accepts_lowercase_request_underscore_alias_for_request_id_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            request_id_header="  x_request_id  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("request_id_header_source"), "request")
        self.assertEqual(data.get("request_id_header_name"), "X_Request_Id")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_fails_without_token_when_auth_enabled(self):
        cp, data, _ = self._run_smoke(include_token=False)
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual(data.get("status"), "fail")
        self.assertEqual(data.get("reason"), "http_status")
        self.assertEqual(data.get("http_status"), 401)

    def test_smoke_script_rejects_whitespace_only_dev_api_auth_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "   ",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_API_AUTH_TOKEN ist leer nach Whitespace-Normalisierung", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_dev_api_auth_token_with_control_characters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-\ntoken",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_API_AUTH_TOKEN darf keine Steuerzeichen enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_dev_api_auth_token_with_embedded_whitespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18 token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_API_AUTH_TOKEN darf keine eingebetteten Whitespaces enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_normalizes_base_url_when_analyze_suffix_is_provided(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"{self.base_url}/analyze",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_base_url_when_health_suffix_is_provided(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"{self.base_url}/health",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_chained_health_and_analyze_suffixes(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"{self.base_url}/health/analyze",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_chained_analyze_and_health_suffixes(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"{self.base_url}/analyze/health//",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_accepts_uppercase_http_scheme(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"HTTP://127.0.0.1:{self.port}/health",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_suffixes_case_insensitively(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"http://127.0.0.1:{self.port}/HeAlTh/AnAlYzE",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_trims_whitespace_around_base_url(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"   http://127.0.0.1:{self.port}/health   ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_trims_tab_wrapped_base_url_and_header_mode(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"\thttp://127.0.0.1:{self.port}/health\t",
            request_id_header="\tCorrelation\t",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id_header_source"), "correlation")
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)
        self.assertEqual(data.get("response_header_request_id"), request_id)

    def test_smoke_script_trims_smoke_mode_before_validation(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            smoke_mode="  basic  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_smoke_mode_case_before_validation(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            smoke_mode="  ExTenDeD  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_trims_smoke_query_before_request(self):
        cp, data, _ = self._run_smoke(
            include_token=True,
            smoke_query="  __ok__  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)

    def test_smoke_script_rejects_whitespace_only_smoke_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "   ",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_QUERY ist leer nach Whitespace-Normalisierung", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_smoke_query_with_control_characters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__\nwith-break",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_QUERY darf keine Steuerzeichen enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_trims_retry_count_and_delay_before_validation(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            curl_retry_count="\t1\t",
            curl_retry_delay="\t1\t",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_trims_timeout_and_curl_max_time_before_validation(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            smoke_timeout_seconds="\t2.5\t",
            curl_max_time=" 15 ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_handles_combined_scheme_case_suffix_chain_slash_and_whitespace(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"  HTTP://127.0.0.1:{self.port}/HeAlTh/AnAlYzE/  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_handles_combined_scheme_case_reverse_suffix_chain_slash_and_whitespace(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"  HTTP://127.0.0.1:{self.port}/AnAlYzE/health//  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_repeated_health_analyze_suffix_chain(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"http://127.0.0.1:{self.port}/health/analyze/health/analyze///",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_repeated_reverse_suffix_chain_with_scheme_case_and_whitespace(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"  HTTP://127.0.0.1:{self.port}/AnAlYzE/health/analyze/health///  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_repeated_reverse_suffix_chain_with_internal_double_slash(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"  HTTP://127.0.0.1:{self.port}/AnAlYzE//health/analyze/health///  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_repeated_forward_suffix_chain_with_internal_double_slash(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"  HTTP://127.0.0.1:{self.port}/health//analyze/health/analyze///  ",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_normalizes_redundant_trailing_slashes_after_suffix_chain(self):
        cp, data, request_id = self._run_smoke(
            include_token=True,
            base_url=f"http://127.0.0.1:{self.port}/health//analyze//",
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertEqual(data.get("status"), "pass")
        self.assertEqual(data.get("reason"), "ok")
        self.assertEqual(data.get("http_status"), 200)
        self.assertEqual(data.get("request_id"), request_id)
        self.assertEqual(data.get("response_request_id"), request_id)

    def test_smoke_script_rejects_whitespace_only_base_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": "   ",
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_BASE_URL ist leer nach Whitespace-Normalisierung", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_invalid_base_url_scheme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": f"127.0.0.1:{self.port}",
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_BASE_URL muss mit http:// oder https:// beginnen", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_base_url_with_embedded_whitespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": f"http://127.0.0.1:{self.port}/hea lth",
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_BASE_URL darf keine eingebetteten Whitespaces/Steuerzeichen enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_base_url_with_query_or_fragment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": f"{self.base_url}/health?from=ci#frag",
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_BASE_URL darf keine Query- oder Fragment-Komponenten enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_base_url_with_non_numeric_port(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": "http://127.0.0.1:abc/health",
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_BASE_URL ist nach Normalisierung ungültig", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_base_url_with_out_of_range_port(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": "http://127.0.0.1:70000/health",
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_BASE_URL ist nach Normalisierung ungültig", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_base_url_with_userinfo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": f"http://ci-user:ci-pass@127.0.0.1:{self.port}/health",
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("DEV_BASE_URL darf keine Userinfo", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_invalid_smoke_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "abc",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_TIMEOUT_SECONDS muss eine Zahl > 0 sein", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_non_finite_smoke_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "nan",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_TIMEOUT_SECONDS muss eine Zahl > 0 sein", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_non_finite_curl_max_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "CURL_MAX_TIME": "inf",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("CURL_MAX_TIME muss eine Zahl > 0 sein", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_curl_max_time_below_smoke_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "3",
                    "CURL_MAX_TIME": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("CURL_MAX_TIME muss >= SMOKE_TIMEOUT_SECONDS sein", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_invalid_retry_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "CURL_RETRY_COUNT": "-1",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("CURL_RETRY_COUNT muss eine Ganzzahl >= 0 sein", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_invalid_retry_delay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "CURL_RETRY_DELAY": "-1",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("CURL_RETRY_DELAY muss eine Ganzzahl >= 0 sein", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_whitespace_only_request_id_header_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID_HEADER": "   ",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID_HEADER ist leer nach Whitespace-Normalisierung", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_request_id_header_mode_with_control_characters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID_HEADER": "request\nheader",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID_HEADER darf keine Steuerzeichen enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_request_id_header_mode_with_embedded_whitespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID_HEADER": "request header",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID_HEADER darf keine eingebetteten Whitespaces enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_invalid_request_id_header_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID_HEADER": "x-trace-id",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("Ungültiger SMOKE_REQUEST_ID_HEADER='x-trace-id'", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_invalid_request_id_echo_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_ENFORCE_REQUEST_ID_ECHO": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("Ungültiger SMOKE_ENFORCE_REQUEST_ID_ECHO='2'", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_trims_request_id_echo_flag_before_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_ENFORCE_REQUEST_ID_ECHO": " 1 ",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
            self.assertTrue(out_json.exists())
            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(data.get("status"), "pass")
            self.assertTrue(data.get("request_id_echo_enforced"))

    def test_smoke_script_accepts_boolean_request_id_echo_flag_aliases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_ENFORCE_REQUEST_ID_ECHO": "  fAlSe  ",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
            self.assertTrue(out_json.exists())
            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(data.get("status"), "pass")
            self.assertFalse(data.get("request_id_echo_enforced"))

    def test_smoke_script_rejects_whitespace_only_request_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID": "   ",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID ist leer nach Whitespace-Normalisierung", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_request_id_with_control_characters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID": "bl18-bad\nrequest-id",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID darf keine Steuerzeichen enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_request_id_with_embedded_whitespace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID": "bl18 bad-request-id",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID darf keine eingebetteten Whitespaces enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_request_id_with_delimiters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID": "bl18,bad-request-id",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID darf keine Trennzeichen ',' oder ';' enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_request_id_longer_than_128_chars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID": "x" * 129,
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID darf maximal 128 Zeichen enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_request_id_with_non_ascii_characters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_REQUEST_ID": "bl18-é-bad-request-id",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_REQUEST_ID darf nur ASCII-Zeichen enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_whitespace_only_output_json_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke-whitespace-only.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": "   ",
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_OUTPUT_JSON ist leer nach Whitespace-Normalisierung", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_output_json_path_with_control_characters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke-control-char.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": f"{out_json}\nreport.json",
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_OUTPUT_JSON darf keine Steuerzeichen enthalten", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_rejects_output_json_path_when_target_is_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "smoke-report-dir"
            out_dir.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_dir),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("SMOKE_OUTPUT_JSON darf kein Verzeichnis sein", cp.stderr)

    def test_smoke_script_rejects_output_json_path_when_parent_is_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_parent_file = Path(tmpdir) / "existing-file"
            out_parent_file.write_text("not-a-directory", encoding="utf-8")
            out_json = out_parent_file / "smoke.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": self.base_url,
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "2",
                    "SMOKE_OUTPUT_JSON": str(out_json),
                    "DEV_API_AUTH_TOKEN": "bl18-token",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2)
            self.assertIn("Elternpfad von SMOKE_OUTPUT_JSON ist kein Verzeichnis", cp.stderr)
            self.assertFalse(out_json.exists())

    def test_smoke_script_trims_output_json_path_before_writing_curl_error_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "smoke-curl-error.json"
            env = os.environ.copy()
            env.update(
                {
                    "DEV_BASE_URL": f"http://127.0.0.1:{_free_port()}",
                    "SMOKE_QUERY": "__ok__",
                    "SMOKE_MODE": "basic",
                    "SMOKE_TIMEOUT_SECONDS": "1",
                    "CURL_MAX_TIME": "1",
                    "CURL_RETRY_COUNT": "0",
                    "CURL_RETRY_DELAY": "0",
                    "SMOKE_OUTPUT_JSON": f"  {out_json}  ",
                }
            )

            cp = subprocess.run(
                [str(SMOKE_SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 1)
            self.assertIn("curl-Aufruf fehlgeschlagen", cp.stdout)
            self.assertTrue(out_json.exists())

            report = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(report.get("status"), "fail")
            self.assertEqual(report.get("reason"), "curl_error")
            self.assertEqual(report.get("http_status"), None)


if __name__ == "__main__":
    unittest.main()
