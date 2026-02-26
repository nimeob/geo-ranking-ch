#!/usr/bin/env python3
"""Minimaler HTTP-Webservice für ECS (stdlib only).

Endpoints:
- GET /health
- GET /version
- POST /analyze {"query": "...", "intelligence_mode": "basic|extended|risk"}
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from src.address_intel import AddressIntelError, build_report

SUPPORTED_INTELLIGENCE_MODES = {"basic", "extended", "risk"}


class Handler(BaseHTTPRequestHandler):
    server_version = "geo-ranking-ch/0.1"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json({"ok": True, "service": "geo-ranking-ch", "ts": datetime.now(timezone.utc).isoformat()})
            return
        if self.path == "/version":
            self._send_json({
                "service": "geo-ranking-ch",
                "version": os.getenv("APP_VERSION", "dev"),
                "commit": os.getenv("GIT_SHA", "unknown"),
            })
            return
        self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/analyze":
            self._send_json({"ok": False, "error": "not_found"}, status=HTTPStatus.NOT_FOUND)
            return

        required_token = os.getenv("API_AUTH_TOKEN", "").strip()
        if required_token:
            auth_header = self.headers.get("Authorization", "")
            expected = f"Bearer {required_token}"
            if auth_header != expected:
                self._send_json({"ok": False, "error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
                return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("empty body")
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
            query = str(data.get("query", "")).strip()
            if not query:
                raise ValueError("query is required")

            mode = str(data.get("intelligence_mode", "basic")).strip() or "basic"
            if mode not in SUPPORTED_INTELLIGENCE_MODES:
                raise ValueError(f"intelligence_mode must be one of {sorted(SUPPORTED_INTELLIGENCE_MODES)}")

            if os.getenv("ENABLE_E2E_FAULT_INJECTION", "0") == "1":
                if query == "__timeout__":
                    raise TimeoutError("forced timeout for e2e")
                if query == "__internal__":
                    raise RuntimeError("forced internal error for e2e")
                if query == "__ok__":
                    self._send_json({"ok": True, "result": {"query": query, "status": "e2e_stub"}})
                    return

            default_timeout = float(os.getenv("ANALYZE_DEFAULT_TIMEOUT_SECONDS", "15"))
            max_timeout = float(os.getenv("ANALYZE_MAX_TIMEOUT_SECONDS", "45"))
            req_timeout_raw = data.get("timeout_seconds", default_timeout)
            timeout = float(req_timeout_raw)
            if timeout <= 0:
                raise ValueError("timeout_seconds must be > 0")
            timeout = min(timeout, max_timeout)

            report = build_report(
                query,
                include_osm=True,
                candidate_limit=8,
                candidate_preview=3,
                timeout=timeout,
                retries=2,
                backoff_seconds=0.6,
                intelligence_mode=mode,
            )
            self._send_json({"ok": True, "result": report})
        except TimeoutError as e:
            self._send_json({"ok": False, "error": "timeout", "message": str(e)}, status=HTTPStatus.GATEWAY_TIMEOUT)
        except AddressIntelError as e:
            self._send_json({"ok": False, "error": "address_intel", "message": str(e)}, status=422)
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json({"ok": False, "error": "bad_request", "message": str(e)}, status=400)
        except Exception as e:  # pragma: no cover
            self._send_json({"ok": False, "error": "internal", "message": str(e)}, status=500)


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"geo-ranking-ch web service listening on {host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
