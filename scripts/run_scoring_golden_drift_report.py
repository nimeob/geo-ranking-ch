#!/usr/bin/env python3
"""Golden-Run + Drift-Report für Scoring-Referenzartefakte.

Motivation (Parent #649 / WP #713):
- Golden-Referenzfälle sind unter `docs/api/examples/scoring/` versioniert.
- Bei Änderungen an Scoring-Logik soll Drift nicht nur als Test-Fail sichtbar sein,
  sondern als Report (pro Case: Input, Expected vs Actual, Komponenten-Snapshot).

Scope (bewusst klein / deterministisch):
- Worked Examples (`worked-example-*.input.json`): Confidence-Formel aus
  `docs/api/scoring_methodology.md` wird reproduzierbar berechnet.
- Runtime-Personalisierung (`personalized-golden-*.input.json`):
  `compute_two_stage_scores` wird gegen die versionierten `engine_output` Artefakte
  geprüft und mit diff-freundlichem Komponenten-Snapshot versehen.

Out of scope:
- Explainability-v2 E2E Artefakte (`docs/api/examples/explainability/*`):
  diese sind illustrative Beispiele; es gibt aktuell kein runtime-nahes Generator-API,
  daher werden sie hier nicht ausgeführt.

Exit codes:
- 0: report erzeugt (und optional: kein Drift, wenn `--fail-on-drift` aktiv)
- 1: Drift gefunden und `--fail-on-drift` aktiv
- 2: harte Fehler (IO/JSON/Unexpected schema)
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import difflib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.personalized_scoring import compute_two_stage_scores


SCORING_EXAMPLES_DIR = REPO_ROOT / "docs" / "api" / "examples" / "scoring"
DEFAULT_OUT_DIR = REPO_ROOT / "reports" / "scoring" / "golden_drift"


class ReportError(Exception):
    pass


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReportError(f"Datei fehlt: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(f"Ungültiges JSON in {path}: {exc}") from exc


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return parsed


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _confidence_level(score: int) -> str:
    if score >= 82:
        return "high"
    if score >= 62:
        return "medium"
    return "low"


def _run_worked_example_case(input_payload: Mapping[str, Any]) -> dict[str, Any]:
    inputs = input_payload.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ReportError("worked-example input muss object 'inputs' enthalten")

    selected_score = _finite(inputs.get("match_selected_score"), 0.0)
    match_component_points = selected_score * 40.0

    score_raw = (
        match_component_points
        + _finite(inputs.get("data_completeness_points"), 0.0)
        + _finite(inputs.get("cross_source_consistency_points"), 0.0)
        + _finite(inputs.get("required_source_health_points"), 0.0)
        - _finite(inputs.get("mismatch_penalty_points"), 0.0)
        - _finite(inputs.get("ambiguity_penalty_points"), 0.0)
    )

    score_rounded = int(_clamp(round(score_raw), 0, 100))
    legacy_confidence = round(score_rounded / 100.0, 2)

    return {
        "calculation": {
            "match_component_points": round(match_component_points, 6),
            "score_raw": round(score_raw, 6),
            "score_rounded": score_rounded,
            "score_max": 100,
            "level": _confidence_level(score_rounded),
            "legacy_confidence": legacy_confidence,
        }
    }


def _engine_components_snapshot(*, factors: Sequence[Mapping[str, Any]], engine_output: Mapping[str, Any]):
    """Diff-freundlicher Snapshot (weights + contributions)."""

    weights = engine_output.get("weights") if isinstance(engine_output, Mapping) else {}
    base_weights = (weights or {}).get("base") or {}
    personalized_weights = (weights or {}).get("personalized") or {}
    delta_weights = (weights or {}).get("delta") or {}

    rows: list[dict[str, Any]] = []

    for raw in sorted((factors or []), key=lambda item: str((item or {}).get("key", ""))):
        if not isinstance(raw, Mapping):
            continue
        key = str(raw.get("key") or "").strip()
        if not key:
            continue
        score = _finite(raw.get("score"), 0.0)
        fallback_weight = max(0.0, _finite(raw.get("weight"), 0.0))

        def _get_weight(mapping: Any, fallback: float) -> float:
            if not isinstance(mapping, Mapping):
                return float(fallback)
            return _finite(mapping.get(key, fallback), float(fallback))

        base_w = _get_weight(base_weights, fallback_weight)
        pers_w = _get_weight(personalized_weights, base_w)
        delta = _get_weight(delta_weights, 0.0)

        rows.append(
            {
                "key": key,
                "score": round(score, 4),
                "base_weight": round(base_w, 6),
                "personalized_weight": round(pers_w, 6),
                "delta": round(delta, 6),
                "base_contribution": round(score * base_w, 4),
                "personalized_contribution": round(score * pers_w, 4),
            }
        )

    snapshot = {
        "totals": {
            "base_total_weight": round(sum(row["base_weight"] for row in rows), 6),
            "personalized_total_weight": round(
                sum(row["personalized_weight"] for row in rows),
                6,
            ),
            "base_score": engine_output.get("base_score"),
            "personalized_score": engine_output.get("personalized_score"),
            "fallback_applied": engine_output.get("fallback_applied"),
            "signal_strength": engine_output.get("signal_strength"),
        },
        "factors": rows,
    }

    return snapshot


def _run_personalized_runtime_case(input_payload: Mapping[str, Any]) -> dict[str, Any]:
    factors = input_payload.get("factors")
    if not isinstance(factors, list):
        raise ReportError("personalized-golden input muss list 'factors' enthalten")

    preferences = input_payload.get("preferences")
    if preferences is not None and not isinstance(preferences, Mapping):
        raise ReportError("personalized-golden input: 'preferences' muss object sein")

    engine_output = compute_two_stage_scores(factors, preferences)

    return {
        "engine_output": engine_output,
        "components_snapshot": _engine_components_snapshot(
            factors=factors,
            engine_output=engine_output,
        ),
    }


@dataclasses.dataclass(frozen=True)
class GoldenCase:
    case_id: str
    input_path: Path
    expected_path: Path


def _discover_cases(*, examples_dir: Path) -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    for input_path in sorted(examples_dir.glob("*.input.json")):
        case_id = input_path.name[: -len(".input.json")]
        expected_path = input_path.with_name(f"{case_id}.output.json")
        if not expected_path.exists():
            # Nicht hart failen: drift report soll auch bei unvollständigen Paaren laufen.
            continue
        cases.append(GoldenCase(case_id=case_id, input_path=input_path, expected_path=expected_path))
    return sorted(cases, key=lambda c: c.case_id)


def _case_kind(input_payload: Mapping[str, Any], case_id: str) -> str:
    if isinstance(input_payload.get("inputs"), Mapping) and case_id.startswith("worked-example-"):
        return "worked-example"
    if isinstance(input_payload.get("factors"), list) and case_id.startswith("personalized-golden-"):
        return "personalized-runtime"
    return "unknown"


def _compare_numeric(a: Any, b: Any, tol: float = 1e-9) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tol
    return a == b


def _diff_json(expected: Any, actual: Any, *, title: str) -> str | None:
    expected_lines = _stable_json(expected).splitlines()
    actual_lines = _stable_json(actual).splitlines()
    if expected_lines == actual_lines:
        return None
    return "\n".join(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile=f"expected: {title}",
            tofile=f"actual: {title}",
            lineterm="",
        )
    )


def _summarize_worked_example(expected_payload: Mapping[str, Any], actual_payload: Mapping[str, Any]) -> dict[str, Any]:
    expected_calc = expected_payload.get("calculation") if isinstance(expected_payload.get("calculation"), Mapping) else {}
    actual_calc = actual_payload.get("calculation") if isinstance(actual_payload.get("calculation"), Mapping) else {}

    expected_score = expected_calc.get("score_rounded")
    actual_score = actual_calc.get("score_rounded")

    drift = expected_score != actual_score

    return {
        "expected_score": expected_score,
        "actual_score": actual_score,
        "delta": (None if expected_score is None or actual_score is None else int(actual_score) - int(expected_score)),
        "drift": drift,
    }


def _summarize_personalized(expected_payload: Mapping[str, Any], actual_payload: Mapping[str, Any]) -> dict[str, Any]:
    expected_engine = expected_payload.get("engine_output") if isinstance(expected_payload.get("engine_output"), Mapping) else {}
    actual_engine = actual_payload.get("engine_output") if isinstance(actual_payload.get("engine_output"), Mapping) else {}

    keys = ["base_score", "personalized_score", "fallback_applied", "signal_strength"]
    drift_fields: list[str] = []
    for key in keys:
        if not _compare_numeric(expected_engine.get(key), actual_engine.get(key), tol=1e-6):
            drift_fields.append(key)

    drift = bool(drift_fields)

    expected_snapshot = actual_payload.get("expected_components_snapshot")
    actual_snapshot = actual_payload.get("components_snapshot")
    snapshot_diff = None
    if isinstance(expected_snapshot, Mapping) and isinstance(actual_snapshot, Mapping):
        snapshot_diff = _diff_json(expected_snapshot, actual_snapshot, title="components_snapshot")

    return {
        "drift": drift,
        "drift_fields": drift_fields,
        "snapshot_diff": snapshot_diff,
        "expected": {k: expected_engine.get(k) for k in keys},
        "actual": {k: actual_engine.get(k) for k in keys},
    }


def _render_markdown(report: Mapping[str, Any]) -> str:
    generated_at = report.get("generated_at")
    cases = report.get("cases") if isinstance(report.get("cases"), list) else []

    drift_cases = [case for case in cases if isinstance(case, Mapping) and case.get("summary", {}).get("drift")]

    lines: list[str] = []
    lines.append("# Scoring Golden Drift Report")
    lines.append("")
    lines.append(f"Generated at: `{generated_at}`")
    lines.append(f"Cases: **{len(cases)}**")
    lines.append(f"Drift cases: **{len(drift_cases)}**")

    if drift_cases:
        lines.append("")
        lines.append("## Drift Overview")
        for case in drift_cases:
            lines.append(f"- **{case.get('case_id')}** ({case.get('kind')})")

    for case in cases:
        if not isinstance(case, Mapping):
            continue
        lines.append("")
        lines.append(f"## {case.get('case_id')} ({case.get('kind')})")

        summary = case.get("summary") if isinstance(case.get("summary"), Mapping) else {}
        if summary:
            lines.append(f"- drift: **{summary.get('drift')}**")
            if "expected_score" in summary:
                lines.append(f"- expected_score: `{summary.get('expected_score')}`")
                lines.append(f"- actual_score: `{summary.get('actual_score')}`")
                lines.append(f"- delta: `{summary.get('delta')}`")
            if "drift_fields" in summary and summary.get("drift_fields"):
                lines.append(f"- drift_fields: `{', '.join(summary.get('drift_fields') or [])}`")

        details = case.get("details") if isinstance(case.get("details"), Mapping) else {}
        diff = details.get("snapshot_diff") if isinstance(details, Mapping) else None
        if diff:
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>components snapshot diff</summary>")
            lines.append("")
            lines.append("```diff")
            lines.append(str(diff).rstrip())
            lines.append("```")
            lines.append("</details>")

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Runs scoring golden cases and produces a drift report (JSON + Markdown). "
            "See docs/api/examples/scoring/* for the reference artifacts."
        )
    )
    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=SCORING_EXAMPLES_DIR,
        help=f"Pfad zu Scoring-Examples (default: {SCORING_EXAMPLES_DIR})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--format",
        choices=("json", "md", "both"),
        default="both",
        help="Which report formats to emit",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Optional mehrfach: nur Cases matchen (substring in case_id)",
    )
    parser.add_argument(
        "--fail-on-drift",
        dest="fail_on_drift",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exit 1 if drift detected (default: true)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    generated_at = _dt.datetime.now(tz=_dt.timezone.utc)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")

    try:
        cases = _discover_cases(examples_dir=args.examples_dir.resolve())
        if args.case:
            needles = [token.strip() for token in args.case if token and token.strip()]
            cases = [case for case in cases if any(needle in case.case_id for needle in needles)]

        results: list[dict[str, Any]] = []
        drift_found = False

        for case in cases:
            input_payload = _load_json(case.input_path)
            expected_payload = _load_json(case.expected_path)

            if not isinstance(input_payload, Mapping) or not isinstance(expected_payload, Mapping):
                raise ReportError(f"Case {case.case_id}: input/output must be JSON objects")

            kind = _case_kind(input_payload, case.case_id)
            if kind == "unknown":
                continue

            actual_payload: dict[str, Any]
            summary: dict[str, Any]
            details: dict[str, Any] = {}

            if kind == "worked-example":
                actual_payload = _run_worked_example_case(input_payload)
                summary = _summarize_worked_example(expected_payload, actual_payload)
            elif kind == "personalized-runtime":
                actual_payload = _run_personalized_runtime_case(input_payload)

                # Expected snapshot wird aus expected engine_output berechnet, damit Drift-Diffs sichtbar werden.
                expected_engine = expected_payload.get("engine_output")
                if isinstance(expected_engine, Mapping):
                    actual_payload["expected_components_snapshot"] = _engine_components_snapshot(
                        factors=input_payload.get("factors") or [],
                        engine_output=expected_engine,
                    )

                summary = _summarize_personalized(expected_payload, actual_payload)
                details = {
                    "snapshot_diff": summary.get("snapshot_diff"),
                }
            else:
                continue

            if summary.get("drift"):
                drift_found = True

            results.append(
                {
                    "case_id": case.case_id,
                    "kind": kind,
                    "input_path": str(case.input_path.relative_to(REPO_ROOT)),
                    "expected_path": str(case.expected_path.relative_to(REPO_ROOT)),
                    "input": input_payload,
                    "expected": expected_payload,
                    "actual": actual_payload,
                    "summary": summary,
                    "details": details,
                }
            )

        report: dict[str, Any] = {
            "generated_at": generated_at.isoformat(),
            "repo": "nimeob/geo-ranking-ch",
            "cases": results,
        }

        out_dir = args.out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        if args.format in ("json", "both"):
            json_path = out_dir / f"scoring_golden_drift_report.{stamp}.json"
            json_path.write_text(_stable_json(report) + "\n", encoding="utf-8")

        if args.format in ("md", "both"):
            md_path = out_dir / f"scoring_golden_drift_report.{stamp}.md"
            md_path.write_text(_render_markdown(report), encoding="utf-8")

        if drift_found and args.fail_on_drift:
            return 1

        return 0

    except ReportError as exc:
        print(f"scoring golden drift report FAILED\n- {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
