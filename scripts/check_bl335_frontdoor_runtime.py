#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import ipaddress
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib import error, parse, request


@dataclass(frozen=True)
class Config:
    ui_health_url: str
    api_analyze_url: str
    expected_api_base_url: str
    expected_ui_origins: tuple[str, ...]
    timeout_seconds: float
    output_json: str


@dataclass(frozen=True)
class CheckResult:
    status: str
    reason: str
    details: dict[str, object]


def _normalize_url(raw: str) -> str:
    value = raw.strip()
    parsed = parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"invalid URL scheme (expected http/https): {raw}")
    if not parsed.netloc:
        raise ValueError(f"missing host in URL: {raw}")
    if parsed.query or parsed.fragment:
        raise ValueError(f"URL must not include query/fragment: {raw}")
    path = parsed.path or ""
    normalized_path = path.rstrip("/") if path not in {"", "/"} else ""
    return parse.urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))


def _normalize_origin(raw: str) -> str:
    value = raw.strip()
    parsed = parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"invalid origin scheme (expected http/https): {raw}")
    if not parsed.netloc:
        raise ValueError(f"missing host in origin: {raw}")
    if parsed.path not in {"", "/"}:
        raise ValueError(f"origin must not include path: {raw}")
    if parsed.query or parsed.fragment:
        raise ValueError(f"origin must not include query/fragment: {raw}")
    return f"{parsed.scheme}://{parsed.netloc}"


def _looks_like_ip_host(url: str) -> bool:
    host = parse.urlsplit(url).hostname
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _load_json_response(url: str, timeout_seconds: float) -> tuple[int, dict[str, object], dict[str, str]]:
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
        payload = json.loads(raw)
        headers = {k.lower(): v for k, v in response.headers.items()}
        return int(response.status), payload, headers


def _preflight(url: str, origin: str, timeout_seconds: float) -> tuple[int, dict[str, str]]:
    req = request.Request(url=url, method="OPTIONS")
    req.add_header("Origin", origin)
    req.add_header("Access-Control-Request-Method", "POST")
    req.add_header("Access-Control-Request-Headers", "content-type,authorization,x-request-id")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            headers = {k.lower(): v for k, v in response.headers.items()}
            return int(response.status), headers
    except error.HTTPError as exc:
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return int(exc.code), headers


