#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib import error, request

DEFAULT_MATRIX_PATH = Path("artifacts/bl337/latest-internet-e2e-matrix.json")
DEFAULT_QUERY = "St. Leonhard-Strasse 40, St. Gallen"
DEFAULT_MODE = "basic"
DEFAULT_TIMEOUT_SECONDS = 20.0

API_TEST_IDS = {
    "API.HEALTH.200",
    "API.ANALYZE.POST.200",
    "API.ANALYZE.NON_BASIC.FINAL_STATE",
    "API.ANALYZE.INVALID_PAYLOAD.400",
    "API.ANALYZE.METHOD_MISMATCH.405",
}


@dataclass(frozen=True)
class Config:
    matrix_path: Path
    evidence_json: Path
    api_base_url: str
    timeout_seconds: float
    query: str
    intelligence_mode: str
    auth_token: str | None


@dataclass
class ApiCheckResult:
    test_id: str
    status: str
    actual_result: str
    http_status: int | None
    reason: str
    response_excerpt: str
    evidence_links: list[str]


@dataclass(frozen=True)
class HttpResponse:
    http_status: int
    body_text: str
    json_body: object | None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError("api-base-url must start with http:// or https://")
    return normalized


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_config(argv: Iterable[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description=(
            "Run BL-337 WP2 API frontdoor E2E checks (Expected vs Actual), "
            "persist evidence JSON and update API rows in the matrix."
        )
    )
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX_PATH)
    parser.add_argument("--evidence-json", type=Path, default=None)
    parser.add_argument("--api-base-url", default="")
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--intelligence-mode", default=DEFAULT_MODE)
    parser.add_argument("--auth-token", default=os.getenv("BL337_API_AUTH_TOKEN", ""))

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be > 0")

    matrix_path = args.matrix
    if not matrix_path.exists() or not matrix_path.is_file():
        raise ValueError(f"matrix file not found: {matrix_path}")

    matrix_payload = _read_json(matrix_path)
    if not isinstance(matrix_payload, dict):
        raise ValueError("matrix must be a JSON object")

    if args.api_base_url.strip():
        api_base_url = _normalize_base_url(args.api_base_url)
    else:
        targets = matrix_payload.get("targets")
        if not isinstance(targets, dict):
            raise ValueError("matrix.targets missing or invalid")
        matrix_api = targets.get("apiBaseUrl")
        if not isinstance(matrix_api, str) or not matrix_api.strip():
            raise ValueError("matrix.targets.apiBaseUrl missing")
        api_base_url = _normalize_base_url(matrix_api)

    evidence_json = args.evidence_json
    if evidence_json is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        evidence_json = Path(f"artifacts/bl337/{stamp}-wp2-api-frontdoor-e2e.json")

    mode = args.intelligence_mode.strip().lower()
    if mode not in {"basic", "extended", "risk"}:
        raise ValueError("intelligence-mode must be one of basic|extended|risk")

    auth_token = args.auth_token.strip() if args.auth_token else ""

    return Config(
        matrix_path=matrix_path,
        evidence_json=evidence_json,
        api_base_url=api_base_url,
        timeout_seconds=args.timeout_seconds,
        query=args.query.strip(),
        intelligence_mode=mode,
        auth_token=auth_token or None,
    )


def _perform_request(
    *,
    url: str,
    method: str,
    timeout_seconds: float,
    body_bytes: bytes | None,
    auth_token: str | None,
) -> HttpResponse:
    req = request.Request(url=url, method=method)
    if body_bytes is not None:
        req.add_header("Content-Type", "application/json")
    if auth_token:
        req.add_header("Authorization", f"Bearer {auth_token}")

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


