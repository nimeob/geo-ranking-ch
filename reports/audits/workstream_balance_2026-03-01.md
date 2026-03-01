# Workstream-Balance Baseline — 2026-03-01

Kontext: Dieses Dokument dient als **belastbarer Abschlussnachweis** für das Crawler-Finding Issue **#609**.

## Command

```bash
python3 scripts/github_repo_crawler.py --print-workstream-balance --format markdown
```

## Output

```markdown
# Workstream-Balance Baseline (2026-03-01T20:16:57+00:00)

Heuristische Zählung aus offenen, nicht-blockierten Issues (ohne `crawler:auto`).

## Counts
- Development: **4**
- Dokumentation: **5**
- Testing: **4**
- Gap (max-min): **1**
- Ziel-Gap: **<= 2**
- Catch-up nötig: **nein**

## Catch-up-Empfehlung (minimaler Delta-Plan)
- Kein zusätzlicher Delta-Bedarf erkannt.
```
