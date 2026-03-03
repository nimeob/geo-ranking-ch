# Issue #1015 – Parent Closeout Evidence (20260303T221850Z)

## Ziel
Abschlussnachweis für den stabilen Dev-Auth-Basisflow
`Unauth -> Login -> Analyze/Search -> Logout -> Unauth`.

## Umgesetzte Work-Packages
- #1017 (PR #1020, merged): Login-Entrypoint + Analyze/Search Redirect-Guard
- #1018 (PR #1021, merged): deterministischer Logout-Return-Path + Session-Invalidate
- #1019 (PR #1023, merged): reproduzierbarer Auth-Regression-Smoke
- #1016 (PR #1029, merged): separater Mobile-UX-Follow-up (nicht blocker-kritisch für Auth, aber im Parent-Kontext referenziert)

## Reale Verifikation (lokal)
Ausgeführt am 20260303T221850Z (UTC):

```bash
./.venv/bin/python -m pytest -q \
  tests/test_web_service_gui_mvp.py \
  tests/test_web_service_bff_gui_guard.py \
  tests/test_bff_token_delegation.py \
  tests/test_auth_regression_smoke_issue_1019.py \
  tests/test_gui_auth_smoke_runbook_docs.py \
  tests/test_markdown_links.py
```

Ergebnis: **48 passed in 1.50s**

## AC-Abdeckung
1. Login-Entrypoint in `/gui` sichtbar  
   - Abgedeckt über PR #1020 + Tests `tests/test_web_service_gui_mvp.py`
2. Analyze/Search ohne Session -> Login-Redirect (kein API-Fehler-UI)  
   - Abgedeckt über PR #1020 + Tests `tests/test_web_service_bff_gui_guard.py`
3. Analyze/Search nach Login ohne Auth-Fehler  
   - Abgedeckt über PR #1020/#1023 + `tests/test_auth_regression_smoke_issue_1019.py`
4. Logout fehlerfrei, zurück in unauth state  
   - Abgedeckt über PR #1021 + Tests `tests/test_bff_token_delegation.py` und `tests/test_auth_regression_smoke_issue_1019.py`
5. Automatisierbarer Dev-Smoke ist vorhanden/verlinkbar  
   - Implementiert in PR #1023 (`tests/test_auth_regression_smoke_issue_1019.py`)

## Restrisiken
- Echte externe OIDC-Provider-Instabilitäten können weiterhin sporadisch auftreten; der lokale/mocked Regression-Smoke bleibt dennoch deterministisch reproduzierbar.
