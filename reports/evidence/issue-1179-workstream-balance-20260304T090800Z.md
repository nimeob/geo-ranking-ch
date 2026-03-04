# Issue #1179 — Workstream-Balance Catch-up (2026-03-04)

## Reproduzierbare Abfrage

```bash
python3 scripts/github_repo_crawler.py --dry-run --print-workstream-balance --format json
```

## Vorher (09:05:58Z)

- Development: **13**
- Dokumentation: **9**
- Testing: **7**
- Gap: **6** (Ziel: <= 2)
- Delta-Plan: Dokumentation **+2**, Testing **+4** (total +6)

## Umgesetzter Catch-up-Plan

Neue, worker-claimable Catch-up-Issues:

- #1183 Docs Catch-up: Boundary-Contract Quick-Reference
- #1184 Docs Catch-up: Migrations-Runbook History/Trace
- #1185 Testing Catch-up: Boundary-Linter Unit-Tests
- #1186 Testing Catch-up: Deprecated-Endpunkte Warning/Sunset Tests
- #1187 Testing Catch-up: History-Migration Fluss-Tests
- #1188 Testing Catch-up: Trace-Migration E2E-Regression

Label-Set je Child: `backlog`, `status:todo`, passende `priority:*`, `enhancement` (+ Workstream-Labels `documentation` bzw. `testing`/`qa`).

## Nachher (09:08:00Z)

- Development: **13**
- Dokumentation: **15**
- Testing: **13**
- Gap: **2** (Ziel erreicht)
- Restdelta: **0**

## Ergebnis

Mindeststand pro Workstream liegt im Zielkorridor (`gap <= 2`).
