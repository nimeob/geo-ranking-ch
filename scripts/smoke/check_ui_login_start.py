#!/usr/bin/env python3
"""Smoke-check for UI login start flow.

Ensures `/login?...&start=1` reaches an IdP authorize redirect.
The flow may be either:

1) direct redirect to authorize, or
2) UI-owned intermediate hop via `/auth/login` followed by authorize.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


@dataclass(frozen=True)
class LoginStartCheckResult:
    ok: bool
    status_code: int
    location: str
    request_url: str
    reason: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _build_request_url(base_url: str, *, next_path: str, reason: str) -> str:
    normalized_base = base_url.strip().rstrip("/")
    query = urlencode({"next": next_path, "reason": reason, "start": "1"})
    return f"{normalized_base}/login?{query}"


def _send_request(
    *,
    request_url: str,
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
) -> tuple[int, str]:
    req = Request(request_url, method="GET")
    opener = build_opener(_NoRedirect)

    attempts = max(1, int(max_attempts))
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            resp = opener.open(req, timeout=timeout_seconds)
            status = int(getattr(resp, "status", 0) or resp.getcode())
            location = str(resp.headers.get("Location") or "").strip()
            return status, location
        except HTTPError as exc:
            status = int(getattr(exc, "status", 0) or exc.getcode())
            location = str(exc.headers.get("Location") or "").strip()
            if status in {502, 503, 504} and attempt < attempts:
                time.sleep(max(0.0, retry_delay_seconds))
                continue
            return status, location
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(max(0.0, retry_delay_seconds))

    raise RuntimeError(
        f"request_failed_after_retries(attempts={attempts}, timeout_seconds={timeout_seconds}): {last_error}"
    )


def _is_authorize_redirect(location: str) -> bool:
    parsed_location = urlparse(location)
    authorize_hint = (
        f"{parsed_location.path}?{parsed_location.query}"
        if parsed_location.query
        else parsed_location.path
    )
    return "authorize" in authorize_hint.lower()


def _is_auth_login_redirect(location: str) -> bool:
    return urlparse(location).path.rstrip("/").lower() == "/auth/login"


def _is_login_unavailable_redirect(location: str) -> bool:
    return "reason=login_unavailable" in location.lower()


def check_login_start(
    *,
    base_url: str,
    next_path: str = "/gui",
    reason: str = "manual_login",
    timeout_seconds: float = 15.0,
    max_attempts: int = 3,
    retry_delay_seconds: float = 2.0,
) -> LoginStartCheckResult:
    request_url = _build_request_url(base_url, next_path=next_path, reason=reason)

    first_status, first_location = _send_request(
        request_url=request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
    if first_status != 302:
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=request_url,
            reason=f"unexpected_status_{first_status}",
        )

    if not first_location:
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=request_url,
            reason="missing_location_header",
        )

    if _is_login_unavailable_redirect(first_location):
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=request_url,
            reason="login_unavailable_fallback",
        )

    if _is_authorize_redirect(first_location):
        return LoginStartCheckResult(
            ok=True,
            status_code=first_status,
            location=first_location,
            request_url=request_url,
            reason="ok",
        )

    if not _is_auth_login_redirect(first_location):
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=request_url,
            reason="location_is_not_authorize_or_auth_login_redirect",
        )

    second_request_url = urljoin(request_url, first_location)
    second_status, second_location = _send_request(
        request_url=second_request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )

    if second_status != 302:
        return LoginStartCheckResult(
            ok=False,
            status_code=second_status,
            location=second_location,
            request_url=request_url,
            reason=f"auth_login_hop_unexpected_status_{second_status}",
        )

    if not second_location:
        return LoginStartCheckResult(
            ok=False,
            status_code=second_status,
            location=second_location,
            request_url=request_url,
            reason="auth_login_hop_missing_location_header",
        )

    if _is_login_unavailable_redirect(second_location):
        return LoginStartCheckResult(
            ok=False,
            status_code=second_status,
            location=second_location,
            request_url=request_url,
            reason="auth_login_hop_login_unavailable_fallback",
        )

    if not _is_authorize_redirect(second_location):
        return LoginStartCheckResult(
            ok=False,
            status_code=second_status,
            location=second_location,
            request_url=request_url,
            reason="auth_login_hop_non_authorize_redirect",
        )

    return LoginStartCheckResult(
        ok=True,
        status_code=second_status,
        location=second_location,
        request_url=request_url,
        reason="ok",
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-check UI login start redirect contract")
    parser.add_argument("--base-url", required=True, help="UI base URL, e.g. https://www.dev.georanking.ch")
    parser.add_argument("--next", default="/gui", dest="next_path", help="next path for login start (default: /gui)")
    parser.add_argument("--reason", default="manual_login", help="login reason query value (default: manual_login)")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout per attempt in seconds (default: 15)")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max HTTP attempts per hop on transient request errors (default: 3)")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Delay between retries in seconds (default: 2.0)")
    parser.add_argument("--output-json", help="Optional output path for machine-readable result")
    return parser.parse_args(argv)


def _write_result(path: str, payload: dict[str, object]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    try:
        result = check_login_start(
            base_url=args.base_url,
            next_path=args.next_path,
            reason=args.reason,
            timeout_seconds=args.timeout,
            max_attempts=args.max_attempts,
            retry_delay_seconds=args.retry_delay,
        )
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "reason": "request_failed",
            "error": str(exc),
            "request": {
                "base_url": args.base_url,
                "next": args.next_path,
                "reason": args.reason,
                "timeout": args.timeout,
                "max_attempts": args.max_attempts,
                "retry_delay": args.retry_delay,
            },
        }
        print(json.dumps(payload, ensure_ascii=False))
        if args.output_json:
            _write_result(args.output_json, payload)
        return 1

    payload = {
        "ok": result.ok,
        "reason": result.reason,
        "status_code": result.status_code,
        "request_url": result.request_url,
        "location": result.location,
    }
    print(json.dumps(payload, ensure_ascii=False))
    if args.output_json:
        _write_result(args.output_json, payload)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
