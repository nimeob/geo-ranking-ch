# Issue #1019 — Auth/UI Regression-Smoke Nachweis

## Scope
- Login → Analyze/History → Logout Regression-Schutz als reproduzierbarer automatisierter Smoke
- Integration in bestehenden Smoke-Entrypoint
- Runbook-Sync

## Implementierung
- Neuer Integration-Smoke-Test: `tests/test_auth_regression_smoke_issue_1019.py`
- Runbook-Marker-Test: `tests/test_gui_auth_smoke_runbook_docs.py`
- Entrypoint-Integration: `scripts/run_webservice_e2e.sh`
- Doku-Update: `docs/testing/GUI_AUTH_SMOKE_RUNBOOK.md`

## Ausgeführte Checks
```bash
/data/.openclaw/workspace/geo-ranking-ch/.venv/bin/python -m pytest -q \
  tests/test_auth_regression_smoke_issue_1019.py \
  tests/test_gui_auth_smoke_runbook_docs.py \
  tests/test_web_service_bff_gui_guard.py \
  tests/test_bff_integration.py \
  tests/test_markdown_links.py
```

Ergebnis:
- `31 passed`

## Erwartete Regression-Abdeckung
- unauth `/gui` Redirect auf `/auth/login`
- Session-Aufbau via `/auth/login` + `/auth/callback` inkl. Cookie-Handling
- `/auth/me` authentifiziert nach Login
- `POST /analyze` + `GET /analyze/history` erfolgreich im Smoke-Flow
- `/auth/logout` liefert Redirect + Cookie-Clear; `/auth/me` danach 401