def _check_ui_health(config: Config) -> CheckResult:
    try:
        status, payload, _ = _load_json_response(config.ui_health_url, config.timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - explicit structured error
        return CheckResult(
            status="fail",
            reason="ui_health_request_failed",
            details={"error": str(exc)},
        )

    if status != 200:
        return CheckResult(
            status="fail",
            reason="ui_health_status_not_200",
            details={"http_status": status},
        )

    api_base_url = payload.get("api_base_url")
    if not isinstance(api_base_url, str) or not api_base_url.strip():
        return CheckResult(
            status="fail",
            reason="ui_health_missing_api_base_url",
            details={"api_base_url": api_base_url},
        )

    try:
        normalized_ui_api_base = _normalize_url(api_base_url)
    except ValueError as exc:
        return CheckResult(
            status="fail",
            reason="ui_health_invalid_api_base_url",
            details={"api_base_url": api_base_url, "error": str(exc)},
        )

    expected = config.expected_api_base_url
    if normalized_ui_api_base != expected:
        return CheckResult(
            status="fail",
            reason="api_base_url_mismatch",
            details={"actual": normalized_ui_api_base, "expected": expected},
        )

    if parse.urlsplit(normalized_ui_api_base).scheme != "https":
        return CheckResult(
            status="fail",
            reason="api_base_url_not_https",
            details={"actual": normalized_ui_api_base},
        )

    if _looks_like_ip_host(normalized_ui_api_base):
        return CheckResult(
            status="fail",
            reason="api_base_url_must_not_be_ip",
            details={"actual": normalized_ui_api_base},
        )

    return CheckResult(
        status="pass",
        reason="ok",
        details={"actual": normalized_ui_api_base},
    )


def _check_cors(config: Config) -> CheckResult:
    origin_checks: list[dict[str, object]] = []
    has_failures = False

    for origin in config.expected_ui_origins:
        try:
            status_code, headers = _preflight(config.api_analyze_url, origin, config.timeout_seconds)
        except Exception as exc:  # noqa: BLE001
            origin_checks.append(
                {
                    "origin": origin,
                    "status": "fail",
                    "reason": "request_failed",
                    "error": str(exc),
                }
            )
            has_failures = True
            continue

        allow_origin = headers.get("access-control-allow-origin", "")
        if 200 <= status_code < 300 and allow_origin == origin:
            origin_checks.append(
                {
                    "origin": origin,
                    "status": "pass",
                    "reason": "ok",
                    "http_status": status_code,
                    "allow_origin": allow_origin,
                }
            )
            continue

        has_failures = True
        reason = "allow_origin_mismatch"
        if not allow_origin:
            reason = "missing_allow_origin"
        elif not (200 <= status_code < 300):
            reason = "non_2xx_preflight"

        origin_checks.append(
            {
                "origin": origin,
                "status": "fail",
                "reason": reason,
                "http_status": status_code,
                "allow_origin": allow_origin or None,
            }
        )

    if has_failures:
        return CheckResult(status="fail", reason="cors_preflight_failed", details={"origins": origin_checks})

    return CheckResult(status="pass", reason="ok", details={"origins": origin_checks})


def _load_config(argv: Iterable[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description=(
            "BL-335 runtime guardrail: verify UI health advertises the expected HTTPS API frontdoor "
            "and API CORS preflight allows all expected UI origins."
        )
    )
    parser.add_argument("--ui-health-url", default=os.getenv("BL335_UI_HEALTH_URL", ""))
    parser.add_argument("--api-analyze-url", default=os.getenv("BL335_API_ANALYZE_URL", ""))
    parser.add_argument("--expected-api-base-url", default=os.getenv("BL335_EXPECTED_API_BASE_URL", ""))
    parser.add_argument(
        "--expected-ui-origin",
        action="append",
        default=[],
        help="Expected UI origin allowed by API CORS (repeatable)",
    )
    parser.add_argument(
        "--expected-ui-origins",
        default=os.getenv("BL335_EXPECTED_UI_ORIGINS", ""),
        help="Comma-separated expected UI origins (alternative to repeated --expected-ui-origin)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.getenv("BL335_HTTP_TIMEOUT", "8")),
    )
    parser.add_argument("--output-json", default=os.getenv("BL335_OUTPUT_JSON", ""))

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be > 0")

    if not args.ui_health_url.strip():
        raise ValueError("ui-health-url is required")
    if not args.api_analyze_url.strip():
        raise ValueError("api-analyze-url is required")
    if not args.expected_api_base_url.strip():
        raise ValueError("expected-api-base-url is required")

    origins = [origin.strip() for origin in args.expected_ui_origin if origin.strip()]
    if args.expected_ui_origins.strip():
        origins.extend([value.strip() for value in args.expected_ui_origins.split(",") if value.strip()])
    if not origins:
        raise ValueError("at least one expected UI origin is required")

    normalized_origins = tuple(dict.fromkeys(_normalize_origin(value) for value in origins))

    return Config(
        ui_health_url=_normalize_url(args.ui_health_url),
        api_analyze_url=_normalize_url(args.api_analyze_url),
        expected_api_base_url=_normalize_url(args.expected_api_base_url),
        expected_ui_origins=normalized_origins,
        timeout_seconds=args.timeout_seconds,
        output_json=args.output_json.strip(),
    )


def _write_json(path: str, payload: dict[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    try:
        config = _load_config(argv)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    ui_check = _check_ui_health(config)
    cors_check = _check_cors(config)

    overall_status = "pass"
    overall_reason = "ok"
    if ui_check.status != "pass":
        overall_status = "fail"
        overall_reason = ui_check.reason
    elif cors_check.status != "pass":
        overall_status = "fail"
        overall_reason = cors_check.reason

    payload: dict[str, object] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "overall": {"status": overall_status, "reason": overall_reason},
        "config": {
            "ui_health_url": config.ui_health_url,
            "api_analyze_url": config.api_analyze_url,
            "expected_api_base_url": config.expected_api_base_url,
            "expected_ui_origins": list(config.expected_ui_origins),
            "timeout_seconds": config.timeout_seconds,
        },
        "checks": {
            "ui_health": {
                "status": ui_check.status,
                "reason": ui_check.reason,
                **ui_check.details,
            },
            "cors_preflight": {
                "status": cors_check.status,
                "reason": cors_check.reason,
                **cors_check.details,
            },
        },
    }

    print(
        "[BL-335] UI health check: "
        f"{ui_check.status} (reason={ui_check.reason}, details={json.dumps(ui_check.details, ensure_ascii=False)})"
    )
    print(
        "[BL-335] CORS preflight check: "
        f"{cors_check.status} (reason={cors_check.reason})"
    )
    print(f"[BL-335] OVERALL: {overall_status} ({overall_reason})")

    if config.output_json:
        _write_json(config.output_json, payload)

    return 0 if overall_status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
