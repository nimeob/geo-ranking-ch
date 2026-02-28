#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_API_BASE_URL = "https://api.dev.georanking.ch"
DEFAULT_APP_BASE_URL = "https://www.dev.georanking.ch"
DEFAULT_OUTPUT = Path("artifacts/bl337/latest-internet-e2e-matrix.json")

ALLOWED_AREAS = {"api", "ui"}
ALLOWED_STATUS = {"planned", "pass", "fail", "blocked"}

TEST_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "testId": "API.HEALTH.200",
        "area": "api",
        "title": "Health-Endpoint über Frontdoor antwortet 200",
        "preconditions": ["Internetzugang", "API-Frontdoor erreichbar"],
        "steps": ["GET {apiBaseUrl}/health"],
        "expectedResult": "HTTP 200 mit JSON-Body und Statusindikator für healthy/readiness.",
    },
    {
        "testId": "API.ANALYZE.POST.200",
        "area": "api",
        "title": "Analyze Success Path liefert gültige Antwort",
        "preconditions": ["Valider Request-Payload verfügbar"],
        "steps": ["POST {apiBaseUrl}/analyze mit validem JSON-Payload"],
        "expectedResult": "HTTP 200; Response entspricht Contract-Grundstruktur (Result + Explainability-Felder).",
    },
    {
        "testId": "API.ANALYZE.NON_BASIC.FINAL_STATE",
        "area": "api",
        "title": "Analyze Non-Basic Mode terminiert mit finalem Ergebnis oder sauberem Fehler",
        "preconditions": ["Valider Request-Payload verfügbar", "intelligence_mode != basic"],
        "steps": [
            "POST {apiBaseUrl}/analyze mit validem JSON-Payload und intelligence_mode=extended",
            "Antwort innerhalb Request-Timeout auswerten",
        ],
        "expectedResult": "Deterministischer Final-State: entweder HTTP 200 + ok=true + result oder strukturierter Fehler (ok=false + error + message) statt hängendem Loading.",
    },
    {
        "testId": "API.ANALYZE.INVALID_PAYLOAD.400",
        "area": "api",
        "title": "Analyze lehnt invalides JSON deterministisch ab",
        "preconditions": ["Keine"],
        "steps": ["POST {apiBaseUrl}/analyze mit schemafremdem/inkomplettem Payload"],
        "expectedResult": "HTTP 4xx (erwartet 400) mit klarer Fehlermeldung im Error-Body.",
    },
    {
        "testId": "API.ANALYZE.METHOD_MISMATCH.405",
        "area": "api",
        "title": "Method-Mismatch auf Analyze wird korrekt abgewiesen",
        "preconditions": ["Keine"],
        "steps": ["GET {apiBaseUrl}/analyze"],
        "expectedResult": "HTTP 405 (oder dokumentierter 4xx-Reject) mit nachvollziehbarer Fehlermeldung.",
    },
    {
        "testId": "UI.LOAD.HOME.200",
        "area": "ui",
        "title": "UI-Frontdoor lädt ohne Mixed-Content/TLS-Fehler",
        "preconditions": ["Browser mit Internetzugang"],
        "steps": ["GET {appBaseUrl}"],
        "expectedResult": "Startseite lädt mit HTTP 200; keine offensichtliche Runtime-Error-Seite.",
    },
    {
        "testId": "UI.NAV.CORE_FLOW.VISIBLE",
        "area": "ui",
        "title": "Kern-Flow (Adresseingabe/Form) ist sichtbar und bedienbar",
        "preconditions": ["UI erfolgreich geladen"],
        "steps": ["Zur Analyse-Ansicht navigieren", "Adress-/Parameterfelder prüfen"],
        "expectedResult": "Kernformulare sind sichtbar, interaktiv und ohne Frontend-Fehler renderbar.",
    },
    {
        "testId": "UI.INVALID_INPUT.ERROR_SURFACE",
        "area": "ui",
        "title": "Ungültige Eingabe zeigt erwartetes Fehlerbild",
        "preconditions": ["UI erfolgreich geladen"],
        "steps": ["Ungültige/inkomplette Eingabe absenden"],
        "expectedResult": "UI zeigt nachvollziehbare Validierungs-/Fehlermeldung statt stiller Failure.",
    },
    {
        "testId": "UI.API_ERROR.CONSISTENCY",
        "area": "ui",
        "title": "UI-Fehlerbild bleibt konsistent zum API-Fehler",
        "preconditions": ["API-Negativfall reproduzierbar"],
        "steps": ["Flow triggern, der API-4xx/5xx auslöst", "UI-Fehlerdarstellung prüfen"],
        "expectedResult": "UI zeigt einen konsistenten, benutzerverständlichen Fehlerzustand inkl. sinnvoller Recovery-Hinweise.",
    },
]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _materialize_steps(steps: list[str], *, api_base_url: str, app_base_url: str) -> list[str]:
    return [
        step.replace("{apiBaseUrl}", api_base_url).replace("{appBaseUrl}", app_base_url)
        for step in steps
    ]


def build_matrix(*, api_base_url: str, app_base_url: str, generated_at_utc: str | None = None) -> dict[str, Any]:
    tests: list[dict[str, Any]] = []
    for blueprint in TEST_BLUEPRINTS:
        tests.append(
            {
                "testId": blueprint["testId"],
                "area": blueprint["area"],
                "title": blueprint["title"],
                "preconditions": list(blueprint["preconditions"]),
                "steps": _materialize_steps(
                    list(blueprint["steps"]),
                    api_base_url=api_base_url,
                    app_base_url=app_base_url,
                ),
                "expectedResult": blueprint["expectedResult"],
                "actualResult": None,
                "status": "planned",
                "evidenceLinks": [],
                "notes": "",
            }
        )

    return {
        "schemaVersion": "bl337.internet-e2e.v1",
        "generatedAtUtc": generated_at_utc or _utc_timestamp(),
        "targets": {
            "apiBaseUrl": api_base_url,
            "appBaseUrl": app_base_url,
        },
        "summary": {
            "total": len(tests),
            "planned": len(tests),
            "pass": 0,
            "fail": 0,
            "blocked": 0,
        },
        "tests": tests,
    }


