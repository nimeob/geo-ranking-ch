#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "BL-17 OIDC-only Guard: kombiniert Runtime- und CloudTrail-Evidenz "
            "zu einem einheitlichen ok|warn|fail-Befund."
        )
    )
    parser.add_argument(
        "--output-json",
        default=os.environ.get("BL17_OIDC_GUARD_REPORT_JSON", "artifacts/bl17/oidc-only-guard-report.json"),
        help="Pfad für den zusammengeführten Guard-Report (default: artifacts/bl17/oidc-only-guard-report.json)",
    )
    parser.add_argument(
        "--posture-report-json",
        default="artifacts/bl17/posture-report.json",
        help="Pfad für den Posture-Teilreport (default: artifacts/bl17/posture-report.json)",
    )
    parser.add_argument(
        "--runtime-report-json",
        default="artifacts/bl17/runtime-credential-inventory.json",
        help="Pfad für den Runtime-Inventory-Teilreport (default: artifacts/bl17/runtime-credential-inventory.json)",
    )
    parser.add_argument(
        "--cloudtrail-log",
        default="artifacts/bl17/legacy-cloudtrail-audit.log",
        help="Pfad für den CloudTrail-Audit-Log (default: artifacts/bl17/legacy-cloudtrail-audit.log)",
    )
    parser.add_argument(
        "--cloudtrail-lookback-hours",
        type=int,
        default=int(os.environ.get("LOOKBACK_HOURS", "6")),
        help="Lookback-Fenster für CloudTrail-Audit in Stunden (default: LOOKBACK_HOURS oder 6)",
    )
    return parser.parse_args(argv)


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path


