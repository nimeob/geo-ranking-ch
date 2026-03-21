# Night Worker Log – 2026-03-21

## 00:15 CET – Nacht-Worker gestartet / UI-Watch aufgenommen
- Repo-Status geprüft; aktive Arbeitsbasis auf Branch `debug/result-500-introspect` (enthält Fix für DEV Full-Regression-Runner).
- Live-Frontdoor-Checks gegen DEV durchgeführt:
  - `scripts/run_bl337_frontdoor_e2e.sh` mit `https://api.dev.georanking.ch` + `https://www.dev.georanking.ch`.
  - Ergebnis: WP2/WP3 **pass**; erwartete `auth_required`-Blockierung nur bei nicht-authentifizierten Analyze-Probes.
- Login-Entry-Vertrag gegen DEV erneut verifiziert:
  - `scripts/smoke/check_ui_login_start.py --base-url https://www.dev.georanking.ch`
  - Ergebnis: **ok** (302 → IdP authorize wie erwartet).

## 00:18 CET – Aktiver UI-Blocker reproduziert (GitHub Actions)
- Workflow manuell getriggert: `gui-dev-live-full-regression` auf `main`.
- Run: `23366410556` (failure).
- Root Cause aus `--log-failed`:
  - `page.waitForFunction: Timeout 30000ms exceeded` in `scripts/run_dev_ui_live_full_regression.mjs`.
  - Ursache: Playwright-Signatur falsch verwendet (`waitForFunction(fn, {timeout})` statt `waitForFunction(fn, arg, {timeout})`), daher fiel der erwartete `MAX_WAIT_MS`-Override weg.

## 00:22 CET – Blocker-Härtung + Guard-Test
- Regression-Guard ergänzt: `tests/test_run_dev_ui_live_full_regression_script_contract.py`.
- Test stellt sicher, dass die beiden kritischen `waitForFunction`-Aufrufe explizit `undefined` als 2. Argument und `timeout: MAX_WAIT_MS` als 3. Argument nutzen.
- Validierung:
  - `pytest -q tests/test_run_dev_ui_live_full_regression_script_contract.py tests/test_gui_dev_live_full_regression_workflow.py tests/test_validate_gui_live_auth_analyze_secrets_script.py`
  - Ergebnis: **8 passed**.

## Offene Stränge / nächste Schritte
- Branch committen/pushen, PR gegen `main` öffnen (Ziel: Flaky/False-Negative im Live-Regression-Workflow eliminieren).
- Nach Merge: `gui-dev-live-full-regression` erneut triggern und grünen Lauf dokumentieren.
- Parallel laufenden Deploy-Run `23366192511` weiter beobachten; bei Failure gezielt triagieren.

## 00:56 CET – Full-Regression nach Deploy erneut geprüft
- Deploy-Run auf `main` (`23366640003`) erfolgreich abgeschlossen.
- Anschließend `gui-dev-live-full-regression` erneut getriggert:
  - `23367064199` → weiterhin **failure**.
- Neue Root Cause aus Artefakt:
  - Sync-Analyze liefert `result_id`, aber unmittelbarer Fetch `GET /analyze/results/<id>?view=latest` liefert transient `404 not_found`.
  - UI bricht sofort ab, dadurch Timeout auf Ergebnis-Status.

## 01:03 CET – Fix für transienten Latest-Result-Read-Race
- Neuer Branch: `fix/ui-result-latest-404-retry`.
- Änderung in `src/shared/ui_pages.py`:
  - Result-Loader retryt bei `view=latest` transientes `404/not_found` (bounded retries + delay), statt sofort hart zu failen.
  - Fehler-/Auth-Handling für 401 und nicht-transiente Fehler bleibt unverändert.
- Tests ergänzt: `tests/test_ui_service.py` (Contract-Checks für Retry-Guard).
- Validierung: relevante UI/Workflow-Tests grün (`27 passed`).
- PR erstellt: **#1400** `fix(ui): retry transient latest-result 404s before failing`.

## Aktueller Status
- PR #1397 ist gemerged (Timeout-Signatur-Fix `waitForFunction`).
- Persistenter Live-Blocker jetzt als Race Condition adressiert in PR #1400.
- Nächster Schritt nach Merge von #1400: Full-Regression erneut triggern und auf green verifizieren.

## 01:26 CET – Persistenter `/analyze/results/<id>` 404 trotz UI-Retry
- Nach Merge von PR #1400 und erfolgreichem Deploy (`23367269014`) Full-Regression erneut ausgeführt (`23367469775`).
- Ergebnis weiterhin **failure**: wiederholte `404 not_found` auf `/analyze/results/<id>?view=latest`.
- Beobachtung:
  - History enthält Result-Link (Job wurde mit `result_id` aktualisiert).
  - Result-Fetch bleibt dennoch 404.
- Schlussfolgerung: wahrscheinlich Ownership-Guard/Legacy-Metadaten-Lücke zwischen `job_results` und `jobs`.

## 01:34 CET – DB Owner-Guard Legacy-Fallback implementiert
- Änderung in `DbAsyncJobStore.get_result_for_owner`:
  - strikter Owner-Fast-Path bleibt erhalten (user_id+org_id direkt auf Result-Row).
  - für Legacy-/teilweise Metadaten auf Result-Row: zusätzlicher Guard über Parent-Job (`jobs.job_id + user_id + org_id`).
  - Zugriff nur bei eindeutiger Job-Ownership, kein Relaxing ohne Guard.
- Tests ergänzt/angepasst: `tests/test_async_job_store_db.py` (inkl. Legacy-Fallback-Szenario).
- Relevante Testmatrix erneut grün (`61 passed`).

## Nächster Schritt
- Commit + Push + PR für DB-Guard-Fallback.
- Nach Merge & Deploy: Full-Regression nochmals triggern, Ziel = durchgehend grün.
