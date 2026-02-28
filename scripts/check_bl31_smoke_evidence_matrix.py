#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


VALID_MODES = {"api", "ui", "both"}
VALID_RESULTS = {"planned", "pass", "fail"}
DEFAULT_GLOB_PATTERNS = [
    "artifacts/bl31/*-bl31-split-deploy-api.json",
    "artifacts/bl31/*-bl31-split-deploy-ui.json",
    "artifacts/bl31/*-bl31-split-deploy-both.json",
]


def _parse_required_modes(raw: str) -> set[str]:
    values = {token.strip() for token in raw.split(",") if token.strip()}
    unknown = values - VALID_MODES
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise ValueError(f"unsupported required mode(s): {unknown_list}")
    return values


def _validate_taskdef_snapshot(name: str, snapshot: object, errors: list[str]) -> None:
    if not isinstance(snapshot, dict):
        errors.append(f"{name} must be an object with api/ui fields")
        return

    for key in ("api", "ui"):
        value = snapshot.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name}.{key} must be a non-empty string")


def _validate_payload(payload: object, source: Path) -> tuple[list[str], str | None]:
    errors: list[str] = []

    if not isinstance(payload, dict):
        return ["payload must be a JSON object"], None

    mode = payload.get("mode")
    if not isinstance(mode, str) or mode not in VALID_MODES:
        errors.append("mode must be one of api|ui|both")
        mode = None

    timestamp = payload.get("timestampUtc")
    if not isinstance(timestamp, str) or not timestamp.strip():
        errors.append("timestampUtc must be a non-empty string")

    result = payload.get("result")
    if not isinstance(result, str) or result not in VALID_RESULTS:
        errors.append("result must be one of planned|pass|fail")

    _validate_taskdef_snapshot("taskDefinitionBefore", payload.get("taskDefinitionBefore"), errors)
    _validate_taskdef_snapshot("taskDefinitionAfter", payload.get("taskDefinitionAfter"), errors)

    smoke_artifacts = payload.get("smokeArtifacts")
    if not isinstance(smoke_artifacts, list):
        errors.append("smokeArtifacts must be a list")

    steps = payload.get("steps")
    if not isinstance(steps, list):
        errors.append("steps must be a list")
    elif mode == "both":
        step_order = [step.get("step") for step in steps if isinstance(step, dict)]
        if step_order and step_order != ["api", "ui"]:
            errors.append("both mode must keep step order api -> ui")

    if errors:
        prefixed = [f"{source}: {error}" for error in errors]
        return prefixed, mode

    return [], mode


def _resolve_paths(paths: list[str], glob_pattern: str) -> list[Path]:
    resolved_paths: list[Path] = [Path(path) for path in paths]
    if resolved_paths:
        return resolved_paths

    if glob_pattern:
        return sorted(Path().glob(glob_pattern))

    discovered: list[Path] = []
    for pattern in DEFAULT_GLOB_PATTERNS:
        discovered.extend(sorted(Path().glob(pattern)))

    return sorted(set(discovered))


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate BL-31 split-deploy evidence artifacts for consistent minimum fields "
            "(mode, before/after task definitions, result, timestamp)."
        )
    )
    parser.add_argument("paths", nargs="*", help="Explicit artifact paths to validate")
    parser.add_argument(
        "--glob",
        default="",
        help=(
            "Optional glob pattern used when no explicit paths are provided "
            "(default: artifacts/bl31/*-bl31-split-deploy-{api,ui,both}.json)"
        ),
    )
    parser.add_argument(
        "--require-modes",
        default="api,ui,both",
        help="Comma-separated mode list that must be present at least once (default: api,ui,both)",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    try:
        required_modes = _parse_required_modes(args.require_modes)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    paths = _resolve_paths(args.paths, args.glob)
    if not paths:
        print("ERROR: no BL-31 split-deploy evidence artifacts found")
        return 1

    seen_modes: set[str] = set()
    errors: list[str] = []

    for path in paths:
        if not path.exists() or not path.is_file():
            errors.append(f"{path}: file not found")
            continue

        try:
            payload = _load_json(path)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON ({exc})")
            continue

        payload_errors, mode = _validate_payload(payload, path)
        errors.extend(payload_errors)
        if mode:
            seen_modes.add(mode)

    missing_modes = sorted(required_modes - seen_modes)
    if missing_modes:
        errors.append(f"missing required mode evidence: {', '.join(missing_modes)}")

    if errors:
        print("❌ BL-31 smoke/evidence matrix validation failed")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "✅ BL-31 smoke/evidence matrix validation passed "
        f"({len(paths)} artifact(s), modes: {', '.join(sorted(seen_modes))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
