#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib import error, parse, request


@dataclass(frozen=True)
class Config:
    ui_base_url: str
    expected_version: str
    api_health_url: str | None
    api_base_url: str | None
    trace_debug_required: bool
    trace_request_id: str | None
    trace_smoke_json: str | None
    trace_lookback_seconds: int
    trace_max_events: int
    timeout_seconds: float
    output_json: str | None
    summary_path: str | None


@dataclass(frozen=True)
class CheckResult:
    status: str
    reason: str
    details: dict[str, object]


def _normalize_base_url(raw: str, *, allow_empty: bool = False) -> str | None:
    value = raw.strip()
    if allow_empty and not value:
        return None
    if not value:
        raise ValueError("URL is required")

    parsed = parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"invalid URL scheme (expected http/https): {raw}")
    if not parsed.netloc:
        raise ValueError(f"missing host in URL: {raw}")
    if parsed.query or parsed.fragment:
        raise ValueError(f"URL must not include query/fragment: {raw}")

    normalized_path = parsed.path.rstrip("/") if parsed.path not in {"", "/"} else ""
    return parse.urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))


def _fetch_json(url: str, timeout_seconds: float) -> tuple[int, dict[str, object] | None, str | None]:
    req = request.Request(url=url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                return int(response.status), None, "response_json_not_object"
            return int(response.status), payload, None
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                payload = None
        except json.JSONDecodeError:
            payload = None
        return int(exc.code), payload, f"http_error_{exc.code}"
    except json.JSONDecodeError:
        return 0, None, "invalid_json"
    except Exception as exc:  # noqa: BLE001
        return 0, None, f"request_failed:{exc}"


def _check_ui_version(config: Config) -> CheckResult:
    url = f"{config.ui_base_url}/healthz"
    status, payload, error_reason = _fetch_json(url, config.timeout_seconds)
    if error_reason:
        return CheckResult(
            status="fail",
            reason="ui_health_request_failed",
            details={"url": url, "error": error_reason, "http_status": status or None},
        )

    if status != 200:
        return CheckResult(
            status="fail",
            reason="ui_health_status_not_200",
            details={"url": url, "http_status": status},
        )

    if not payload:
        return CheckResult(
            status="fail",
            reason="ui_health_missing_json",
            details={"url": url, "http_status": status},
        )

    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        return CheckResult(
            status="fail",
            reason="ui_health_missing_version",
            details={"url": url, "version": version},
        )

    version = version.strip()
    if version != config.expected_version:
        return CheckResult(
            status="fail",
            reason="ui_version_mismatch",
            details={
                "url": url,
                "actual_version": version,
                "expected_version": config.expected_version,
            },
        )

    return CheckResult(
        status="pass",
        reason="ok",
        details={"url": url, "version": version},
    )


def _check_api_health(config: Config) -> CheckResult:
    if not config.api_health_url:
        return CheckResult(status="skip", reason="not_configured", details={})

    status, payload, error_reason = _fetch_json(config.api_health_url, config.timeout_seconds)
    if error_reason:
        return CheckResult(
            status="fail",
            reason="api_health_request_failed",
            details={"url": config.api_health_url, "error": error_reason, "http_status": status or None},
        )

    if status != 200:
        return CheckResult(
            status="fail",
            reason="api_health_status_not_200",
            details={"url": config.api_health_url, "http_status": status},
        )

    details: dict[str, object] = {"url": config.api_health_url, "http_status": status}
    if isinstance(payload, dict):
        details["ok"] = payload.get("ok")

    return CheckResult(status="pass", reason="ok", details=details)


def _resolve_trace_request_id(config: Config) -> tuple[str | None, str | None]:
    if config.trace_request_id and config.trace_request_id.strip():
        return config.trace_request_id.strip(), None

    if not config.trace_smoke_json:
        return None, "trace_request_id_missing"

    path = Path(config.trace_smoke_json)
    if not path.exists():
        return None, f"trace_smoke_json_missing:{path}"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"trace_smoke_json_invalid:{exc}"

    request_id = payload.get("request_id") if isinstance(payload, dict) else None
    if not isinstance(request_id, str) or not request_id.strip():
        return None, "trace_smoke_json_request_id_missing"

    return request_id.strip(), None


def _check_trace_debug(config: Config) -> CheckResult:
    if not config.trace_debug_required:
        return CheckResult(status="skip", reason="not_required", details={})

    if not config.api_base_url:
        return CheckResult(
            status="fail",
            reason="trace_api_base_missing",
            details={"hint": "api-base-url is required when trace-debug is enabled"},
        )

    request_id, request_error = _resolve_trace_request_id(config)
    if request_error:
        return CheckResult(status="fail", reason="trace_request_id_unavailable", details={"error": request_error})

    query = parse.urlencode(
        {
            "request_id": request_id,
            "lookback_seconds": str(config.trace_lookback_seconds),
            "max_events": str(config.trace_max_events),
        }
    )
    url = f"{config.api_base_url}/debug/trace?{query}"

    status, payload, error_reason = _fetch_json(url, config.timeout_seconds)
    if error_reason:
        return CheckResult(
            status="fail",
            reason="trace_debug_request_failed",
            details={"url": url, "error": error_reason, "http_status": status or None},
        )

    if status != 200:
        return CheckResult(
            status="fail",
            reason="trace_debug_status_not_200",
            details={"url": url, "http_status": status},
        )

    if not payload:
        return CheckResult(
            status="fail",
            reason="trace_debug_missing_json",
            details={"url": url, "http_status": status},
        )

    if payload.get("error") == "debug_trace_disabled":
        return CheckResult(
            status="fail",
            reason="trace_debug_disabled",
            details={"url": url, "request_id": request_id, "payload_error": payload.get("error")},
        )

    if payload.get("ok") is not True:
        return CheckResult(
            status="fail",
            reason="trace_debug_not_ok",
            details={"url": url, "request_id": request_id, "payload": payload},
        )

    trace_state = None
    trace_obj = payload.get("trace")
    if isinstance(trace_obj, dict):
        trace_state = trace_obj.get("state")

    return CheckResult(
        status="pass",
        reason="ok",
        details={"url": url, "request_id": request_id, "trace_state": trace_state},
    )


def _truthy(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_config(argv: Iterable[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description=(
            "Verify post-deploy runtime: UI /healthz version matches expected SHA, optional API /health check, "
            "and optional trace-debug sanity check (/debug/trace)."
        )
    )

    parser.add_argument("--ui-base-url", default=os.getenv("SERVICE_APP_BASE_URL", ""))
    parser.add_argument("--expected-version", default=os.getenv("EXPECTED_UI_VERSION", ""))
    parser.add_argument("--api-health-url", default=os.getenv("SERVICE_HEALTH_URL", ""))
    parser.add_argument("--api-base-url", default=os.getenv("SERVICE_API_BASE_URL", ""))
    parser.add_argument(
        "--trace-debug-required",
        action="store_true",
        default=_truthy(os.getenv("TRACE_DEBUG_EXPECT_ENABLED", "0")),
    )
    parser.add_argument("--trace-request-id", default=os.getenv("TRACE_DEBUG_REQUEST_ID", ""))
    parser.add_argument("--trace-smoke-json", default=os.getenv("TRACE_DEBUG_SMOKE_JSON", ""))
    parser.add_argument(
        "--trace-lookback-seconds",
        type=int,
        default=int(os.getenv("TRACE_DEBUG_LOOKBACK_SECONDS", "86400")),
    )
    parser.add_argument(
        "--trace-max-events",
        type=int,
        default=int(os.getenv("TRACE_DEBUG_MAX_EVENTS", "500")),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.getenv("DEPLOY_VERIFY_TIMEOUT_SECONDS", "12")),
    )
    parser.add_argument("--output-json", default=os.getenv("DEPLOY_VERIFY_OUTPUT_JSON", ""))
    parser.add_argument("--summary-path", default=os.getenv("GITHUB_STEP_SUMMARY", ""))

    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.expected_version.strip():
        raise ValueError("expected-version is required")
    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be > 0")
    if args.trace_lookback_seconds <= 0:
        raise ValueError("trace-lookback-seconds must be > 0")
    if args.trace_max_events <= 0:
        raise ValueError("trace-max-events must be > 0")

    ui_base_url = _normalize_base_url(args.ui_base_url)
    api_base_url = _normalize_base_url(args.api_base_url, allow_empty=True)

    api_health_url = args.api_health_url.strip()
    if api_health_url:
        api_health_url = _normalize_base_url(api_health_url)
    elif api_base_url:
        api_health_url = f"{api_base_url}/health"
    else:
        api_health_url = None

    trace_request_id = args.trace_request_id.strip() or None
    trace_smoke_json = args.trace_smoke_json.strip() or None
    output_json = args.output_json.strip() or None
    summary_path = args.summary_path.strip() or None

    return Config(
        ui_base_url=ui_base_url or "",
        expected_version=args.expected_version.strip(),
        api_health_url=api_health_url,
        api_base_url=api_base_url,
        trace_debug_required=bool(args.trace_debug_required),
        trace_request_id=trace_request_id,
        trace_smoke_json=trace_smoke_json,
        trace_lookback_seconds=args.trace_lookback_seconds,
        trace_max_events=args.trace_max_events,
        timeout_seconds=args.timeout_seconds,
        output_json=output_json,
        summary_path=summary_path,
    )


def _write_json(path: str, payload: dict[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_summary(path: str | None, lines: list[str]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _status_emoji(status: str) -> str:
    return {"pass": "✅", "fail": "❌", "skip": "⏭️"}.get(status, "ℹ️")


def main(argv: Iterable[str] | None = None) -> int:
    try:
        config = _load_config(argv)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    ui_check = _check_ui_version(config)
    api_check = _check_api_health(config)
    trace_check = _check_trace_debug(config)

    overall_status = "pass"
    overall_reason = "ok"
    for check in (ui_check, api_check, trace_check):
        if check.status == "fail":
            overall_status = "fail"
            overall_reason = check.reason
            break

    payload: dict[str, object] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "overall": {"status": overall_status, "reason": overall_reason},
        "config": {
            "ui_base_url": config.ui_base_url,
            "expected_version": config.expected_version,
            "api_health_url": config.api_health_url,
            "api_base_url": config.api_base_url,
            "trace_debug_required": config.trace_debug_required,
            "trace_lookback_seconds": config.trace_lookback_seconds,
            "trace_max_events": config.trace_max_events,
            "timeout_seconds": config.timeout_seconds,
        },
        "checks": {
            "ui_version": {"status": ui_check.status, "reason": ui_check.reason, **ui_check.details},
            "api_health": {"status": api_check.status, "reason": api_check.reason, **api_check.details},
            "trace_debug": {"status": trace_check.status, "reason": trace_check.reason, **trace_check.details},
        },
    }

    print(
        "[deploy-verify] UI /healthz: "
        f"{ui_check.status} (reason={ui_check.reason}, details={json.dumps(ui_check.details, ensure_ascii=False)})"
    )
    print(
        "[deploy-verify] API /health: "
        f"{api_check.status} (reason={api_check.reason}, details={json.dumps(api_check.details, ensure_ascii=False)})"
    )
    print(
        "[deploy-verify] Trace /debug/trace: "
        f"{trace_check.status} (reason={trace_check.reason}, details={json.dumps(trace_check.details, ensure_ascii=False)})"
    )
    print(f"[deploy-verify] OVERALL: {overall_status} ({overall_reason})")

    summary_lines = [
        "## Post-deploy verification (Version + Trace-Debug)",
        f"- UI `/healthz` Version: {_status_emoji(ui_check.status)} `{ui_check.status}` ({ui_check.reason})",
        f"- API `/health`: {_status_emoji(api_check.status)} `{api_check.status}` ({api_check.reason})",
        f"- Trace `/debug/trace`: {_status_emoji(trace_check.status)} `{trace_check.status}` ({trace_check.reason})",
        f"- Gesamtstatus: {_status_emoji(overall_status)} `{overall_status}` ({overall_reason})",
    ]
    _append_summary(config.summary_path, summary_lines)

    if config.output_json:
        _write_json(config.output_json, payload)

    return 0 if overall_status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
