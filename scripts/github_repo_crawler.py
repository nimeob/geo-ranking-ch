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
TODO_TOKEN_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
TODO_PREFIX_CONTEXT_RE = re.compile(
    r"^\s*(?:(?:#|//|/\*|<!--)\s*)?(?:[-*]\s+)?(?:\[[ xX]\]\s+)?(TODO|FIXME|HACK|XXX)\b",
    re.IGNORECASE,
)
TODO_INLINE_COMMENT_CONTEXT_RE = re.compile(r"(?:#|//|/\*|<!--)\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
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
WORKSTREAM_LABELS = {
    "development": "Development",
    "documentation": "Dokumentation",
    "testing": "Testing",
}

WORKSTREAM_BALANCE_ISSUE_TITLE = "[Crawler][P0] Workstream-Balance: Development/Dokumentation/Testing angleichen"
CONSISTENCY_REPORT_JSON = Path("reports/consistency_report.json")
CONSISTENCY_REPORT_MD = Path("reports/consistency_report.md")
SEVERITY_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
VISION_DOC_PATH = Path("docs/VISION_PRODUCT.md")
VISION_SCOPE_HEADING = "## Scope-Module"
VISION_REQUIREMENT_HEADING_RE = re.compile(r"^###\s*(M\d+)\s+—\s+(.+?)\s*$")
TOKEN_RE = re.compile(r"[a-z0-9äöüß]{3,}", re.IGNORECASE)
MATCH_STOPWORDS = {
    "und", "oder", "der", "die", "das", "mit", "von", "für", "ein", "eine", "einer", "eines",
    "inkl", "inklusive", "ohne", "sowie", "mehr", "mvp", "modul", "module", "profil", "punkt", "ch",
    "the", "and", "for", "with", "from", "into", "via", "read", "only", "check",
}
CODE_DOCS_PRIMARY_PATHS = [
    Path("README.md"),
    Path("docs/OPERATIONS.md"),
]
CODE_DOCS_API_DOCS_DIR = Path("docs/api")
CODE_ROUTE_RE = re.compile(r"@app\.(?:route|get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]")
DOC_ROUTE_RE = re.compile(r"`(/[^`\s]+)`")
ENV_FLAG_RE = re.compile(r"getenv\(\s*['\"]([A-Z][A-Z0-9_]{2,})['\"]")
CODE_DOCS_MAX_FINDINGS = 12


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


def build_consistency_report(
    findings: list[dict[str, Any]],
    generated_at: str | None = None,
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ordered_findings = sort_findings(findings)
    by_severity = Counter(f.get("severity", "medium") for f in ordered_findings)
    by_type = Counter(f.get("type", "unknown") for f in ordered_findings)

    report = {
        "schema_version": "1.0",
        "generated_at": generated_at or now_iso(),
        "summary": {
            "total_findings": len(ordered_findings),
            "by_severity": dict(sorted(by_severity.items(), key=lambda kv: SEVERITY_PRIORITY.get(kv[0], 99))),
            "by_type": dict(sorted(by_type.items())),
        },
        "findings": ordered_findings,
    }

    if coverage:
        report["coverage"] = coverage

    return report


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

    coverage = report.get("coverage") or {}
    if coverage:
        lines.extend(["", "## Vision ↔ Issue Coverage (MVP)", ""])
        lines.append(f"- Vision source: `{coverage.get('vision_source', VISION_DOC_PATH.as_posix())}`")
        lines.append(
            "- Anforderungen: **{total}** (covered={covered}, unclear={unclear}, missing={missing})".format(
                total=coverage.get("total_requirements", 0),
                covered=coverage.get("covered", 0),
                unclear=coverage.get("unclear", 0),
                missing=coverage.get("missing", 0),
            )
        )

        requirement_rows = coverage.get("requirements") or []
        if requirement_rows:
            lines.extend([
                "",
                "| Requirement | Status | Best Match | Matched keywords |",
                "|---|---|---|---|",
            ])
            for req in requirement_rows:
                best_match = req.get("best_match") or {}
                best_match_ref = "--"
                if best_match.get("number") is not None:
                    best_match_ref = "#{number} ({state}, score={score})".format(
                        number=best_match.get("number"),
                        state=best_match.get("state", "unknown"),
                        score=best_match.get("score", 0),
                    )
                matched_keywords = ", ".join(req.get("matched_keywords") or []) or "--"
                lines.append(
                    "| {requirement} | {status} | {best_match} | {keywords} |".format(
                        requirement=f"{req.get('id', '?')} — {req.get('title', '')}".strip(),
                        status=req.get("status", "unknown"),
                        best_match=best_match_ref,
                        keywords=matched_keywords.replace("|", "\\|"),
                    )
                )

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


def tokenize_text(text: str) -> list[str]:
    seen = set()
    tokens: list[str] = []
    for token in TOKEN_RE.findall((text or "").lower()):
        if token in MATCH_STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def parse_vision_requirements(markdown: str, source_path: Path = VISION_DOC_PATH) -> list[dict[str, Any]]:
    lines = markdown.splitlines()
    in_scope = False
    current: dict[str, Any] | None = None
    requirements: list[dict[str, Any]] = []

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()

        if line.startswith("## "):
            if line.startswith(VISION_SCOPE_HEADING):
                in_scope = True
                continue
            if in_scope:
                break

        if not in_scope:
            continue

        header_match = VISION_REQUIREMENT_HEADING_RE.match(line)
        if header_match:
            if current is not None:
                scope_text = " ".join(current["bullets"])
                current["tokens"] = tokenize_text(f"{current['title']} {scope_text}")
                requirements.append(current)

            current = {
                "id": header_match.group(1),
                "title": header_match.group(2),
                "line": idx,
                "source": source_path.as_posix(),
                "bullets": [],
            }
            continue

        if current is not None and line.strip().startswith("-"):
            current["bullets"].append(line.strip().lstrip("-").strip())

    if current is not None:
        scope_text = " ".join(current["bullets"])
        current["tokens"] = tokenize_text(f"{current['title']} {scope_text}")
        requirements.append(current)

    return requirements


def get_issues_for_coverage(limit: int = 300) -> list[dict[str, Any]]:
    open_issues = run_json([
        "issue", "list", "--state", "open", "--limit", str(limit),
        "--json", "number,title,body,state,url"
    ])
    closed_issues = run_json([
        "issue", "list", "--state", "closed", "--limit", str(limit),
        "--json", "number,title,body,state,url"
    ])

    merged: dict[int, dict[str, Any]] = {}
    for issue in [*open_issues, *closed_issues]:
        merged[issue.get("number")] = issue
    return list(merged.values())


def match_requirement_to_issues(requirement: dict[str, Any], issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tokens = requirement.get("tokens") or []
    if not tokens:
        return []

    matches: list[dict[str, Any]] = []
    for issue in issues:
        haystack = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
        matched_keywords = [token for token in tokens if keyword_matches(haystack, token)]
        score = len(matched_keywords)
        if score == 0:
            continue

        matches.append(
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state", "open"),
                "url": issue.get("url"),
                "score": score,
                "matched_keywords": matched_keywords,
            }
        )

    return sorted(
        matches,
        key=lambda item: (
            -item.get("score", 0),
            0 if item.get("state") == "open" else 1,
            item.get("number", 0),
        ),
    )


def assess_vision_issue_coverage(requirements: list[dict[str, Any]], issues: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    covered = 0
    unclear = 0
    missing = 0

    for req in requirements:
        matches = match_requirement_to_issues(req, issues)
        best_match = matches[0] if matches else None
        status = "missing"
        matched_keywords: list[str] = []

        if best_match is not None:
            matched_keywords = best_match.get("matched_keywords", [])
            if best_match.get("score", 0) >= 2:
                status = "covered"
                covered += 1
            else:
                status = "unclear"
                unclear += 1
        else:
            missing += 1

        if status == "missing":
            matched_keywords = []

        rows.append(
            {
                "id": req.get("id"),
                "title": req.get("title"),
                "line": req.get("line"),
                "status": status,
                "matched_keywords": matched_keywords,
                "best_match": (
                    {
                        "number": best_match.get("number"),
                        "state": best_match.get("state"),
                        "score": best_match.get("score"),
                        "url": best_match.get("url"),
                    }
                    if best_match
                    else None
                ),
            }
        )

    return {
        "vision_source": VISION_DOC_PATH.as_posix(),
        "total_requirements": len(requirements),
        "covered": covered,
        "unclear": unclear,
        "missing": missing,
        "requirements": rows,
    }


def collect_vision_issue_coverage_findings(coverage: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for req in coverage.get("requirements", []):
        requirement_ref = f"{req.get('id')} ({req.get('title')})"
        evidence = [
            {
                "kind": "file_line",
                "path": VISION_DOC_PATH.as_posix(),
                "line": req.get("line"),
            }
        ]

        best_match = req.get("best_match") or {}
        if best_match.get("number") is not None:
            evidence.append(
                {
                    "kind": "issue",
                    "number": best_match.get("number"),
                    "url": best_match.get("url"),
                }
            )

        if req.get("status") == "missing":
            findings.append(
                build_finding(
                    finding_type="vision_issue_coverage_gap",
                    severity="high",
                    summary=f"Vision-Anforderung {requirement_ref} hat keine Issue-Zuordnung",
                    evidence=evidence,
                    source={"kind": "vision_issue_coverage", "component": "module_matcher", "requirement_id": req.get("id")},
                )
            )
        elif req.get("status") == "unclear":
            findings.append(
                build_finding(
                    finding_type="vision_issue_coverage_unclear",
                    severity="medium",
                    summary=f"Vision-Anforderung {requirement_ref} ist nur schwach mit Issues verknüpft",
                    evidence=evidence,
                    source={"kind": "vision_issue_coverage", "component": "module_matcher", "requirement_id": req.get("id")},
                )
            )

    return findings


def audit_vision_issue_coverage() -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    vision_abs = (REPO_ROOT / VISION_DOC_PATH).resolve()
    if not vision_abs.exists():
        return [], None

    markdown = vision_abs.read_text(encoding="utf-8", errors="ignore")
    requirements = parse_vision_requirements(markdown)
    if not requirements:
        return [], {
            "vision_source": VISION_DOC_PATH.as_posix(),
            "total_requirements": 0,
            "covered": 0,
            "unclear": 0,
            "missing": 0,
            "requirements": [],
        }

    issues = get_issues_for_coverage(limit=300)
    coverage = assess_vision_issue_coverage(requirements, issues)
    findings = collect_vision_issue_coverage_findings(coverage)
    return findings, coverage


def normalize_route(route: str) -> str:
    normalized = (route or "").strip()
    if not normalized:
        return normalized
    normalized = normalized.split("?", 1)[0]
    normalized = normalized.rstrip(").,;:")
    if len(normalized) > 1 and normalized.endswith("/"):
        normalized = normalized[:-1]
    return normalized


def extract_code_route_indicators(repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    indicators: list[dict[str, Any]] = []
    src_root = repo_root / "src"
    if not src_root.exists():
        return indicators

    for file_path in src_root.rglob("*.py"):
        rel_path = file_path.relative_to(repo_root).as_posix()
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in CODE_ROUTE_RE.finditer(line):
                route = normalize_route(match.group(1))
                if not route.startswith("/"):
                    continue
                indicators.append(
                    {
                        "route": route,
                        "path": rel_path,
                        "line": line_no,
                    }
                )

    return indicators


def extract_code_env_flags(repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    indicators: list[dict[str, Any]] = []
    src_root = repo_root / "src"
    if not src_root.exists():
        return indicators

    for file_path in src_root.rglob("*.py"):
        rel_path = file_path.relative_to(repo_root).as_posix()
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in ENV_FLAG_RE.finditer(line):
                indicators.append(
                    {
                        "flag": match.group(1),
                        "path": rel_path,
                        "line": line_no,
                    }
                )

    return indicators


def load_docs_snapshot(repo_root: Path = REPO_ROOT) -> tuple[str, list[dict[str, Any]]]:
    docs_paths: list[Path] = []
    for rel_path in CODE_DOCS_PRIMARY_PATHS:
        abs_path = repo_root / rel_path
        if abs_path.exists():
            docs_paths.append(abs_path)

    api_docs_dir = repo_root / CODE_DOCS_API_DOCS_DIR
    if api_docs_dir.exists():
        docs_paths.extend(sorted(api_docs_dir.rglob("*.md")))

    combined_text_parts: list[str] = []
    documented_routes: list[dict[str, Any]] = []

    for doc_path in docs_paths:
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        combined_text_parts.append(text.lower())
        rel_path = doc_path.relative_to(repo_root).as_posix()

        for line_no, line in enumerate(text.splitlines(), start=1):
            line_upper = line.upper()
            if not any(verb in line_upper for verb in ("GET", "POST", "PUT", "DELETE", "PATCH", "ENDPOINT")):
                continue
            for match in DOC_ROUTE_RE.finditer(line):
                route = normalize_route(match.group(1))
                if not route.startswith("/") or "//" in route:
                    continue
                documented_routes.append(
                    {
                        "route": route,
                        "path": rel_path,
                        "line": line_no,
                    }
                )

    return "\n".join(combined_text_parts), documented_routes


def audit_code_docs_drift(max_findings: int = CODE_DOCS_MAX_FINDINGS) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    docs_text, documented_route_refs = load_docs_snapshot(REPO_ROOT)

    code_routes = extract_code_route_indicators(REPO_ROOT)
    code_env_flags = extract_code_env_flags(REPO_ROOT)

    route_first_seen: dict[str, dict[str, Any]] = {}
    for route_ref in code_routes:
        route = route_ref.get("route")
        if route and route not in route_first_seen:
            route_first_seen[route] = route_ref

    for route, route_ref in sorted(route_first_seen.items()):
        if len(findings) >= max_findings:
            return findings
        if route.lower() in docs_text:
            continue
        findings.append(
            build_finding(
                finding_type="code_docs_drift_undocumented_feature",
                severity="medium",
                summary=f"Code-Route {route} ist in zentraler Doku nicht referenziert",
                evidence=[
                    {
                        "kind": "file_line",
                        "path": route_ref.get("path"),
                        "line": route_ref.get("line"),
                    }
                ],
                source={"kind": "code_docs_drift", "component": "route_coverage"},
            )
        )

    flag_first_seen: dict[str, dict[str, Any]] = {}
    for flag_ref in code_env_flags:
        flag = flag_ref.get("flag")
        if flag and flag not in flag_first_seen:
            flag_first_seen[flag] = flag_ref

    for flag, flag_ref in sorted(flag_first_seen.items()):
        if len(findings) >= max_findings:
            return findings
        if flag.lower() in docs_text:
            continue
        findings.append(
            build_finding(
                finding_type="code_docs_drift_undocumented_feature",
                severity="low",
                summary=f"Code-Flag {flag} ist in zentraler Doku nicht referenziert",
                evidence=[
                    {
                        "kind": "file_line",
                        "path": flag_ref.get("path"),
                        "line": flag_ref.get("line"),
                    }
                ],
                source={"kind": "code_docs_drift", "component": "flag_coverage"},
            )
        )

    known_code_routes = set(route_first_seen.keys())
    stale_route_refs: dict[str, dict[str, Any]] = {}
    for doc_ref in documented_route_refs:
        route = doc_ref.get("route")
        if not route:
            continue
        if route in known_code_routes:
            continue
        if route not in stale_route_refs:
            stale_route_refs[route] = doc_ref

    for route, doc_ref in sorted(stale_route_refs.items()):
        if len(findings) >= max_findings:
            return findings
        findings.append(
            build_finding(
                finding_type="code_docs_drift_stale_reference",
                severity="medium",
                summary=f"Doku referenziert Route {route}, die im Code nicht gefunden wurde",
                evidence=[
                    {
                        "kind": "file_line",
                        "path": doc_ref.get("path"),
                        "line": doc_ref.get("line"),
                    }
                ],
                source={"kind": "code_docs_drift", "component": "stale_route_reference"},
            )
        )

    return findings


def is_actionable_todo_line(line: str) -> bool:
    if not TODO_TOKEN_RE.search(line):
        return False
    if NON_ACTIONABLE_TODO_RE.search(line):
        return False
    if TODO_PREFIX_CONTEXT_RE.search(line):
        return True
    if TODO_INLINE_COMMENT_CONTEXT_RE.search(line):
        return True
    return False


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


def build_workstream_catchup_plan(counts: dict[str, int], *, target_gap_max: int, severe_zero_gap: bool) -> dict[str, Any]:
    if not counts:
        return {
            "target_min_count": 0,
            "total_delta": 0,
            "categories": [],
        }

    max_count = max(counts.values())
    target_min_count = max(max_count - target_gap_max, 1 if severe_zero_gap else 0)

    categories = []
    for category in sorted(counts.keys()):
        current = counts[category]
        delta = max(0, target_min_count - current)
        if delta <= 0:
            continue
        categories.append(
            {
                "category": category,
                "label": WORKSTREAM_LABELS.get(category, category),
                "current": current,
                "target": target_min_count,
                "delta": delta,
            }
        )

    return {
        "target_min_count": target_min_count,
        "total_delta": sum(item["delta"] for item in categories),
        "categories": categories,
    }


def format_workstream_catchup_lines(catchup_plan: dict[str, Any]) -> list[str]:
    categories = catchup_plan.get("categories") or []
    if not categories:
        return ["- Kein zusätzlicher Delta-Bedarf erkannt."]

    lines = [f"- Ziel-Mindeststand je Workstream: **{catchup_plan['target_min_count']}**"]
    for item in categories:
        lines.append(
            "- {label}: **+{delta}** (aktuell {current}, Ziel >= {target})".format(
                label=item["label"],
                delta=item["delta"],
                current=item["current"],
                target=item["target"],
            )
        )
    return lines


def format_workstream_catchup_issue_block(catchup_plan: dict[str, Any]) -> str:
    lines = ["## Catch-up-Empfehlung (minimaler Delta-Plan)", *format_workstream_catchup_lines(catchup_plan)]
    return "\n".join(lines)


def build_workstream_balance_baseline(issues):
    counts = compute_workstream_counts(issues)
    max_count = max(counts.values()) if counts else 0
    min_count = min(counts.values()) if counts else 0
    gap = max_count - min_count
    severe_zero_gap = max_count >= 2 and min_count == 0
    spread_too_large = gap >= 3
    target_gap_max = 2

    return {
        "counts": counts,
        "max_count": max_count,
        "min_count": min_count,
        "gap": gap,
        "target_gap_max": target_gap_max,
        "severe_zero_gap": severe_zero_gap,
        "spread_too_large": spread_too_large,
        "needs_catchup": severe_zero_gap or spread_too_large,
        "catchup_plan": build_workstream_catchup_plan(
            counts,
            target_gap_max=target_gap_max,
            severe_zero_gap=severe_zero_gap,
        ),
    }


def format_workstream_balance_markdown(baseline, generated_at: str):
    counts = baseline["counts"]
    catchup_block = "\n".join(format_workstream_catchup_lines(baseline["catchup_plan"]))
    return (
        f"# Workstream-Balance Baseline ({generated_at})\n\n"
        "Heuristische Zählung aus offenen, nicht-blockierten Issues (ohne `crawler:auto`).\n\n"
        "## Counts\n"
        f"- Development: **{counts['development']}**\n"
        f"- Dokumentation: **{counts['documentation']}**\n"
        f"- Testing: **{counts['testing']}**\n"
        f"- Gap (max-min): **{baseline['gap']}**\n"
        f"- Ziel-Gap: **<= {baseline['target_gap_max']}**\n"
        f"- Catch-up nötig: **{'ja' if baseline['needs_catchup'] else 'nein'}**\n\n"
        "## Catch-up-Empfehlung (minimaler Delta-Plan)\n"
        f"{catchup_block}\n"
    )


def write_report_output(rendered: str, output_file: str | None) -> Path | None:
    if not output_file:
        return None

    target = Path(output_file)
    if not target.is_absolute():
        target = REPO_ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = rendered if rendered.endswith("\n") else f"{rendered}\n"
    target.write_text(payload, encoding="utf-8")
    return target


def print_workstream_balance_report(report_format: str, output_file: str | None = None):
    issues = get_open_issues_for_workstream_balance()
    baseline = build_workstream_balance_baseline(issues)
    generated_at = now_iso()

    if report_format == "json":
        rendered = json.dumps(
            {
                "generated_at": generated_at,
                **baseline,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    else:
        rendered = format_workstream_balance_markdown(baseline, generated_at)

    print(rendered)
    write_report_output(rendered, output_file)


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

    catchup_block = format_workstream_catchup_issue_block(baseline["catchup_plan"])
    body = (
        f"Automatisch vom Repository-Crawler erkannt ({now_iso()}).\n\n"
        "Es besteht ein Ungleichgewicht zwischen den offenen, nicht-blockierten Arbeitsströmen.\n"
        "Regel: Development, Dokumentation und Testing sollen auf ähnlichem Fortschrittsniveau bleiben.\n\n"
        "Aktuelle Zählung (heuristisch, aus offenen Issues):\n"
        f"- Development: **{counts['development']}**\n"
        f"- Dokumentation: **{counts['documentation']}**\n"
        f"- Testing: **{counts['testing']}**\n\n"
        f"{catchup_block}\n\n"
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
    parser.add_argument(
        "--output-file",
        help=(
            "Optionaler Dateipfad für persistente Report-Ausgabe bei --print-workstream-balance. "
            "Relative Pfade werden ab Repo-Root aufgelöst."
        ),
    )
    args = parser.parse_args()

    if args.print_workstream_balance:
        print_workstream_balance_report(report_format=args.format, output_file=args.output_file)
        return

    ensure_label("crawler:auto", "5319e7", "Automatisch vom Crawler erzeugte Findings", dry_run=args.dry_run)
    ensure_label("priority:P0", "b60205", "Kritisch/zeitnah", dry_run=args.dry_run)

    findings: list[dict[str, Any]] = []
    findings.extend(audit_closed_issues(dry_run=args.dry_run))
    findings.extend(scan_repo_for_findings(dry_run=args.dry_run))
    coverage_findings, coverage = audit_vision_issue_coverage()
    findings.extend(coverage_findings)
    findings.extend(audit_code_docs_drift(max_findings=CODE_DOCS_MAX_FINDINGS))
    findings.extend(audit_workstream_balance(dry_run=args.dry_run))

    report = build_consistency_report(findings, coverage=coverage)
    json_path, md_path = write_consistency_reports(report)
    print(f"consistency reports written: {json_path.relative_to(REPO_ROOT)}, {md_path.relative_to(REPO_ROOT)}")
    print("crawler run complete")


if __name__ == "__main__":
    main()
