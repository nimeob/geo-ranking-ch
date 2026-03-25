#!/usr/bin/env python3
"""Live smoke-check for BFF auth-proxy forwarded-host guards.

This validates that `/auth/login`, `/auth/logout` and `/auth/callback`
- allow trusted proxied traffic (login redirect still works), and
- fail-closed for untrusted or mixed forwarded-host chains.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

_TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 502, 503, 504})
_REDIRECT_HTTP_STATUSES = frozenset({301, 302, 303, 307, 308})
_PROXY_MARKER_HEADER = "X-Geo-Auth-Proxy"
_PROXY_MARKER_VALUE = "1"
_EXPECTED_DISABLED_ERROR = "external_direct_login_disabled"


@dataclass(frozen=True)
class _HttpProbeResult:
    status_code: int
    location: str
    body_text: str


@dataclass(frozen=True)
class _ProbeSpec:
    name: str
    path_with_query: str
    forwarded_host: str
    expect_status: int | None = None
    expect_redirect: bool = False
    expect_location_contains: str = ""
    expect_error: str = ""


@dataclass(frozen=True)
class _ProbeOutcome:
    name: str
    ok: bool
    reason: str
    status_code: int
    location: str
    expected_status: int | None
    expected_redirect: bool
    forwarded_host: str
    hint: str = ""


@dataclass(frozen=True)
class AuthProxyGuardSmokeResult:
    ok: bool
    reason: str
    api_base_url: str
    ui_base_url: str
    trusted_forwarded_host: str
    untrusted_forwarded_host: str
    expected_authorize_hosts: list[str]
    checks: list[dict[str, object]]
    hint: str = ""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _normalize_origin(raw_origin: str) -> str:
    value = str(raw_origin or "").strip().rstrip("/")
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid_origin:{raw_origin}")
    return f"{parsed.scheme}://{parsed.netloc}"


def _normalize_host(raw_value: str) -> str:
    value = str(raw_value or "").split(",", 1)[0].strip()
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"//{value}")
    return str(parsed.hostname or "").strip().lower()


def _normalize_host_token(raw_host: str) -> str:
    candidate = str(raw_host or "").strip()
    if not candidate:
        return ""

    parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
    host = str(parsed.hostname or "").strip().lower()
    if host:
        return host

    return candidate.strip("[]").lower()


def _expand_geo_host_variants(host: str) -> set[str]:
    normalized = str(host or "").strip().lower()
    if not normalized:
        return set()

    variants = {normalized}
    if "geo-ranking" in normalized:
        variants.add(normalized.replace("geo-ranking", "georanking"))
    if "georanking" in normalized:
        variants.add(normalized.replace("georanking", "geo-ranking"))
    return {candidate for candidate in variants if candidate}


def _parse_allowed_authorize_hosts(raw_hosts: str | None) -> set[str]:
    if not raw_hosts:
        return set()

    hosts: set[str] = set()
    for token in str(raw_hosts).split(","):
        normalized = _normalize_host_token(token)
        if not normalized:
            continue
        hosts.update(_expand_geo_host_variants(normalized))
    return hosts


def _derive_default_authorize_hosts(ui_origin: str) -> set[str]:
    host = _normalize_host_token(urlparse(ui_origin).hostname or "")
    if not host:
        return set()

    seed_hosts: set[str] = {host}
    if host.startswith("www.") and len(host) > 4:
        seed_hosts.add(f"auth.{host[4:]}")
    else:
        seed_hosts.add(f"auth.{host}")

    allowed_hosts: set[str] = set()
    for seed in seed_hosts:
        allowed_hosts.update(_expand_geo_host_variants(seed))
    return {candidate for candidate in allowed_hosts if candidate}


def _is_redirect_status(status_code: int) -> bool:
    return int(status_code) in _REDIRECT_HTTP_STATUSES


def _is_login_unavailable_redirect(location: str) -> bool:
    return "reason=login_unavailable" in str(location or "").lower()


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
    headers: dict[str, str],
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
    max_retry_delay_seconds: float = 10.0,
) -> _HttpProbeResult:
    opener = build_opener(_NoRedirect)
    attempts = max(1, int(max_attempts))
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        req = Request(request_url, method="GET")
        for key, value in headers.items():
            req.add_header(key, value)

        try:
            resp = opener.open(req, timeout=timeout_seconds)
            try:
                status = int(getattr(resp, "status", 0) or resp.getcode())
                location = str(resp.headers.get("Location") or "").strip()
                body_text = resp.read(1500).decode("utf-8", errors="replace")
            finally:
                close_fn = getattr(resp, "close", None)
                if callable(close_fn):
                    close_fn()
            return _HttpProbeResult(status_code=status, location=location, body_text=body_text)
        except HTTPError as exc:
            try:
                status = int(getattr(exc, "status", 0) or exc.getcode())
                headers = exc.headers or {}
                location = str(headers.get("Location") or "").strip()
                retry_after_header = str(headers.get("Retry-After") or "").strip()
                body_text = exc.read(1500).decode("utf-8", errors="replace")
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
            return _HttpProbeResult(status_code=status, location=location, body_text=body_text)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(min(max(0.0, retry_delay_seconds), max(0.0, max_retry_delay_seconds)))

    raise RuntimeError(
        f"request_failed_after_retries(attempts={attempts}, timeout_seconds={timeout_seconds}): {last_error}"
    )


def _build_probe_headers(forwarded_host: str) -> dict[str, str]:
    return {
        _PROXY_MARKER_HEADER: _PROXY_MARKER_VALUE,
        "X-Forwarded-Host": forwarded_host,
        "X-Forwarded-Proto": "https",
        "Accept": "application/json",
    }


def _build_probe_specs(*, trusted_host: str, untrusted_host: str) -> list[_ProbeSpec]:
    mixed = f"{trusted_host},{untrusted_host}"
    return [
        _ProbeSpec(
            name="login_trusted",
            path_with_query="/auth/login?next=%2Fgui",
            forwarded_host=trusted_host,
            expect_redirect=True,
            expect_location_contains="authorize",
        ),
        _ProbeSpec(
            name="login_untrusted",
            path_with_query="/auth/login?next=%2Fgui",
            forwarded_host=untrusted_host,
            expect_status=403,
            expect_error=_EXPECTED_DISABLED_ERROR,
        ),
        _ProbeSpec(
            name="login_chain_untrusted",
            path_with_query="/auth/login?next=%2Fgui",
            forwarded_host=mixed,
            expect_status=403,
            expect_error=_EXPECTED_DISABLED_ERROR,
        ),
        _ProbeSpec(
            name="logout_chain_untrusted",
            path_with_query="/auth/logout",
            forwarded_host=mixed,
            expect_status=403,
            expect_error=_EXPECTED_DISABLED_ERROR,
        ),
        _ProbeSpec(
            name="callback_untrusted",
            path_with_query="/auth/callback?code=fake-code&state=fake-state",
            forwarded_host=untrusted_host,
            expect_status=403,
            expect_error=_EXPECTED_DISABLED_ERROR,
        ),
        _ProbeSpec(
            name="callback_chain_untrusted",
            path_with_query="/auth/callback?code=fake-code&state=fake-state",
            forwarded_host=mixed,
            expect_status=403,
            expect_error=_EXPECTED_DISABLED_ERROR,
        ),
    ]


def _evaluate_probe(
    *, spec: _ProbeSpec, probe: _HttpProbeResult, allowed_authorize_hosts: set[str]
) -> _ProbeOutcome:
    if spec.expect_redirect:
        if not _is_redirect_status(probe.status_code):
            return _ProbeOutcome(
                name=spec.name,
                ok=False,
                reason=f"unexpected_status_{probe.status_code}",
                status_code=probe.status_code,
                location=probe.location,
                expected_status=spec.expect_status,
                expected_redirect=spec.expect_redirect,
                forwarded_host=spec.forwarded_host,
            )
        if spec.expect_location_contains and spec.expect_location_contains not in probe.location:
            return _ProbeOutcome(
                name=spec.name,
                ok=False,
                reason="redirect_target_mismatch",
                status_code=probe.status_code,
                location=probe.location,
                expected_status=spec.expect_status,
                expected_redirect=spec.expect_redirect,
                forwarded_host=spec.forwarded_host,
            )

        if spec.expect_redirect and allowed_authorize_hosts:
            parsed_location = urlparse(probe.location)
            if parsed_location.netloc:
                observed_host = _normalize_host_token(parsed_location.hostname or "")
                if observed_host not in allowed_authorize_hosts:
                    return _ProbeOutcome(
                        name=spec.name,
                        ok=False,
                        reason="authorize_redirect_host_not_allowed",
                        status_code=probe.status_code,
                        location=probe.location,
                        expected_status=spec.expect_status,
                        expected_redirect=spec.expect_redirect,
                        forwarded_host=spec.forwarded_host,
                        hint=(
                            "expected_authorize_hosts="
                            + ",".join(sorted(allowed_authorize_hosts))
                        ),
                    )

        return _ProbeOutcome(
            name=spec.name,
            ok=True,
            reason="ok",
            status_code=probe.status_code,
            location=probe.location,
            expected_status=spec.expect_status,
            expected_redirect=spec.expect_redirect,
            forwarded_host=spec.forwarded_host,
        )

    expected_status = int(spec.expect_status or 0)
    if probe.status_code != expected_status:
        if (
            expected_status == 403
            and _is_redirect_status(probe.status_code)
            and _is_login_unavailable_redirect(probe.location)
        ):
            return _ProbeOutcome(
                name=spec.name,
                ok=False,
                reason="unexpected_login_unavailable_redirect",
                status_code=probe.status_code,
                location=probe.location,
                expected_status=expected_status,
                expected_redirect=spec.expect_redirect,
                forwarded_host=spec.forwarded_host,
                hint="api_base_url_likely_points_to_ui_origin",
            )

        return _ProbeOutcome(
            name=spec.name,
            ok=False,
            reason=f"unexpected_status_{probe.status_code}",
            status_code=probe.status_code,
            location=probe.location,
            expected_status=expected_status,
            expected_redirect=spec.expect_redirect,
            forwarded_host=spec.forwarded_host,
        )

    if spec.expect_error:
        body_lc = probe.body_text.lower()
        if spec.expect_error.lower() not in body_lc:
            return _ProbeOutcome(
                name=spec.name,
                ok=False,
                reason="missing_expected_error_marker",
                status_code=probe.status_code,
                location=probe.location,
                expected_status=expected_status,
                expected_redirect=spec.expect_redirect,
                forwarded_host=spec.forwarded_host,
            )

    return _ProbeOutcome(
        name=spec.name,
        ok=True,
        reason="ok",
        status_code=probe.status_code,
        location=probe.location,
        expected_status=expected_status,
        expected_redirect=spec.expect_redirect,
        forwarded_host=spec.forwarded_host,
    )


def check_auth_proxy_guard(
    *,
    api_base_url: str,
    ui_base_url: str,
    trusted_forwarded_host: str,
    untrusted_forwarded_host: str,
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
    expected_authorize_host: str = "",
    max_retry_delay_seconds: float = 10.0,
) -> AuthProxyGuardSmokeResult:
    normalized_api_origin = _normalize_origin(api_base_url)
    normalized_ui_origin = _normalize_origin(ui_base_url) if str(ui_base_url or "").strip() else ""

    trusted_host = _normalize_host(trusted_forwarded_host) or _normalize_host(normalized_ui_origin)
    if not trusted_host:
        raise ValueError("trusted_forwarded_host_missing")

    untrusted_host = _normalize_host(untrusted_forwarded_host)
    if not untrusted_host:
        raise ValueError("invalid_untrusted_forwarded_host")
    if untrusted_host == trusted_host:
        raise ValueError("untrusted_forwarded_host_must_differ_from_trusted")

    allowed_authorize_hosts = _parse_allowed_authorize_hosts(expected_authorize_host)
    if not allowed_authorize_hosts and normalized_ui_origin:
        allowed_authorize_hosts = _derive_default_authorize_hosts(normalized_ui_origin)

    checks: list[dict[str, object]] = []
    for spec in _build_probe_specs(trusted_host=trusted_host, untrusted_host=untrusted_host):
        request_url = f"{normalized_api_origin}{spec.path_with_query}"
        probe = _send_request_probe(
            request_url=request_url,
            headers=_build_probe_headers(spec.forwarded_host),
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay_seconds,
            max_retry_delay_seconds=max_retry_delay_seconds,
        )
        outcome = _evaluate_probe(
            spec=spec,
            probe=probe,
            allowed_authorize_hosts=allowed_authorize_hosts,
        )
        checks.append(
            {
                "name": outcome.name,
                "ok": outcome.ok,
                "reason": outcome.reason,
                "request_url": request_url,
                "status_code": outcome.status_code,
                "location": outcome.location,
                "expected_status": outcome.expected_status,
                "expected_redirect": outcome.expected_redirect,
                "forwarded_host": outcome.forwarded_host,
                "hint": outcome.hint,
            }
        )

    failed = [check for check in checks if not bool(check.get("ok"))]
    reason = "ok" if not failed else f"failed_{failed[0].get('name', 'unknown')}"

    hint = ""
    if failed:
        first_failed_reason = str(failed[0].get("reason") or "").strip().lower()
        if (
            first_failed_reason == "unexpected_login_unavailable_redirect"
            and normalized_ui_origin
            and normalized_api_origin == normalized_ui_origin
        ):
            hint = "api_base_url_equals_ui_base_url_use_api_origin"

    return AuthProxyGuardSmokeResult(
        ok=not failed,
        reason=reason,
        api_base_url=normalized_api_origin,
        ui_base_url=normalized_ui_origin,
        trusted_forwarded_host=trusted_host,
        untrusted_forwarded_host=untrusted_host,
        expected_authorize_hosts=sorted(allowed_authorize_hosts),
        checks=checks,
        hint=hint,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-check BFF auth-proxy forwarded-host guard")
    parser.add_argument(
        "--api-base-url",
        required=True,
        help=(
            "API origin (BFF), e.g. https://api.dev.georanking.ch. "
            "Do not point this to the UI origin."
        ),
    )
    parser.add_argument(
        "--ui-base-url",
        default="",
        help="UI origin used to infer trusted forwarded host when --trusted-forwarded-host is omitted",
    )
    parser.add_argument(
        "--trusted-forwarded-host",
        default="",
        help="Trusted X-Forwarded-Host value (defaults to host from --ui-base-url)",
    )
    parser.add_argument(
        "--untrusted-forwarded-host",
        default="evil.example.test",
        help="Untrusted forwarded host used for fail-closed checks",
    )
    parser.add_argument(
        "--expected-authorize-host",
        default="",
        help=(
            "Optional comma-separated allow-list for absolute authorize redirect hosts "
            "(hostname, host:port, or URL). Defaults to auth.<ui-host-without-www> + <ui-host> "
            "and auto-adds geo-ranking/georanking host variants when --ui-base-url is provided."
        ),
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    parser.add_argument(
        "--max-retry-delay",
        type=float,
        default=10.0,
        help="Cap for effective retry sleep in seconds (default: 10.0)",
    )
    parser.add_argument("--output-json", default="", help="Optional JSON output path")
    parser.add_argument("--json-out", default="", help="Alias for --output-json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    try:
        result = check_auth_proxy_guard(
            api_base_url=args.api_base_url,
            ui_base_url=args.ui_base_url,
            trusted_forwarded_host=args.trusted_forwarded_host,
            untrusted_forwarded_host=args.untrusted_forwarded_host,
            timeout_seconds=max(1.0, float(args.timeout)),
            max_attempts=max(1, int(args.max_attempts)),
            retry_delay_seconds=max(0.0, float(args.retry_delay)),
            expected_authorize_host=str(args.expected_authorize_host or ""),
            max_retry_delay_seconds=max(0.0, float(args.max_retry_delay)),
        )
    except ValueError as exc:
        payload = {
            "ok": False,
            "reason": f"invalid_arguments:{exc}",
            "api_base_url": args.api_base_url,
            "ui_base_url": args.ui_base_url,
            "expected_authorize_hosts": [],
            "max_retry_delay": float(args.max_retry_delay),
            "checks": [],
            "hint": "",
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 2
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "reason": f"probe_exception:{exc}",
            "api_base_url": args.api_base_url,
            "ui_base_url": args.ui_base_url,
            "expected_authorize_hosts": [],
            "max_retry_delay": float(args.max_retry_delay),
            "checks": [],
            "hint": "",
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    payload = asdict(result)
    rendered = json.dumps(payload, ensure_ascii=False)
    print(rendered)

    out_path = str(args.output_json or args.json_out or "").strip()
    if out_path:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
