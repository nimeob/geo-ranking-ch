#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set


API_SERVICE_MODULES: Set[str] = {
    "web_service",
    "address_intel",
    "personalized_scoring",
    "suitability_light",
}

UI_SERVICE_MODULES: Set[str] = {
    "ui_service",
}

# Shared modules are explicitly allowed to be imported by API and UI modules.
# They must remain neutral and may not import API/UI service-specific modules.
SHARED_MODULES: Set[str] = {
    "gui_mvp",
    "geo_utils",
    "gwr_codes",
    "mapping_transform_rules",
}


def _normalize_local_module(import_name: str, local_modules: Set[str]) -> str | None:
    """Map an import name to a local src module stem when possible."""
    if import_name.startswith("src."):
        candidate = import_name.split(".", 1)[1].split(".", 1)[0]
    else:
        candidate = import_name.split(".", 1)[0]

    if candidate in local_modules:
        return candidate
    return None


def _collect_local_imports(file_path: Path, local_modules: Set[str]) -> Set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    imports: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = _normalize_local_module(alias.name, local_modules)
                if module:
                    imports.add(module)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = _normalize_local_module(node.module, local_modules)
                if module:
                    imports.add(module)
                continue

            # Relative import like `from . import foo`
            for alias in node.names:
                module = _normalize_local_module(alias.name, local_modules)
                if module:
                    imports.add(module)

    return imports


def _service_group(module: str) -> str:
    if module in API_SERVICE_MODULES:
        return "api"
    if module in UI_SERVICE_MODULES:
        return "ui"
    if module in SHARED_MODULES:
        return "shared"
    return "neutral"


def analyze_service_boundaries(src_dir: Path) -> List[str]:
    if not src_dir.exists() or not src_dir.is_dir():
        return [f"src directory not found: {src_dir}"]

    py_files = sorted(p for p in src_dir.glob("*.py") if p.name != "__init__.py")
    local_modules = {p.stem for p in py_files}

    expected_modules = API_SERVICE_MODULES | UI_SERVICE_MODULES | SHARED_MODULES
    missing_modules = sorted(m for m in expected_modules if m not in local_modules)
    violations: List[str] = []

    if missing_modules:
        violations.append(
            "Policy modules missing in src/: " + ", ".join(missing_modules)
        )

    import_graph: Dict[str, Set[str]] = {}
    for py_file in py_files:
        import_graph[py_file.stem] = _collect_local_imports(py_file, local_modules)

    for importer, dependencies in sorted(import_graph.items()):
        importer_group = _service_group(importer)
        for dependency in sorted(dependencies):
            dependency_group = _service_group(dependency)

            if importer_group == "api" and dependency_group == "ui":
                violations.append(
                    f"API module '{importer}' must not import UI module '{dependency}'"
                )
            elif importer_group == "ui" and dependency_group == "api":
                violations.append(
                    f"UI module '{importer}' must not import API module '{dependency}'"
                )
            elif importer_group == "shared" and dependency_group in {"api", "ui"}:
                violations.append(
                    f"Shared module '{importer}' must remain neutral and not import {dependency_group.upper()} module '{dependency}'"
                )

    return violations


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "BL-31 service-boundary guard: validates API/UI split and shared-module neutrality."
        )
    )
    parser.add_argument(
        "--src-dir",
        default="src",
        help="Path to source directory containing Python modules (default: src)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    src_dir = Path(args.src_dir)
    violations = analyze_service_boundaries(src_dir)
    ok = len(violations) == 0

    if args.format == "json":
        payload = {
            "ok": ok,
            "src_dir": str(src_dir),
            "violations": violations,
            "policy": {
                "api_modules": sorted(API_SERVICE_MODULES),
                "ui_modules": sorted(UI_SERVICE_MODULES),
                "shared_modules": sorted(SHARED_MODULES),
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if ok:
            print("✅ BL-31 service-boundary check passed")
        else:
            print("❌ BL-31 service-boundary check failed")
            for violation in violations:
                print(f"- {violation}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
