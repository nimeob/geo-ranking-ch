from __future__ import annotations

import importlib.util
import json
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_bl337_ui_frontdoor_e2e.py"

spec = importlib.util.spec_from_file_location("run_bl337_ui_frontdoor_e2e", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


GOOD_UI_HTML = """<!doctype html>
<html lang="de">
  <head><title>geo-ranking.ch GUI MVP</title></head>
  <body>
    <nav id="gui-shell-nav" aria-label="Kernnavigation">
      <a href="#input">Input</a>
      <a href="#map">Karte</a>
      <a href="#result">Result-Panel</a>
    </nav>
    <article id="input">
      <form id="analyze-form" class="stack">
        <input id="query" name="query" type="text" required />
        <select id="intelligence-mode" name="intelligence_mode"><option>basic</option></select>
        <input id="api-token" type="password" />
        <button id="submit-btn" type="submit">Senden</button>
      </form>
    </article>
    <article id="map">
      <div id="map-click-surface" role="application">
        <div id="map-tile-layer" aria-hidden="true"></div>
      </div>
    </article>
    <article id="result"></article>
    <script>
      const formEl = document.getElementById("analyze-form");
      const queryEl = document.getElementById("query");
      const modeEl = document.getElementById("intelligence-mode");
      const tokenEl = document.getElementById("api-token");
      const submitBtn = document.getElementById("submit-btn");
      const mapSurface = document.getElementById("map-click-surface");
      const state = { phase: "idle", lastError: null };

      function buildOsmTileUrl(zoom, tileX, tileY) {
        return `https://tile.openstreetmap.org/${zoom}/${tileX}/${tileY}.png`;
      }

      function initializeInteractiveMap() {
        const mapTile = document.getElementById("map-tile-layer");
        mapTile.setAttribute("data-src", buildOsmTileUrl(8, 133, 88));
        mapSurface.addEventListener("wheel", (event) => {
          event.preventDefault();
        }, { passive: false });
      }

      async function runAnalyze(payload, token) {
        const response = await fetch("https://api.dev.georanking.ch/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const parsed = await response.json();
        if (!response.ok || !parsed.ok) {
          const errCode = parsed && parsed.error ? parsed.error : `http_${response.status}`;
          const errMsg = parsed && parsed.message ? parsed.message : "Unbekannter Fehler";
          const richError = `${errCode}: ${errMsg}`;
          return { ok: false, response: parsed, errorMessage: richError };
        }
        return { ok: true, response: parsed, errorMessage: null };
      }

      async function startAnalyze(payload) {
        const result = await runAnalyze(payload, (tokenEl.value || "").trim());
        state.phase = result.ok ? "success" : "error";
        state.lastError = result.errorMessage;
      }

      initializeInteractiveMap();

      formEl.addEventListener("submit", async (event) => {
        event.preventDefault();
        const query = (queryEl.value || "").trim();
        if (!query) {
          state.phase = "error";
          state.lastError = "Bitte eine Adresse eingeben.";
          state.lastPayload = {
            ok: false,
            error: "validation",
            message: "query darf nicht leer sein",
          };
          return;
        }
        await startAnalyze({ query, intelligence_mode: modeEl.value || "basic" });
      });
    </script>
  </body>
</html>
"""

BROKEN_UI_HTML = """<!doctype html>
<html><head><title>broken</title></head><body><p>UI down</p></body></html>
"""


class _UiHandler(BaseHTTPRequestHandler):
    html = GOOD_UI_HTML
    status_code = 200

    def do_GET(self):  # noqa: N802
        body = self.html.encode("utf-8")
        self.send_response(self.status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: A003
        return


class _ApiHandler(BaseHTTPRequestHandler):
    def _write_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        if self.path != "/analyze":
            self._write_json(404, {"ok": False, "error": "not_found", "message": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            json.loads(raw.decode("utf-8"))
            self._write_json(200, {"ok": True, "request_id": "ok-1"})
        except Exception:
            self._write_json(400, {"ok": False, "error": "bad_request", "message": "invalid json"})

    def log_message(self, fmt, *args):  # noqa: A003
        return


class TestRunBl337UiFrontdoorE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ui_port = _free_port()
        cls.api_port = _free_port()

        cls.ui_server = ThreadingHTTPServer(("127.0.0.1", cls.ui_port), _UiHandler)
        cls.api_server = ThreadingHTTPServer(("127.0.0.1", cls.api_port), _ApiHandler)

        cls.ui_thread = threading.Thread(target=cls.ui_server.serve_forever, daemon=True)
        cls.api_thread = threading.Thread(target=cls.api_server.serve_forever, daemon=True)

        cls.ui_thread.start()
        cls.api_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.ui_server.shutdown()
        cls.api_server.shutdown()
        cls.ui_server.server_close()
        cls.api_server.server_close()
        cls.ui_thread.join(timeout=5)
        cls.api_thread.join(timeout=5)

    def _build_matrix(self, *, app_base_url: str, api_base_url: str, path: Path) -> None:
        payload = {
            "schemaVersion": "bl337.internet-e2e.v1",
            "generatedAtUtc": "2026-03-01T00:00:00Z",
            "targets": {
                "apiBaseUrl": api_base_url,
                "appBaseUrl": app_base_url,
            },
            "summary": {"total": 9, "planned": 9, "pass": 0, "fail": 0, "blocked": 0},
            "tests": [
                {
                    "testId": "API.HEALTH.200",
                    "area": "api",
                    "title": "health",
                    "preconditions": [],
                    "steps": ["GET"],
                    "expectedResult": "HTTP 200",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "API.ANALYZE.POST.200",
                    "area": "api",
                    "title": "analyze",
                    "preconditions": [],
                    "steps": ["POST"],
                    "expectedResult": "HTTP 200",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "API.ANALYZE.NON_BASIC.FINAL_STATE",
                    "area": "api",
                    "title": "analyze non-basic",
                    "preconditions": [],
                    "steps": ["POST extended"],
                    "expectedResult": "Success oder strukturierter Fehler",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "API.ANALYZE.INVALID_PAYLOAD.400",
                    "area": "api",
                    "title": "invalid",
                    "preconditions": [],
                    "steps": ["POST invalid"],
                    "expectedResult": "HTTP 400",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "API.ANALYZE.METHOD_MISMATCH.405",
                    "area": "api",
                    "title": "method mismatch",
                    "preconditions": [],
                    "steps": ["GET"],
                    "expectedResult": "HTTP 405",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "UI.LOAD.HOME.200",
                    "area": "ui",
                    "title": "ui load",
                    "preconditions": [],
                    "steps": ["GET"],
                    "expectedResult": "HTTP 200",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "UI.NAV.CORE_FLOW.VISIBLE",
                    "area": "ui",
                    "title": "ui nav",
                    "preconditions": [],
                    "steps": ["ui"],
                    "expectedResult": "visible",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "UI.INVALID_INPUT.ERROR_SURFACE",
                    "area": "ui",
                    "title": "ui invalid",
                    "preconditions": [],
                    "steps": ["ui"],
                    "expectedResult": "error",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
                {
                    "testId": "UI.API_ERROR.CONSISTENCY",
                    "area": "ui",
                    "title": "ui consistency",
                    "preconditions": [],
                    "steps": ["ui"],
                    "expectedResult": "consistent",
                    "actualResult": None,
                    "status": "planned",
                    "evidenceLinks": [],
                    "notes": "",
                },
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_main_updates_matrix_and_evidence_when_ui_checks_pass(self) -> None:
        _UiHandler.html = GOOD_UI_HTML
        _UiHandler.status_code = 200

        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = Path(tmpdir) / "matrix.json"
            evidence = Path(tmpdir) / "evidence.json"
            self._build_matrix(
                app_base_url=f"http://127.0.0.1:{self.ui_port}",
                api_base_url=f"http://127.0.0.1:{self.api_port}",
                path=matrix,
            )

            rc = module.main(["--matrix", str(matrix), "--evidence-json", str(evidence)])
            self.assertEqual(rc, 0)
            self.assertTrue(evidence.exists())

            matrix_payload = json.loads(matrix.read_text(encoding="utf-8"))
            summary = matrix_payload["summary"]
            self.assertEqual(summary["pass"], 4)
            self.assertEqual(summary["planned"], 5)
            self.assertEqual(summary["fail"], 0)
            self.assertEqual(summary["blocked"], 0)

            ui_rows = [
                case
                for case in matrix_payload["tests"]
                if case.get("testId", "").startswith("UI.")
            ]
            self.assertEqual(len(ui_rows), 4)
            for row in ui_rows:
                self.assertEqual(row["status"], "pass")
                self.assertIsInstance(row["actualResult"], str)
                self.assertTrue(row["actualResult"].strip())
                self.assertGreaterEqual(len(row["evidenceLinks"]), 2)

            evidence_payload = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(evidence_payload["summary"]["pass"], 4)
            self.assertEqual(evidence_payload["summary"]["fail"], 0)

    def test_main_returns_nonzero_when_dom_markers_are_missing(self) -> None:
        _UiHandler.html = BROKEN_UI_HTML
        _UiHandler.status_code = 200

        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = Path(tmpdir) / "matrix.json"
            evidence = Path(tmpdir) / "evidence.json"
            self._build_matrix(
                app_base_url=f"http://127.0.0.1:{self.ui_port}",
                api_base_url=f"http://127.0.0.1:{self.api_port}",
                path=matrix,
            )

            rc = module.main(["--matrix", str(matrix), "--evidence-json", str(evidence)])
            self.assertEqual(rc, 1)

            matrix_payload = json.loads(matrix.read_text(encoding="utf-8"))
            nav_case = next(case for case in matrix_payload["tests"] if case.get("testId") == "UI.NAV.CORE_FLOW.VISIBLE")
            self.assertEqual(nav_case["status"], "fail")
            self.assertIn("WP3 runtime reason", nav_case["notes"])


if __name__ == "__main__":
    unittest.main()
