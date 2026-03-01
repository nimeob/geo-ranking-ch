#!/usr/bin/env python3
"""Minimaler UI-Webservice für BL-31.2.

Stellt das GUI-MVP (`/` und `/gui`) als eigenständigen HTTP-Service bereit
und liefert einen separaten Healthcheck-Endpunkt (`/healthz`).
"""

from __future__ import annotations

import json
import os
import posixpath
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from src.shared.gui_mvp import render_gui_mvp_html


def _normalize_path(path: str) -> str:
    """Normalisiert doppelte Slashes und entfernt Trailing-Slash (außer Root)."""

    raw = path or "/"
    normalized = posixpath.normpath(raw)
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized == "/.":
        return "/"
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

        if request_path in {"/health", "/healthz"}:
            self._send_json(
                {
                    "ok": True,
                    "service": "geo-ranking-ch-ui",
                    "version": self.server.app_version,
                    "api_base_url": self.server.ui_api_base_url or None,
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
