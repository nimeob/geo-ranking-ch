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


def _http_json(url: str, *, timeout: float = 10.0) -> tuple[int, dict, dict]:
    req = request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body), {k.lower(): v for k, v in resp.headers.items()}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body), {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}


def _http_text(url: str, *, timeout: float = 10.0) -> tuple[int, str, dict]:
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body, {k.lower(): v for k, v in resp.headers.items()}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, body, headers


def _http_post_json(url: str, payload: dict, *, timeout: float = 20.0) -> tuple[int, dict, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        method="POST",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
            return resp.status, parsed, {k.lower(): v for k, v in resp.headers.items()}
    except error.HTTPError as exc:
        parsed = json.loads(exc.read().decode("utf-8"))
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, parsed, headers


class TestHistoryNavigationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store_file = str(Path(cls.tmp.name) / "async_jobs_store.json")

        cls.api_port = _free_port()
        cls.api_base_url = f"http://127.0.0.1:{cls.api_port}"

        api_env = os.environ.copy()
        api_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.api_port),
                "APP_VERSION": "api-test-v1",
                "PYTHONPATH": str(REPO_ROOT),
                "ENABLE_E2E_FAULT_INJECTION": "1",
                "ENABLE_QUERY_HISTORY": "1",
                "ASYNC_JOBS_STORE_FILE": cls.store_file,
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
                status, _, _ = _http_json(f"{cls.api_base_url}/health")
                if status == 200:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError("api web_service wurde lokal nicht rechtzeitig erreichbar")

        status, body, _ = _http_post_json(
            f"{cls.api_base_url}/analyze",
            {"query": "__ok__", "intelligence_mode": "basic"},
        )
        if status != 200 or not body.get("ok"):
            raise RuntimeError(f"sync analyze failed: {status} {body}")

        status, history_payload, _ = _http_json(f"{cls.api_base_url}/analyze/history?limit=20")
        if status != 200 or not history_payload.get("ok"):
            raise RuntimeError(f"history fetch failed: {status} {history_payload}")

        entries = history_payload.get("history") or []
        if not entries:
            raise RuntimeError("expected at least one history entry")

        cls.result_id = str(entries[0].get("result_id") or "").strip()
        if not cls.result_id:
            raise RuntimeError(f"missing result_id in history entry: {entries[0]}")

        cls.ui_port = _free_port()
        cls.ui_base_url = f"http://127.0.0.1:{cls.ui_port}"

        ui_env = os.environ.copy()
        ui_env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.ui_port),
                "APP_VERSION": "ui-test-v1",
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
                status, _, _ = _http_text(f"{cls.ui_base_url}/healthz")
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

    def test_ui_history_page_renders_and_targets_api_base(self) -> None:
        status, body, headers = _http_text(f"{self.ui_base_url}/history")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Historische Abfragen", body)
        self.assertIn('aria-label="Navigation umschalten"', body)
        self.assertIn('aria-label="Hauptnavigation"', body)
        self.assertIn('function setBurgerOpen(nextOpen)', body)
        self.assertIn('"pointerdown",', body)
        self.assertIn(f'const ANALYZE_HISTORY_ENDPOINT = "{self.api_base_url}/analyze/history"', body)

    def test_ui_result_page_renders_tabs_and_targets_api_base(self) -> None:
        status, body, headers = _http_text(f"{self.ui_base_url}/results/{self.result_id}")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("Overview", body)
        self.assertIn("Sources / Evidence", body)
        self.assertIn("Generated / Derived", body)
        self.assertIn("Raw JSON", body)
        self.assertIn('aria-label="Navigation umschalten"', body)
        self.assertIn('aria-label="Hauptnavigation"', body)
        self.assertIn('if (event.key === "ArrowDown")', body)
        self.assertIn('window.addEventListener("keydown"', body)
        self.assertIn(f'const RESULTS_ENDPOINT_BASE = "{self.api_base_url}/analyze/results"', body)


if __name__ == "__main__":
    unittest.main()
