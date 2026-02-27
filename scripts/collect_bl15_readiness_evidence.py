#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AuditSpec:
    key: str
    description: str
    script_path: Path
    finding_exit_codes: set[int]
    blocker_exit_codes: set[int]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_path(raw: str, *, base: Path = REPO_ROOT) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Führt BL-15 Read-only Audits in einem Lauf aus und erzeugt strukturierte "
            "Readiness-Evidenz als JSON/Markdown (inkl. optionalem Bundle-Export)."
        )
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/bl15",
        help="Ausgabebasis für Collector-Artefakte (default: artifacts/bl15)",
    )
    parser.add_argument(
        "--report-id",
        default="",
        help="Optionaler Report-Identifier (default: UTC timestamp)",
    )
    parser.add_argument(
        "--lookback-hours",
        default="6",
        help="Lookback-Fenster für CloudTrail-Audit (default: 6)",
    )
    parser.add_argument(
        "--include-lookup-events",
        choices=["0", "1"],
        default="0",
        help="CloudTrail LookupEvents in Fingerprint-Auswertung einbeziehen (0|1, default: 0)",
    )
    parser.add_argument(
        "--fingerprint-report",
        default="artifacts/bl15/legacy-cloudtrail-fingerprint-report.json",
        help="Zielpfad für CloudTrail-Fingerprint-JSON (default: artifacts/bl15/legacy-cloudtrail-fingerprint-report.json)",
    )

    parser.add_argument(
        "--repo-audit-script",
        default="scripts/audit_legacy_aws_consumer_refs.sh",
        help="Pfad zum Repo-Consumer-Audit-Skript",
    )
    parser.add_argument(
        "--runtime-audit-script",
        default="scripts/audit_legacy_runtime_consumers.sh",
        help="Pfad zum Runtime-Consumer-Audit-Skript",
    )
    parser.add_argument(
        "--cloudtrail-audit-script",
        default="scripts/audit_legacy_cloudtrail_consumers.sh",
        help="Pfad zum CloudTrail-Fingerprint-Audit-Skript",
    )

    parser.add_argument(
        "--skip-bundle",
        action="store_true",
        help="Bundle-Export (export_bl15_readiness_bundle.py) überspringen",
    )
    parser.add_argument(
        "--bundle-export-script",
        default="scripts/export_bl15_readiness_bundle.py",
        help="Pfad zum Bundle-Export-Skript",
    )
    parser.add_argument(
        "--bundle-output-root",
        default="reports/bl15_readiness",
        help="Bundle-Output-Root für Exportskript (default: reports/bl15_readiness)",
    )
    parser.add_argument(
        "--bundle-id",
        default="",
        help="Optionaler Bundle-Identifier (default: report-id)",
    )
    parser.add_argument(
        "--optional-glob",
        action="append",
        default=[],
        help="Optionales Glob-Pattern für Exportskript (repeatable)",
    )

    return parser.parse_args(argv)


def _run_command(*, command: list[str], env: dict[str, str], cwd: Path) -> tuple[int, str, str, int]:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    duration_ms = int((time.monotonic() - started) * 1000)
    return completed.returncode, completed.stdout, completed.stderr, duration_ms


