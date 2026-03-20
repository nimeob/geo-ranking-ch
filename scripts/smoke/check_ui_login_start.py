#!/usr/bin/env python3
"""Smoke-check for the UI-owned login contract.

Verifies both contracts:
1) ``/login?next=...&reason=...`` renders a UI HTML entry page (no redirect), and
2) ``/login?next=...&reason=...&start=1`` reaches an IdP authorize redirect.

The start flow may be either:
- direct redirect to authorize, or
- UI-owned intermediate hop via ``/auth/login`` followed by authorize.
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
class LoginEntryCheckResult:
    ok: bool
    status_code: int
    location: str
    request_url: str
    content_type: str
    reason: str


@dataclass(frozen=True)
class LoginStartCheckResult:
    ok: bool
    status_code: int
    location: str
    request_url: str
    reason: str


@dataclass(frozen=True)
class _HttpProbeResult:
    status_code: int
    location: str
    content_type: str
    body_preview: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _build_entry_request_url(base_url: str, *, next_path: str, reason: str) -> str:
    normalized_base = base_url.strip().rstrip("/")
    query = urlencode({"next": next_path, "reason": reason})
    return f"{normalized_base}/login?{query}"


def _build_start_request_url(base_url: str, *, next_path: str, reason: str) -> str:
    normalized_base = base_url.strip().rstrip("/")
    query = urlencode({"next": next_path, "reason": reason, "start": "1"})
    return f"{normalized_base}/login?{query}"


def _send_request_probe(
    *,
    request_url: str,
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
    read_body_preview: bool = False,
) -> _HttpProbeResult:
    req = Request(request_url, method="GET")
    opener = build_opener(_NoRedirect)

    attempts = max(1, int(max_attempts))
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            resp = opener.open(req, timeout=timeout_seconds)
            try:
                status = int(getattr(resp, "status", 0) or resp.getcode())
                location = str(resp.headers.get("Location") or "").strip()
                content_type = str(resp.headers.get("Content-Type") or "").strip()
                body_preview = ""
                if read_body_preview:
                    body_preview = resp.read(4096).decode("utf-8", errors="replace")
            finally:
                close_fn = getattr(resp, "close", None)
                if callable(close_fn):
                    close_fn()
            return _HttpProbeResult(
                status_code=status,
                location=location,
                content_type=content_type,
                body_preview=body_preview,
            )
        except HTTPError as exc:
            try:
                status = int(getattr(exc, "status", 0) or exc.getcode())
                location = str(exc.headers.get("Location") or "").strip()
                content_type = str(exc.headers.get("Content-Type") or "").strip()
                body_preview = ""
                if read_body_preview and exc.fp is not None:
                    try:
                        body_preview = exc.read(4096).decode("utf-8", errors="replace")
                    except Exception:  # noqa: BLE001
                        body_preview = ""
            finally:
                exc.close()
            if status in {502, 503, 504} and attempt < attempts:
                time.sleep(max(0.0, retry_delay_seconds))
                continue
            return _HttpProbeResult(
                status_code=status,
                location=location,
                content_type=content_type,
                body_preview=body_preview,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(max(0.0, retry_delay_seconds))

    raise RuntimeError(
        f"request_failed_after_retries(attempts={attempts}, timeout_seconds={timeout_seconds}): {last_error}"
    )


def _send_request(
    *,
    request_url: str,
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
) -> tuple[int, str]:
    probe = _send_request_probe(
        request_url=request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        read_body_preview=False,
    )
    return probe.status_code, probe.location


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


def check_login_entry(
    *,
    base_url: str,
    next_path: str = "/gui",
    reason: str = "manual_login",
    timeout_seconds: float = 15.0,
    max_attempts: int = 3,
    retry_delay_seconds: float = 2.0,
) -> LoginEntryCheckResult:
    request_url = _build_entry_request_url(base_url, next_path=next_path, reason=reason)
    probe = _send_request_probe(
        request_url=request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        read_body_preview=True,
    )

    if probe.status_code != 200:
        reason_code = f"unexpected_entry_status_{probe.status_code}"
        if _is_login_unavailable_redirect(probe.location):
            reason_code = "entry_redirected_login_unavailable"
        return LoginEntryCheckResult(
            ok=False,
            status_code=probe.status_code,
            location=probe.location,
            request_url=request_url,
            content_type=probe.content_type,
            reason=reason_code,
        )

    content_type = str(probe.content_type or "").lower()
    if "text/html" not in content_type:
        return LoginEntryCheckResult(
            ok=False,
            status_code=probe.status_code,
            location=probe.location,
            request_url=request_url,
            content_type=probe.content_type,
            reason="entry_content_type_not_html",
        )

    body_preview = probe.body_preview.lower()
    if "start=1" not in body_preview:
        return LoginEntryCheckResult(
            ok=False,
            status_code=probe.status_code,
            location=probe.location,
            request_url=request_url,
            content_type=probe.content_type,
            reason="entry_missing_start_link",
        )

    return LoginEntryCheckResult(
        ok=True,
        status_code=probe.status_code,
        location=probe.location,
        request_url=request_url,
        content_type=probe.content_type,
        reason="ok",
    )


def check_login_start(
    *,
    base_url: str,
    next_path: str = "/gui",
    reason: str = "manual_login",
    timeout_seconds: float = 15.0,
    max_attempts: int = 3,
    retry_delay_seconds: float = 2.0,
) -> LoginStartCheckResult:
    request_url = _build_start_request_url(base_url, next_path=next_path, reason=reason)

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
            reason=f"unexpected_start_status_{first_status}",
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
    parser = argparse.ArgumentParser(description="Smoke-check UI-owned login entry + login-start redirect contract")
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

    request_meta = {
        "base_url": args.base_url,
        "next": args.next_path,
        "reason": args.reason,
        "timeout": args.timeout,
        "max_attempts": args.max_attempts,
        "retry_delay": args.retry_delay,
    }

    try:
        entry_result = check_login_entry(
            base_url=args.base_url,
            next_path=args.next_path,
            reason=args.reason,
            timeout_seconds=args.timeout,
            max_attempts=args.max_attempts,
            retry_delay_seconds=args.retry_delay,
        )
        if not entry_result.ok:
            payload = {
                "ok": False,
                "phase": "entry",
                "reason": entry_result.reason,
                "status_code": entry_result.status_code,
                "request_url": entry_result.request_url,
                "location": entry_result.location,
                "content_type": entry_result.content_type,
                "request": request_meta,
            }
            print(json.dumps(payload, ensure_ascii=False))
            if args.output_json:
                _write_result(args.output_json, payload)
            return 1

        start_result = check_login_start(
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
            "phase": "request",
            "reason": "request_failed",
            "error": str(exc),
            "request": request_meta,
        }
        print(json.dumps(payload, ensure_ascii=False))
        if args.output_json:
            _write_result(args.output_json, payload)
        return 1

    payload = {
        "ok": start_result.ok,
        "phase": "start",
        "reason": start_result.reason,
        "status_code": start_result.status_code,
        "request_url": start_result.request_url,
        "location": start_result.location,
        "entry": {
            "ok": entry_result.ok,
            "reason": entry_result.reason,
            "status_code": entry_result.status_code,
            "request_url": entry_result.request_url,
            "location": entry_result.location,
            "content_type": entry_result.content_type,
        },
    }
    print(json.dumps(payload, ensure_ascii=False))
    if args.output_json:
        _write_result(args.output_json, payload)

    return 0 if start_result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
