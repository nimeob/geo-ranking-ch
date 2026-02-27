#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
GHA = str(REPO_ROOT / "scripts" / "gha")

EVIDENCE_RE = re.compile(r"\b(commit|pr\s*#|#\d+|pytest|test[s]?|merged|fixes)\b", re.IGNORECASE)
TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
NON_ACTIONABLE_TODO_RE = re.compile(
    r"(✅|\berledigt\b|\babgeschlossen\b|\bclosed\b|\bhistorisch\b|\bchangelog\b)",
    re.IGNORECASE,
)

WORKSTREAM_KEYWORDS = {
    "development": {
        "entwickl", "develop", "implement", "feature", "api", "service", "pipeline",
        "integration", "gui", "vertical", "build", "refactor"
    },
    "documentation": {
        "doku", "dokument", "docs", "readme", "runbook", "guide", "architecture", "operations"
    },
    "testing": {
        "test", "pytest", "e2e", "smoke", "stability", "regression", "qa", "validation"
    },
}

WORKSTREAM_BALANCE_ISSUE_TITLE = "[Crawler][P0] Workstream-Balance: Development/Dokumentation/Testing angleichen"
CONSISTENCY_REPORT_JSON = Path("reports/consistency_report.json")
CONSISTENCY_REPORT_MD = Path("reports/consistency_report.md")
SEVERITY_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def run(args):
    return subprocess.check_output([GHA, *args], cwd=REPO_ROOT, text=True)


def run_json(args):
    out = run(args)
    return json.loads(out)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_label(name: str, color: str, desc: str, dry_run: bool):
    try:
        run(["label", "create", name, "--color", color, "--description", desc])
    except subprocess.CalledProcessError:
        # likely exists
        pass


def list_open_titles():
    issues = run_json(["issue", "list", "--state", "open", "--limit", "200", "--json", "number,title"])
    return {i["title"]: i["number"] for i in issues}


def reopen_issue(number: int, reason: str, dry_run: bool):
    comment = f"🔎 Crawler-Audit ({now_iso()}): Reopening, weil die Abschlusskriterien nicht sauber erfüllt sind.\n\nGrund:\n- {reason}\n\nBitte nachziehen und mit Commit/PR/Test-Nachweis erneut schließen."
    if dry_run:
        print(f"[DRY] reopen #{number}: {reason}")
        return
    run(["issue", "reopen", str(number)])
    run(["issue", "comment", str(number), "--body", comment])
    print(f"reopened #{number}: {reason}")


def close_issue(number: int, reason: str, dry_run: bool):
    comment = (
        f"✅ Crawler-Audit ({now_iso()}): Workstream-Balance wieder im Zielkorridor.\n\n"
        f"Grund:\n- {reason}\n\n"
        "Das automatische P0-Catch-up-Issue wird daher geschlossen."
    )
    if dry_run:
        print(f"[DRY] close #{number}: {reason}")
        return
    run(["issue", "comment", str(number), "--body", comment])
    run(["issue", "close", str(number)])
    print(f"closed #{number}: {reason}")


def create_issue(title: str, body: str, dry_run: bool, priority: str = "priority:P2"):
    if dry_run:
        print(f"[DRY] create issue: {title} [{priority}]")
        return
    run([
        "issue", "create",
        "--title", title,
        "--body", body,
        "--label", "backlog",
        "--label", priority,
        "--label", "status:todo",
        "--label", "crawler:auto",
    ])
    print(f"created: {title} [{priority}]")


def normalize_severity(severity: str) -> str:
    sev = (severity or "").strip().lower()
    return sev if sev in SEVERITY_PRIORITY else "medium"


def build_finding(*, finding_type: str, severity: str, summary: str, evidence: list[dict[str, Any]], source: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": finding_type,
        "severity": normalize_severity(severity),
        "summary": summary,
        "evidence": evidence,
        "source": source,
    }


def sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda item: (
            SEVERITY_PRIORITY.get(item.get("severity", "medium"), SEVERITY_PRIORITY["medium"]),
            item.get("type", ""),
            item.get("summary", ""),
        ),
    )


