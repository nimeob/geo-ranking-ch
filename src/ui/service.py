#!/usr/bin/env python3
"""Minimaler UI-Webservice für BL-31.2.

Stellt das GUI-MVP (`/` und `/gui`) als eigenständigen HTTP-Service bereit,
liefert einen separaten Healthcheck-Endpunkt (`/healthz`) und bietet eine
Result-Permalink-Page (`/results/<result_id>`), die Result-Daten über
`GET /analyze/results/<result_id>` lädt.

Hinweis: Die Result-Page ist bewusst minimal (API-first) und soll vor allem
Deep-Link-/Sharing-Workflows für Async-Results abdecken.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from src.shared.gui_mvp import render_gui_mvp_html

_RESULT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")

_RESULT_PAGE_TEMPLATE = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>geo-ranking.ch — Result __RESULT_ID__</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f8fb;
        --surface: #ffffff;
        --ink: #1b2637;
        --muted: #5a6474;
        --border: #d5dbea;
        --primary: #1957d2;
        --danger: #b93a2f;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        background: var(--bg);
        color: var(--ink);
      }
      header {
        background: var(--surface);
        border-bottom: 1px solid var(--border);
        padding: 1rem 1.25rem;
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: baseline;
      }
      header h1 { margin: 0; font-size: 1.05rem; }
      header p { margin: 0; color: var(--muted); font-size: 0.9rem; }
      header a {
        text-decoration: none;
        color: var(--primary);
        border: 1px solid var(--border);
        padding: 0.35rem 0.55rem;
        border-radius: 0.5rem;
        font-size: 0.86rem;
        background: #f9fbff;
      }
      main {
        padding: 1rem 1.25rem 1.5rem;
        display: grid;
        gap: 1rem;
        max-width: 980px;
      }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.85rem;
        padding: 1rem;
      }
      .card h2 { margin: 0 0 0.75rem; font-size: 1rem; }
      label {
        display: grid;
        gap: 0.3rem;
        font-size: 0.86rem;
        color: var(--muted);
      }
      input, select, button {
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 0.55rem 0.6rem;
        font: inherit;
      }
      button {
        background: var(--primary);
        color: #fff;
        border-color: var(--primary);
        cursor: pointer;
      }
      button[disabled] { opacity: 0.65; cursor: not-allowed; }
      .grid-2 {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: 1fr 1fr;
      }
      @media (max-width: 720px) {
        .grid-2 { grid-template-columns: 1fr; }
      }
      .meta { font-size: 0.84rem; color: var(--muted); }
      .error {
        border: 1px solid rgba(185, 58, 47, 0.35);
        background: rgba(185, 58, 47, 0.08);
        padding: 0.75rem;
        border-radius: 0.65rem;
        color: var(--danger);
        white-space: pre-wrap;
      }
      pre {
        margin: 0;
        max-height: 32rem;
        overflow: auto;
        background: #f8faff;
        border: 1px solid var(--border);
        border-radius: 0.65rem;
        padding: 0.75rem;
      }
      code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>Result-Permalink</h1>
        <p>result_id: <code id="result-id" data-result-id="__RESULT_ID__">__RESULT_ID__</code> · Version __APP_VERSION__</p>
      </div>
      <div>
        <a href="/gui">GUI öffnen</a>
      </div>
    </header>

    <main>
      <section class="card">
        <h2>Loader</h2>
        <p class="meta">Die Seite lädt JSON via <code>GET /analyze/results/&lt;result_id&gt;</code>. Optional kann ein Bearer-Token gesetzt werden (z. B. für geschützte Deployments).</p>
        <div class="grid-2">
          <label>
            API Token (optional)
            <input id="api-token" type="password" placeholder="Bearer-Token" autocomplete="off" />
          </label>
          <label>
            view
            <select id="view-mode">
              <option value="latest">latest</option>
              <option value="requested">requested</option>
            </select>
          </label>
        </div>
        <div style="display:flex; gap: 0.65rem; flex-wrap: wrap; margin-top: 0.85rem; align-items: center;">
          <button id="load-btn" type="button">Result laden</button>
          <a id="raw-link" class="meta" href="#" target="_blank" rel="noopener noreferrer">Raw JSON öffnen</a>
          <span id="status" class="meta">Status: idle</span>
        </div>
        <div id="error" class="error" hidden></div>
      </section>

      <section class="card">
        <h2>Response (JSON)</h2>
        <pre id="payload">{
  "hint": "Loading..."
}</pre>
      </section>

      <script>
        const RESULT_ID = __RESULT_ID_JSON__;
        const RESULTS_ENDPOINT_BASE = __RESULTS_ENDPOINT_BASE_JSON__;
        const TOKEN_STORAGE_KEY = "geo-ranking-ui-api-token";

        const tokenEl = document.getElementById("api-token");
        const viewModeEl = document.getElementById("view-mode");
        const statusEl = document.getElementById("status");
        const loadBtn = document.getElementById("load-btn");
        const payloadEl = document.getElementById("payload");
        const errorEl = document.getElementById("error");
        const rawLinkEl = document.getElementById("raw-link");

        function prettyPrint(value) {
          try {
            return JSON.stringify(value, null, 2);
          } catch (error) {
            return String(value);
          }
        }

        function normalizedViewMode() {
          const raw = String(viewModeEl.value || "latest").trim().toLowerCase();
          if (raw === "requested") return "requested";
          return "latest";
        }

        function buildResultUrl() {
          const view = normalizedViewMode();
          const encodedId = encodeURIComponent(RESULT_ID);
          return `${RESULTS_ENDPOINT_BASE}/${encodedId}?view=${encodeURIComponent(view)}`;
        }

        function setStatus(value) {
          statusEl.textContent = `Status: ${value}`;
        }

        function setError(message) {
          const text = String(message || "").trim();
          if (!text) {
            errorEl.hidden = true;
            errorEl.textContent = "";
            return;
          }
          errorEl.hidden = false;
          errorEl.textContent = text;
        }

        async function loadResult() {
          setError("");
          setStatus("loading");
          loadBtn.disabled = true;

          const url = buildResultUrl();
          rawLinkEl.href = url;

          const token = String(tokenEl.value || "").trim();
          try {
            if (typeof window !== "undefined" && window.sessionStorage) {
              if (token) {
                window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
              } else {
                window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
              }
            }
          } catch (error) {
            // ignore
          }

          const headers = { "Accept": "application/json" };
          if (token) {
            headers["Authorization"] = `Bearer ${token}`;
          }

          let response;
          let parsed;
          try {
            response = await fetch(url, { method: "GET", headers });
            parsed = await response.json();
          } catch (error) {
            setStatus("error");
            setError(error instanceof Error ? error.message : "network_error");
            payloadEl.textContent = prettyPrint({ ok: false, error: "network_error" });
            loadBtn.disabled = false;
            return;
          }

          payloadEl.textContent = prettyPrint(parsed);

          if (!response.ok || !parsed || !parsed.ok) {
            const errCode = parsed && parsed.error ? parsed.error : `http_${response.status}`;
            const errMsg = parsed && parsed.message ? parsed.message : "Unbekannter Fehler";
            setStatus("error");
            setError(`${errCode}: ${errMsg}`);
            loadBtn.disabled = false;
            return;
          }

          setStatus("success");
          loadBtn.disabled = false;
        }

        function applyInitialStateFromUrl() {
          try {
            const url = new URL(window.location.href);
            const view = String(url.searchParams.get("view") || "").trim().toLowerCase();
            if (view === "requested") {
              viewModeEl.value = "requested";
            }
          } catch (error) {
            // ignore
          }

          try {
            if (typeof window !== "undefined" && window.sessionStorage) {
              const token = String(window.sessionStorage.getItem(TOKEN_STORAGE_KEY) || "").trim();
              if (token) {
                tokenEl.value = token;
              }
            }
          } catch (error) {
            // ignore
          }

          rawLinkEl.href = buildResultUrl();
        }

        loadBtn.addEventListener("click", () => {
          void loadResult();
        });

        viewModeEl.addEventListener("change", () => {
          rawLinkEl.href = buildResultUrl();
        });

        applyInitialStateFromUrl();
        void loadResult();
      </script>
    </main>
  </body>
</html>
"""


