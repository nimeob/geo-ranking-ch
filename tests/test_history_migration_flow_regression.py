from __future__ import annotations

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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(
    method: str,
    url: str,
    *,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> tuple[int, dict, dict[str, str]]:
    body = None
    request_headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url, method=method, data=body, headers=request_headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
            response_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, parsed, response_headers
    except error.HTTPError as exc:
        parsed = json.loads(exc.read().decode("utf-8"))
        response_headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, parsed, response_headers


def _http_text(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> tuple[int, str, dict[str, str]]:
    req = request.Request(url, method=method, headers=headers or {})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            response_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, body, response_headers
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        response_headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, body, response_headers


class TestHistoryMigrationFlowRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory(prefix="history-migration-regression-")
        cls.store_file = str(Path(cls.tmp.name) / "async_jobs_store.json")

        cls.user_a = {"token": "history-user-a", "user_id": "user-a", "org_id": "org-shared"}
        cls.user_b = {"token": "history-user-b", "user_id": "user-b", "org_id": "org-shared"}

        cls.api_port = _free_port()
        cls.api_base_url = f"http://127.0.0.1:{cls.api_port}"
        api_env = os.environ.copy()
        api_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.api_port),
                "APP_VERSION": "history-migration-api-test-v1",
                "PYTHONPATH": str(REPO_ROOT),
                "ENABLE_QUERY_HISTORY": "1",
                "ENABLE_E2E_FAULT_INJECTION": "1",
                "ASYNC_JOBS_STORE_FILE": cls.store_file,
                "PHASE1_AUTH_USERS_JSON": json.dumps({"users": [cls.user_a, cls.user_b]}),
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

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _, _ = _http_json("GET", f"{cls.api_base_url}/health")
                if status == 200:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError("api web_service wurde lokal nicht rechtzeitig erreichbar")

        analyze_headers = {"Authorization": f"Bearer {cls.user_a['token']}"}
        for index in range(3):
            status, analyze_payload, _ = _http_json(
                "POST",
                f"{cls.api_base_url}/analyze",
                payload={"query": f"__ok__ history regression {index}", "intelligence_mode": "basic"},
                headers=analyze_headers,
                timeout=20.0,
            )
            if status != 200 or not analyze_payload.get("ok"):
                raise RuntimeError(f"sync analyze failed: {status} {analyze_payload}")

        status, history_payload, _ = _http_json(
            "GET",
            f"{cls.api_base_url}/analyze/history?limit=20",
            headers=analyze_headers,
        )
        if status != 200 or not history_payload.get("ok"):
            raise RuntimeError(f"history fetch failed: {status} {history_payload}")

        history_entries = history_payload.get("history") or []
        if len(history_entries) < 3:
            raise RuntimeError(f"expected at least three history entries for owner user, got {len(history_entries)}")

        cls.owner_result_ids = [str(row.get("result_id") or "").strip() for row in history_entries]
        cls.owner_result_ids = [result_id for result_id in cls.owner_result_ids if result_id]
        if len(cls.owner_result_ids) < 3:
            raise RuntimeError("missing result_id values in owner history entries")

        cls.owner_result_id = cls.owner_result_ids[0]

        cls.ui_port = _free_port()
        cls.ui_base_url = f"http://127.0.0.1:{cls.ui_port}"
        ui_env = os.environ.copy()
        ui_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.ui_port),
                "APP_VERSION": "history-migration-ui-test-v1",
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

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _, _ = _http_text("GET", f"{cls.ui_base_url}/healthz")
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.2)

        raise RuntimeError("ui_service wurde lokal nicht rechtzeitig erreichbar")

    @classmethod
    def tearDownClass(cls) -> None:
        for proc in (getattr(cls, "ui_proc", None), getattr(cls, "api_proc", None)):
            if proc is None:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        if hasattr(cls, "tmp"):
            cls.tmp.cleanup()

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_history_flow_happy_path_keeps_ui_and_api_ownership_boundaries(self) -> None:
        ui_status, ui_body, ui_headers = _http_text("GET", f"{self.ui_base_url}/history")
        self.assertEqual(ui_status, 200)
        self.assertIn("text/html", ui_headers.get("content-type", ""))
        self.assertIn(f'const ANALYZE_HISTORY_ENDPOINT = "{self.api_base_url}/analyze/history"', ui_body)

        api_status, api_payload, api_headers = _http_json(
            "GET",
            f"{self.api_base_url}/analyze/history?limit=10",
            headers=self._auth_headers(self.user_a["token"]),
        )
        self.assertEqual(api_status, 200)
        self.assertTrue(api_payload.get("ok"))
        self.assertIn("application/json", api_headers.get("content-type", ""))
        self.assertTrue(
            any(str(row.get("result_id") or "") == self.owner_result_id for row in api_payload.get("history") or [])
        )
        deprecation = api_payload.get("deprecation") or {}
        self.assertEqual(deprecation.get("successor"), "/history")

    def test_history_flow_pagination_metadata_and_deprecation_headers(self) -> None:
        status, payload, headers = _http_json(
            "GET",
            f"{self.api_base_url}/analyze/history?limit=1&offset=1",
            headers=self._auth_headers(self.user_a["token"]),
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("limit"), 1)
        self.assertEqual(payload.get("offset"), 1)
        self.assertGreaterEqual(int(payload.get("total") or 0), 3)
        history_rows = payload.get("history") or []
        self.assertEqual(len(history_rows), 1)
        self.assertIn(str(history_rows[0].get("result_id") or ""), self.owner_result_ids)

        self.assertEqual(headers.get("deprecation"), "true")
        self.assertTrue((headers.get("sunset") or "").strip())
        self.assertIn('rel="deprecation"', str(headers.get("link") or ""))

    def test_history_flow_guard_missing_session_returns_401(self) -> None:
        status, payload, _ = _http_json("GET", f"{self.api_base_url}/analyze/history?limit=5")
        self.assertEqual(status, 401)
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("error"), "unauthorized")
        self.assertIn("missing or invalid bearer token", str(payload.get("message") or ""))

    def test_history_flow_guard_missing_owner_data_returns_empty_history(self) -> None:
        status, payload, _ = _http_json(
            "GET",
            f"{self.api_base_url}/analyze/history?limit=10",
            headers=self._auth_headers(self.user_b["token"]),
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("total"), 0)
        self.assertEqual(payload.get("history"), [])

    def test_history_route_on_api_is_removed_and_points_to_ui_successor(self) -> None:
        status, payload, headers = _http_json("GET", f"{self.api_base_url}/history")
        self.assertEqual(status, 410)
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("error"), "gone")
        self.assertEqual(payload.get("next"), "/history (UI service)")
        self.assertEqual(payload.get("data_source"), "/analyze/history")
        self.assertEqual(headers.get("deprecation"), "true")
        self.assertIn('rel="deprecation"', str(headers.get("link") or ""))


if __name__ == "__main__":
    unittest.main()