def build_consistency_report(findings: list[dict[str, Any]], generated_at: str | None = None) -> dict[str, Any]:
    ordered_findings = sort_findings(findings)
    by_severity = Counter(f.get("severity", "medium") for f in ordered_findings)
    by_type = Counter(f.get("type", "unknown") for f in ordered_findings)

    return {
        "schema_version": "1.0",
        "generated_at": generated_at or now_iso(),
        "summary": {
            "total_findings": len(ordered_findings),
            "by_severity": dict(sorted(by_severity.items(), key=lambda kv: SEVERITY_PRIORITY.get(kv[0], 99))),
            "by_type": dict(sorted(by_type.items())),
        },
        "findings": ordered_findings,
    }


def _render_evidence_refs(evidence: list[dict[str, Any]]) -> str:
    refs = []
    for entry in evidence:
        if entry.get("kind") == "file_line":
            refs.append(f"`{entry.get('path')}:{entry.get('line')}`")
        elif entry.get("kind") == "issue":
            number = entry.get("number")
            refs.append(f"`#{number}`" if number is not None else "`issue`")
        elif entry.get("kind") == "metric":
            refs.append(f"`{entry.get('name')}={entry.get('value')}`")
    return ", ".join(refs) if refs else "-"


def render_consistency_report_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    by_severity = summary.get("by_severity") or {}
    by_type = summary.get("by_type") or {}
    findings = report.get("findings") or []

    lines = [
        "# Consistency Report",
        "",
        f"- Generated at (UTC): `{report.get('generated_at')}`",
        f"- Schema version: `{report.get('schema_version')}`",
        f"- Total findings: **{summary.get('total_findings', 0)}**",
        "",
        "## Priorisierte Zusammenfassung",
    ]

    if by_severity:
        lines.append("- Findings nach Severity: " + ", ".join(f"{key}={value}" for key, value in by_severity.items()))
    else:
        lines.append("- Findings nach Severity: none")

    if by_type:
        lines.append("- Findings nach Typ: " + ", ".join(f"{key}={value}" for key, value in by_type.items()))
    else:
        lines.append("- Findings nach Typ: none")

    lines.extend(["", "## Findings", ""])

    if not findings:
        lines.append("Keine Findings in diesem Lauf.")
        return "\n".join(lines) + "\n"

    lines.extend([
        "| Severity | Type | Summary | Evidence | Source |",
        "|---|---|---|---|---|",
    ])

    for finding in findings:
        source = finding.get("source") or {}
        source_name = source.get("kind") or "unknown"
        component = source.get("component")
        if component:
            source_name = f"{source_name}:{component}"
        lines.append(
            "| {severity} | {type} | {summary} | {evidence} | {source} |".format(
                severity=finding.get("severity", "medium"),
                type=finding.get("type", "unknown"),
                summary=(finding.get("summary", "").replace("|", "\\|")),
                evidence=_render_evidence_refs(finding.get("evidence") or []),
                source=source_name,
            )
        )

    return "\n".join(lines) + "\n"


def write_consistency_reports(
    report: dict[str, Any],
    *,
    json_path: Path = CONSISTENCY_REPORT_JSON,
    markdown_path: Path = CONSISTENCY_REPORT_MD,
) -> tuple[Path, Path]:
    json_abs = (REPO_ROOT / json_path).resolve()
    md_abs = (REPO_ROOT / markdown_path).resolve()
    json_abs.parent.mkdir(parents=True, exist_ok=True)
    md_abs.parent.mkdir(parents=True, exist_ok=True)

    json_abs.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_abs.write_text(render_consistency_report_markdown(report), encoding="utf-8")
    return json_abs, md_abs


def is_actionable_todo_line(line: str) -> bool:
    if not TODO_RE.search(line):
        return False
    if NON_ACTIONABLE_TODO_RE.search(line):
        return False
    return True


