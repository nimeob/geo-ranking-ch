# Consistency Report

- Generated at (UTC): `2026-03-01T16:16:56+00:00`
- Schema version: `1.0`
- Total findings: **33**

## Priorisierte Zusammenfassung
- Findings nach Severity: high=1, medium=22, low=10
- Findings nach Typ: code_docs_drift_stale_reference=2, code_docs_drift_undocumented_feature=10, issue_closure_consistency=20, workstream_balance_gap=1

## Vision ↔ Issue Coverage (MVP)

- Vision source: `docs/VISION_PRODUCT.md`
- Anforderungen: **5** (covered=5, unclear=0, missing=0)

| Requirement | Status | Best Match | Matched keywords |
|---|---|---|---|
| M1 — Gebäudeprofil | covered | #6 (CLOSED, score=2) | gebäudeprofil, adress |
| M2 — Umfeldprofil | covered | #6 (CLOSED, score=2) | umfeldprofil, lärm |
| M3 — Bau-Eignung am Punkt | covered | #110 (CLOSED, score=5) | bau, eignung, standortanalyse, hangneigung, distanz |
| M4 — Explainability | covered | #14 (CLOSED, score=4) | ergebnis, quelle, harte, ableitungen |
| M5 — Produktoberflächen | covered | #17 (CLOSED, score=7) | api, first, gui, karten, interaktion, ergebnis, panel |

## Findings

| Severity | Type | Summary | Evidence | Source |
|---|---|---|---|---|
| high | workstream_balance_gap | Workstream-Balance außerhalb Zielkorridor (gap=10, ziel<=2) | `development=12`, `documentation=18`, `testing=8`, `gap=10` | workstream_balance:heuristic_counts |
| medium | code_docs_drift_stale_reference | Doku referenziert Route /analyze, die im Code nicht gefunden wurde | `README.md:154` | code_docs_drift:stale_route_reference |
| medium | code_docs_drift_stale_reference | Doku referenziert Route /api/v1/dictionaries*, die im Code nicht gefunden wurde | `docs/OPERATIONS.md:143` | code_docs_drift:stale_route_reference |
| medium | issue_closure_consistency | Geschlossenes Issue #567 hat inkonsistente Abschlusssignale | `#567`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #568 hat inkonsistente Abschlusssignale | `#568`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #570 hat inkonsistente Abschlusssignale | `#570`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #573 hat inkonsistente Abschlusssignale | `#573`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #574 hat inkonsistente Abschlusssignale | `#574`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #576 hat inkonsistente Abschlusssignale | `#576`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #577 hat inkonsistente Abschlusssignale | `#577`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #585 hat inkonsistente Abschlusssignale | `#585`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #586 hat inkonsistente Abschlusssignale | `#586`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #587 hat inkonsistente Abschlusssignale | `#587`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #588 hat inkonsistente Abschlusssignale | `#588`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #592 hat inkonsistente Abschlusssignale | `#592`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #593 hat inkonsistente Abschlusssignale | `#593`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #594 hat inkonsistente Abschlusssignale | `#594`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #596 hat inkonsistente Abschlusssignale | `#596`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #599 hat inkonsistente Abschlusssignale | `#599`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #600 hat inkonsistente Abschlusssignale | `#600`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #601 hat inkonsistente Abschlusssignale | `#601`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #602 hat inkonsistente Abschlusssignale | `#602`, `reason_count=1` | github_issue_audit:closed_issue_review |
| medium | issue_closure_consistency | Geschlossenes Issue #606 hat inkonsistente Abschlusssignale | `#606`, `reason_count=1` | github_issue_audit:closed_issue_review |
| low | code_docs_drift_undocumented_feature | Code-Flag ADDRESS_INTEL_MAX_RETRY_AFTER ist in zentraler Doku nicht referenziert | `src/api/address_intel.py:70` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ADDRESS_INTEL_MIN_REQUEST_INTERVAL ist in zentraler Doku nicht referenziert | `src/api/address_intel.py:69` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ANALYZE_DEFAULT_TIMEOUT_SECONDS ist in zentraler Doku nicht referenziert | `src/api/web_service.py:2785` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ANALYZE_MAX_TIMEOUT_SECONDS ist in zentraler Doku nicht referenziert | `src/api/web_service.py:2789` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag APP_VERSION ist in zentraler Doku nicht referenziert | `src/api/web_service.py:2308` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ASYNC_WORKER_STAGE_DELAY_MS ist in zentraler Doku nicht referenziert | `src/api/async_worker_runtime.py:21` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag DICTIONARY_VERSION ist in zentraler Doku nicht referenziert | `src/api/web_service.py:181` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag GIT_SHA ist in zentraler Doku nicht referenziert | `src/api/web_service.py:2340` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag TLS_REDIRECT_HOST ist in zentraler Doku nicht referenziert | `src/api/web_service.py:3085` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag UI_API_BASE_URL ist in zentraler Doku nicht referenziert | `src/ui/service.py:117` | code_docs_drift:flag_coverage |