def to_repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def run_command(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> CommandResult:
    proc = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(command=command, exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def load_json_file(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def classify_posture(result: CommandResult, report: dict | None) -> tuple[str, list[str]]:
    notes: list[str] = []

    caller_classification = None
    static_key_refs_found = None
    if isinstance(report, dict):
        caller_classification = (report.get("caller") or {}).get("classification")
        static_key_refs_found = (report.get("workflow") or {}).get("static_key_refs_found")

    if caller_classification == "legacy-user-swisstopo-api-deploy":
        notes.append("legacy runtime caller detected")
    if static_key_refs_found is True:
        notes.append("static key references found in workflows")

    if result.exit_code in {20, 30} or notes:
        return "fail", notes or ["posture check reported hard findings"]

    if result.exit_code == 10:
        return "warn", ["oidc posture markers incomplete"]

    if result.exit_code == 0:
        return "ok", ["oidc posture check clean"]

    return "warn", [f"unexpected posture exit code: {result.exit_code}"]


def classify_runtime_inventory(result: CommandResult, report: dict | None) -> tuple[str, list[str]]:
    summary = (report or {}).get("summary") if isinstance(report, dict) else None
    risk_findings = 0
    risk_ids: list[str] = []
    if isinstance(summary, dict):
        risk_findings = int(summary.get("risk_findings") or 0)
        raw_ids = summary.get("risk_ids") or []
        risk_ids = [str(item) for item in raw_ids]

    if result.exit_code == 10 or risk_findings > 0:
        detail = f"runtime risk findings: {risk_findings}"
        if risk_ids:
            detail += f" ({', '.join(risk_ids)})"
        return "fail", [detail]

    if result.exit_code == 0:
        return "ok", ["runtime inventory clean"]

    return "warn", [f"unexpected runtime inventory exit code: {result.exit_code}"]


def classify_cloudtrail(result: CommandResult) -> tuple[str, list[str]]:
    if result.exit_code == 10:
        return "fail", ["legacy cloudtrail events found in lookback window"]
    if result.exit_code == 0:
        return "ok", ["no legacy cloudtrail events found"]
    return "warn", [f"cloudtrail audit inconclusive (exit {result.exit_code})"]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.cloudtrail_lookback_hours < 1:
        raise SystemExit("--cloudtrail-lookback-hours must be >= 1")

    repo_root = Path(__file__).resolve().parents[1]
    scripts_dir = repo_root / "scripts"

    posture_script = scripts_dir / "check_bl17_oidc_assumerole_posture.sh"
    runtime_script = scripts_dir / "inventory_bl17_runtime_credential_paths.py"
    cloudtrail_script = scripts_dir / "audit_legacy_cloudtrail_consumers.sh"

    output_path = resolve_path(repo_root, args.output_json)
    posture_report_path = resolve_path(repo_root, args.posture_report_json)
    runtime_report_path = resolve_path(repo_root, args.runtime_report_json)
    cloudtrail_log_path = resolve_path(repo_root, args.cloudtrail_log)

    missing_scripts = [
        str(path)
        for path in (posture_script, runtime_script, cloudtrail_script)
        if not path.is_file()
    ]
    if missing_scripts:
        report = {
            "version": 1,
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "warn",
            "summary": "required BL-17 scripts missing",
            "missing_scripts": missing_scripts,
            "checks": {},
            "evidence_paths": [],
        }
        rendered = json.dumps(report, indent=2, sort_keys=True)
        print(rendered)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        return 20

    posture_report_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_report_path.parent.mkdir(parents=True, exist_ok=True)
    cloudtrail_log_path.parent.mkdir(parents=True, exist_ok=True)

    posture_result = run_command(
        [str(posture_script), "--report-json", str(posture_report_path)],
        cwd=repo_root,
    )
    runtime_result = run_command(
        [sys.executable, str(runtime_script), "--output-json", str(runtime_report_path)],
        cwd=repo_root,
    )

    cloudtrail_env = os.environ.copy()
    cloudtrail_env["LOOKBACK_HOURS"] = str(args.cloudtrail_lookback_hours)
    cloudtrail_result = run_command(
        [str(cloudtrail_script)],
        cwd=repo_root,
        env=cloudtrail_env,
    )
    cloudtrail_log_path.write_text(
        cloudtrail_result.stdout + ("\n" if cloudtrail_result.stdout and not cloudtrail_result.stdout.endswith("\n") else "") + cloudtrail_result.stderr,
        encoding="utf-8",
    )

    posture_report = load_json_file(posture_report_path)
    runtime_report = load_json_file(runtime_report_path)

    posture_status, posture_notes = classify_posture(posture_result, posture_report)
    runtime_status, runtime_notes = classify_runtime_inventory(runtime_result, runtime_report)
    cloudtrail_status, cloudtrail_notes = classify_cloudtrail(cloudtrail_result)

    statuses = [posture_status, runtime_status, cloudtrail_status]
    if "fail" in statuses:
        overall_status = "fail"
        exit_code = 10
    elif "warn" in statuses:
        overall_status = "warn"
        exit_code = 20
    else:
        overall_status = "ok"
        exit_code = 0

    checks = {
        "posture": {
            "status": posture_status,
            "exit_code": posture_result.exit_code,
            "command": posture_result.command,
            "notes": posture_notes,
            "evidence_paths": [to_repo_relative(repo_root, posture_report_path)],
        },
        "runtime_inventory": {
            "status": runtime_status,
            "exit_code": runtime_result.exit_code,
            "command": runtime_result.command,
            "notes": runtime_notes,
            "evidence_paths": [to_repo_relative(repo_root, runtime_report_path)],
        },
        "cloudtrail": {
            "status": cloudtrail_status,
            "exit_code": cloudtrail_result.exit_code,
            "command": cloudtrail_result.command,
            "lookback_hours": args.cloudtrail_lookback_hours,
            "notes": cloudtrail_notes,
            "evidence_paths": [to_repo_relative(repo_root, cloudtrail_log_path)],
        },
    }

    report = {
        "version": 1,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": overall_status,
        "summary": "BL-17 OIDC-only Guard (runtime + cloudtrail) consolidated result",
        "checks": checks,
        "evidence_paths": [
            to_repo_relative(repo_root, posture_report_path),
            to_repo_relative(repo_root, runtime_report_path),
            to_repo_relative(repo_root, cloudtrail_log_path),
            to_repo_relative(repo_root, output_path),
        ],
    }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)
