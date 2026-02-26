#!/usr/bin/env python3
"""Minimaler HTTP-Webservice für ECS (stdlib only).

Endpoints:
- GET /health
- GET /version
- POST /analyze {"query": "...", "intelligence_mode": "basic|extended|risk"}
"""

from __future__ import annotations

import json
import math
import os
import re
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from src.address_intel import AddressIntelError, build_report

SUPPORTED_INTELLIGENCE_MODES = {"basic", "extended", "risk"}


def _as_positive_finite_number(value: Any, field_name: str) -> float:
    """Validiert numerische Inputs robust für API/ENV-Werte."""
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number > 0") from exc

    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{field_name} must be a finite number > 0")
    return parsed


def _sanitize_request_id_candidate(candidate: Any) -> str:
    """Normalisiert Request-ID-Header robust für Echo/Response-Header."""
    value = str(candidate).strip()
    if not value:
        return ""
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return ""
    if any(ch.isspace() for ch in value):
        return ""
    if any(ch in ",;" for ch in value):
        return ""
    if len(value) > 128:
        return ""
    if not value.isascii():
        return ""
    return value


class Handler(BaseHTTPRequestHandler):
    server_version = "geo-ranking-ch/0.1"

    def _normalized_path(self) -> str:
        """Normalisiert den Request-Pfad für robustes Routing.

        - ignoriert Query/Fragment-Komponenten
        - behandelt optionale trailing Slashes auf bekannten Endpunkten tolerant
        - kollabiert doppelte Slash-Segmente (`//`) auf einen Slash
        """
        path = urlsplit(self.path).path or "/"
        path = re.sub(r"/{2,}", "/", path)
        if path != "/":
            path = path.rstrip("/") or "/"
        return path

    def _request_id(self) -> str:
        """Liefert eine korrelierbare Request-ID (Header oder Fallback)."""
        header_candidates = (
            self.headers.get("X-Request-Id", ""),
            self.headers.get("X_Request_Id", ""),
            self.headers.get("Request-Id", ""),
            self.headers.get("Request_Id", ""),
            self.headers.get("X-Correlation-Id", ""),
            self.headers.get("X_Correlation_Id", ""),
            self.headers.get("Correlation-Id", ""),
            self.headers.get("Correlation_Id", ""),
        )
        for candidate in header_candidates:
            request_id = _sanitize_request_id_candidate(candidate)
            if request_id:
                return request_id
        return f"req-{uuid.uuid4().hex[:16]}"

    def _send_json(
        self,
        payload: dict[str, Any],
        status: int = 200,
        *,
        request_id: str | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if request_id:
            self.send_header("X-Request-Id", request_id)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        request_id = self._request_id()
        request_path = self._normalized_path()

        if request_path == "/health":
            self._send_json(
                {
                    "ok": True,
                    "service": "geo-ranking-ch",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                },
                request_id=request_id,
            )
            return
        if request_path == "/version":
            self._send_json(
                {
                    "service": "geo-ranking-ch",
                    "version": os.getenv("APP_VERSION", "dev"),
                    "commit": os.getenv("GIT_SHA", "unknown"),
                    "request_id": request_id,
                },
                request_id=request_id,
            )
            return
        self._send_json(
            {"ok": False, "error": "not_found", "request_id": request_id},
            status=HTTPStatus.NOT_FOUND,
            request_id=request_id,
        )

    def do_POST(self) -> None:  # noqa: N802
        request_id = self._request_id()
        request_path = self._normalized_path()

        if request_path != "/analyze":
            self._send_json(
                {"ok": False, "error": "not_found", "request_id": request_id},
                status=HTTPStatus.NOT_FOUND,
                request_id=request_id,
            )
            return

        required_token = os.getenv("API_AUTH_TOKEN", "").strip()
        if required_token:
            auth_header = self.headers.get("Authorization", "")
            expected = f"Bearer {required_token}"
            if auth_header != expected:
                self._send_json(
                    {"ok": False, "error": "unauthorized", "request_id": request_id},
                    status=HTTPStatus.UNAUTHORIZED,
                    request_id=request_id,
                )
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
            mode = mode.lower()
            if mode not in SUPPORTED_INTELLIGENCE_MODES:
                raise ValueError(
                    f"intelligence_mode must be one of {sorted(SUPPORTED_INTELLIGENCE_MODES)}"
                )

            if os.getenv("ENABLE_E2E_FAULT_INJECTION", "0") == "1":
                if query == "__timeout__":
                    raise TimeoutError("forced timeout for e2e")
                if query == "__internal__":
                    raise RuntimeError("forced internal error for e2e")
                if query == "__ok__":
                    self._send_json(
                        {
                            "ok": True,
                            "result": {"query": query, "status": "e2e_stub"},
                            "request_id": request_id,
                        },
                        request_id=request_id,
                    )
                    return

            default_timeout = _as_positive_finite_number(
                os.getenv("ANALYZE_DEFAULT_TIMEOUT_SECONDS", "15"),
                "ANALYZE_DEFAULT_TIMEOUT_SECONDS",
            )
            max_timeout = _as_positive_finite_number(
                os.getenv("ANALYZE_MAX_TIMEOUT_SECONDS", "45"),
                "ANALYZE_MAX_TIMEOUT_SECONDS",
            )
            req_timeout_raw = data.get("timeout_seconds", default_timeout)
            timeout = _as_positive_finite_number(req_timeout_raw, "timeout_seconds")
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
            self._send_json(
                {"ok": True, "result": report, "request_id": request_id},
                request_id=request_id,
            )
        except TimeoutError as e:
            self._send_json(
                {
                    "ok": False,
                    "error": "timeout",
                    "message": str(e),
                    "request_id": request_id,
                },
                status=HTTPStatus.GATEWAY_TIMEOUT,
                request_id=request_id,
            )
        except AddressIntelError as e:
            self._send_json(
                {
                    "ok": False,
                    "error": "address_intel",
                    "message": str(e),
                    "request_id": request_id,
                },
                status=422,
                request_id=request_id,
            )
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(
                {
                    "ok": False,
                    "error": "bad_request",
                    "message": str(e),
                    "request_id": request_id,
                },
                status=400,
                request_id=request_id,
            )
        except Exception as e:  # pragma: no cover
            self._send_json(
                {
                    "ok": False,
                    "error": "internal",
                    "message": str(e),
                    "request_id": request_id,
                },
                status=500,
                request_id=request_id,
            )


def _resolve_port() -> int:
    """Liest die Service-Port-Konfiguration robust aus ENV.

    Kompatibilität: `PORT` bleibt primär, `WEB_PORT` dient als Fallback
    (z. B. für lokale Wrapper/Runner).
    """

    port_raw = os.getenv("PORT")
    if port_raw is None or not str(port_raw).strip():
        port_raw = os.getenv("WEB_PORT", "8080")
    return int(str(port_raw).strip())


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = _resolve_port()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"geo-ranking-ch web service listening on {host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
