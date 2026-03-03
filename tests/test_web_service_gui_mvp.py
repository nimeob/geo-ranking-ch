import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_text(url: str, *, timeout: float = 10.0):
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return (
                resp.status,
                resp.read().decode("utf-8"),
                {k.lower(): v for k, v in resp.headers.items()},
            )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, body, headers


class TestWebServiceGuiMvp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        env = os.environ.copy()
        env.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(cls.port),
                "APP_VERSION": "test-gui-v1",
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

        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                status, _, _ = _http_text(f"{cls.base_url}/health")
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

    def test_gui_shell_is_served_with_html_content_type(self):
        status, body, headers = _http_text(f"{self.base_url}/gui")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertIn("geo-ranking.ch GUI MVP", body)
        self.assertIn('id="burger-shell"', body)
        self.assertIn('id="burger-btn"', body)
        self.assertIn('aria-label="Navigation umschalten"', body)
        self.assertIn('id="burger-menu"', body)
        self.assertIn('id="burger-backdrop"', body)
        self.assertIn('aria-label="Hauptnavigation"', body)
        self.assertIn('id="analyze-form"', body)
        self.assertIn('id="trace-debug"', body)
        self.assertIn('id="burger-login-link"', body)
        self.assertIn('id="burger-logout-link"', body)
        self.assertIn('id="auth-login-inline"', body)
        self.assertIn('href="/auth/logout"', body)
        self.assertIn("Version test-gui-v1", body)

    def test_gui_shell_exposes_state_machine_markers(self):
        status, body, _ = _http_text(f"{self.base_url}/gui")
        self.assertEqual(status, 200)
        self.assertIn('Status: idle', body)
        self.assertIn('idle -> loading -> success/error', body)
        self.assertIn('id="error-box"', body)
        self.assertIn('id="map-click-surface"', body)
        self.assertIn('id="map-tile-layer"', body)
        self.assertIn('id="map-click-marker"', body)
        self.assertIn('id="map-user-marker"', body)
        self.assertIn('id="map-user-accuracy"', body)
        self.assertIn('id="map-locate-btn"', body)
        self.assertIn('id="map-location-meta"', body)
        self.assertIn('id="map-zoom-in"', body)
        self.assertIn('id="map-zoom-out"', body)
        self.assertIn('id="core-factors"', body)
        self.assertIn('id="results-list"', body)
        self.assertIn('id="results-sort"', body)
        self.assertIn('id="results-dir"', body)
        self.assertIn('id="results-ko"', body)
        self.assertIn('id="results-min-score"', body)
        self.assertIn('id="results-max-distance"', body)
        self.assertIn('id="results-min-security"', body)
        self.assertIn('id="results-clear"', body)
        self.assertIn('id="results-table-shell"', body)
        self.assertIn('id="results-body"', body)
        self.assertIn('const RESULTS_LIST_COPY = Object.freeze({', body)
        self.assertIn('function resolveResultsEmptyState(total)', body)
        self.assertIn('function handleResultsEmptyStatePrimaryAction(reason)', body)
        self.assertIn('className = "results-empty-state"', body)
        self.assertIn('className = "results-empty-action"', body)
        self.assertIn('min-height: 12.25rem', body)
        self.assertIn('id="history-shell"', body)
        self.assertIn('const ANALYZE_HISTORY_ENDPOINT = "/analyze/history";', body)
        self.assertIn('const AUTH_ME_ENDPOINT = "/auth/me";', body)
        self.assertIn('function refreshAuthSession({ force = false } = {})', body)
        self.assertIn('function ensureAuthenticatedForAction({ trigger = "auth_guard", requestId = "" } = {})', body)
        self.assertIn('const authenticated = await ensureAuthenticatedForAction({', body)
        self.assertIn('rows.join("\\n")', body)
        self.assertIn('function restoreResultsListDeepLinkInput()', body)
        self.assertIn('results_sort', body)
        self.assertIn('id="async-mode-requested"', body)
        self.assertIn('id="async-job-box"', body)
        self.assertIn('const ANALYZE_JOBS_ENDPOINT_BASE = "/analyze/jobs";', body)
        self.assertIn('coordinates.lat/lon', body)
        self.assertIn('https://tile.openstreetmap.org/', body)
        self.assertIn('function buildOsmTileUrl(zoom, tileX, tileY)', body)
        self.assertIn('function initializeInteractiveMap()', body)
        self.assertIn('"wheel",', body)
        self.assertIn('function normalizeWheelZoomDelta(event)', body)
        self.assertIn('const touchState = {', body)
        self.assertIn('function startPinchGesture()', body)
        self.assertIn('function applyPinchTransform()', body)
        self.assertIn('function schedulePinchTransform()', body)
        self.assertIn('window.requestAnimationFrame(() => {', body)
        self.assertIn('function cancelPinchFrame()', body)
        self.assertIn('Math.log2(scale)', body)
        self.assertIn('ui.interaction.map.pinch_start', body)
        self.assertIn('touchState.pointers.size >= 2', body)
        self.assertIn('async function requestDeviceLocation()', body)
        self.assertIn('navigator.geolocation.getCurrentPosition', body)
        self.assertIn('function setUserLocation(lat, lon', body)
        self.assertIn('id="map-location-meta"', body)
        self.assertIn('zoomMapAtSurfaceCenter(1);', body)
        self.assertIn('zoomMapAtSurfaceCenter(-1);', body)
        self.assertIn('function timeoutSecondsForMode(mode)', body)
        self.assertIn('const controller = new AbortController();', body)
        self.assertIn('timeout_seconds: timeoutSecondsForMode(mode)', body)
        self.assertIn('function emitUiEvent(eventName, details = {})', body)
        self.assertIn('function setPhase(nextPhase, context = {})', body)
        self.assertIn('ui.api.request.start', body)
        self.assertIn('ui.api.request.end', body)
        self.assertIn('headers["X-Request-Id"] = requestId;', body)
        self.assertIn('headers["X-Session-Id"] = uiSessionId;', body)
        self.assertIn('id="request-id-value"', body)
        self.assertIn('id="request-trace-link"', body)
        self.assertIn('id="request-id-copy-btn"', body)
        self.assertIn('id="request-id-feedback"', body)
        self.assertIn('function copyTextToClipboard(value)', body)
        self.assertIn('function openTraceFromResultPanel()', body)
        self.assertIn('ui.interaction.request_id.copy', body)
        self.assertIn('id="trace-debug-form"', body)
        self.assertIn('id="trace-phase-pill"', body)
        self.assertIn('id="trace-timeline"', body)
        self.assertIn('const TRACE_DEBUG_ENDPOINT = "/debug/trace";', body)
        self.assertIn('function restoreTraceDeepLinkInput()', body)
        self.assertIn('function buildTraceLookupUrl(requestId)', body)
        self.assertIn('function normalizeTraceEvents(rawEvents)', body)
        self.assertIn('function renderTraceState()', body)
        self.assertIn('ui.trace.request.start', body)
        self.assertIn('ui.trace.request.end', body)
        self.assertIn('startTraceLookup(deepLinkTraceRequestId, "trace_deep_link")', body)
        self.assertIn('function setBurgerOpen(nextOpen)', body)
        self.assertIn('document.body.classList.toggle("burger-open", nextOpen);', body)
        self.assertIn('burgerBackdrop.addEventListener("click"', body)
        self.assertIn('document.addEventListener(', body)
        self.assertIn('"pointerdown",', body)
        self.assertIn('if (event.key === "ArrowDown")', body)
        self.assertIn('window.addEventListener("keydown"', body)

    def test_gui_map_marker_legibility_styles_present(self):
        status, body, _ = _http_text(f"{self.base_url}/gui")
        self.assertEqual(status, 200)
        self.assertIn(".map-surface.has-marker .map-crosshair", body)
        self.assertIn('mapSurface.classList.add("has-marker")', body)
        self.assertIn("overflow-wrap: anywhere", body)
        self.assertIn("flex: 1 1 260px", body)
        self.assertIn(".map-legend small + small", body)
        self.assertIn("word-break: break-word", body)
        self.assertIn("@media (max-width: 520px)", body)
        self.assertIn("min-height: 280px", body)
        self.assertIn("width: 22px", body)
        self.assertIn("flex-direction: column", body)

    def test_gui_mobile_touch_target_css_contract_present(self):
        status, body, _ = _http_text(f"{self.base_url}/gui")
        self.assertEqual(status, 200)
        self.assertIn("--touch-target-min: 44px", body)
        self.assertIn("@media (max-width: 768px)", body)
        self.assertIn("#burger-btn,", body)
        self.assertIn(".touch-toggle", body)
        self.assertIn("id=\"async-mode-requested\"", body)
        self.assertIn("min-height: var(--touch-target-min)", body)
        self.assertIn("width: var(--touch-target-min)", body)
        self.assertIn('id="map-zoom-in"', body)

    def test_gui_route_accepts_trailing_slash_query_and_double_slash(self):
        status, body, _ = _http_text(f"{self.base_url}//gui///?probe=1")
        self.assertEqual(status, 200)
        self.assertIn("Result-Panel", body)


if __name__ == "__main__":
    unittest.main()
