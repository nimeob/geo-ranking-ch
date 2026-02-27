#!/usr/bin/env python3
"""Read-only Schema-Drift-Check für BL-20.2.b.r3 (#65).

Der Check vergleicht die in `docs/mapping/source-field-mapping.ch.v1.json`
dokumentierten Quellfelder mit aktuellen (oder repräsentativen) Source-Samples.

Standardmäßig werden die drei Pflichtquellen geprüft:
- geoadmin_search
- geoadmin_gwr
- bfs_heating_layer
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC_PATH = REPO_ROOT / "docs" / "mapping" / "source-field-mapping.ch.v1.json"
DEFAULT_SAMPLES_PATH = REPO_ROOT / "tests" / "data" / "mapping" / "source_schema_samples.ch.v1.json"
DEFAULT_REQUIRED_SOURCES = ("geoadmin_search", "geoadmin_gwr", "bfs_heating_layer")


class DriftCheckError(Exception):
    pass


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DriftCheckError(f"Datei fehlt: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DriftCheckError(f"Ungültiges JSON in {path}: {exc}") from exc


def _extract_source_mapping(spec: dict[str, Any], source_name: str) -> dict[str, Any] | None:
    sources = spec.get("sources")
    if not isinstance(sources, list):
        return None

    for source_entry in sources:
        if not isinstance(source_entry, dict):
            continue
        if source_entry.get("source") == source_name:
            return source_entry
    return None


def _expand_source_field_expression(source_field: str) -> list[str]:
    return [token.strip() for token in str(source_field).split("/") if token.strip()]


def _check_path_exists(payload: Any, dotted_path: str) -> tuple[bool, str]:
    segments = [segment for segment in dotted_path.split(".") if segment]

    def walk(node: Any, rest: list[str], prefix: str) -> tuple[bool, str]:
        if not rest:
            return True, ""

        segment = rest[0]
        is_array = segment.endswith("[]")
        key = segment[:-2] if is_array else segment

        if not isinstance(node, dict):
            return False, (
                f"expected object at '{prefix or '<root>'}', got {type(node).__name__}"
            )

        if key not in node:
            return False, f"missing key '{key}' at '{prefix or '<root>'}'"

        value = node[key]

        if is_array:
            if not isinstance(value, list):
                return False, f"expected list at '{prefix + key}', got {type(value).__name__}"
            if not value:
                return False, f"expected non-empty list at '{prefix + key}'"

            next_rest = rest[1:]
            reasons: list[str] = []
            for idx, item in enumerate(value):
                ok, reason = walk(item, next_rest, f"{prefix}{key}[{idx}].")
                if ok:
                    return True, ""
                reasons.append(reason)

            collapsed_reasons = "; ".join(dict.fromkeys(reasons))
            return False, (
                f"no element under '{prefix + key}' satisfied remainder '{'.'.join(next_rest)}'"
                + (f" ({collapsed_reasons})" if collapsed_reasons else "")
            )

        return walk(value, rest[1:], f"{prefix}{key}.")

    return walk(payload, segments, "")


def check_drift(
    *, spec_path: Path, samples_path: Path, required_sources: tuple[str, ...]
) -> list[str]:
    errors: list[str] = []

    spec = _load_json(spec_path)
    samples = _load_json(samples_path)

    if not isinstance(spec, dict):
        raise DriftCheckError("Mapping-Spezifikation muss ein JSON-Objekt sein")
    if not isinstance(samples, dict):
        raise DriftCheckError("Samples-Datei muss ein JSON-Objekt sein (source -> payload)")

    for source_name in required_sources:
        source_entry = _extract_source_mapping(spec, source_name)
        if source_entry is None:
            errors.append(
                f"source={source_name}: fehlt in Mapping-Spezifikation ({spec_path.relative_to(REPO_ROOT)})"
            )
            continue

        if source_name not in samples:
            errors.append(
                f"source={source_name}: fehlt in Samples-Datei ({samples_path.relative_to(REPO_ROOT)})"
            )
            continue

        payload = samples[source_name]
        mappings = source_entry.get("mappings")
        if not isinstance(mappings, list) or not mappings:
            errors.append(f"source={source_name}: mappings fehlen oder sind leer")
            continue

        for mapping in mappings:
            if not isinstance(mapping, dict):
                errors.append(f"source={source_name}: ungültiger mapping-Eintrag (kein Objekt)")
                continue

            source_field = mapping.get("source_field")
            if not isinstance(source_field, str) or not source_field.strip():
                errors.append(f"source={source_name}: mapping ohne gültiges source_field")
                continue

            for expected_path in _expand_source_field_expression(source_field):
                ok, reason = _check_path_exists(payload, expected_path)
                if not ok:
                    errors.append(
                        "source="
                        + source_name
                        + f": missing/renamed field '{expected_path}' (spec source_field='{source_field}'): {reason}"
                    )

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Check: vergleicht erwartete Mapping-Felder mit Source-Samples "
            "und meldet Schema-Drift reproduzierbar."
        )
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=DEFAULT_SPEC_PATH,
        help=f"Pfad zur Mapping-Spezifikation (Default: {DEFAULT_SPEC_PATH})",
    )
    parser.add_argument(
        "--samples",
        type=Path,
        default=DEFAULT_SAMPLES_PATH,
        help=f"Pfad zur Samples-Datei (Default: {DEFAULT_SAMPLES_PATH})",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Optional mehrfach: nur diese Source(s) prüfen",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    required_sources = tuple(args.source) if args.source else DEFAULT_REQUIRED_SOURCES

    try:
        errors = check_drift(
            spec_path=args.spec.resolve(),
            samples_path=args.samples.resolve(),
            required_sources=required_sources,
        )
    except DriftCheckError as exc:
        print(f"source-field-mapping drift check FAILED\n- {exc}")
        return 1

    if errors:
        print("source-field-mapping drift check FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "source-field-mapping drift check OK"
        + f" (sources={', '.join(required_sources)}, samples={args.samples})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
