# Evidence — Issue #998 Auth UX + Runbook Sync

- Issue: https://github.com/nimeob/geo-ranking-ch/issues/998
- Scope: Konsolidierte Session-Expiry/Auth-Fehler-UX (`/gui`, `/history`), dokumentierter Redirect-Contract (`reason`), Logout-Verhalten (lokal vs IdP), README/Runbook-Sync.
- UTC timestamp: 2026-03-03T19:49:00Z

## Änderungen (Kurzüberblick)

1. **Frontend-UX Konsolidierung**
   - `src/shared/gui_mvp.py`
   - `src/shared/ui_pages.py`
   - Einheitliche Fehlertexte für Session/Refresh/Consent/403.
   - Einheitlicher Re-Login-Redirect: `/auth/login?next=<path>&reason=<reason>`.

2. **Doku-Sync**
   - `README.md` (BFF Auth-Recovery + Logout-Varianten)
   - `docs/gui/GUI_AUTH_BFF_SESSION_FLOW.md` (neue UX-/Redirect-Konvention)
   - `docs/testing/GUI_AUTH_SMOKE_RUNBOOK.md` (Checks für `reason` + Logout-Redirect-Variante)
   - `docs/gui/GUI_AUTH_MVP_AC_MATRIX_978.md` (Stand + Nachweislink aktualisiert)

3. **Regressionstests**
   - `tests/test_ui_service.py`
   - `tests/test_gui_auth_bff_session_flow_docs.py`

## Testlauf 1

```bash
./.venv/bin/python -m unittest tests.test_ui_service tests.test_web_service_gui_mvp
```

Ergebnis:

```text
................
----------------------------------------------------------------------
Ran 16 tests in 0.439s

OK
```

## Testlauf 2 (nach Evidence-Link-Ergänzung)

```bash
./.venv/bin/python -m pytest -q tests/test_gui_auth_bff_session_flow_docs.py tests/test_markdown_links.py
```

Finales Ergebnis (nach Anlage dieser Evidence-Datei):

```text
4 passed
```

## DoD-Abgleich #998

- [x] UX-Verhalten für Expiry/Auth-Fehler konsolidiert und dokumentiert
- [x] Logout-Pfad inkl. optional Provider-Logout dokumentiert
- [x] README/Runbook auf finalen Auth-Flow synchronisiert