def _classify_exit(spec: AuditSpec, exit_code: int) -> str:
    if exit_code == 0:
        return "ok"
    if exit_code in spec.finding_exit_codes:
        return "finding"
    if exit_code in spec.blocker_exit_codes:
        return "blocker"
    return "error"


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# BL-15 Readiness Collector Report",
        "",
        f"- Report ID: `{report['report_id']}`",
        f"- Generated at (UTC): `{report['generated_at_utc']}`",
        f"- Final status: `{report['final_status']}`",
        f"- Final exit code: `{report['final_exit_code']}`",
        "",
        "## Audit-Läufe",
        "",
        "| Audit | Status | Exit-Code | Dauer (ms) |",
        "| --- | --- | ---: | ---: |",
    ]

    for item in report.get("audits", []):
        lines.append(
            f"| `{item['key']}` | `{item['status']}` | `{item['exit_code']}` | `{item['duration_ms']}` |"
        )

    lines.extend(["", "## Artefakte", ""])

    for item in report.get("audits", []):
        lines.append(f"- `{item['key']}` stdout: `{item['stdout_log']}`")
        lines.append(f"- `{item['key']}` stderr: `{item['stderr_log']}`")

    bundle = report.get("bundle_export")
    if bundle:
        lines.extend(
            [
                "",
                "## Bundle-Export",
                "",
                f"- Status: `{bundle.get('status')}`",
                f"- Exit-Code: `{bundle.get('exit_code')}`",
            ]
        )
        if bundle.get("bundle_path"):
            lines.append(f"- Bundle-Pfad: `{bundle['bundle_path']}`")

    blockers = report.get("blockers") or []
    findings = report.get("findings") or []

    if findings:
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- {finding}" for finding in findings)

    if blockers:
        lines.extend(["", "## Blocker", ""])
        lines.extend(f"- {blocker}" for blocker in blockers)

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    report_id = args.report_id.strip() or _utc_stamp()
    generated_at_utc = _utc_now_iso()

    output_dir = _resolve_path(args.output_dir)
    run_dir = output_dir / f"readiness-collector-{report_id}"
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=False)

    fingerprint_report_path = _resolve_path(args.fingerprint_report)
    fingerprint_report_path.parent.mkdir(parents=True, exist_ok=True)

    specs = [
        AuditSpec(
            key="repo_consumer_audit",
            description="Repo-scope Legacy Consumer Audit",
            script_path=_resolve_path(args.repo_audit_script),
            finding_exit_codes={10, 20},
            blocker_exit_codes=set(),
        ),
        AuditSpec(
            key="runtime_consumer_audit",
            description="Host Runtime Legacy Consumer Audit",
            script_path=_resolve_path(args.runtime_audit_script),
            finding_exit_codes={10, 20, 30},
            blocker_exit_codes=set(),
        ),
        AuditSpec(
            key="cloudtrail_fingerprint_audit",
            description="CloudTrail Fingerprint Audit",
            script_path=_resolve_path(args.cloudtrail_audit_script),
            finding_exit_codes={10},
            blocker_exit_codes={20},
        ),
    ]

    report: dict[str, Any] = {
        "version": 1,
        "report_id": report_id,
        "generated_at_utc": generated_at_utc,
        "collector_run_dir": str(run_dir),
        "audits": [],
        "findings": [],
        "blockers": [],
        "bundle_export": None,
    }

    for spec in specs:
        if not spec.script_path.is_file():
            report["blockers"].append(f"missing script for {spec.key}: {spec.script_path}")
            continue

        env = dict(os.environ)
        if spec.key == "cloudtrail_fingerprint_audit":
            env["LOOKBACK_HOURS"] = str(args.lookback_hours)
            env["INCLUDE_LOOKUP_EVENTS"] = str(args.include_lookup_events)
            env["FINGERPRINT_REPORT_JSON"] = str(fingerprint_report_path)

        exit_code, stdout, stderr, duration_ms = _run_command(
            command=[str(spec.script_path)],
            env=env,
            cwd=REPO_ROOT,
        )

        stdout_log = logs_dir / f"{spec.key}.stdout.log"
        stderr_log = logs_dir / f"{spec.key}.stderr.log"
        stdout_log.write_text(stdout, encoding="utf-8")
        stderr_log.write_text(stderr, encoding="utf-8")

        status = _classify_exit(spec, exit_code)
        if status == "finding":
            report["findings"].append(f"{spec.key} reported findings (exit={exit_code})")
        elif status in {"blocker", "error"}:
            report["blockers"].append(f"{spec.key} returned exit code {exit_code}")

        report["audits"].append(
            {
                "key": spec.key,
                "description": spec.description,
                "script": str(spec.script_path),
                "status": status,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "stdout_log": str(stdout_log.relative_to(run_dir)),
                "stderr_log": str(stderr_log.relative_to(run_dir)),
            }
        )

    if not args.skip_bundle and not report["blockers"]:
        bundle_export_script = _resolve_path(args.bundle_export_script)
        if not bundle_export_script.is_file():
            report["blockers"].append(f"missing bundle export script: {bundle_export_script}")
        else:
            bundle_id = args.bundle_id.strip() or report_id
            bundle_output_root = _resolve_path(args.bundle_output_root)
            cmd = [
                str(bundle_export_script),
                "--output-root",
                str(bundle_output_root),
                "--bundle-id",
                bundle_id,
                "--fingerprint-report",
                str(fingerprint_report_path),
                "--optional-glob",
                str(run_dir / "*.json"),
                "--optional-glob",
                str(run_dir / "*.md"),
            ]
            for glob_pattern in args.optional_glob:
                cmd.extend(["--optional-glob", glob_pattern])

            env = dict(os.environ)
            exit_code, stdout, stderr, duration_ms = _run_command(command=cmd, env=env, cwd=REPO_ROOT)

            stdout_log = logs_dir / "bundle_export.stdout.log"
            stderr_log = logs_dir / "bundle_export.stderr.log"
            stdout_log.write_text(stdout, encoding="utf-8")
            stderr_log.write_text(stderr, encoding="utf-8")

            bundle_payload: dict[str, Any] = {
                "status": "ok" if exit_code == 0 else "blocker",
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "stdout_log": str(stdout_log.relative_to(run_dir)),
                "stderr_log": str(stderr_log.relative_to(run_dir)),
                "bundle_id": bundle_id,
            }

            if exit_code == 0:
                try:
                    parsed = json.loads(stdout)
                    if isinstance(parsed, dict):
                        bundle_payload.update(parsed)
                except json.JSONDecodeError:
                    bundle_payload["stdout_parse_error"] = "bundle export output is not valid JSON"
            else:
                report["blockers"].append(f"bundle export failed with exit code {exit_code}")

            report["bundle_export"] = bundle_payload

    if report["blockers"]:
        final_status = "blocker"
        final_exit_code = 20
    elif report["findings"]:
        final_status = "findings"
        final_exit_code = 10
    else:
        final_status = "ok"
        final_exit_code = 0

    report["final_status"] = final_status
    report["final_exit_code"] = final_exit_code

    report_json_path = run_dir / "collector_report.json"
    report_md_path = run_dir / "collector_report.md"
    report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_md_path.write_text(_render_markdown(report), encoding="utf-8")

    summary = {
        "status": final_status,
        "exit_code": final_exit_code,
        "report_id": report_id,
        "collector_run_dir": str(run_dir),
        "report_json": str(report_json_path),
        "report_md": str(report_md_path),
        "findings": len(report["findings"]),
        "blockers": len(report["blockers"]),
    }

    print(json.dumps(summary, indent=2, sort_keys=True))

    if final_exit_code == 20 and report["blockers"]:
        for blocker in report["blockers"]:
            print(f"BLOCKER: {blocker}", file=sys.stderr)

    return final_exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
