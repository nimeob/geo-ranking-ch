import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_deploy_version_trace.py"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for(url: str, timeout_seconds: float = 12.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Endpoint nicht erreichbar: {url}")


def _http_json(url: str, *, method: str = "GET", payload: dict | None = None, headers: dict | None = None):
    raw_body = None
    req_headers = dict(headers or {})
    if payload is not None:
        raw_body = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = request.Request(url=url, method=method, data=raw_body, headers=req_headers)
    try:
        with request.urlopen(req, timeout=8) as resp:
            return int(resp.status), json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode("utf-8"))


class TestCheckDeployVersionTrace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_port = _free_port()
        cls.ui_port = _free_port()

        cls.api_base_url = f"http://127.0.0.1:{cls.api_port}"
        cls.ui_base_url = f"http://127.0.0.1:{cls.ui_port}"
        cls.expected_version = "cafebabe"

        cls.tmpdir = tempfile.TemporaryDirectory(prefix="deploy-verify-")
        cls.trace_log_path = Path(cls.tmpdir.name) / "trace-events.jsonl"
        cls.trace_log_path.write_text("", encoding="utf-8")
        cls.smoke_json_path = Path(cls.tmpdir.name) / "smoke.json"

        api_env = os.environ.copy()
        api_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.api_port),
                "APP_VERSION": "api-test-version",
                "TRACE_DEBUG_ENABLED": "1",
                "TRACE_DEBUG_LOG_PATH": str(cls.trace_log_path),
                "PYTHONPATH": str(REPO_ROOT),
            }
        )
        cls.api_proc = subprocess.Popen(
            [sys.executable, "-m", "src.web_service"],
            cwd=str(REPO_ROOT),
            env=api_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        ui_env = os.environ.copy()
        ui_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.ui_port),
                "APP_VERSION": cls.expected_version,
                "UI_API_BASE_URL": cls.api_base_url,
                "PYTHONPATH": str(REPO_ROOT),
            }
        )
        cls.ui_proc = subprocess.Popen(
            [sys.executable, "-m", "src.ui_service"],
            cwd=str(REPO_ROOT),
            env=ui_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        _wait_for(f"{cls.api_base_url}/health")
        _wait_for(f"{cls.ui_base_url}/healthz")

        cls.trace_request_id = "deploy-trace-test-001"
        _http_json(
            f"{cls.api_base_url}/analyze",
            method="POST",
            payload={"intelligence_mode": "basic"},
            headers={"X-Request-Id": cls.trace_request_id},
        )

        # Give API logger a brief moment to flush request events.
        time.sleep(0.25)

        cls.smoke_json_path.write_text(
            json.dumps({"request_id": cls.trace_request_id}, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls):
        for proc in (cls.api_proc, cls.ui_proc):
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        cls.tmpdir.cleanup()

    def test_post_deploy_verification_passes_with_matching_version_and_trace(self):
        summary_path = Path(self.tmpdir.name) / "summary.md"
        output_path = Path(self.tmpdir.name) / "verify-pass.json"

        cp = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--ui-base-url",
                self.ui_base_url,
                "--expected-version",
                self.expected_version,
                "--api-base-url",
                self.api_base_url,
                "--trace-debug-required",
                "--trace-smoke-json",
                str(self.smoke_json_path),
                "--summary-path",
                str(summary_path),
                "--output-json",
                str(output_path),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )

        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["overall"]["status"], "pass")
        self.assertEqual(payload["checks"]["ui_version"]["status"], "pass")
        self.assertEqual(payload["checks"]["trace_debug"]["status"], "pass")

        summary_text = summary_path.read_text(encoding="utf-8")
        self.assertIn("Post-deploy verification (Version + Trace-Debug)", summary_text)
        self.assertIn("Gesamtstatus: ✅ `pass`", summary_text)

    def test_post_deploy_verification_fails_on_version_mismatch(self):
        output_path = Path(self.tmpdir.name) / "verify-fail-version.json"

        cp = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--ui-base-url",
                self.ui_base_url,
                "--expected-version",
                "deadbeef",
                "--api-base-url",
                self.api_base_url,
                "--output-json",
                str(output_path),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )

        self.assertEqual(cp.returncode, 1, msg=cp.stdout + "\n" + cp.stderr)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["overall"]["status"], "fail")
        self.assertEqual(payload["overall"]["reason"], "ui_version_mismatch")


if __name__ == "__main__":
    unittest.main()