def _excerpt(raw_text: str, *, limit: int = 400) -> str:
    clean = " ".join(raw_text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "…"


def _run_api_checks(config: Config) -> list[ApiCheckResult]:
    analyze_payload = json.dumps(
        {
            "query": config.query,
            "intelligence_mode": config.intelligence_mode,
            "timeout_seconds": 15,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    non_basic_mode = config.intelligence_mode if config.intelligence_mode != "basic" else "extended"
    non_basic_payload = json.dumps(
        {
            "query": config.query,
            "intelligence_mode": non_basic_mode,
            "timeout_seconds": 30,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    cases = [
        {
            "test_id": "API.HEALTH.200",
            "url": f"{config.api_base_url}/health",
            "method": "GET",
            "body": None,
        },
        {
            "test_id": "API.ANALYZE.POST.200",
            "url": f"{config.api_base_url}/analyze",
            "method": "POST",
            "body": analyze_payload,
        },
        {
            "test_id": "API.ANALYZE.NON_BASIC.FINAL_STATE",
            "url": f"{config.api_base_url}/analyze",
            "method": "POST",
            "body": non_basic_payload,
        },
        {
            "test_id": "API.ANALYZE.INVALID_PAYLOAD.400",
            "url": f"{config.api_base_url}/analyze",
            "method": "POST",
            "body": b'{"query": ',
        },
        {
            "test_id": "API.ANALYZE.METHOD_MISMATCH.405",
            "url": f"{config.api_base_url}/analyze",
            "method": "GET",
            "body": None,
        },
    ]

    results: list[ApiCheckResult] = []
    for case in cases:
        test_id = str(case["test_id"])
        try:
            response = _perform_request(
                url=str(case["url"]),
                method=str(case["method"]),
                timeout_seconds=config.timeout_seconds,
                body_bytes=case["body"] if isinstance(case["body"], (bytes, type(None))) else None,
                auth_token=config.auth_token,
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                ApiCheckResult(
                    test_id=test_id,
                    status="blocked",
                    actual_result=f"Request fehlgeschlagen: {exc}",
                    http_status=None,
                    reason="request_failed",
                    response_excerpt="",
                    evidence_links=[str(config.evidence_json)],
                )
            )
            continue

        outcome = _evaluate_case(test_id=test_id, response=response)
        results.append(
            ApiCheckResult(
                test_id=test_id,
                status=outcome["status"],
                actual_result=outcome["actual_result"],
                http_status=response.http_status,
                reason=outcome["reason"],
                response_excerpt=_excerpt(response.body_text),
                evidence_links=[str(config.evidence_json)],
            )
        )

    return results


def _evaluate_case(*, test_id: str, response: HttpResponse) -> dict[str, str]:
    http_status = response.http_status
    json_body = response.json_body
    ok_flag = isinstance(json_body, dict) and json_body.get("ok") is True

    if test_id == "API.HEALTH.200":
        passed = http_status == 200 and isinstance(json_body, dict)
        reason = "ok" if passed else "expected_http_200_json"
        return {
            "status": "pass" if passed else "fail",
            "reason": reason,
            "actual_result": (
                f"HTTP {http_status}; JSON={isinstance(json_body, dict)}; "
                f"keys={sorted(json_body.keys())[:8] if isinstance(json_body, dict) else []}"
            ),
        }

    if test_id == "API.ANALYZE.POST.200":
        has_result = isinstance(json_body, dict) and isinstance(json_body.get("result"), dict)
        passed = http_status == 200 and ok_flag and has_result
        reason = "ok" if passed else "expected_http_200_ok_true_result_object"
        return {
            "status": "pass" if passed else "fail",
            "reason": reason,
            "actual_result": (
                f"HTTP {http_status}; ok={ok_flag}; result_object={has_result}; "
                f"request_id={json_body.get('request_id') if isinstance(json_body, dict) else None}"
            ),
        }

    if test_id == "API.ANALYZE.NON_BASIC.FINAL_STATE":
        has_result = isinstance(json_body, dict) and isinstance(json_body.get("result"), dict)
        has_structured_error = (
            isinstance(json_body, dict)
            and json_body.get("ok") is False
            and isinstance(json_body.get("error"), str)
            and isinstance(json_body.get("message"), str)
        )
        passed = (http_status == 200 and ok_flag and has_result) or has_structured_error
        reason = "ok" if passed else "expected_success_or_structured_error_final_state"
        return {
            "status": "pass" if passed else "fail",
            "reason": reason,
            "actual_result": (
                f"HTTP {http_status}; ok={ok_flag}; result_object={has_result}; "
                f"structured_error={has_structured_error}; "
                f"error={json_body.get('error') if isinstance(json_body, dict) else None}"
            ),
        }

    if test_id == "API.ANALYZE.INVALID_PAYLOAD.400":
        passed = http_status == 400
        reason = "ok" if passed else "expected_http_400"
        return {
            "status": "pass" if passed else "fail",
            "reason": reason,
            "actual_result": f"HTTP {http_status}; body_is_json={json_body is not None}",
        }

    if test_id == "API.ANALYZE.METHOD_MISMATCH.405":
        passed = http_status == 405 or (400 <= http_status < 500)
        reason = "ok" if passed else "expected_http_405_or_other_4xx"
        return {
            "status": "pass" if passed else "fail",
            "reason": reason,
            "actual_result": f"HTTP {http_status}; body_is_json={json_body is not None}",
        }

    return {
        "status": "fail",
        "reason": "unsupported_test_id",
        "actual_result": f"Unsupported API test id: {test_id}",
    }


def _update_matrix(matrix_payload: dict[str, Any], results: list[ApiCheckResult]) -> None:
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
            note_prefix = f"WP2 runtime reason: {result.reason}"
            case["notes"] = note_prefix if not isinstance(note, str) or not note.strip() else f"{note_prefix}; {note}"

    missing = sorted(API_TEST_IDS - seen)
    if missing:
        raise ValueError(f"matrix missing required API test ids: {', '.join(missing)}")

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
    results = _run_api_checks(config)
    finished = _utc_now()

    try:
        _update_matrix(matrix_payload, results)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    _write_json(config.matrix_path, matrix_payload)

    evidence_payload: dict[str, Any] = {
        "schemaVersion": "bl337.wp2.api-frontdoor-e2e.v1",
        "startedAtUtc": started,
        "finishedAtUtc": finished,
        "target": {"apiBaseUrl": config.api_base_url},
        "request": {
            "query": config.query,
            "intelligence_mode": config.intelligence_mode,
            "auth_token_provided": config.auth_token is not None,
            "timeout_seconds": config.timeout_seconds,
        },
        "results": [
            {
                "testId": result.test_id,
                "status": result.status,
                "reason": result.reason,
                "httpStatus": result.http_status,
                "actualResult": result.actual_result,
                "responseExcerpt": result.response_excerpt,
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
        "matrixPath": str(config.matrix_path),
    }
    _write_json(config.evidence_json, evidence_payload)

    for result in results:
        print(
            "[BL-337.wp2] "
            f"{result.test_id}: {result.status} "
            f"(http={result.http_status}, reason={result.reason})"
        )

    if any(result.status != "pass" for result in results):
        print(f"[BL-337.wp2] OVERALL: fail (evidence={config.evidence_json})")
        return 1

    print(f"[BL-337.wp2] OVERALL: pass (evidence={config.evidence_json})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
