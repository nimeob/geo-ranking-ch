#!/usr/bin/env python3
"""Validiert docs/api/field_catalog.json gegen Beispielpayloads.

Checks:
1) Manifest-Schema (Pflichtfelder, erlaubte Werte)
2) Alle Leaf-Felder aus den Beispielpayloads sind im Manifest abgedeckt
3) Typen im Manifest passen zu den Beispieldaten
4) Als required markierte Felder sind im jeweiligen Shape vorhanden
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs" / "api" / "field_catalog.json"

EXAMPLES = {
    "legacy": REPO_ROOT
    / "docs"
    / "api"
    / "examples"
    / "v1"
    / "location-intelligence.response.success.address.json",
    "grouped": REPO_ROOT
    / "docs"
    / "api"
    / "examples"
    / "current"
    / "analyze.response.grouped.success.json",
}

ALLOWED_SHAPES = {"legacy", "grouped"}
ALLOWED_TYPES = {"string", "number", "boolean", "object", "array", "null"}
ALLOWED_STABILITY = {"stable", "beta", "internal"}


class ValidationError(Exception):
    pass


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            return "number"
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise ValidationError(f"Unsupported JSON value type: {type(value)!r}")


def _iter_leaf_paths(payload: Any, tokens: list[str] | None = None):
    current = tokens or []

    if isinstance(payload, dict):
        for key, value in payload.items():
            key_token = str(key)
            yield from _iter_leaf_paths(value, [*current, key_token])
        return

    if isinstance(payload, list):
        for item in payload:
            yield from _iter_leaf_paths(item, [*current, "[*]"])
        return

    yield current, _json_type(payload)


def _parse_path(path: str) -> list[str]:
    normalized = path.replace("[*]", ".[*]")
    tokens = [part for part in normalized.split(".") if part]
    if not tokens:
        raise ValidationError(f"Invalid empty path: {path!r}")
    return tokens


def _path_str(tokens: list[str]) -> str:
    return ".".join(tokens)


def _path_matches(pattern: list[str], actual: list[str]) -> bool:
    if len(pattern) != len(actual):
        return False

    for p, a in zip(pattern, actual, strict=True):
        if p == "*":
            if a == "[*]":
                return False
            continue
        if p != a:
            return False
    return True


def _required_for_shape(required_field: Any, shape: str) -> bool:
    if isinstance(required_field, bool):
        return required_field
    if isinstance(required_field, dict):
        value = required_field.get(shape, False)
        if not isinstance(value, bool):
            raise ValidationError(
                f"required[{shape}] must be bool, got: {type(value).__name__}"
            )
        return value
    raise ValidationError("required must be bool or object")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def validate() -> list[str]:
    errors: list[str] = []

    catalog = _load_json(CATALOG_PATH)
    if not isinstance(catalog, dict):
        return ["Catalog must be a JSON object"]

    fields = catalog.get("fields")
    if not isinstance(fields, list) or not fields:
        return ["Catalog must contain non-empty 'fields' array"]

    compiled_entries: list[dict[str, Any]] = []
    seen_path_shape: set[tuple[str, str]] = set()

    for idx, entry in enumerate(fields):
        prefix = f"fields[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: entry must be object")
            continue

        required_keys = {
            "path",
            "response_shapes",
            "type",
            "required",
            "stability",
            "description",
            "provenance_hint",
            "mode_conditions",
            "example",
        }
        missing = required_keys - set(entry.keys())
        if missing:
            errors.append(f"{prefix}: missing keys: {sorted(missing)}")
            continue

        path = entry.get("path")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"{prefix}: path must be non-empty string")
            continue
        try:
            path_tokens = _parse_path(path)
        except ValidationError as exc:
            errors.append(f"{prefix}: {exc}")
            continue

        response_shapes = entry.get("response_shapes")
        if not isinstance(response_shapes, list) or not response_shapes:
            errors.append(f"{prefix}: response_shapes must be non-empty list")
            continue
        if any(shape not in ALLOWED_SHAPES for shape in response_shapes):
            errors.append(
                f"{prefix}: response_shapes contains unsupported value(s): {response_shapes}"
            )
            continue

        field_type = entry.get("type")
        if field_type not in ALLOWED_TYPES:
            errors.append(f"{prefix}: unsupported type {field_type!r}")
            continue

        stability = entry.get("stability")
        if stability not in ALLOWED_STABILITY:
            errors.append(f"{prefix}: unsupported stability {stability!r}")
            continue

        description = entry.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{prefix}: description must be non-empty string")
            continue

        provenance_hint = entry.get("provenance_hint")
        if not isinstance(provenance_hint, str) or not provenance_hint.strip():
            errors.append(f"{prefix}: provenance_hint must be non-empty string")
            continue

        mode_conditions = entry.get("mode_conditions")
        if not isinstance(mode_conditions, list) or not mode_conditions:
            errors.append(f"{prefix}: mode_conditions must be non-empty list")
            continue
        if any(not isinstance(item, str) or not item.strip() for item in mode_conditions):
            errors.append(f"{prefix}: mode_conditions must contain non-empty strings")
            continue

        try:
            _ = _required_for_shape(entry.get("required"), "legacy")
            _ = _required_for_shape(entry.get("required"), "grouped")
        except ValidationError as exc:
            errors.append(f"{prefix}: {exc}")
            continue

        for shape in response_shapes:
            dedupe_key = (path, shape)
            if dedupe_key in seen_path_shape:
                errors.append(f"{prefix}: duplicate path/shape mapping: {path} ({shape})")
            seen_path_shape.add(dedupe_key)

        compiled_entries.append(
            {
                "path": path,
                "tokens": path_tokens,
                "response_shapes": response_shapes,
                "type": field_type,
                "required": entry.get("required"),
            }
        )

    if errors:
        return errors

    example_leafs: dict[str, list[tuple[list[str], str]]] = {}
    for shape, path in EXAMPLES.items():
        payload = _load_json(path)
        leafs = list(_iter_leaf_paths(payload))
        example_leafs[shape] = leafs

    for shape, leafs in example_leafs.items():
        for actual_tokens, actual_type in leafs:
            matches = [
                entry
                for entry in compiled_entries
                if shape in entry["response_shapes"]
                and _path_matches(entry["tokens"], actual_tokens)
            ]
            if not matches:
                errors.append(
                    f"missing manifest field for {shape}: {_path_str(actual_tokens)} ({actual_type})"
                )
                continue

            if not any(entry["type"] == actual_type for entry in matches):
                manifest_types = sorted({entry["type"] for entry in matches})
                errors.append(
                    "type mismatch for "
                    f"{shape}:{_path_str(actual_tokens)} -> example={actual_type}, "
                    f"manifest={manifest_types}"
                )

    for entry in compiled_entries:
        path = entry["path"]
        for shape in ALLOWED_SHAPES:
            if shape not in entry["response_shapes"]:
                continue
            if not _required_for_shape(entry["required"], shape):
                continue

            exists = any(
                _path_matches(entry["tokens"], actual_tokens)
                for actual_tokens, _actual_type in example_leafs[shape]
            )
            if not exists:
                errors.append(
                    f"required manifest field not found in {shape} example: {path}"
                )

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("field_catalog validation FAILED")
        for err in errors:
            print(f"- {err}")
        return 1

    print("field_catalog validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
