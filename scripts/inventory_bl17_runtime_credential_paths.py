#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

LEGACY_USER = "swisstopo-api-deploy"
AWS_REF_REGEX = re.compile(
    r"swisstopo-api-deploy|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|aws_access_key_id|aws_secret_access_key|AKIA[0-9A-Z]{16}",
    re.IGNORECASE,
)
SCAN_SUFFIXES = {".service", ".timer", ".conf", ".env", ".sh"}


@dataclass
class Detection:
    id: str
    detected: bool
    source_type: str
    source: str
    risk_level: str
    effect: str
    migration_next_step: str
    owner: str
    evidence: dict

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "detected": self.detected,
            "source_type": self.source_type,
            "source": self.source,
            "risk_level": self.risk_level,
            "effect": self.effect,
            "migration_next_step": self.migration_next_step,
            "owner": self.owner,
            "evidence": self.evidence,
        }


def short_key(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def detect_caller_arn() -> tuple[str | None, str]:
    aws_bin = shutil_which("aws")
    if not aws_bin:
        return None, "aws-cli-missing"

    proc = subprocess.run(
        [aws_bin, "sts", "get-caller-identity", "--query", "Arn", "--output", "text"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None, "aws-caller-unavailable"

    arn = proc.stdout.strip()
    if not arn or arn == "None":
        return None, "aws-caller-unavailable"

    if arn.endswith(f":user/{LEGACY_USER}"):
        return arn, "legacy-user-swisstopo-api-deploy"
    if ":assumed-role/openclaw-ops-role/" in arn:
        return arn, "assume-role-openclaw-ops-role"
    return arn, "other-principal"


def iter_existing_files(paths: Iterable[Path]) -> list[Path]:
    return [p for p in paths if p.is_file()]


def scan_file_matches(paths: Iterable[Path]) -> list[dict]:
    hits: list[dict] = []
    for file_path in paths:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(content, start=1):
            if AWS_REF_REGEX.search(line):
                hits.append({"path": str(file_path), "line": idx})
                break
    return hits


def scan_directory_matches(dirs: Iterable[Path]) -> list[str]:
    matches: list[str] = []
    for directory in dirs:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if AWS_REF_REGEX.search(text):
                matches.append(str(path))
    return matches


def scan_user_crontab() -> dict:
    crontab_bin = shutil_which("crontab")
    if not crontab_bin:
        return {"available": False, "detected": False, "entries": []}

    proc = subprocess.run([crontab_bin, "-l"], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return {"available": True, "detected": False, "entries": []}

    entries: list[str] = []
    for line in proc.stdout.splitlines():
        if AWS_REF_REGEX.search(line):
            entries.append("match-in-user-crontab")
            break

    return {"available": True, "detected": bool(entries), "entries": entries}


def shutil_which(cmd: str) -> str | None:
    for part in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(part) / cmd
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def build_report(repo_root: Path) -> tuple[dict, int]:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    caller_arn, caller_classification = detect_caller_arn()

    profile_files = iter_existing_files(
        [
            Path.home() / ".bashrc",
            Path.home() / ".bash_profile",
            Path.home() / ".profile",
            Path.home() / ".zshrc",
            Path.home() / ".zprofile",
            Path.home() / ".config/fish/config.fish",
            Path("/etc/environment"),
        ]
    )
    aws_config_files = iter_existing_files([Path.home() / ".aws/credentials", Path.home() / ".aws/config"])
    openclaw_config_files = iter_existing_files(
        [
            Path("/data/.openclaw/openclaw.json"),
            Path("/data/.openclaw/openclaw.json.bak"),
            Path("/data/.openclaw/cron/jobs.json"),
            Path("/data/.openclaw/cron/jobs.json.bak"),
        ]
    )
    system_cron_dirs = [p for p in [Path("/etc/cron.d"), Path("/etc/cron.daily"), Path("/etc/cron.hourly"), Path("/etc/cron.weekly"), Path("/etc/cron.monthly")] if p.is_dir()]
    systemd_dirs = [p for p in [Path.home() / ".config/systemd/user", Path("/etc/systemd/system")] if p.is_dir()]

    profile_hits = scan_file_matches(profile_files)
    aws_cfg_hits = scan_file_matches(aws_config_files)
    openclaw_cfg_hits = scan_file_matches(openclaw_config_files)
    system_cron_hits = scan_directory_matches(system_cron_dirs)
    systemd_hits = scan_directory_matches(systemd_dirs)
    user_crontab = scan_user_crontab()

    env_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
    env_secret_key_set = bool(os.environ.get("AWS_SECRET_ACCESS_KEY"))
    env_session_token_set = bool(os.environ.get("AWS_SESSION_TOKEN"))
    env_web_identity = os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE", "")

    detections: list[Detection] = [
        Detection(
            id="runtime-caller-legacy-user",
            detected=caller_classification == "legacy-user-swisstopo-api-deploy",
            source_type="runtime-caller",
            source="aws sts get-caller-identity",
            risk_level="high",
            effect="Default AWS caller läuft auf Legacy-IAM-User statt AssumeRole.",
            migration_next_step="OpenClaw-Runtime auf AssumeRole-Wrapper umstellen und Legacy-Caller nur als dokumentierten Fallback zulassen.",
            owner="platform-ops",
            evidence={"caller_arn": caller_arn, "classification": caller_classification},
        ),
        Detection(
            id="runtime-env-static-keys",
            detected=bool(env_access_key and env_secret_key_set),
            source_type="environment",
            source="process env",
            risk_level="high",
            effect="Statische AWS-Keys sind im Runtime-Environment aktiv und können Legacy-Zugriffe erzwingen.",
            migration_next_step="Statische Keys aus Runtime-Startpfaden entfernen und AWS-CLI-Aufrufe über aws_exec_via_openclaw_ops.sh routen.",
            owner="platform-ops",
            evidence={
                "aws_access_key_id": short_key(env_access_key) if env_access_key else None,
                "aws_secret_access_key_set": env_secret_key_set,
                "aws_session_token_set": env_session_token_set,
            },
        ),
        Detection(
            id="runtime-env-web-identity",
            detected=bool(env_web_identity),
            source_type="environment",
            source="process env",
            risk_level="low",
            effect="Web identity token file ist gesetzt (OIDC-kompatibler Pfad).",
            migration_next_step="Pfad beibehalten und sicherstellen, dass Role-Assumption ohne Legacy-Keys priorisiert wird.",
            owner="platform-ops",
            evidence={"aws_web_identity_token_file_set": bool(env_web_identity)},
        ),
        Detection(
            id="shell-profile-credential-references",
            detected=bool(profile_hits),
            source_type="file-scan",
            source="shell profiles + /etc/environment",
            risk_level="medium",
            effect="Persistente Profile können Legacy-Credentials in neue Shell-Sessions injizieren.",
            migration_next_step="Gefundene Credential-Referenzen aus Profilen entfernen und stattdessen kurzlebige AssumeRole-Sessions nutzen.",
            owner="platform-ops",
            evidence={"hits": profile_hits},
        ),
        Detection(
            id="aws-config-credential-references",
            detected=bool(aws_cfg_hits),
            source_type="file-scan",
            source="~/.aws/config + ~/.aws/credentials",
            risk_level="medium",
            effect="Persistierte AWS-Config kann Legacy-Profile als Default aktivieren.",
            migration_next_step="Legacy-Profile entfernen oder explizit auf AssumeRole-Profile umstellen (ohne statische User-Keys).",
            owner="platform-ops",
            evidence={"hits": aws_cfg_hits},
        ),
        Detection(
            id="openclaw-config-credential-references",
            detected=bool(openclaw_cfg_hits),
            source_type="file-scan",
            source="/data/.openclaw/*.json",
            risk_level="medium",
            effect="OpenClaw-Konfiguration enthält Legacy- oder Key-Referenzen für Runtime-Injection.",
            migration_next_step="OpenClaw-Config auf Role-basierte Aufrufpfade umstellen; Secrets nicht in Config-Dateien halten.",
            owner="platform-ops",
            evidence={"hits": openclaw_cfg_hits},
        ),
        Detection(
            id="cron-credential-references",
            detected=bool(system_cron_hits or user_crontab["detected"]),
            source_type="scheduler",
            source="user/system cron",
            risk_level="medium",
            effect="Cronjobs können Legacy-Credentials automatisiert injizieren.",
            migration_next_step="Cron-AWS-Aufrufe auf AssumeRole-Wrapper umstellen und Legacy-Referenzen entfernen.",
            owner="platform-ops",
            evidence={"user_crontab": user_crontab, "system_cron_hits": system_cron_hits},
        ),
        Detection(
            id="systemd-credential-references",
            detected=bool(systemd_hits),
            source_type="scheduler",
            source="systemd units",
            risk_level="medium",
            effect="Systemd-Units können Legacy-Credentials beim Start injizieren.",
            migration_next_step="Systemd-Units auf credential-freie Runtime oder AssumeRole-Wrapper migrieren.",
            owner="platform-ops",
            evidence={"hits": systemd_hits},
        ),
        Detection(
            id="assumerole-wrapper-available",
            detected=(repo_root / "scripts/aws_exec_via_openclaw_ops.sh").is_file(),
            source_type="repo-signal",
            source="scripts/aws_exec_via_openclaw_ops.sh",
            risk_level="low",
            effect="Kontrollierter Migrationspfad für direkte AWS-Ops ist verfügbar.",
            migration_next_step="Wrapper standardmäßig in Runtime-Pfaden nutzen und Legacy-Direktaufrufe zurückdrängen.",
            owner="platform-ops",
            evidence={"path": "scripts/aws_exec_via_openclaw_ops.sh"},
        ),
    ]

    risky_detected = [
        d
        for d in detections
        if d.detected and d.risk_level in {"high", "medium"}
    ]

    report = {
        "version": 1,
        "generated_at_utc": timestamp,
        "scope": "BL-17.wp5 runtime credential injection inventory",
        "caller": {"arn": caller_arn, "classification": caller_classification},
        "detections": [d.as_dict() for d in detections],
        "summary": {
            "detected_total": sum(1 for d in detections if d.detected),
            "risk_findings": len(risky_detected),
            "risk_ids": [d.id for d in risky_detected],
            "recommended_exit_code": 10 if risky_detected else 0,
        },
    }

    exit_code = 10 if risky_detected else 0
    return report, exit_code


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory runtime credential injection paths for BL-17 OIDC-first migration evidence."
    )
    parser.add_argument("--output-json", help="Optional path for JSON report output")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]

    report, exit_code = build_report(repo_root=repo_root)

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)

    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)
