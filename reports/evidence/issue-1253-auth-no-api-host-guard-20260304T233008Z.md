# Issue #1253 — Auth Core-Flow + No-API-Host Guard (Evidence)

- Datum (UTC): 2026-03-04T23:30:08Z
- Branch: `fix/issue-1253`
- Scope: E2E-Smoke Erweiterung (logout->relogin + failure-modes) und CI-Guard "kein API-Host im browser-sichtbaren Auth-Flow"

## 1) Testlauf: fokussierte Regressionen

```bash
.venv/bin/python -m pytest -q \
  tests/test_auth_regression_smoke_issue_1019.py \
  tests/test_gui_auth_smoke_runbook_docs.py \
  tests/test_api_ui_dev_smoke_matrix_docs.py \
  tests/test_bl334_split_smokes_script.py \
  tests/test_gui_auth_bff_session_flow_docs.py
```

Ergebnis:
- `10 passed in 0.99s`

## 2) Gate-Nachweis: BL-334 Split-Smokes inkl. Core-Flow

```bash
./scripts/check_bl334_split_smokes.sh
```

Ergebnis:
- Exit: `0`
- Core-Flow Smoke: PASS
- Dauer Core-Flow: `1s` (Budget `300s`)
- Artefakt: `artifacts/bl334/20260304T232958Z-bl334-split-smokes.json`
- Logs:
  - `artifacts/bl334/20260304T232958Z-api-smoke.log`
  - `artifacts/bl334/20260304T232958Z-ui-smoke.log`
  - `artifacts/bl334/20260304T232958Z-core-flow-smoke.log`

## 3) Inhaltliche Abdeckung

- Re-Login nach Logout ist regressionsgetestet (`next=/history` Restore).
- Callback-Failure-Modes regressionsgetestet:
  - `invalid_state`
  - `consent_denied`
  - `session_expired`
- Browser-sichtbarer Auth-Flow enthält keinen API-Host:
  - Login-Redirect
  - Callback-Redirect/Error-CTA
  - Logout-Redirect

Referenztests:
- `tests/test_auth_regression_smoke_issue_1019.py::test_login_search_ranking_logout_regression_smoke`
- `tests/test_auth_regression_smoke_issue_1019.py::test_callback_failure_modes_render_ui_relogin_without_api_host_leak`
- `tests/test_auth_regression_smoke_issue_1019.py::test_no_api_host_in_browser_auth_flow_guard`
