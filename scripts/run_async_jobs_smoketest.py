#!/usr/bin/env python3
"""Async Jobs API smoke test runner.

Ziel:
- Reproduzierbarer Smoke-Test für Async Analyze Jobs: submit -> job-status poll -> result fetch.
- Für dev/staging/prod nutzbar (Base-URL via CLI oder Env).

Usage (Beispiele):
  SERVICE_API_BASE_URL="https://api.dev.<domain>" \
    python3 scripts/run_async_jobs_smoketest.py

  python3 scripts/run_async_jobs_smoketest.py \
    --api-base-url "http://127.0.0.1:8000" \
    --query "St. Leonhard-Strasse 40, St. Gallen" \
    --mode basic \
    --output-json artifacts/async-jobs-smoke.json

Inputs (Env, optional):
- SERVICE_API_BASE_URL / DEV_BASE_URL / STAGING_BASE_URL: Base-URL (ohne /analyze).
- SERVICE_API_AUTH_TOKEN / DEV_API_AUTH_TOKEN / STAGING_API_AUTH_TOKEN: Bearer token.
- DEV_TLS_CA_CERT / TLS_CA_CERT: zusätzlicher Trust-Anchor (self-signed dev TLS).
- SMOKE_QUERY, SMOKE_MODE, SMOKE_TIMEOUT_SECONDS: Request-Payload Defaults.
- ASYNC_SMOKE_POLL_TIMEOUT_SECONDS, ASYNC_SMOKE_POLL_INTERVAL_SECONDS: Polling.

Exit Codes:
- 0: pass
- 2: bad input / usage
- 1: smoke failed
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib import error, parse, request


DEFAULT_QUERY = "St. Leonhard-Strasse 40, St. Gallen"
DEFAULT_MODE = "basic"


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    query: str
    mode: str
    analyze_timeout_seconds: float
    poll_timeout_seconds: float
    poll_interval_seconds: float
    auth_token: str
    tls_ca_cert: str
    output_json: str
    request_id: str


def _strip(value: str) -> str:
    return str(value or "").strip()


def _fail_usage(message: str) -> int:
    print(f"[async-jobs-smoke] {message}", file=sys.stderr)
    return 2


def _has_control_chars(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _normalize_base_url(raw: str) -> str:
    value = _strip(raw)
    if not value:
        raise ValueError("missing base URL")
    if any(ch.isspace() for ch in value) or _has_control_chars(value):
        raise ValueError("base URL must not contain whitespaces/control chars")

    parsed = parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base URL must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("base URL must include a host")
    if parsed.query or parsed.fragment:
        raise ValueError("base URL must not include query/fragment")

    # Robustness: allow users to pass /health or /analyze; strip those suffixes.
    path = parsed.path or ""
    normalized_path = path.rstrip("/")
    for suffix in ("/health", "/analyze"):
        if normalized_path.endswith(suffix):
            normalized_path = normalized_path[: -len(suffix)]
            normalized_path = normalized_path.rstrip("/")
            break

    rebuilt = parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            normalized_path,
            "",
            "",
        )
    )
    return rebuilt.rstrip("/")


def _build_url(base_url: str, route: str) -> str:
    assert route.startswith("/")
    return base_url.rstrip("/") + route


def _ssl_context(tls_ca_cert: str) -> ssl.SSLContext | None:
    cert_path = _strip(tls_ca_cert)
    if not cert_path:
        return None
    if _has_control_chars(cert_path):
        raise ValueError("TLS_CA_CERT must not contain control chars")
    path = Path(cert_path)
    if not path.exists() or not path.is_file():
        raise ValueError(f"TLS_CA_CERT path does not exist or is not a file: {cert_path}")
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=str(path))
    return ctx


def _read_json_response(resp: Any, *, max_bytes: int = 1_500_000) -> dict[str, Any]:
    raw = resp.read(max_bytes)
    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = text[:1000]
        raise ValueError(f"response is not valid JSON: {exc}: {snippet}") from exc
    if not isinstance(payload, dict):
        raise ValueError("response JSON must be an object")
    return payload


def _request_headers(*, request_id: str, auth_token: str) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Request-Id": request_id,
    }
    token = _strip(auth_token)
    if token:
        if any(ch.isspace() for ch in token) or _has_control_chars(token):
            raise ValueError("auth token must not contain whitespaces/control chars")
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _http_json(
    *,
    url: str,
    method: str,
    payload: dict[str, Any] | None,
    timeout_seconds: float,
    context: ssl.SSLContext | None,
    headers: dict[str, str],
) -> tuple[int, dict[str, Any]]:
    data = None
    if payload is not None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")

    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout_seconds, context=context) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            body = _read_json_response(resp)
            return status, body
    except error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            body = _read_json_response(exc)
        except Exception:
            body = {"ok": False, "error": "http_error", "message": str(exc)}
        return status, body


def _coerce_positive_float(value: str, *, name: str) -> float:
    raw = _strip(value)
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not (parsed > 0.0):
        raise ValueError(f"{name} must be > 0")
    return parsed


def _select_auth_token() -> str:
    for key in (
        "SERVICE_API_AUTH_TOKEN",
        "DEV_API_AUTH_TOKEN",
        "STAGING_API_AUTH_TOKEN",
    ):
        value = _strip(os.getenv(key, ""))
        if value:
            return value
    return ""


def _select_base_url_env() -> str:
    for key in (
        "SERVICE_API_BASE_URL",
        "DEV_BASE_URL",
        "STAGING_BASE_URL",
    ):
        value = _strip(os.getenv(key, ""))
        if value:
            return value
    return ""


def _select_tls_ca_cert_env() -> str:
    for key in (
        "TLS_CA_CERT",
        "DEV_TLS_CA_CERT",
    ):
        value = _strip(os.getenv(key, ""))
        if value:
            return value
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_async_jobs_smoketest.py",
        description="Async Jobs API Smoke Test (submit/status/result)",
    )
    parser.add_argument(
        "--api-base-url",
        default=_select_base_url_env(),
        help="Base URL of the service (e.g. https://api.dev.<domain>), without /analyze",
    )
    parser.add_argument(
        "--query",
        default=_strip(os.getenv("SMOKE_QUERY", DEFAULT_QUERY)),
        help="Analyze query used for the smoke request",
    )
    parser.add_argument(
        "--mode",
        default=_strip(os.getenv("SMOKE_MODE", DEFAULT_MODE)),
        help="intelligence_mode (basic|extended|risk)",
    )
    parser.add_argument(
        "--analyze-timeout-seconds",
        default=_strip(os.getenv("SMOKE_TIMEOUT_SECONDS", "20")),
        help="timeout_seconds passed in the analyze request payload",
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        default=_strip(os.getenv("ASYNC_SMOKE_POLL_TIMEOUT_SECONDS", "60")),
        help="max time to wait for job completion",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        default=_strip(os.getenv("ASYNC_SMOKE_POLL_INTERVAL_SECONDS", "0.5")),
        help="poll interval for job status",
    )
    parser.add_argument(
        "--auth-token",
        default=_select_auth_token(),
        help="Bearer token (fallback: SERVICE_API_AUTH_TOKEN/DEV_API_AUTH_TOKEN/STAGING_API_AUTH_TOKEN)",
    )
    parser.add_argument(
        "--tls-ca-cert",
        default=_select_tls_ca_cert_env(),
        help="Optional CA cert file for TLS verification (self-signed dev)",
    )
    parser.add_argument(
        "--output-json",
        default=_strip(os.getenv("ASYNC_SMOKE_OUTPUT_JSON", "")),
        help="Optional output JSON path (structured evidence)",
    )
    parser.add_argument(
        "--request-id",
        default=_strip(os.getenv("SMOKE_REQUEST_ID", "")),
        help="Optional request id (X-Request-Id). If empty: autogenerated.",
    )
    return parser


def _resolve_config(args: argparse.Namespace) -> SmokeConfig:
    base_url = _normalize_base_url(str(args.api_base_url))

    query = _strip(str(args.query))
    if not query:
        raise ValueError("query must not be empty")
    if _has_control_chars(query):
        raise ValueError("query must not contain control chars")

    mode = _strip(str(args.mode)).lower() or DEFAULT_MODE

    analyze_timeout_seconds = _coerce_positive_float(str(args.analyze_timeout_seconds), name="analyze-timeout-seconds")
    poll_timeout_seconds = _coerce_positive_float(str(args.poll_timeout_seconds), name="poll-timeout-seconds")
    poll_interval_seconds = _coerce_positive_float(str(args.poll_interval_seconds), name="poll-interval-seconds")

    output_json = _strip(str(args.output_json))
    if output_json and _has_control_chars(output_json):
        raise ValueError("output-json must not contain control chars")

    request_id = _strip(str(args.request_id))
    if not request_id:
        request_id = f"async-smoke-{int(time.time())}-{uuid.uuid4().hex[:10]}"
    if any(ch.isspace() for ch in request_id) or _has_control_chars(request_id):
        raise ValueError("request-id must not contain whitespaces/control chars")

    return SmokeConfig(
        base_url=base_url,
        query=query,
        mode=mode,
        analyze_timeout_seconds=analyze_timeout_seconds,
        poll_timeout_seconds=poll_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        auth_token=_strip(str(args.auth_token)),
        tls_ca_cert=_strip(str(args.tls_ca_cert)),
        output_json=output_json,
        request_id=request_id,
    )


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = _resolve_config(args)
        ctx = _ssl_context(cfg.tls_ca_cert)
        headers = _request_headers(request_id=cfg.request_id, auth_token=cfg.auth_token)
    except ValueError as exc:
        return _fail_usage(str(exc))

    analyze_url = _build_url(cfg.base_url, "/analyze")

    payload: dict[str, Any] = {
        "query": cfg.query,
        "intelligence_mode": cfg.mode,
        "timeout_seconds": cfg.analyze_timeout_seconds,
        "options": {"async_mode": {"requested": True}},
    }

    print(f"[async-jobs-smoke] submit: POST {analyze_url}")
    started_at = time.time()

    status_code, submit_body = _http_json(
        url=analyze_url,
        method="POST",
        payload=payload,
        timeout_seconds=max(5.0, cfg.analyze_timeout_seconds + 10.0),
        context=ctx,
        headers=headers,
    )

    if status_code not in {HTTPStatus.ACCEPTED, HTTPStatus.OK}:
        print(
            f"[async-jobs-smoke] submit failed: HTTP {status_code} body={json.dumps(submit_body, sort_keys=True)[:1200]}",
            file=sys.stderr,
        )
        return 1

    if submit_body.get("ok") is not True:
        print(f"[async-jobs-smoke] submit failed: ok!=true body={submit_body}", file=sys.stderr)
        return 1

    job = submit_body.get("job")
    if not isinstance(job, dict):
        print(f"[async-jobs-smoke] submit failed: missing job object body={submit_body}", file=sys.stderr)
        return 1

    job_id = _strip(str(job.get("job_id", "")))
    if not job_id:
        print(f"[async-jobs-smoke] submit failed: missing job_id body={submit_body}", file=sys.stderr)
        return 1

    job_url = _build_url(cfg.base_url, f"/analyze/jobs/{job_id}")

    deadline = time.time() + cfg.poll_timeout_seconds
    terminal_job: dict[str, Any] | None = None

    print(f"[async-jobs-smoke] poll: GET {job_url} (timeout={cfg.poll_timeout_seconds}s)")

    while time.time() < deadline:
        code, job_body = _http_json(
            url=job_url,
            method="GET",
            payload=None,
            timeout_seconds=15.0,
            context=ctx,
            headers={k: v for k, v in headers.items() if k != "Content-Type"},
        )

        if code != HTTPStatus.OK:
            print(f"[async-jobs-smoke] job poll got HTTP {code} body={job_body}", file=sys.stderr)
            time.sleep(cfg.poll_interval_seconds)
            continue

        job_obj = job_body.get("job")
        if not isinstance(job_obj, dict):
            print(f"[async-jobs-smoke] job poll missing job object body={job_body}", file=sys.stderr)
            time.sleep(cfg.poll_interval_seconds)
            continue

        status = _strip(str(job_obj.get("status", "")))
        progress = int(job_obj.get("progress_percent", 0) or 0)
        result_id = _strip(str(job_obj.get("result_id", "")))

        print(f"[async-jobs-smoke] status={status} progress={progress}% result_id={result_id or '-'}")

        if status in {"completed", "failed", "canceled"}:
            terminal_job = job_obj
            break

        time.sleep(cfg.poll_interval_seconds)

    if terminal_job is None:
        print(
            f"[async-jobs-smoke] job did not reach terminal state within {cfg.poll_timeout_seconds}s (job_id={job_id})",
            file=sys.stderr,
        )
        return 1

    terminal_status = _strip(str(terminal_job.get("status", "")))
    terminal_result_id = _strip(str(terminal_job.get("result_id", "")))

    if terminal_status != "completed":
        print(
            f"[async-jobs-smoke] job terminal status is not completed: status={terminal_status} job={terminal_job}",
            file=sys.stderr,
        )
        return 1

    if not terminal_result_id:
        print(f"[async-jobs-smoke] completed job missing result_id: job={terminal_job}", file=sys.stderr)
        return 1

    result_url = _build_url(cfg.base_url, f"/analyze/results/{terminal_result_id}")
    print(f"[async-jobs-smoke] fetch result: GET {result_url}")

    code, result_body = _http_json(
        url=result_url,
        method="GET",
        payload=None,
        timeout_seconds=20.0,
        context=ctx,
        headers={k: v for k, v in headers.items() if k != "Content-Type"},
    )

    if code != HTTPStatus.OK:
        print(f"[async-jobs-smoke] result fetch failed: HTTP {code} body={result_body}", file=sys.stderr)
        return 1

    if result_body.get("ok") is not True:
        print(f"[async-jobs-smoke] result fetch failed: ok!=true body={result_body}", file=sys.stderr)
        return 1

    ended_at = time.time()

    evidence = {
        "ok": True,
        "base_url": cfg.base_url,
        "request_id": cfg.request_id,
        "submit": {
            "url": analyze_url,
            "http": int(status_code),
        },
        "job": {
            "job_id": job_id,
            "url": job_url,
            "status": terminal_status,
            "result_id": terminal_result_id,
        },
        "result": {
            "url": result_url,
            "http": int(code),
            "result_id": terminal_result_id,
        },
        "timing": {
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": round(ended_at - started_at, 3),
        },
    }

    output_path = _strip(cfg.output_json)
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[async-jobs-smoke] wrote evidence: {out}")

    print("[async-jobs-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
