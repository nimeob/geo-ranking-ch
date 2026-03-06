# Consistency Report

- Generated at (UTC): `2026-03-06T19:16:00+00:00`
- Schema version: `1.0`
- Total findings: **3**

## Priorisierte Zusammenfassung
- Findings nach Severity: medium=3
- Findings nach Typ: vision_issue_coverage_unclear=3

## Vision ↔ Issue Coverage (MVP)

- Vision source: `docs/VISION_PRODUCT.md`
- Anforderungen: **5** (covered=2, unclear=3, missing=0)

| Requirement | Status | Best Match | Matched keywords |
|---|---|---|---|
| M1 — Gebäudeprofil | unclear | #646 (CLOSED, score=1) | adress |
| M2 — Umfeldprofil | unclear | #619 (CLOSED, score=1) | basis |
| M3 — Bau-Eignung am Punkt | unclear | #660 (CLOSED, score=1) | per |
| M4 — Explainability | covered | #648 (CLOSED, score=2) | explainability, quelle |
| M5 — Produktoberflächen | covered | #777 (CLOSED, score=4) | api, first, ergebnis, panel |

## Findings

| Severity | Type | Summary | Evidence | Source |
|---|---|---|---|---|
| medium | vision_issue_coverage_unclear | Vision-Anforderung M1 (Gebäudeprofil) ist nur schwach mit Issues verknüpft | `docs/VISION_PRODUCT.md:40`, `#646` | vision_issue_coverage:module_matcher |
| medium | vision_issue_coverage_unclear | Vision-Anforderung M2 (Umfeldprofil) ist nur schwach mit Issues verknüpft | `docs/VISION_PRODUCT.md:44`, `#619` | vision_issue_coverage:module_matcher |
| medium | vision_issue_coverage_unclear | Vision-Anforderung M3 (Bau-Eignung am Punkt) ist nur schwach mit Issues verknüpft | `docs/VISION_PRODUCT.md:49`, `#660` | vision_issue_coverage:module_matcher |
