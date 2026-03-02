# Consistency Report

- Generated at (UTC): `2026-03-02T18:22:56+00:00`
- Schema version: `1.0`
- Total findings: **14**

## Priorisierte Zusammenfassung
- Findings nach Severity: medium=3, low=11
- Findings nach Typ: code_docs_drift_stale_reference=1, code_docs_drift_undocumented_feature=11, vision_issue_coverage_unclear=1, workstream_balance_gap=1

## Vision ↔ Issue Coverage (MVP)

- Vision source: `docs/VISION_PRODUCT.md`
- Anforderungen: **5** (covered=4, unclear=1, missing=0)

| Requirement | Status | Best Match | Matched keywords |
|---|---|---|---|
| M1 — Gebäudeprofil | unclear | #128 (CLOSED, score=1) | adress |
| M2 — Umfeldprofil | covered | #329 (CLOSED, score=2) | erreichbarkeit, basis |
| M3 — Bau-Eignung am Punkt | covered | #405 (CLOSED, score=2) | per, strasse |
| M4 — Explainability | covered | #409 (CLOSED, score=3) | ergebnis, quelle, trennung |
| M5 — Produktoberflächen | covered | #480 (CLOSED, score=6) | api, gui, karten, interaktion, ergebnis, panel |

## Findings

| Severity | Type | Summary | Evidence | Source |
|---|---|---|---|---|
| medium | code_docs_drift_stale_reference | Doku referenziert Route /analyze, die im Code nicht gefunden wurde | `README.md:165` | code_docs_drift:stale_route_reference |
| medium | vision_issue_coverage_unclear | Vision-Anforderung M1 (Gebäudeprofil) ist nur schwach mit Issues verknüpft | `docs/VISION_PRODUCT.md:40`, `#128` | vision_issue_coverage:module_matcher |
| medium | workstream_balance_gap | Workstream-Balance außerhalb Zielkorridor (gap=3, ziel<=2) | `development=6`, `documentation=9`, `testing=7`, `gap=3` | workstream_balance:heuristic_counts |
| low | code_docs_drift_undocumented_feature | Code-Flag ADDRESS_INTEL_MAX_RETRY_AFTER ist in zentraler Doku nicht referenziert | `src/api/address_intel.py:81` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ADDRESS_INTEL_MIN_REQUEST_INTERVAL ist in zentraler Doku nicht referenziert | `src/api/address_intel.py:80` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ANALYZE_DEFAULT_TIMEOUT_SECONDS ist in zentraler Doku nicht referenziert | `src/api/web_service.py:4006` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ANALYZE_MAX_TIMEOUT_SECONDS ist in zentraler Doku nicht referenziert | `src/api/web_service.py:4010` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag APP_VERSION ist in zentraler Doku nicht referenziert | `src/api/web_service.py:3225` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ASYNC_WORKER_STAGE_DELAY_MS ist in zentraler Doku nicht referenziert | `src/api/async_worker_runtime.py:21` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag DICTIONARY_VERSION ist in zentraler Doku nicht referenziert | `src/api/web_service.py:374` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag GIT_SHA ist in zentraler Doku nicht referenziert | `src/api/web_service.py:3285` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag OIDC_CLOCK_SKEW ist in zentraler Doku nicht referenziert | `src/api/oidc_jwt.py:42` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag TLS_REDIRECT_HOST ist in zentraler Doku nicht referenziert | `src/api/web_service.py:4395` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag UI_API_BASE_URL ist in zentraler Doku nicht referenziert | `src/ui/service.py:1602` | code_docs_drift:flag_coverage |