def audit_closed_issues(dry_run: bool) -> list[dict[str, Any]]:
    closed = run_json([
        "issue", "list", "--state", "closed", "--limit", "200",
        "--json", "number,title,labels,closedAt,url"
    ])

    findings: list[dict[str, Any]] = []

    for issue in closed:
        n = issue["number"]
        detail = run_json([
            "issue", "view", str(n),
            "--json", "number,title,body,labels,comments,closedByPullRequestsReferences,state,url"
        ])

        labels = {l["name"] for l in detail.get("labels", [])}
        body = detail.get("body") or ""
        comments = "\n".join((c.get("body") or "") for c in detail.get("comments", []))
        prs = detail.get("closedByPullRequestsReferences", [])

        reasons = []
        stale_status_label = ("status:todo" in labels or "status:in-progress" in labels)
        if re.search(r"^- \[ \] ", body, flags=re.MULTILINE):
            reasons.append("Issue-Body enthält offene Checklist-Items")
        no_closure_evidence = (not prs and not EVIDENCE_RE.search(comments))
        if no_closure_evidence:
            reasons.append("Kein PR-Link und kein belastbarer Abschlussnachweis im Kommentar")
        # Nur ein veraltetes Status-Label ist noch kein Reopen-Grund.
        if stale_status_label and no_closure_evidence:
            reasons.append("Status-Label ist noch todo/in-progress")

        if reasons:
            findings.append(
                build_finding(
                    finding_type="issue_closure_consistency",
                    severity="high" if no_closure_evidence else "medium",
                    summary=f"Geschlossenes Issue #{n} hat inkonsistente Abschlusssignale",
                    evidence=[
                        {"kind": "issue", "number": n, "url": detail.get("url")},
                        {"kind": "metric", "name": "reason_count", "value": len(reasons)},
                    ],
                    source={"kind": "github_issue_audit", "component": "closed_issue_review", "reasons": reasons},
                )
            )
            reopen_issue(n, "; ".join(reasons), dry_run=dry_run)

    return findings


