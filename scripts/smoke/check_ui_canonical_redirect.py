#!/usr/bin/env python3
"""Smoke-check for optional UI canonical-host redirects.

Contract (when canonical alias hosts are configured):
- Requesting ``/login?...`` on an alias host should redirect to the canonical origin
  while preserving path + query.

If no usable alias host is configured, the check is treated as skipped (exit 0).
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

_TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 502, 503, 504})
_REDIRECT_HTTP_STATUSES = frozenset({301, 302, 303, 307, 308})


@dataclass(frozen=True)
class _HttpProbeResult:
    status_code: int
    location: str


@dataclass(frozen=True)
class CanonicalRedirectCheckResult:
    ok: bool
    skipped: bool
    reason: str
    request_url: str
    status_code: int
    location: str
    expected_location: str
    canonical_origin: str
    alias_host: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _normalize_origin(origin: str) -> str:
    candidate = origin.strip().rstrip("/")
    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid_origin:{origin}")
    return f"{parsed.scheme}://{parsed.netloc}"


def _normalize_host(value: str) -> str:
    raw_value = str(value or "").split(",", 1)[0].strip()
    if not raw_value:
        return ""
    parsed = urlparse(raw_value if "://" in raw_value else f"//{raw_value}")
    return str(parsed.hostname or "").strip().lower()


def _parse_canonical_hosts(raw_hosts: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in str(raw_hosts or "").split(","):
        host = _normalize_host(item)
        if host and host not in seen:
            seen.add(host)
            normalized.append(host)
    return normalized


def _is_redirect_status(status_code: int) -> bool:
    return int(status_code) in _REDIRECT_HTTP_STATUSES


def _resolve_retry_delay(
    *,
    retry_after_header: str,
    default_delay_seconds: float,
    max_retry_delay_seconds: float,
) -> float:
    retry_cap = max(0.0, float(max_retry_delay_seconds))
    fallback_delay = min(max(0.0, float(default_delay_seconds)), retry_cap)
    candidate = str(retry_after_header or "").strip()
    if not candidate:
        return fallback_delay

    try:
        return min(max(0.0, float(candidate)), retry_cap)
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(candidate)
    except (TypeError, ValueError):
        return fallback_delay

    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)

    delta_seconds = (retry_at - datetime.now(timezone.utc)).total_seconds()
    if delta_seconds <= 0:
        return fallback_delay
    return min(delta_seconds, retry_cap)


def _send_request_probe(
    *,
    request_url: str,
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
    max_retry_delay_seconds: float = 10.0,
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
            finally:
                close_fn = getattr(resp, "close", None)
                if callable(close_fn):
                    close_fn()
            return _HttpProbeResult(status_code=status, location=location)
        except HTTPError as exc:
            try:
                status = int(getattr(exc, "status", 0) or exc.getcode())
                headers = exc.headers or {}
                location = str(headers.get("Location") or "").strip()
                retry_after_header = str(headers.get("Retry-After") or "").strip()
            finally:
                exc.close()
            if status in _TRANSIENT_HTTP_STATUSES and attempt < attempts:
                time.sleep(
                    _resolve_retry_delay(
                        retry_after_header=retry_after_header,
                        default_delay_seconds=retry_delay_seconds,
                        max_retry_delay_seconds=max_retry_delay_seconds,
                    )
                )
                continue
            return _HttpProbeResult(status_code=status, location=location)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(min(max(0.0, retry_delay_seconds), max(0.0, max_retry_delay_seconds)))

    raise RuntimeError(
        f"request_failed_after_retries(attempts={attempts}, timeout_seconds={timeout_seconds}): {last_error}"
    )


def _build_alias_request_url(
    *, alias_host: str, canonical_origin: str, next_path: str, reason: str
) -> str:
    canonical = urlparse(canonical_origin)
    query = urlencode({"next": next_path, "reason": reason, "start": "1"})
    return f"{canonical.scheme}://{alias_host}/login?{query}"


def check_canonical_redirect(
    *,
    base_url: str,
    canonical_origin: str,
    canonical_hosts: str,
    alias_host: str = "",
    next_path: str = "/gui",
    reason: str = "manual_login",
    timeout_seconds: float = 15.0,
    max_attempts: int = 3,
    retry_delay_seconds: float = 2.0,
    max_retry_delay_seconds: float = 10.0,
) -> CanonicalRedirectCheckResult:
    normalized_base_origin = _normalize_origin(base_url)
    normalized_canonical_origin = (
        _normalize_origin(canonical_origin)
        if canonical_origin.strip()
        else normalized_base_origin
    )

    selected_alias_host = ""
    expected_location = ""
    request_url = ""

    canonical_host = _normalize_host(normalized_canonical_origin)

    alias_candidates: list[str] = []
    normalized_alias_override = _normalize_host(alias_host)
    if alias_host.strip():
        if not normalized_alias_override:
            raise ValueError(f"invalid_alias_host:{alias_host}")
        if normalized_alias_override != canonical_host:
            alias_candidates.append(normalized_alias_override)
    else:
        configured_hosts = _parse_canonical_hosts(canonical_hosts)
        alias_candidates = [
            host for host in configured_hosts if host and host != canonical_host
        ]

    if not alias_candidates:
        return CanonicalRedirectCheckResult(
            ok=True,
            skipped=True,
            reason="skipped_no_alias_hosts",
            request_url=request_url,
            status_code=0,
            location="",
            expected_location=expected_location,
            canonical_origin=normalized_canonical_origin,
            alias_host=selected_alias_host,
        )

    selected_alias_host = alias_candidates[0]
    request_url = _build_alias_request_url(
        alias_host=selected_alias_host,
        canonical_origin=normalized_canonical_origin,
        next_path=next_path,
        reason=reason,
    )

    expected_location = f"{normalized_canonical_origin}/login?{urlencode({'next': next_path, 'reason': reason, 'start': '1'})}"

    probe = _send_request_probe(
        request_url=request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        max_retry_delay_seconds=max_retry_delay_seconds,
    )

    if not _is_redirect_status(probe.status_code):
        return CanonicalRedirectCheckResult(
            ok=False,
            skipped=False,
            reason=f"unexpected_status_{probe.status_code}",
            request_url=request_url,
            status_code=probe.status_code,
            location=probe.location,
            expected_location=expected_location,
            canonical_origin=normalized_canonical_origin,
            alias_host=selected_alias_host,
        )

    resolved_location = urljoin(request_url, probe.location)
    if resolved_location != expected_location:
        return CanonicalRedirectCheckResult(
            ok=False,
            skipped=False,
            reason="canonical_redirect_target_mismatch",
            request_url=request_url,
            status_code=probe.status_code,
            location=probe.location,
            expected_location=expected_location,
            canonical_origin=normalized_canonical_origin,
            alias_host=selected_alias_host,
        )

    return CanonicalRedirectCheckResult(
        ok=True,
        skipped=False,
        reason="ok",
        request_url=request_url,
        status_code=probe.status_code,
        location=probe.location,
        expected_location=expected_location,
        canonical_origin=normalized_canonical_origin,
        alias_host=selected_alias_host,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke-check optional canonical-host redirect contract for UI /login"
    )
    parser.add_argument("--base-url", required=True, help="Canonical GUI base URL")
    parser.add_argument(
        "--canonical-origin",
        default="",
        help="Optional canonical origin override (defaults to base URL origin)",
    )
    parser.add_argument(
        "--canonical-hosts",
        default="",
        help="Comma-separated canonical host list from UI_CANONICAL_HOSTS",
    )
    parser.add_argument(
        "--alias-host",
        default="",
        help="Optional explicit alias host override for the redirect probe",
    )
    parser.add_argument(
        "--next",
        dest="next_path",
        default="/gui",
        help="next query value to preserve in redirect target",
    )
    parser.add_argument(
        "--reason",
        default="manual_login",
        help="reason query value to preserve in redirect target",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-attempts", type=int, default=8)
    parser.add_argument("--retry-delay", type=float, default=5.0)
    parser.add_argument(
        "--max-retry-delay",
        type=float,
        default=10.0,
        help="Cap for effective retry sleep in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional JSON output file path",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Alias for --output-json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    output_json = str(args.output_json or args.json_out or "").strip()

    try:
        result = check_canonical_redirect(
            base_url=args.base_url,
            canonical_origin=args.canonical_origin,
            canonical_hosts=args.canonical_hosts,
            alias_host=args.alias_host,
            next_path=args.next_path,
            reason=args.reason,
            timeout_seconds=float(args.timeout),
            max_attempts=int(args.max_attempts),
            retry_delay_seconds=float(args.retry_delay),
            max_retry_delay_seconds=float(args.max_retry_delay),
        )
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "skipped": False,
            "reason": "request_error",
            "error": str(exc),
            "base_url": args.base_url,
            "canonical_origin": args.canonical_origin,
            "canonical_hosts": args.canonical_hosts,
            "alias_host": args.alias_host,
            "next": args.next_path,
            "reason_input": args.reason,
            "max_retry_delay": float(args.max_retry_delay),
        }
        if output_json:
            output_path = Path(output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    payload = asdict(result)
    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(payload, ensure_ascii=False))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
