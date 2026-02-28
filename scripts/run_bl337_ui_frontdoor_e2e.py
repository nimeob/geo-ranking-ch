#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib import error, request

DEFAULT_MATRIX_PATH = Path("artifacts/bl337/latest-internet-e2e-matrix.json")
DEFAULT_TIMEOUT_SECONDS = 20.0

UI_TEST_IDS = {
    "UI.LOAD.HOME.200",
    "UI.NAV.CORE_FLOW.VISIBLE",
    "UI.INVALID_INPUT.ERROR_SURFACE",
    "UI.API_ERROR.CONSISTENCY",
}


@dataclass(frozen=True)
class Config:
    matrix_path: Path
    evidence_json: Path
    app_base_url: str
    api_base_url: str
    timeout_seconds: float


@dataclass(frozen=True)
class HttpResponse:
    http_status: int
    body_text: str
    json_body: object | None


@dataclass
class UiCheckResult:
    test_id: str
    status: str
    actual_result: str
    reason: str
    http_status: int | None
    evidence_links: list[str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_base_url(value: str, *, arg_name: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError(f"{arg_name} must start with http:// or https://")
    return normalized


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_config(argv: Iterable[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description=(
            "Run BL-337 WP3 UI frontdoor E2E checks (Expected vs Actual), "
            "persist evidence JSON and update UI rows in the matrix."
        )
    )
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX_PATH)
    parser.add_argument("--evidence-json", type=Path, default=None)
    parser.add_argument("--app-base-url", default="")
    parser.add_argument("--api-base-url", default="")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be > 0")

    matrix_path = args.matrix
    if not matrix_path.exists() or not matrix_path.is_file():
        raise ValueError(f"matrix file not found: {matrix_path}")

    matrix_payload = _read_json(matrix_path)
    if not isinstance(matrix_payload, dict):
        raise ValueError("matrix must be a JSON object")

    targets = matrix_payload.get("targets")
    if not isinstance(targets, dict):
        raise ValueError("matrix.targets missing or invalid")

    matrix_app = targets.get("appBaseUrl")
    matrix_api = targets.get("apiBaseUrl")

    if args.app_base_url.strip():
        app_base_url = _normalize_base_url(args.app_base_url, arg_name="app-base-url")
    else:
        if not isinstance(matrix_app, str) or not matrix_app.strip():
            raise ValueError("matrix.targets.appBaseUrl missing")
        app_base_url = _normalize_base_url(matrix_app, arg_name="matrix.targets.appBaseUrl")

    if args.api_base_url.strip():
        api_base_url = _normalize_base_url(args.api_base_url, arg_name="api-base-url")
    else:
        if not isinstance(matrix_api, str) or not matrix_api.strip():
            raise ValueError("matrix.targets.apiBaseUrl missing")
        api_base_url = _normalize_base_url(matrix_api, arg_name="matrix.targets.apiBaseUrl")

    evidence_json = args.evidence_json
    if evidence_json is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        evidence_json = Path(f"artifacts/bl337/{stamp}-wp3-ui-frontdoor-e2e.json")

    return Config(
        matrix_path=matrix_path,
        evidence_json=evidence_json,
        app_base_url=app_base_url,
        api_base_url=api_base_url,
        timeout_seconds=args.timeout_seconds,
    )


def _http_request(*, url: str, method: str, timeout_seconds: float, body_bytes: bytes | None = None) -> HttpResponse:
    req = request.Request(url=url, method=method)
    if body_bytes is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with request.urlopen(req, data=body_bytes, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return HttpResponse(
                http_status=int(response.status),
                body_text=raw,
                json_body=_try_parse_json(raw),
            )
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return HttpResponse(
            http_status=int(exc.code),
            body_text=raw,
            json_body=_try_parse_json(raw),
        )


def _try_parse_json(raw_text: str) -> object | None:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def _extract_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title


def _excerpt(raw_text: str, *, limit: int = 280) -> str:
    clean = " ".join(raw_text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "…"


def _check_ui_load(response: HttpResponse) -> UiCheckResult:
    body = response.body_text
    lower_body = body.lower()
    title = _extract_title(body)

    error_markers = [
        marker
        for marker in ["internal server error", "service unavailable", "application error", "cloudfront"]
        if marker in lower_body
    ]

    passed = response.http_status == 200 and bool(body.strip()) and not error_markers
    reason = "ok" if passed else "expected_http_200_html_without_runtime_error_marker"

    return UiCheckResult(
        test_id="UI.LOAD.HOME.200",
        status="pass" if passed else "fail",
        actual_result=(
            f"HTTP {response.http_status}; html_len={len(body)}; title={title!r}; "
            f"runtime_error_markers={error_markers}"
        ),
        reason=reason,
        http_status=response.http_status,
        evidence_links=[],
    )


def _required_marker_presence(html: str, markers: dict[str, str]) -> tuple[bool, list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for name, marker in markers.items():
        if marker in html:
            present.append(name)
        else:
            missing.append(name)
    return not missing, present, missing


def _check_ui_navigation_and_core_flow(html: str) -> UiCheckResult:
    markers = {
        "nav_shell": 'id="gui-shell-nav"',
        "nav_input": 'href="#input"',
        "nav_map": 'href="#map"',
        "nav_result": 'href="#result"',
        "form": 'id="analyze-form"',
        "query_input": 'id="query"',
        "query_required": "required",
        "mode_select": 'id="intelligence-mode"',
        "submit_button": 'id="submit-btn"',
        "map_surface": 'id="map-click-surface"',
    }
    passed, present, missing = _required_marker_presence(html, markers)

    reason = "ok" if passed else "expected_navigation_and_core_form_markers"
    return UiCheckResult(
        test_id="UI.NAV.CORE_FLOW.VISIBLE",
        status="pass" if passed else "fail",
        actual_result=(
            f"required_markers={len(present)}/{len(markers)}; "
            f"missing={missing if missing else []}"
        ),
        reason=reason,
        http_status=200,
        evidence_links=[],
    )


def _check_ui_invalid_input_error_surface(html: str) -> UiCheckResult:
    markers = {
        "required_query_input": 'id="query" name="query" type="text"',
        "submit_handler": 'formEl.addEventListener("submit"',
        "empty_query_guard": 'if (!query)',
        "empty_query_message": 'Bitte eine Adresse eingeben.',
        "validation_error_code": 'error: "validation"',
        "validation_error_message": 'message: "query darf nicht leer sein"',
    }

    passed, present, missing = _required_marker_presence(html, markers)
    reason = "ok" if passed else "expected_client_side_validation_markers"
    return UiCheckResult(
        test_id="UI.INVALID_INPUT.ERROR_SURFACE",
        status="pass" if passed else "fail",
        actual_result=(
            f"validation_markers={len(present)}/{len(markers)}; "
            f"missing={missing if missing else []}"
        ),
        reason=reason,
        http_status=200,
        evidence_links=[],
    )


def _check_ui_api_error_consistency(*, html: str, api_probe: HttpResponse) -> UiCheckResult:
    ui_markers = {
        "fetch_analyze": "/analyze",
        "response_guard": "if (!response.ok || !parsed.ok)",
        "error_code_mapping": "parsed && parsed.error",
        "error_message_mapping": "parsed && parsed.message",
        "rich_error": "`${errCode}: ${errMsg}`",
        "phase_error_switch": 'state.phase = result.ok ? "success" : "error"',
        "last_error_binding": "state.lastError = result.errorMessage",
    }
    ui_passed, present, missing = _required_marker_presence(html, ui_markers)

    api_json = api_probe.json_body if isinstance(api_probe.json_body, dict) else {}
    api_passed = (
        400 <= api_probe.http_status < 500
        and isinstance(api_json, dict)
        and isinstance(api_json.get("error"), str)
        and isinstance(api_json.get("message"), str)
    )

    passed = ui_passed and api_passed
    if passed:
        reason = "ok"
    elif not ui_passed:
        reason = "expected_ui_error_mapping_markers"
    else:
        reason = "expected_api_4xx_with_error_and_message"

    return UiCheckResult(
        test_id="UI.API_ERROR.CONSISTENCY",
        status="pass" if passed else "fail",
        actual_result=(
            f"ui_markers={len(present)}/{len(ui_markers)}; missing={missing if missing else []}; "
            f"api_http={api_probe.http_status}; api_json_keys={sorted(api_json.keys()) if isinstance(api_json, dict) else []}"
        ),
        reason=reason,
        http_status=api_probe.http_status,
        evidence_links=[],
    )


def _run_ui_checks(
    config: Config,
    *,
    html_snapshot_path: Path,
    api_probe_path: Path,
) -> tuple[list[UiCheckResult], dict[str, Any]]:
    homepage_url = f"{config.app_base_url}/"
    try:
        homepage = _http_request(
            url=homepage_url,
            method="GET",
            timeout_seconds=config.timeout_seconds,
            body_bytes=None,
        )
    except Exception as exc:  # noqa: BLE001
        blocked_results = [
            UiCheckResult(
                test_id=test_id,
                status="blocked",
                actual_result=f"UI request failed: {exc}",
                reason="homepage_request_failed",
                http_status=None,
                evidence_links=[],
            )
            for test_id in sorted(UI_TEST_IDS)
        ]
        return (
            blocked_results,
            {
                "homepage": {
                    "url": homepage_url,
                    "error": str(exc),
                },
                "captures": {
                    "htmlSnapshot": None,
                    "apiProbe": None,
                },
            },
        )

    _write_text(html_snapshot_path, homepage.body_text)

    load_result = _check_ui_load(homepage)
    nav_result = _check_ui_navigation_and_core_flow(homepage.body_text)
    invalid_input_result = _check_ui_invalid_input_error_surface(homepage.body_text)

    api_probe = None
    api_probe_error: str | None = None
    try:
        api_probe = _http_request(
            url=f"{config.api_base_url}/analyze",
            method="POST",
            timeout_seconds=config.timeout_seconds,
            body_bytes=b'{"query": ',
        )
        api_probe_payload: dict[str, Any] = {
            "target": f"{config.api_base_url}/analyze",
            "httpStatus": api_probe.http_status,
            "bodyExcerpt": _excerpt(api_probe.body_text),
            "isJson": isinstance(api_probe.json_body, dict),
            "json": api_probe.json_body if isinstance(api_probe.json_body, dict) else None,
        }
        _write_json(api_probe_path, api_probe_payload)
    except Exception as exc:  # noqa: BLE001
        api_probe_error = str(exc)

    if api_probe is None:
        consistency_result = UiCheckResult(
            test_id="UI.API_ERROR.CONSISTENCY",
            status="blocked",
            actual_result=f"API probe failed: {api_probe_error}",
            reason="api_probe_failed",
            http_status=None,
            evidence_links=[],
        )
    else:
        consistency_result = _check_ui_api_error_consistency(html=homepage.body_text, api_probe=api_probe)

    diagnostics = {
        "homepage": {
            "url": homepage_url,
            "httpStatus": homepage.http_status,
            "title": _extract_title(homepage.body_text),
            "htmlLength": len(homepage.body_text),
        },
        "captures": {
            "htmlSnapshot": str(html_snapshot_path),
            "apiProbe": str(api_probe_path) if api_probe is not None else None,
        },
        "apiProbeError": api_probe_error,
    }

    return ([load_result, nav_result, invalid_input_result, consistency_result], diagnostics)


def _update_matrix(matrix_payload: dict[str, Any], results: list[UiCheckResult]) -> None:
    tests = matrix_payload.get("tests")
    if not isinstance(tests, list):
        raise ValueError("matrix.tests missing or invalid")

    by_id = {result.test_id: result for result in results}

    seen: set[str] = set()
    for case in tests:
        if not isinstance(case, dict):
            continue
        test_id = case.get("testId")
        if not isinstance(test_id, str):
            continue
        if test_id not in by_id:
            continue

        result = by_id[test_id]
        seen.add(test_id)
        case["actualResult"] = result.actual_result
        case["status"] = result.status
        case["evidenceLinks"] = result.evidence_links
        if result.reason != "ok":
            note = case.get("notes")
            note_prefix = f"WP3 runtime reason: {result.reason}"
            case["notes"] = note_prefix if not isinstance(note, str) or not note.strip() else f"{note_prefix}; {note}"

    missing = sorted(UI_TEST_IDS - seen)
    if missing:
        raise ValueError(f"matrix missing required UI test ids: {', '.join(missing)}")

    counts = {"planned": 0, "pass": 0, "fail": 0, "blocked": 0}
    for case in tests:
        if isinstance(case, dict):
            status = case.get("status")
            if isinstance(status, str) and status in counts:
                counts[status] += 1

    summary = matrix_payload.setdefault("summary", {})
    if not isinstance(summary, dict):
        raise ValueError("matrix.summary must be an object")
    summary["total"] = len(tests)
    summary["planned"] = counts["planned"]
    summary["pass"] = counts["pass"]
    summary["fail"] = counts["fail"]
    summary["blocked"] = counts["blocked"]


def main(argv: Iterable[str] | None = None) -> int:
    try:
        config = _load_config(argv)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    matrix_payload = _read_json(config.matrix_path)
    if not isinstance(matrix_payload, dict):
        print("ERROR: matrix payload must be a JSON object")
        return 2

    started = _utc_now()

    evidence_stem = config.evidence_json.stem
    html_snapshot = config.evidence_json.with_name(f"{evidence_stem}-home.html")
    api_probe_path = config.evidence_json.with_name(f"{evidence_stem}-api-probe.json")

    results, diagnostics = _run_ui_checks(
        config,
        html_snapshot_path=html_snapshot,
        api_probe_path=api_probe_path,
    )

    evidence_links = [
        str(config.evidence_json),
        str(html_snapshot),
    ]
    if diagnostics.get("captures", {}).get("apiProbe"):
        evidence_links.append(str(api_probe_path))

    for result in results:
        result.evidence_links = list(evidence_links)

    finished = _utc_now()

    try:
        _update_matrix(matrix_payload, results)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    _write_json(config.matrix_path, matrix_payload)

    evidence_payload: dict[str, Any] = {
        "schemaVersion": "bl337.wp3.ui-frontdoor-e2e.v1",
        "startedAtUtc": started,
        "finishedAtUtc": finished,
        "targets": {
            "appBaseUrl": config.app_base_url,
            "apiBaseUrl": config.api_base_url,
        },
        "matrixPath": str(config.matrix_path),
        "diagnostics": diagnostics,
        "results": [
            {
                "testId": result.test_id,
                "status": result.status,
                "reason": result.reason,
                "httpStatus": result.http_status,
                "actualResult": result.actual_result,
                "evidenceLinks": result.evidence_links,
            }
            for result in results
        ],
        "summary": {
            "total": len(results),
            "pass": sum(1 for result in results if result.status == "pass"),
            "fail": sum(1 for result in results if result.status == "fail"),
            "blocked": sum(1 for result in results if result.status == "blocked"),
        },
    }

    _write_json(config.evidence_json, evidence_payload)

    for result in results:
        print(
            "[BL-337.wp3] "
            f"{result.test_id}: {result.status} "
            f"(http={result.http_status}, reason={result.reason})"
        )

    if any(result.status != "pass" for result in results):
        print(f"[BL-337.wp3] OVERALL: fail (evidence={config.evidence_json})")
        return 1

    print(f"[BL-337.wp3] OVERALL: pass (evidence={config.evidence_json})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
