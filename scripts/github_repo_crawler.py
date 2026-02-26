#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GHA = str(REPO_ROOT / "scripts" / "gha")

EVIDENCE_RE = re.compile(r"\b(commit|pr\s*#|#\d+|pytest|test[s]?|merged|fixes)\b", re.IGNORECASE)
TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")

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


def audit_closed_issues(dry_run: bool):
    closed = run_json([
        "issue", "list", "--state", "closed", "--limit", "200",
        "--json", "number,title,labels,closedAt"
    ])

    for issue in closed:
        n = issue["number"]
        detail = run_json([
            "issue", "view", str(n),
            "--json", "number,title,body,labels,comments,closedByPullRequestsReferences,state"
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
            reopen_issue(n, "; ".join(reasons), dry_run=dry_run)


def scan_repo_for_findings(dry_run: bool):
    open_titles = list_open_titles()
    paths = ["src", "tests", "docs", "scripts", "README.md"]
    findings = []

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
                if TODO_RE.search(line):
                    snippet = line.strip()
                    if len(snippet) > 120:
                        snippet = snippet[:117] + "..."
                    findings.append((rel_path, i, snippet))

    # cap per run
    for rel, line_no, snippet in findings[:20]:
        title = f"[Crawler] Offener TODO/FIXME: {rel}:{line_no}"
        if title in open_titles:
            continue
        body = (
            f"Automatisch vom Repository-Crawler erkannt ({now_iso()}).\n\n"
            f"Fundstelle: `{rel}:{line_no}`\n"
            f"Inhalt: `{snippet}`\n\n"
            "Bitte prüfen, ob der Punkt bereits abgedeckt ist. Falls nicht, sauber umsetzen und Nachweis im Abschlusskommentar liefern."
        )
        create_issue(title, body, dry_run=dry_run)


def keyword_matches(text: str, keyword: str) -> bool:
    # Kurze Kürzel (api/gui/qa/e2e) nur als eigenständige Tokens matchen,
    # um False-Positives wie "guide" -> "gui" zu vermeiden.
    if len(keyword) <= 3:
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def compute_workstream_counts(issues):
    counts = {k: 0 for k in WORKSTREAM_KEYWORDS}

    for issue in issues:
        labels = {l["name"] for l in issue.get("labels", [])}
        if "crawler:auto" in labels:
            continue
        if "status:blocked" in labels:
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


def audit_workstream_balance(dry_run: bool):
    """
    Guardrail: Development, Documentation und Testing sollen parallel nachgezogen werden.
    Wenn ein Bereich deutlich hinterherhinkt, wird ein P0-Catch-up-Issue erzeugt.
    """
    open_titles = list_open_titles()

    issues = run_json([
        "issue", "list", "--state", "open", "--limit", "300",
        "--json", "number,title,body,labels"
    ])

    counts = compute_workstream_counts(issues)

    max_count = max(counts.values()) if counts else 0
    min_count = min(counts.values()) if counts else 0

    severe_zero_gap = max_count >= 2 and min_count == 0
    spread_too_large = (max_count - min_count) >= 3

    if not (severe_zero_gap or spread_too_large):
        return

    title = "[Crawler][P0] Workstream-Balance: Development/Dokumentation/Testing angleichen"
    if title in open_titles:
        return

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
        "Hinweis: P0 ist hier ausschließlich für das Aufholen liegengebliebener, kritischer Arbeit reserviert."
    )
    create_issue(title, body, dry_run=dry_run, priority="priority:P0")


def main():
    parser = argparse.ArgumentParser(description="GitHub repo crawler: reopen inconsistent closed issues + create findings")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_label("crawler:auto", "5319e7", "Automatisch vom Crawler erzeugte Findings", dry_run=args.dry_run)
    ensure_label("priority:P0", "b60205", "Kritisch/zeitnah", dry_run=args.dry_run)
    audit_closed_issues(dry_run=args.dry_run)
    scan_repo_for_findings(dry_run=args.dry_run)
    audit_workstream_balance(dry_run=args.dry_run)
    print("crawler run complete")


if __name__ == "__main__":
    main()
