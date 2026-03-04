import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_deploy_gate.sh"


class _ProbeHandler(BaseHTTPRequestHandler):
    api_status = 200
    gui_status = 200
    db_status = "ok"
    db_reason = "database_ok"

    def log_message(self, format, *args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/health/details"):
            status = 200
            db_status = str(self.db_status)
            db_reason = str(self.db_reason)
            overall = "ok" if db_status == "ok" else "down" if db_status == "down" else "degraded"
            payload = {
                "ok": True,
                "status": overall,
                "checks": {
                    "database": {
                        "status": db_status,
                        "reason": db_reason,
                    }
                },
            }
            body = json.dumps(payload).encode("utf-8")
            content_type = "application/json"
        elif self.path.startswith("/health"):
            status = self.api_status
            body = b'{"ok":true}'
            content_type = "application/json"
        elif self.path.startswith("/gui"):
            status = self.gui_status
            body = b"<html>ready</html>"
            content_type = "text/html"
        else:
            status = 404
            body = b"not-found"
            content_type = "text/plain"

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class TestRunDeployGateScript(unittest.TestCase):
    def _start_server(self, *, api_status: int, gui_status: int, db_status: str = "ok", db_reason: str = "database_ok"):
        handler_cls = type(
            "ConfigurableProbeHandler",
            (_ProbeHandler,),
            {
                "api_status": api_status,
                "gui_status": gui_status,
                "db_status": db_status,
                "db_reason": db_reason,
            },
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    def test_success_when_api_gui_and_db_are_green(self):
        self.assertTrue(SCRIPT_PATH.exists(), f"Script fehlt: {SCRIPT_PATH}")

        server, thread = self._start_server(api_status=200, gui_status=200, db_status="ok", db_reason="database_connected")
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with tempfile.TemporaryDirectory(prefix="deploy-gate-success-") as tmp:
                report_path = Path(tmp) / "deploy-gate.json"
                env = os.environ.copy()
                env.update(
                    {
                        "DEPLOY_GATE_API_HEALTH_URL": f"{base}/health",
                        "DEPLOY_GATE_GUI_READY_URL": f"{base}/gui",
                        "DEPLOY_GATE_DB_DETAILS_URL": f"{base}/health/details",
                        "DEPLOY_GATE_MAX_WAIT_SECONDS": "5",
                        "DEPLOY_GATE_RETRY_DELAY_SECONDS": "1",
                        "DEPLOY_GATE_OUTPUT_JSON": str(report_path),
                    }
                )

                result = subprocess.run(
                    [str(SCRIPT_PATH)],
                    cwd=str(REPO_ROOT),
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=20,
                )

                self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
                self.assertIn("deploy-gate outcome=pass", result.stdout)
                self.assertTrue(report_path.exists(), "Deploy-Gate-Report fehlt")

                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(report["schema_version"], "deploy-gate-report/v1")
                self.assertEqual(report["status"], "success")
                self.assertEqual(report["failure_reason"], "all_checks_green")
                self.assertFalse(report["rollback_required"])
                self.assertEqual(report["last_probe"]["api"]["http_status"], "200")
                self.assertEqual(report["last_probe"]["gui"]["http_status"], "200")
                self.assertEqual(report["last_probe"]["database"]["http_status"], "200")
                self.assertEqual(report["last_probe"]["database"]["status"], "ok")
                self.assertEqual(report["last_probe"]["database"]["reason"], "database_connected")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_fail_closed_with_rollback_required_marker_when_gui_stays_unhealthy(self):
        self.assertTrue(SCRIPT_PATH.exists(), f"Script fehlt: {SCRIPT_PATH}")

        server, thread = self._start_server(api_status=200, gui_status=503, db_status="ok")
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with tempfile.TemporaryDirectory(prefix="deploy-gate-fail-") as tmp:
                report_path = Path(tmp) / "deploy-gate.json"
                env = os.environ.copy()
                env.update(
                    {
                        "DEPLOY_GATE_API_HEALTH_URL": f"{base}/health",
                        "DEPLOY_GATE_GUI_READY_URL": f"{base}/gui",
                        "DEPLOY_GATE_DB_DETAILS_URL": f"{base}/health/details",
                        "DEPLOY_GATE_MAX_WAIT_SECONDS": "2",
                        "DEPLOY_GATE_RETRY_DELAY_SECONDS": "1",
                        "DEPLOY_GATE_OUTPUT_JSON": str(report_path),
                        "DEPLOY_GATE_PREVIOUS_API_TASKDEF": "arn:aws:ecs:eu-central-1:123456789012:task-definition/api:17",
                        "DEPLOY_GATE_PREVIOUS_UI_TASKDEF": "arn:aws:ecs:eu-central-1:123456789012:task-definition/ui:42",
                    }
                )

                result = subprocess.run(
                    [str(SCRIPT_PATH)],
                    cwd=str(REPO_ROOT),
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=20,
                )

                combined_output = (result.stdout or "") + "\n" + (result.stderr or "")
                self.assertEqual(result.returncode, 1, combined_output)
                self.assertIn("ROLLBACK_REQUIRED", combined_output)
                self.assertIn("Deploy gate failure reason", combined_output)
                self.assertTrue(report_path.exists(), "Deploy-Gate-Report fehlt bei Fail-Case")

                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "failed")
                self.assertTrue(report["rollback_required"])
                self.assertEqual(report["failure_reason"], "gui_probe_http_503")
                self.assertEqual(
                    report["rollback_hint"]["api_previous_taskdef"],
                    "arn:aws:ecs:eu-central-1:123456789012:task-definition/api:17",
                )
                self.assertEqual(
                    report["rollback_hint"]["ui_previous_taskdef"],
                    "arn:aws:ecs:eu-central-1:123456789012:task-definition/ui:42",
                )
                self.assertEqual(report["last_probe"]["api"]["http_status"], "200")
                self.assertEqual(report["last_probe"]["gui"]["http_status"], "503")
                self.assertEqual(report["last_probe"]["database"]["status"], "ok")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_fail_closed_when_database_check_is_not_ok(self):
        self.assertTrue(SCRIPT_PATH.exists(), f"Script fehlt: {SCRIPT_PATH}")

        server, thread = self._start_server(api_status=200, gui_status=200, db_status="down", db_reason="connection_refused")
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with tempfile.TemporaryDirectory(prefix="deploy-gate-db-down-") as tmp:
                report_path = Path(tmp) / "deploy-gate.json"
                env = os.environ.copy()
                env.update(
                    {
                        "DEPLOY_GATE_API_HEALTH_URL": f"{base}/health",
                        "DEPLOY_GATE_GUI_READY_URL": f"{base}/gui",
                        "DEPLOY_GATE_DB_DETAILS_URL": f"{base}/health/details",
                        "DEPLOY_GATE_MAX_WAIT_SECONDS": "2",
                        "DEPLOY_GATE_RETRY_DELAY_SECONDS": "1",
                        "DEPLOY_GATE_OUTPUT_JSON": str(report_path),
                    }
                )

                result = subprocess.run(
                    [str(SCRIPT_PATH)],
                    cwd=str(REPO_ROOT),
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=20,
                )

                combined_output = (result.stdout or "") + "\n" + (result.stderr or "")
                self.assertEqual(result.returncode, 1, combined_output)
                self.assertIn("Final DB status", combined_output)
                self.assertTrue(report_path.exists(), "Deploy-Gate-Report fehlt bei DB-Fail-Case")

                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "failed")
                self.assertTrue(report["rollback_required"])
                self.assertEqual(report["last_probe"]["database"]["status"], "down")
                self.assertEqual(report["last_probe"]["database"]["reason"], "connection_refused")
                self.assertTrue(report["failure_reason"].startswith("db_reachability_status_down"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
