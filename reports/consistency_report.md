# Consistency Report

- Generated at (UTC): `2026-02-27T06:13:32+00:00`
- Schema version: `1.0`
- Total findings: **1**

## Priorisierte Zusammenfassung
- Findings nach Severity: medium=1
- Findings nach Typ: workstream_balance_gap=1

## Vision ↔ Issue Coverage (MVP)

- Vision source: `docs/VISION_PRODUCT.md`
- Anforderungen: **5** (covered=5, unclear=0, missing=0)

| Requirement | Status | Best Match | Matched keywords |
|---|---|---|---|
| M1 — Gebäudeprofil | covered | #6 (OPEN, score=2) | gebäudeprofil, adress |
| M2 — Umfeldprofil | covered | #6 (OPEN, score=2) | umfeldprofil, lärm |
| M3 — Bau-Eignung am Punkt | covered | #110 (OPEN, score=5) | bau, eignung, standortanalyse, hangneigung, distanz |
| M4 — Explainability | covered | #14 (OPEN, score=4) | ergebnis, quelle, harte, ableitungen |
| M5 — Produktoberflächen | covered | #17 (OPEN, score=7) | api, first, gui, karten, interaktion, ergebnis, panel |

## Findings

| Severity | Type | Summary | Evidence | Source |
|---|---|---|---|---|
| medium | workstream_balance_gap | Workstream-Balance außerhalb Zielkorridor (gap=3, ziel<=2) | `development=2`, `documentation=5`, `testing=5`, `gap=3` | workstream_balance:heuristic_counts |
