#!/usr/bin/env python3
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GHA = str(REPO_ROOT / "scripts" / "gha")

GRACE_HOURS = 3
MAX_FAILS = 3

FAIL_PATTERNS = [
    r"curl\s+exit\s+28",
    r"timeout",
    r"timed out",
    r"unreachable",
    r"connection refused",
    r"connection reset",
    r"service unavailable",
    r"endpoint .*nicht erreichbar",
    r"kein erreichbarer .*endpoint",
]
FAIL_RE = re.compile("|".join(FAIL_PATTERNS), re.IGNORECASE)
FOLLOWUP_RE = re.compile(r"follow-up issue\s*#(\d+)", re.IGNORECASE)


def run(args):
    return subprocess.check_output([GHA, *args], cwd=REPO_ROOT, text=True)


def run_json(args):
    return json.loads(run(args))


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def list_blocked_issues():
    return run_json([
        "issue", "list", "--state", "open", "--label", "status:blocked", "--limit", "200",
        "--json", "number,title,labels,url"
    ])


def get_comments(number: int):
    return run_json(["api", f"repos/nimeob/geo-ranking-ch/issues/{number}/comments"])


def get_labels(number: int):
    issue = run_json(["issue", "view", str(number), "--json", "labels"])
    return {l["name"] for l in issue.get("labels", [])}


def has_followup_comment(comments):
    for c in comments:
        if c.get("user", {}).get("login", "").startswith("nipa-openclaw") and FOLLOWUP_RE.search(c.get("body") or ""):
            return True
    return False


def external_fail_comments(comments):
    out = []
    for c in comments:
        body = c.get("body") or ""
        if FAIL_RE.search(body):
            out.append(c)
    return out


def add_comment(number: int, body: str):
    run(["issue", "comment", str(number), "--body", body])


def set_todo(number: int):
    labels = get_labels(number)
    args = ["issue", "edit", str(number)]
    if "status:blocked" in labels:
        args += ["--remove-label", "status:blocked"]
    if "status:todo" not in labels:
        args += ["--add-label", "status:todo"]
    run(args)


def create_followup(parent_number: int, fail_count: int, last_fail_iso: str):
    title = f"Follow-up: Externer Blocker für #{parent_number} nach {MAX_FAILS} Fehlversuchen"
    body = (
        f"Quelle: Retry-Supervisor für #{parent_number}.\n\n"
        f"## Problem\n"
        f"Das Parent-Issue ist aufgrund eines externen/temporären Fehlers wiederholt fehlgeschlagen.\n"
        f"Fehlversuche gezählt: **{fail_count}/{MAX_FAILS}** (letzter Fehler: {last_fail_iso}).\n\n"
        "## Ziel\n"
        "Externen Blocker beheben (Endpoint/Deployment/Netz/Token), sodass das Parent-Issue wieder reproduzierbar testbar ist.\n\n"
        "## Definition of Done\n"
        "- [ ] Externer Fehler reproduziert und Root Cause benannt\n"
        "- [ ] Konkrete Behebung umgesetzt oder benötigter externer Input geklärt\n"
        "- [ ] Parent-Issue kann danach ohne Timeout/Reachability-Fehler erneut laufen\n"
        f"- [ ] Rückverlinkung und Recheck von #{parent_number} dokumentiert\n"
    )
    url = run([
        "issue", "create",
        "--title", title,
        "--body", body,
        "--label", "backlog",
        "--label", "priority:P1",
        "--label", "status:todo",
    ]).strip()
    m = re.search(r"/issues/(\d+)", url)
    child = m.group(1) if m else "?"
    add_comment(
        parent_number,
        f"Retry-Supervisor: {MAX_FAILS}/{MAX_FAILS} Fehlversuche erreicht. Follow-up issue #{child} erstellt. "
        "Parent bleibt auf status:blocked, bis externer Blocker geklärt ist."
    )


def process_issue(issue):
    n = issue["number"]
    comments = get_comments(n)
    fails = external_fail_comments(comments)
    if not fails:
        return

    fail_count = len(fails)
    last_fail = max(fails, key=lambda c: c.get("created_at", ""))
    last_fail_dt = parse_dt(last_fail["created_at"])
    grace_until = last_fail_dt + timedelta(hours=GRACE_HOURS)

    if fail_count >= MAX_FAILS:
        if not has_followup_comment(comments):
            create_followup(n, fail_count, last_fail_dt.isoformat())
        return

    if now_utc() >= grace_until:
        set_todo(n)
        next_attempt = fail_count + 1
        add_comment(
            n,
            (
                "Retry-Supervisor: Grace-Period abgelaufen (3h). "
                f"Issue zurück auf status:todo für Retry-Versuch {next_attempt}/{MAX_FAILS}."
            ),
        )


def main():
    for issue in list_blocked_issues():
        try:
            process_issue(issue)
        except subprocess.CalledProcessError as e:
            print(f"ERROR processing #{issue.get('number')}: {e}")


if __name__ == "__main__":
    main()
