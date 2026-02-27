#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RequiredArtifact:
    key: str
    description: str
    source_path: Path
    destination_relpath: Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_path(raw: str, *, base: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _safe_relative(path: Path, *, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _extract_target_ids(consumer_inventory_doc: str) -> list[str]:
    target_ids: list[str] = []
    seen: set[str] = set()

    for line in consumer_inventory_doc.splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if not match:
            continue
        target_id = match.group(1).strip()
        if target_id and target_id not in seen:
            seen.add(target_id)
            target_ids.append(target_id)

    return target_ids


def _write_consumer_targets_hint(
    *,
    output_path: Path,
    source_doc_path: Path,
    source_doc_text: str,
    generated_at_utc: str,
) -> list[str]:
    target_ids = _extract_target_ids(source_doc_text)

    lines = [
        "# Consumer-Targets-Hinweis",
        "",
        f"- Generated at (UTC): `{generated_at_utc}`",
        f"- Source: `{source_doc_path}`",
        "",
        "Dieser Hinweis extrahiert bekannte `target_id`s aus der Consumer-Inventory-Doku,",
        "damit externe Reviews die offenen Consumer schnell gegen Evidenzartefakte prüfen können.",
        "",
    ]

    if target_ids:
        lines.append("## Erkannte target_id-Einträge")
        lines.append("")
        for target_id in target_ids:
            lines.append(f"- `{target_id}`")
    else:
        lines.extend(
            [
                "## Hinweis",
                "",
                "Keine `target_id`-Tabelleneinträge automatisch erkannt.",
                "Bitte `docs/LEGACY_CONSUMER_INVENTORY.md` manuell prüfen.",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return target_ids


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Erzeugt ein read-only BL-15 Decommission-Readiness Evidence-Bundle "
            "aus vorhandenen Evidenzartefakten."
        )
    )
    parser.add_argument(
        "--output-root",
        default="reports/bl15_readiness",
        help="Zielbasis für Bundle-Ordner (default: reports/bl15_readiness)",
    )
    parser.add_argument(
        "--bundle-id",
        default="",
        help="Optionaler Bundle-Identifier (default: UTC timestamp, z. B. 20260227T034500Z)",
    )
    parser.add_argument(
        "--fingerprint-report",
        default="artifacts/bl15/legacy-cloudtrail-fingerprint-report.json",
        help="Pfad zum BL-15 Fingerprint-Report JSON (required)",
    )
    parser.add_argument(
        "--consumer-inventory-doc",
        default="docs/LEGACY_CONSUMER_INVENTORY.md",
        help="Pfad zur Consumer-Inventory-Doku (required)",
    )
    parser.add_argument(
        "--readiness-runbook",
        default="docs/LEGACY_IAM_USER_READINESS.md",
        help="Pfad zum BL-15 Readiness-Runbook (required)",
    )
    parser.add_argument(
        "--optional-glob",
        action="append",
        default=[],
        help=(
            "Optionales Glob-Pattern für zusätzliche Evidenzdateien "
            "(repeatable, relativ zum Repo-Root oder absolut)"
        ),
    )

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    generated_at_utc = _utc_now_iso()
    bundle_id = args.bundle_id.strip() or _utc_now_stamp()
    output_root = _resolve_path(args.output_root, base=REPO_ROOT)
    bundle_dir = output_root / bundle_id

    if bundle_dir.exists():
        print(f"ERROR: bundle target already exists: {bundle_dir}", file=sys.stderr)
        return 2

    required_artifacts = [
        RequiredArtifact(
            key="fingerprint_evidence",
            description="CloudTrail fingerprint report (BL-15)",
            source_path=_resolve_path(args.fingerprint_report, base=REPO_ROOT),
            destination_relpath=Path("evidence/fingerprint/legacy-cloudtrail-fingerprint-report.json"),
        ),
        RequiredArtifact(
            key="consumer_inventory_doc",
            description="Consumer target inventory and migration tracking",
            source_path=_resolve_path(args.consumer_inventory_doc, base=REPO_ROOT),
            destination_relpath=Path("evidence/docs/LEGACY_CONSUMER_INVENTORY.md"),
        ),
        RequiredArtifact(
            key="readiness_runbook",
            description="BL-15 readiness runbook",
            source_path=_resolve_path(args.readiness_runbook, base=REPO_ROOT),
            destination_relpath=Path("evidence/docs/LEGACY_IAM_USER_READINESS.md"),
        ),
    ]

    missing_required = [artifact for artifact in required_artifacts if not artifact.source_path.is_file()]
    if missing_required:
        for artifact in missing_required:
            print(
                f"ERROR: required artifact not found ({artifact.key}): {artifact.source_path}",
                file=sys.stderr,
            )
        return 2

    bundle_dir.mkdir(parents=True, exist_ok=False)

    file_inventory: list[dict[str, Any]] = []

    for artifact in required_artifacts:
        destination_path = bundle_dir / artifact.destination_relpath
        _copy_file(artifact.source_path, destination_path)
        file_inventory.append(
            {
                "key": artifact.key,
                "kind": "required",
                "description": artifact.description,
                "source_path": _safe_relative(artifact.source_path, base=REPO_ROOT),
                "bundle_path": str(artifact.destination_relpath),
                "size_bytes": destination_path.stat().st_size,
                "sha256": _sha256(destination_path),
            }
        )

    consumer_doc_text = required_artifacts[1].source_path.read_text(encoding="utf-8")
    consumer_hint_relpath = Path("consumer_targets_hint.md")
    consumer_hint_path = bundle_dir / consumer_hint_relpath
    target_ids = _write_consumer_targets_hint(
        output_path=consumer_hint_path,
        source_doc_path=required_artifacts[1].source_path,
        source_doc_text=consumer_doc_text,
        generated_at_utc=generated_at_utc,
    )
    file_inventory.append(
        {
            "key": "consumer_targets_hint",
            "kind": "generated",
            "description": "Extracted target_id hint for external consumer review",
            "source_path": _safe_relative(required_artifacts[1].source_path, base=REPO_ROOT),
            "bundle_path": str(consumer_hint_relpath),
            "size_bytes": consumer_hint_path.stat().st_size,
            "sha256": _sha256(consumer_hint_path),
        }
    )

    optional_patterns = args.optional_glob or ["artifacts/bl17/*.json"]
    optional_matches: list[Path] = []
    seen_optional: set[Path] = set()

    for pattern in optional_patterns:
        resolved_pattern = pattern
        if not Path(pattern).is_absolute():
            resolved_pattern = str((REPO_ROOT / pattern).resolve())

        for match in sorted(Path(path).resolve() for path in glob.glob(resolved_pattern)):
            if not match.is_file() or match in seen_optional:
                continue
            seen_optional.add(match)
            optional_matches.append(match)

    for optional_file in optional_matches:
        relative_name = optional_file.name
        destination_relpath = Path("evidence/optional") / relative_name
        destination_path = bundle_dir / destination_relpath
        _copy_file(optional_file, destination_path)

        file_inventory.append(
            {
                "key": f"optional::{relative_name}",
                "kind": "optional",
                "description": "Additional read-only evidence artifact",
                "source_path": _safe_relative(optional_file, base=REPO_ROOT),
                "bundle_path": str(destination_relpath),
                "size_bytes": destination_path.stat().st_size,
                "sha256": _sha256(destination_path),
            }
        )

    inventory_relpath = Path("inventory.json")
    inventory_path = bundle_dir / inventory_relpath
    inventory_payload = {
        "version": 1,
        "bundle_id": bundle_id,
        "generated_at_utc": generated_at_utc,
        "bundle_root": str(bundle_dir),
        "checks": {
            "inventory_present": True,
            "fingerprint_evidence_present": any(item["key"] == "fingerprint_evidence" for item in file_inventory),
            "consumer_targets_hint_present": True,
        },
        "consumer_target_ids": target_ids,
        "files": file_inventory,
    }
    inventory_path.write_text(json.dumps(inventory_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    file_inventory.append(
        {
            "key": "inventory",
            "kind": "generated",
            "description": "Bundle manifest and verification index",
            "source_path": "generated",
            "bundle_path": str(inventory_relpath),
            "size_bytes": inventory_path.stat().st_size,
            "sha256": _sha256(inventory_path),
        }
    )

    readme_relpath = Path("README.md")
    readme_path = bundle_dir / readme_relpath
    readme_lines = [
        "# BL-15 Decommission-Readiness Evidence Bundle",
        "",
        f"- Bundle ID: `{bundle_id}`",
        f"- Generated at (UTC): `{generated_at_utc}`",
        f"- Source repository root: `{REPO_ROOT}`",
        "",
        "## Inhalt",
        "",
        "Dieses Bundle bündelt read-only Evidenz für externe Decommission-Reviews. "
        "Es enthält mindestens:",
        "",
        "- Fingerprint-Evidenz (CloudTrail)",
        "- Consumer-Targets-Hinweis",
        "- Inventory/Manifest mit Prüfsummen",
        "",
        "## Artefakte",
        "",
    ]

    for item in file_inventory:
        readme_lines.append(
            f"- `{item['bundle_path']}` ({item['kind']}): {item['description']} "
            f"[sha256: `{item['sha256']}`]"
        )

    readme_lines.extend(
        [
            "",
            "## Kurzinterpretation",
            "",
            "- `evidence/fingerprint/...`: zeigt beobachtete Legacy-Caller-Fingerprints im Lookback-Fenster.",
            "- `consumer_targets_hint.md`: extrahierte `target_id`s als schneller Einstieg für offene externe Consumer.",
            "- `inventory.json`: maschinenlesbare Dateiliste inklusive Prüfsummen.",
        ]
    )

    readme_path.write_text("\n".join(readme_lines).rstrip() + "\n", encoding="utf-8")

    summary = {
        "status": "ok",
        "bundle_id": bundle_id,
        "bundle_path": str(bundle_dir),
        "generated_at_utc": generated_at_utc,
        "required_artifact_count": len(required_artifacts),
        "optional_artifact_count": len(optional_matches),
        "consumer_target_count": len(target_ids),
        "inventory_file": str(inventory_relpath),
    }

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
