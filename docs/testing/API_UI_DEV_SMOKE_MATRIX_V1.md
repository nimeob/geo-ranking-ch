# API/UI Testmatrix v1 (Dev)

Status: 2026-03-04  
Owner-Issue: #1174  
Scope: API/UI-Entkopplung (Auth, History, Trace, Boundary)

## Pflichtfälle (genau 6)

| # | Pflichtfall | Ziel + Eingangsdaten | Pass/Fail-Kriterium | Testebene | Owner | Trigger | Laufzeitklasse | Referenz (bestehend/neu) |
|---|---|---|---|---|---|---|---|---|
| 1 | UI Login erfolgreich | **Ziel:** Session-basierter Login-End-to-End funktioniert.<br>**Eingangsdaten:** BFF-OIDC aktiv, gültiger OIDC Callback (`code`,`state`). | **PASS:** `/auth/login` startet Redirect-Flow, Session-Cookie wird gesetzt, geschützter Flow läuft durch.<br>**FAIL:** kein Redirect/Cookie oder Flow bricht vor Session-Aufbau ab. | E2E Smoke | UI/Auth | PR Gate (`pull_request`) | M (60-180s) | `tests/test_auth_regression_smoke_issue_1019.py::test_login_search_ranking_logout_regression_smoke` |
| 2 | Geschützte Route ohne Session | **Ziel:** Default-deny auf UI-Routen bleibt stabil.<br>**Eingangsdaten:** Request auf `/gui` oder `/history` ohne gültige Session. | **PASS:** deterministischer Redirect auf `/auth/login?next=...` mit `Cache-Control: no-store`.<br>**FAIL:** 200/5xx/unklarer Redirect ohne Login-Guard. | Integration Smoke | API/Auth | PR Gate (`pull_request`) | S (<30s) | `tests/test_web_service_bff_gui_guard.py::{test_gui_redirects_to_login_when_no_session,test_history_redirect_preserves_next_query}` |
| 3 | History Happy Path im UI | **Ziel:** UI-History bleibt funktionsfähig im Data-Source-Modell.<br>**Eingangsdaten:** mindestens ein Analyze-Resultat in History. | **PASS:** `/history` rendert stabil und nutzt `GET /analyze/history` gegen API-Base.<br>**FAIL:** History-Render bricht oder Endpoint-Bindung fehlt/falsch. | Integration | UI | PR Gate (`pull_request`) + Nightly | M (90-240s) | `tests/test_history_navigation_integration.py::test_ui_history_page_renders_and_targets_api_base` |
| 4 | Trace Happy Path im UI | **Ziel:** Trace-UX bleibt nutzbar (Load -> anzeigen -> Detailprüfung).<br>**Eingangsdaten:** request_id aus Analyze-Lauf, Trace-Feature aktiviert. | **PASS:** Happy Path liefert `ok=true`, Status `ready` und erwartete Events (`api.request.start/end`); Fehlerpfad liefert deterministischen Fehler (`trace_source_unavailable`, HTTP 503).<br>**FAIL:** Trace leer/fehlerhaft ohne erwarteten Grund oder nicht-deterministischer Fehlerpfad. | E2E Smoke | UI/Observability | PR Gate (`pull_request`) + Nightly | M (60-180s) | `tests/test_trace_debug_smoke.py::{test_analyze_to_trace_lookup_smoke_flow,test_trace_lookup_reports_unavailable_source}`<br>Ergänzende Guard-Regression: `tests/test_web_service_gui_mvp.py::test_trace_deep_link_state_flow_markers_present` |
| 5 | API-Deprecation-Signal für Legacy-Auth/History/Trace | **Ziel:** Legacy-Pfade liefern klare Deprecation-/Sunset-Signale statt stiller Brüche.<br>**Eingangsdaten:** Requests auf Legacy-Routen (`/login`, `/history`, Legacy-Trace-Alias). | **PASS:** Legacy-Auth-/History-Pfade senden konsistent `Deprecation` + `Sunset` + `Warning` bei stabilen Übergangs-Statuscodes (Auth `403`, `/history` `410`, `/analyze/history` bleibt data-source-konform inkl. `400` bei invalidem Input). Legacy-Trace ist explizit über Regression abgedeckt.<br>**FAIL:** fehlende Header/unklarer Migrationshinweis/Status-Drift. | API Contract + Integration | API | PR Gate (`pull_request`) | S-M (30-120s) | Bestehend: `tests/test_auth_regression_smoke_issue_1019.py::test_login_search_ranking_logout_regression_smoke` (Legacy-Auth inkl. Alias-Checks), `tests/test_history_api_deprecation.py::{test_analyze_history_emits_deprecation_headers,test_analyze_history_validation_error_keeps_bad_request_status_with_deprecation_headers,test_history_route_returns_gone_with_deprecation_headers}` (Legacy-History + removed endpoint).<br>Ergänzt in #1211: `tests/test_trace_legacy_deprecation.py::test_trace_legacy_alias_returns_gone_with_deprecation_headers` (Legacy-Trace-Alias `/trace` -> `/debug/trace`). |
| 6 | Negativer API-Contract-Fall (fehlender/ungültiger Parameter) | **Ziel:** Fehlende/ungültige Parameter schlagen deterministisch und maschinenlesbar fehl.<br>**Eingangsdaten:** z. B. fehlendes `input` oder ungültiges `input.mode`. | **PASS:** definierter 4xx-Fehler inkl. stabiler Error-Semantik (`bad_request`/`validation_failed`).<br>**FAIL:** 2xx/5xx oder unstabile Fehlersignatur. | Contract Test | API | PR Gate (`pull_request`) | S (<30s) | `tests/test_api_contract_v1.py` (Request-Validierung/Negativfälle) |

## Dev-Smoke-Gate (minimal, verbindlich)

Für Merge/Cutover gilt als minimaler Gate-Satz:

1. **Case 1** (UI Login erfolgreich)
2. **Case 2** (Protected Route Guard)
3. **Case 3** (History Happy Path)
4. **Case 4** (Trace Happy Path)
5. **Case 5** (Deprecation-Signale Legacy)
6. **Case 6** (negativer Contract-Fall)

Regel:
- PR darf nur als „smoke-ready“ gelten, wenn alle sechs Pflichtfälle entweder
  - direkt im PR-Run grün sind, oder
  - als bewusst Nightly-verschoben markiert sind **und** der letzte Nightly-Lauf für den Fall grün ist.

## Laufzeitklassen

- **S**: <30s
- **M**: 60-240s

## Änderungsregel

Änderungen an Pflichtfällen oder Gate-Zuordnung müssen in:
- `docs/testing/DEPLOY_TEST_TIERS.md` (Tier-/Gate-Zuordnung)
- dieser Datei (Matrix)

synchron aktualisiert werden.
