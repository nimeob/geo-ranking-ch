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

## 06:31–06:36 CET – DEV Live-Retest + CLI-Compatibility-Härtung
- Neuer sauberer Arbeitszweig für Nachtarbeit von `origin/main` erstellt: `night/worker-20260321-0630` (Worktree `../geo-ranking-ch-night0630`).
- Relevante Contract-Suites lokal erneut verifiziert:
  - `tests/test_check_ui_login_start.py`
  - `tests/test_run_dev_ui_auth_analyze_smoke_script_contract.py`
  - `tests/test_run_dev_ui_live_full_regression_script_contract.py`
  - Ergebnis: **18 passed**.
- Live-UI-Checks gegen `https://www.dev.georanking.ch` ausgeführt:
  - `/login?next=/gui` → IdP authorize redirect (**ok=true**)
  - `/login?next=/gui/history` → IdP authorize redirect (**ok=true**)
  - Artefakte:
    - `artifacts/nightworker/20260321T053158Z-dev-login-start-smoke-gui.json`
    - `artifacts/nightworker/20260321T053158Z-dev-login-start-smoke-gui-history.json`
- GitHub Actions Live-Retest manuell getriggert und überwacht:
  - `gui-dev-live-full-regression` Run **#23373014225** → **success**
  - `gui-dev-live-auth-analyze-smoke` Run **#23373033268** → **success**
- ROI-Fix umgesetzt (Operator/Runbook-Kompatibilität):
  - `scripts/smoke/check_ui_login_start.py` akzeptiert jetzt zusätzlich Alias `--json-out` (neben `--output-json`).
  - Hintergrund: reduziert Bedienfehler bei manuellen/älteren Aufrufen, ohne bestehende CI-Aufrufe zu brechen.
  - Regressionstest ergänzt: `test_main_accepts_json_out_alias_and_writes_result`.
- Hinweis Blocker-Handling:
  - Browser-Tool war in dieser Session nicht verfügbar (Gateway-Timeout), daher UI-Verifikation über bestehende Smoke-Skripte + Live-Workflows abgesichert.

## 23:00 CET – Nacht-Session Restart (Plan)
- Start auf cleanem Worktree von `origin/main`: Branch `night/worker-20260321-2300`.
- Fokus/ROI für diese Runde:
  1. UI-nahen Full-Regression-Runner (`scripts/run_dev_ui_live_full_regression.mjs`) gegen Placeholder-/Payload-Drift auf `/jobs/<id>` härten.
  2. Contract-Test ergänzen, damit die Guardrail in CI nicht regressiert.
  3. Relevante Test-Suite lokal laufen lassen und anschließend DEV-Login-Contract kurz live gegen `https://www.dev.georanking.ch` gegenprüfen.
- Ziel: frühere Klasse „`Loading...` statt Notifications-Payload“ deterministisch früher failen lassen (klarer Fehlergrund, weniger Flakes).

## 23:06 CET – Paket: Login-Start-Smoke auf `/gui/jobs` erweitert (DEV+STAGING Deploy-Gates)
- Problem/ROI: Deploy-Gates prüften Login-Start nur für `/gui` und `/gui/history`; die UI-Route `/gui/jobs` war nicht in den Gate-Smokes enthalten.
- Änderung umgesetzt:
  - `.github/workflows/deploy.yml`
    - Smoke-Step erweitert auf `/gui/jobs`.
    - zusätzlicher Return-Code `LOGIN_JOBS_RC`.
    - Fehlerausgabe enthält jetzt `gui_jobs_rc=...`.
    - Artifact-Upload erweitert um `artifacts/dev-login-start-smoke-gui-jobs.json`.
  - `.github/workflows/deploy-staging.yml`
    - gleiche Erweiterung für Staging.
    - Artifact-Upload erweitert um `artifacts/staging-login-start-smoke-gui-jobs.json`.
  - `tests/test_deploy_version_trace_docs.py`
    - Contract-Assertions auf neuen dritten Route-Check + Artifact + `LOGIN_JOBS_RC` angepasst.
- Lokal validiert:
  - `pytest -q tests/test_deploy_version_trace_docs.py tests/test_check_ui_login_start.py` → **32 passed**.
- Live gegen DEV geprüft (UI-nah):
  - `scripts/smoke/check_ui_login_start.py` erfolgreich für:
    - `/gui`
    - `/gui/history`
    - `/gui/jobs`
  - neue Artefakte:
    - `artifacts/nightworker/20260321T220616Z-dev-login-start-smoke-gui.json`
    - `artifacts/nightworker/20260321T220616Z-dev-login-start-smoke-gui-history.json`
    - `artifacts/nightworker/20260321T220616Z-dev-login-start-smoke-gui-jobs.json`

## Nächster Schritt
- Branch committen, pushen und PR eröffnen (UI-nahe Deploy-Gate-Härtung).

## 23:09 CET – Push + PR
- Commit: `7c53975` — **Add /gui/jobs login-start smoke coverage in deploy gates**
- Branch: `night/worker-20260321-2300`
- Push: `origin/night/worker-20260321-2300`
- PR erstellt: **#1424**
  - https://github.com/nimeob/geo-ranking-ch/pull/1424
- Blocker + Lösung:
  - initialer Push scheiterte wegen priorisiertem globalem `gh auth git-credential` (invalid host token).
  - für Push explizit command-local Credential-Helper auf `scripts/gha auth git-credential` gesetzt (`git -c credential.helper= -c credential.helper='!...' push ...`).

## 23:12 CET – PR-Checks überwacht
- PR #1424 CI-Status aktiv überwacht (`gh pr checks --watch`).
- Ergebnis:
  - `dev-smoke-required` ✅ pass
  - `gui-webkit-smoke` ✅ pass
- PR ist damit technisch review-ready; kein akuter Blocker offen.