def _validate_test_case(case: object, index: int) -> list[str]:
    prefix = f"tests[{index}]"
    if not isinstance(case, dict):
        return [f"{prefix}: test case must be an object"]

    required_string_fields = ["testId", "area", "title", "expectedResult", "status"]
    required_list_fields = ["preconditions", "steps", "evidenceLinks"]

    errors: list[str] = []

    for field in required_string_fields:
        value = case.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{prefix}.{field}: must be a non-empty string")

    notes = case.get("notes")
    if not isinstance(notes, str):
        errors.append(f"{prefix}.notes: must be a string")

    for field in required_list_fields:
        value = case.get(field)
        if not isinstance(value, list):
            errors.append(f"{prefix}.{field}: must be a list")

    area = case.get("area")
    if isinstance(area, str) and area not in ALLOWED_AREAS:
        errors.append(f"{prefix}.area: unsupported value '{area}'")

    status = case.get("status")
    if isinstance(status, str) and status not in ALLOWED_STATUS:
        errors.append(f"{prefix}.status: unsupported value '{status}'")

    actual = case.get("actualResult")
    if actual is not None and (not isinstance(actual, str) or not actual.strip()):
        errors.append(f"{prefix}.actualResult: must be null or non-empty string")

    return errors


def validate_matrix(payload: object, *, require_actual: bool = False) -> list[str]:
    if not isinstance(payload, dict):
        return ["matrix payload must be a JSON object"]

    errors: list[str] = []

    schema = payload.get("schemaVersion")
    if not isinstance(schema, str) or not schema.strip():
        errors.append("schemaVersion: must be a non-empty string")

    generated_at = payload.get("generatedAtUtc")
    if not isinstance(generated_at, str) or not generated_at.strip():
        errors.append("generatedAtUtc: must be a non-empty string")

    targets = payload.get("targets")
    if not isinstance(targets, dict):
        errors.append("targets: must be an object")
    else:
        for key in ("apiBaseUrl", "appBaseUrl"):
            value = targets.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"targets.{key}: must be a non-empty string")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary: must be an object")
    else:
        for key in ("total", "planned", "pass", "fail", "blocked"):
            value = summary.get(key)
            if not isinstance(value, int) or value < 0:
                errors.append(f"summary.{key}: must be a non-negative integer")

    tests = payload.get("tests")
    if not isinstance(tests, list) or not tests:
        errors.append("tests: must be a non-empty list")
        return errors

    for index, test_case in enumerate(tests):
        errors.extend(_validate_test_case(test_case, index))

    if isinstance(summary, dict):
        counts = {key: 0 for key in ALLOWED_STATUS}
        for test_case in tests:
            if isinstance(test_case, dict):
                status = test_case.get("status")
                if isinstance(status, str) and status in ALLOWED_STATUS:
                    counts[status] += 1
        total = len(tests)
        expected_summary = {
            "total": total,
            "planned": counts["planned"],
            "pass": counts["pass"],
            "fail": counts["fail"],
            "blocked": counts["blocked"],
        }
        for key, expected in expected_summary.items():
            if summary.get(key) != expected:
                errors.append(
                    f"summary.{key}: expected {expected} based on tests, got {summary.get(key)!r}"
                )

    if require_actual:
        for index, test_case in enumerate(tests):
            if not isinstance(test_case, dict):
                continue
            actual = test_case.get("actualResult")
            status = test_case.get("status")
            if actual is None:
                errors.append(f"tests[{index}].actualResult: missing while --require-actual is set")
            if status == "planned":
                errors.append(f"tests[{index}].status: must not stay 'planned' with --require-actual")

    return errors


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate or validate the BL-337 internet E2E expected-vs-actual matrix "
            "for API/UI frontdoor checks."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"Output path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL, help=f"API base URL (default: {DEFAULT_API_BASE_URL})")
    parser.add_argument("--app-base-url", default=DEFAULT_APP_BASE_URL, help=f"UI base URL (default: {DEFAULT_APP_BASE_URL})")
    parser.add_argument("--generated-at-utc", default=None, help="Optional fixed UTC timestamp for deterministic output")
    parser.add_argument("--validate", type=Path, default=None, help="Validate an existing matrix JSON file")
    parser.add_argument(
        "--require-actual",
        action="store_true",
        help="Validation mode only: require every test to have non-null actualResult and non-planned status",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    if args.validate is not None:
        path = args.validate
        if not path.exists() or not path.is_file():
            print(f"ERROR: matrix file not found: {path}")
            return 1

        try:
            payload = _load_json(path)
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON in {path}: {exc}")
            return 1

        errors = validate_matrix(payload, require_actual=args.require_actual)
        if errors:
            print("❌ BL-337 matrix validation failed")
            for error in errors:
                print(f"- {error}")
            return 1

        print(f"✅ BL-337 matrix validation passed ({path})")
        return 0

    payload = build_matrix(
        api_base_url=args.api_base_url,
        app_base_url=args.app_base_url,
        generated_at_utc=args.generated_at_utc,
    )
    _write_json(args.output, payload)
    print(f"✅ BL-337 matrix generated: {args.output} ({len(payload['tests'])} test cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
