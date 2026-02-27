#!/usr/bin/env python3
"""Validiert die machine-readable Feldmapping-Spezifikation aus BL-20.2.b (#63).

Checks:
1) Schema-Datei vorhanden + erwartete Kernstruktur
2) Mapping-Datei vorhanden + required top-level fields
3) Transform-Regeln konsistent (unique IDs, Referenzen aufgelöst)
4) Sources/Mappings strukturell gültig
5) Mindestabdeckung der Kernquellen (geoadmin_search/geoadmin_gwr/bfs_heating_layer)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "docs" / "mapping" / "source-field-mapping.schema.json"
MAPPING_PATH = REPO_ROOT / "docs" / "mapping" / "source-field-mapping.ch.v1.json"

EXPECTED_REQUIRED_TOPLEVEL = {
    "spec_version",
    "spec_name",
    "generated_from",
    "updated_at",
    "transform_rules",
    "sources",
}
REQUIRED_SOURCES = {"geoadmin_search", "geoadmin_gwr", "bfs_heating_layer"}


class ValidationError(Exception):
    pass


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"Datei fehlt: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Ungültiges JSON in {path}: {exc}") from exc


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate() -> list[str]:
    errors: list[str] = []

    try:
        schema = _load_json(SCHEMA_PATH)
    except ValidationError as exc:
        return [str(exc)]

    try:
        spec = _load_json(MAPPING_PATH)
    except ValidationError as exc:
        return [str(exc)]

    if not isinstance(schema, dict):
        return ["Schema muss ein JSON-Objekt sein"]
    if not isinstance(spec, dict):
        return ["Mapping-Spezifikation muss ein JSON-Objekt sein"]

    schema_required = schema.get("required")
    if not isinstance(schema_required, list):
        errors.append("Schema: required muss eine Liste sein")
    else:
        required_set = set(schema_required)
        if required_set != EXPECTED_REQUIRED_TOPLEVEL:
            errors.append(
                "Schema: required-Felder unerwartet. "
                f"Erwartet={sorted(EXPECTED_REQUIRED_TOPLEVEL)}, erhalten={sorted(required_set)}"
            )

    schema_defs = schema.get("$defs")
    if not isinstance(schema_defs, dict):
        errors.append("Schema: $defs fehlt oder ist kein Objekt")
    else:
        for required_def in ("transformRule", "mappingEntry", "sourceMapping"):
            if required_def not in schema_defs:
                errors.append(f"Schema: $defs.{required_def} fehlt")

    missing_toplevel = EXPECTED_REQUIRED_TOPLEVEL - set(spec.keys())
    if missing_toplevel:
        errors.append(f"Spec: fehlende Top-Level-Felder: {sorted(missing_toplevel)}")

    if not _is_non_empty_string(spec.get("spec_version")):
        errors.append("Spec: spec_version muss non-empty string sein")
    elif not str(spec["spec_version"]).startswith("v"):
        errors.append("Spec: spec_version muss mit 'v' beginnen")

    if not _is_non_empty_string(spec.get("spec_name")):
        errors.append("Spec: spec_name muss non-empty string sein")

    generated_from = spec.get("generated_from")
    if not _is_non_empty_string(generated_from):
        errors.append("Spec: generated_from muss non-empty string sein")
    else:
        generated_path = (REPO_ROOT / str(generated_from)).resolve()
        if not generated_path.is_file():
            errors.append(f"Spec: generated_from verweist auf fehlende Datei: {generated_from}")

    updated_at = spec.get("updated_at")
    if not _is_non_empty_string(updated_at):
        errors.append("Spec: updated_at muss non-empty string sein")
    else:
        try:
            datetime.strptime(str(updated_at), "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append("Spec: updated_at muss ISO-8601 UTC Format YYYY-MM-DDTHH:MM:SSZ haben")

    transform_rules = spec.get("transform_rules")
    transform_ids: set[str] = set()
    if not isinstance(transform_rules, list) or not transform_rules:
        errors.append("Spec: transform_rules muss non-empty Liste sein")
    else:
        for idx, rule in enumerate(transform_rules):
            prefix = f"transform_rules[{idx}]"
            if not isinstance(rule, dict):
                errors.append(f"{prefix}: muss Objekt sein")
                continue

            rule_id = rule.get("id")
            if not _is_non_empty_string(rule_id):
                errors.append(f"{prefix}.id: muss non-empty string sein")
                continue
            if not str(rule_id).startswith("TR-"):
                errors.append(f"{prefix}.id: muss mit 'TR-' beginnen")
            if rule_id in transform_ids:
                errors.append(f"{prefix}.id: doppelte ID {rule_id}")
            transform_ids.add(str(rule_id))

            if not _is_non_empty_string(rule.get("name")):
                errors.append(f"{prefix}.name: muss non-empty string sein")
            if not _is_non_empty_string(rule.get("description")):
                errors.append(f"{prefix}.description: muss non-empty string sein")

    sources = spec.get("sources")
    seen_sources: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append("Spec: sources muss non-empty Liste sein")
    else:
        for source_idx, source in enumerate(sources):
            source_prefix = f"sources[{source_idx}]"
            if not isinstance(source, dict):
                errors.append(f"{source_prefix}: muss Objekt sein")
                continue

            source_name = source.get("source")
            if not _is_non_empty_string(source_name):
                errors.append(f"{source_prefix}.source: muss non-empty string sein")
                continue
            source_name = str(source_name)
            if source_name in seen_sources:
                errors.append(f"{source_prefix}.source: doppelte Quelle {source_name}")
            seen_sources.add(source_name)

            mappings = source.get("mappings")
            if not isinstance(mappings, list) or not mappings:
                errors.append(f"{source_prefix}.mappings: muss non-empty Liste sein")
                continue

            for mapping_idx, mapping in enumerate(mappings):
                map_prefix = f"{source_prefix}.mappings[{mapping_idx}]"
                if not isinstance(mapping, dict):
                    errors.append(f"{map_prefix}: muss Objekt sein")
                    continue

                if not _is_non_empty_string(mapping.get("source_field")):
                    errors.append(f"{map_prefix}.source_field: muss non-empty string sein")

                target_paths = mapping.get("target_paths")
                if not isinstance(target_paths, list) or not target_paths:
                    errors.append(f"{map_prefix}.target_paths: muss non-empty Liste sein")
                else:
                    for target_idx, target_path in enumerate(target_paths):
                        if not _is_non_empty_string(target_path):
                            errors.append(
                                f"{map_prefix}.target_paths[{target_idx}]: muss non-empty string sein"
                            )

                transforms = mapping.get("transforms")
                if not isinstance(transforms, list) or not transforms:
                    errors.append(f"{map_prefix}.transforms: muss non-empty Liste sein")
                else:
                    for tr_idx, transform_id in enumerate(transforms):
                        if not _is_non_empty_string(transform_id):
                            errors.append(
                                f"{map_prefix}.transforms[{tr_idx}]: muss non-empty string sein"
                            )
                            continue
                        if transform_ids and str(transform_id) not in transform_ids:
                            errors.append(
                                f"{map_prefix}.transforms[{tr_idx}]: unbekannte Regel-ID {transform_id}"
                            )

    if sources and isinstance(sources, list):
        available_sources = {
            source.get("source")
            for source in sources
            if isinstance(source, dict) and _is_non_empty_string(source.get("source"))
        }
        missing_sources = REQUIRED_SOURCES - set(available_sources)
        if missing_sources:
            errors.append(
                "Spec: Pflichtquellen fehlen: "
                + ", ".join(sorted(str(item) for item in missing_sources))
            )

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("source-field-mapping validation FAILED")
        for err in errors:
            print(f"- {err}")
        return 1

    print("source-field-mapping validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
