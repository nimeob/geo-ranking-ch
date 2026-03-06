# Consistency Report

- Generated at (UTC): `2026-03-06T17:46:30+00:00`
- Schema version: `1.0`
- Total findings: **15**

## Priorisierte Zusammenfassung
- Findings nach Severity: medium=3, low=12
- Findings nach Typ: code_docs_drift_undocumented_feature=12, vision_issue_coverage_unclear=3

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
| low | code_docs_drift_undocumented_feature | Code-Flag ADDRESS_INTEL_MAX_RETRY_AFTER ist in zentraler Doku nicht referenziert | `src/api/address_intel.py:81` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ADDRESS_INTEL_MIN_REQUEST_INTERVAL ist in zentraler Doku nicht referenziert | `src/api/address_intel.py:80` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ANALYZE_DEFAULT_TIMEOUT_SECONDS ist in zentraler Doku nicht referenziert | `src/api/web_service.py:5149` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ANALYZE_MAX_TIMEOUT_SECONDS ist in zentraler Doku nicht referenziert | `src/api/web_service.py:5153` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag APP_VERSION ist in zentraler Doku nicht referenziert | `src/api/web_service.py:4190` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ASYNC_DB_URL ist in zentraler Doku nicht referenziert | `src/shared/async_job_store_db.py:117` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ASYNC_STORE_BACKEND ist in zentraler Doku nicht referenziert | `src/api/web_service.py:363` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag ASYNC_WORKER_STAGE_DELAY_MS ist in zentraler Doku nicht referenziert | `src/api/async_worker_runtime.py:21` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag BFF_OIDC_REDIRECT_URI ist in zentraler Doku nicht referenziert | `src/api/web_service.py:859` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag DATABASE_URL ist in zentraler Doku nicht referenziert | `src/shared/async_job_store_db.py:117` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag DB_HOST ist in zentraler Doku nicht referenziert | `src/shared/async_job_store_db.py:122` | code_docs_drift:flag_coverage |
| low | code_docs_drift_undocumented_feature | Code-Flag DB_NAME ist in zentraler Doku nicht referenziert | `src/shared/async_job_store_db.py:130` | code_docs_drift:flag_coverage |