def collect_actionable_todo_findings(limit: int = 20) -> list[dict[str, Any]]:
    paths = ["src", "tests", "docs", "scripts", "README.md"]
    findings: list[dict[str, Any]] = []

    ignore_files = {
        "scripts/github_repo_crawler.py",
        "scripts/ci-deploy-template.yml",
    }

    for p in paths:
        target = REPO_ROOT / p
        if target.is_file():
            files = [target]
        elif target.is_dir():
            files = [x for x in target.rglob("*") if x.is_file()]
        else:
            continue

        for f in files:
            if any(part in {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__", "artifacts"} for part in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            rel_path = f.relative_to(REPO_ROOT).as_posix()
            if rel_path in ignore_files:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if "crawler:ignore" in line:
                    continue
                if not is_actionable_todo_line(line):
                    continue
                snippet = line.strip()
                if len(snippet) > 120:
                    snippet = snippet[:117] + "..."
                findings.append(
                    build_finding(
                        finding_type="todo_actionable",
                        severity="medium",
                        summary=f"Actionable TODO/FIXME erkannt: {rel_path}:{i}",
                        evidence=[
                            {"kind": "file_line", "path": rel_path, "line": i, "snippet": snippet},
                        ],
                        source={"kind": "repository_scan", "component": "todo_fixme"},
                    )
                )
                if len(findings) >= limit:
                    return findings

    return findings


def scan_repo_for_findings(dry_run: bool) -> list[dict[str, Any]]:
    open_titles = list_open_titles()
    findings = collect_actionable_todo_findings(limit=20)

    for finding in findings:
        evidence = (finding.get("evidence") or [{}])[0]
        rel = evidence.get("path")
        line_no = evidence.get("line")
        snippet = evidence.get("snippet")
        title = f"[Crawler] Offener TODO/FIXME: {rel}:{line_no}"
        if title in open_titles:
            continue
        body = (
            f"Automatisch vom Repository-Crawler erkannt ({now_iso()}).\n\n"
            f"Fundstelle: `{rel}:{line_no}`\n"
            f"Inhalt: `{snippet}`\n\n"
            "Bitte prüfen, ob der Punkt bereits abgedeckt ist. Falls nicht, sauber umsetzen und Nachweis im Abschlusskommentar liefern.\n\n"
            "## Worker-Auswahlregel (ohne Label-Automatik)\n"
            "- Innerhalb derselben Priorität sollen Worker bevorzugt mit den älteren offenen Issues beginnen (oldest-first).\n"
            "- Neuere gleichrangige Issues bleiben trotzdem bearbeitbar (keine künstliche Blockierung über Labels).\n"
            "- Abhängigkeiten gehen vor Alter: Wenn ein älteres Issue blockiert ist, darf ein jüngeres gleichrangiges Issue vorgezogen werden."
        )
        create_issue(title, body, dry_run=dry_run)

    return findings


def keyword_matches(text: str, keyword: str) -> bool:
    # Kurze Kürzel (api/gui/qa/e2e) nur als eigenständige Tokens matchen,
    # um False-Positives wie "guide" -> "gui" zu vermeiden.
    if len(keyword) <= 3:
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def is_countable_for_workstream_balance(issue) -> bool:
    labels = {l["name"] for l in issue.get("labels", [])}
    if "crawler:auto" in labels:
        return False
    if "status:blocked" in labels:
        return False
    return True


def compute_workstream_counts(issues):
    counts = {k: 0 for k in WORKSTREAM_KEYWORDS}

    for issue in issues:
        if not is_countable_for_workstream_balance(issue):
            continue

        text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
        matched = set()
        for category, keywords in WORKSTREAM_KEYWORDS.items():
            if any(keyword_matches(text, keyword) for keyword in keywords):
                matched.add(category)

        # keine Erkennung -> neutral ignorieren
        for category in matched:
            counts[category] += 1

    return counts


def get_open_issues_for_workstream_balance():
    return run_json([
        "issue", "list", "--state", "open", "--limit", "300",
        "--json", "number,title,body,labels"
    ])


def build_workstream_balance_baseline(issues):
    counts = compute_workstream_counts(issues)
    max_count = max(counts.values()) if counts else 0
    min_count = min(counts.values()) if counts else 0
    gap = max_count - min_count
    severe_zero_gap = max_count >= 2 and min_count == 0
    spread_too_large = gap >= 3

    return {
        "counts": counts,
        "max_count": max_count,
        "min_count": min_count,
        "gap": gap,
        "target_gap_max": 2,
        "severe_zero_gap": severe_zero_gap,
        "spread_too_large": spread_too_large,
        "needs_catchup": severe_zero_gap or spread_too_large,
    }


def format_workstream_balance_markdown(baseline, generated_at: str):
    counts = baseline["counts"]
    return (
        f"# Workstream-Balance Baseline ({generated_at})\n\n"
        "Heuristische Zählung aus offenen, nicht-blockierten Issues (ohne `crawler:auto`).\n\n"
        "## Counts\n"
        f"- Development: **{counts['development']}**\n"
        f"- Dokumentation: **{counts['documentation']}**\n"
        f"- Testing: **{counts['testing']}**\n"
        f"- Gap (max-min): **{baseline['gap']}**\n"
        f"- Ziel-Gap: **<= {baseline['target_gap_max']}**\n"
        f"- Catch-up nötig: **{'ja' if baseline['needs_catchup'] else 'nein'}**\n"
    )


def print_workstream_balance_report(report_format: str):
    issues = get_open_issues_for_workstream_balance()
    baseline = build_workstream_balance_baseline(issues)
    generated_at = now_iso()

    if report_format == "json":
        payload = {
            "generated_at": generated_at,
            **baseline,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return

    print(format_workstream_balance_markdown(baseline, generated_at))


def audit_workstream_balance(dry_run: bool) -> list[dict[str, Any]]:
    """
    Guardrail: Development, Documentation und Testing sollen parallel nachgezogen werden.
    Wenn ein Bereich deutlich hinterherhinkt, wird ein P0-Catch-up-Issue erzeugt.
    Wenn die Balance wieder passt, wird ein bestehendes P0-Catch-up-Issue automatisch geschlossen.
    """
    open_titles = list_open_titles()
    issues = get_open_issues_for_workstream_balance()
    baseline = build_workstream_balance_baseline(issues)
    counts = baseline["counts"]

    existing_issue_number = open_titles.get(WORKSTREAM_BALANCE_ISSUE_TITLE)
    findings: list[dict[str, Any]] = []

    if baseline["needs_catchup"]:
        findings.append(
            build_finding(
                finding_type="workstream_balance_gap",
                severity="high" if baseline["gap"] >= 4 else "medium",
                summary=(
                    "Workstream-Balance außerhalb Zielkorridor "
                    f"(gap={baseline['gap']}, ziel<={baseline['target_gap_max']})"
                ),
                evidence=[
                    {"kind": "metric", "name": "development", "value": counts["development"]},
                    {"kind": "metric", "name": "documentation", "value": counts["documentation"]},
                    {"kind": "metric", "name": "testing", "value": counts["testing"]},
                    {"kind": "metric", "name": "gap", "value": baseline["gap"]},
                ],
                source={"kind": "workstream_balance", "component": "heuristic_counts"},
            )
        )

    if not baseline["needs_catchup"]:
        if existing_issue_number is not None:
            reason = (
                "Keine Catch-up-Lücke mehr erkannt "
                f"(Dev={counts['development']}, Doku={counts['documentation']}, Testing={counts['testing']}, "
                f"Gap={baseline['gap']} <= Ziel {baseline['target_gap_max']})."
            )
            close_issue(existing_issue_number, reason, dry_run=dry_run)
        return findings

    if existing_issue_number is not None:
        return findings

    body = (
        f"Automatisch vom Repository-Crawler erkannt ({now_iso()}).\n\n"
        "Es besteht ein Ungleichgewicht zwischen den offenen, nicht-blockierten Arbeitsströmen.\n"
        "Regel: Development, Dokumentation und Testing sollen auf ähnlichem Fortschrittsniveau bleiben.\n\n"
        "Aktuelle Zählung (heuristisch, aus offenen Issues):\n"
        f"- Development: **{counts['development']}**\n"
        f"- Dokumentation: **{counts['documentation']}**\n"
        f"- Testing: **{counts['testing']}**\n\n"
        "Erwartete Aktion (P0 Catch-up):\n"
        "1. Rückstandskategorie identifizieren\n"
        "2. Konkrete Catch-up-Tasks sofort freigeben\n"
        "3. Abschluss erst, wenn die Lücke sichtbar reduziert ist\n\n"
        "## Worker-Auswahlregel (ohne Label-Automatik)\n"
        "- Innerhalb derselben Priorität sollen Worker bevorzugt mit den älteren offenen Issues beginnen (oldest-first).\n"
        "- Neuere gleichrangige Issues bleiben trotzdem bearbeitbar (keine künstliche Blockierung über Labels).\n"
        "- Abhängigkeiten gehen vor Alter: Wenn ein älteres Issue blockiert ist, darf ein jüngeres gleichrangiges Issue vorgezogen werden.\n\n"
        "Hinweis: P0 ist hier ausschließlich für das Aufholen liegengebliebener, kritischer Arbeit reserviert."
    )
    create_issue(WORKSTREAM_BALANCE_ISSUE_TITLE, body, dry_run=dry_run, priority="priority:P0")
    return findings


def main():
    parser = argparse.ArgumentParser(description="GitHub repo crawler: reopen inconsistent closed issues + create findings")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--print-workstream-balance",
        action="store_true",
        help="Gibt eine reproduzierbare Workstream-Balance-Baseline aus, ohne Issues zu verändern.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Ausgabeformat für --print-workstream-balance (default: markdown).",
    )
    args = parser.parse_args()

    if args.print_workstream_balance:
        print_workstream_balance_report(report_format=args.format)
        return

    ensure_label("crawler:auto", "5319e7", "Automatisch vom Crawler erzeugte Findings", dry_run=args.dry_run)
    ensure_label("priority:P0", "b60205", "Kritisch/zeitnah", dry_run=args.dry_run)

    findings: list[dict[str, Any]] = []
    findings.extend(audit_closed_issues(dry_run=args.dry_run))
    findings.extend(scan_repo_for_findings(dry_run=args.dry_run))
    findings.extend(audit_workstream_balance(dry_run=args.dry_run))

    report = build_consistency_report(findings)
    json_path, md_path = write_consistency_reports(report)
    print(f"consistency reports written: {json_path.relative_to(REPO_ROOT)}, {md_path.relative_to(REPO_ROOT)}")
    print("crawler run complete")


if __name__ == "__main__":
    main()