def _normalize_path(path: str) -> str:
    """Normalisiert doppelte Slashes und entfernt Trailing-Slash (außer Root)."""

    raw = path or "/"
    normalized = posixpath.normpath(raw)
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized == "/.":
        return "/"
    return normalized


def _normalize_result_id(raw_value: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        return ""
    if "/" in normalized:
        return ""
    if not _RESULT_ID_RE.match(normalized):
        return ""
    return normalized


def _build_gui_html(*, app_version: str, api_base_url: str) -> str:
    html = render_gui_mvp_html(app_version=app_version)
    if not api_base_url:
        return html

    normalized_base_url = api_base_url.rstrip("/")
    analyze_url = f"{normalized_base_url}/analyze"
    trace_debug_url = f"{normalized_base_url}/debug/trace"

    html = html.replace('fetch("/analyze", {', f"fetch({json.dumps(analyze_url)}, {{")
    html = html.replace(
        'const TRACE_DEBUG_ENDPOINT = "/debug/trace";',
        f"const TRACE_DEBUG_ENDPOINT = {json.dumps(trace_debug_url)};",
    )
    return html


def _build_result_permalink_html(*, app_version: str, api_base_url: str, result_id: str) -> str:
    """Rendert eine minimalistische Result-Page.

    Die Page lädt JSON asynchron vom API-Endpunkt und zeigt es an.
    """

    normalized_result_id = _normalize_result_id(result_id)
    if not normalized_result_id:
        raise ValueError("invalid result_id")

    safe_result_id = escape(normalized_result_id)
    normalized_base_url = api_base_url.rstrip("/")
    results_endpoint_base = (
        f"{normalized_base_url}/analyze/results" if normalized_base_url else "/analyze/results"
    )

    html = _RESULT_PAGE_TEMPLATE
    html = html.replace("__RESULT_ID__", safe_result_id)
    html = html.replace("__APP_VERSION__", escape(app_version))
    html = html.replace("__RESULT_ID_JSON__", json.dumps(normalized_result_id))
    html = html.replace("__RESULTS_ENDPOINT_BASE_JSON__", json.dumps(results_endpoint_base))
    return html


class _UiHandler(BaseHTTPRequestHandler):
    server_version = "geo-ranking-ui/1.0"

    def _send_json(self, payload: dict, *, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, *, status: int = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        request_path = _normalize_path(parsed.path)

        if request_path in {"/", "/gui"}:
            html = _build_gui_html(
                app_version=self.server.app_version,
                api_base_url=self.server.ui_api_base_url,
            )
            self._send_html(html)
            return

        if request_path.startswith("/results/"):
            result_id = request_path.removeprefix("/results/").strip()
            normalized_result_id = _normalize_result_id(result_id)
            if not normalized_result_id:
                self._send_json(
                    {
                        "ok": False,
                        "error": "not_found",
                        "message": "Unknown result_id",
                    },
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            try:
                html = _build_result_permalink_html(
                    app_version=self.server.app_version,
                    api_base_url=self.server.ui_api_base_url,
                    result_id=normalized_result_id,
                )
            except ValueError:
                self._send_json(
                    {
                        "ok": False,
                        "error": "not_found",
                        "message": "Unknown result_id",
                    },
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            self._send_html(html)
            return

        if request_path in {"/health", "/healthz"}:
            self._send_json(
                {
                    "ok": True,
                    "service": "geo-ranking-ch-ui",
                    "version": self.server.app_version,
                    "api_base_url": self.server.ui_api_base_url or None,
                    "result_permalink": {
                        "path_template": "/results/<result_id>",
                    },
                }
            )
            return

        self._send_json(
            {
                "ok": False,
                "error": "not_found",
                "message": f"Unknown endpoint: {request_path}",
            },
            status=HTTPStatus.NOT_FOUND,
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - stdlib signature
        return


class _UiHttpServer(ThreadingHTTPServer):
    def __init__(self, server_address, request_handler_class, *, app_version: str, ui_api_base_url: str):
        super().__init__(server_address, request_handler_class)
        self.app_version = app_version
        self.ui_api_base_url = ui_api_base_url


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    app_version = os.getenv("APP_VERSION", "dev")
    ui_api_base_url = os.getenv("UI_API_BASE_URL", "").strip()

    httpd = _UiHttpServer(
        (host, port),
        _UiHandler,
        app_version=app_version,
        ui_api_base_url=ui_api_base_url,
    )
    print(
        f"[geo-ranking-ch-ui] serving on http://{host}:{port} "
        f"(version={app_version}, api_base_url={ui_api_base_url or '/analyze (relative)'})"
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
