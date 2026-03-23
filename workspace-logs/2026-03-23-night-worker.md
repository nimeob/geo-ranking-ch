# Night Worker Log — 2026-03-23

## 02:05–02:12 CET — ROI: Deploy-Login-Smoke auf kanonische Detailroute erweitert
- Entscheidung (ROI): Obwohl `gui-dev-live-auth-analyze-smoke` bereits `/jobs/demo-job` prüft, deckte der Deploy-Gate-Bundle-Smoke (`run_login_start_smoke_bundle.sh`) die kanonische Detailroute noch nicht ab. Das war ein kleiner, aber realer Blind Spot direkt im Hourly-Deploy-Gate.
- Umsetzung im clean Worktree `chore/deploy-login-smoke-canonical-detail` (von `origin/main`, ohne lokale WIP-Dateien anzufassen):
  - `scripts/smoke/run_login_start_smoke_bundle.sh`
    - neue Probe: `/jobs/demo-job` → `*-login-start-smoke-jobs-detail.json`
    - neuer RC-Guard: `LOGIN_JOBS_DETAIL_RC`
  - `.github/workflows/deploy.yml`
    - Upload-Pfad ergänzt: `artifacts/dev-login-start-smoke-jobs-detail.json`
    - Step-Label präzisiert (`/jobs/:id` enthalten)
  - `.github/workflows/deploy-staging.yml`
    - Upload-Pfad ergänzt: `artifacts/staging-login-start-smoke-jobs-detail.json`
    - Step-Label präzisiert (`/jobs/:id` enthalten)
  - Contract-Tests angepasst:
    - `tests/test_run_login_start_smoke_bundle_script_contract.py`
    - `tests/test_deploy_version_trace_docs.py`
- Validierung:
  - `pytest -q tests/test_run_login_start_smoke_bundle_script_contract.py tests/test_deploy_version_trace_docs.py` ✅
  - `pytest -q tests/test_gui_dev_live_auth_analyze_smoke_workflow.py tests/test_gui_dev_live_auth_analyze_smoke_docs.py tests/test_run_dev_ui_auth_analyze_smoke_script_contract.py` ✅
  - `./scripts/check_dev_quality_gate.sh` ✅ (1695 passed, 9 skipped, 179 subtests)
- Live-UI-Retest (dev):
  - `scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name 20260323T0209Z-dev --output-dir artifacts/night-worker` ✅
  - inklusive neuer Route `/jobs/demo-job` (302 → Cognito authorize)
- Browser-Blocker aktiv adressiert:
  - `browser start` weiterhin timeout.
  - `openclaw gateway status` zeigt weiterhin Config-Fehler: `Cannot access 'ANTHROPIC_MODEL_ALIASES' before initialization`.
  - Konsequenz: UI-Validierung weiter robust über Live-Smoke-Skripte durchgeführt (kein Stillstand wegen Browser-Blocker).

## Nächste Schritte
- Commit + Push auf Branch `chore/deploy-login-smoke-canonical-detail`
- PR öffnen, CI grün verifizieren, mergen und anschliessend Deploy+Live-Retest auf `main` bestätigen.

## 04:15 CET — Route-set Smoke Runner hardening (ROI)
- **Started:** manueller DEV-Route-Set-Run zeigte 8x Fehlerspam bei fehlenden Live-Credentials (`DEV_UI_SMOKE_USERNAME/PASSWORD`), obwohl das eigentliche Problem nur fehlende Secrets war.
- **Implemented:** `scripts/smoke/run_gui_live_auth_analyze_route_set.sh` um integrierten Preflight erweitert:
  - einmaliger Aufruf von `scripts/smoke/validate_gui_live_auth_analyze_secrets.sh`
  - Übergabe stabiler `DEV_UI_SMOKE_RUN_ID` (`base_run_id`)
  - fail-fast mit klarer Meldung, **kein** Route-Fanout bei Secret-Blocker
- **Tests:**
  - neu: `tests/test_run_gui_live_auth_analyze_route_set_preflight.py`
  - regression: `pytest -q tests/test_gui_dev_live_auth_analyze_smoke_workflow.py tests/test_validate_gui_live_auth_analyze_secrets_script.py tests/test_run_gui_live_auth_analyze_route_set_preflight.py` → **9 passed**
- **Docs:** `docs/testing/GUI_DEV_LIVE_AUTH_ANALYZE_SMOKE.md` ergänzt (integrierter Preflight + lokaler Route-Set-Run).
- **Runtime check:** `./scripts/smoke/run_gui_live_auth_analyze_route_set.sh` ohne Secrets bricht jetzt sofort mit einem Blocker-Artifact ab (kein 8x Fehlfanout).

## 04:24 CET — Blocker-Auflösung nach Merge #1462
- **Blocker aktiv gelöst:** Main-Deploy `Deploy to AWS (ECS dev) #23420000720` failte im Unit-Test.
- **Root cause:** neuer Test `test_run_gui_live_auth_analyze_route_set_preflight.py` war CI-instabil, weil `GITHUB_RUN_NUMBER` in GitHub Actions den erwarteten Dateinamen überschreibt.
- **Fix:** im Test-Setup `GITHUB_RUN_NUMBER` explizit entfernt (`env.pop("GITHUB_RUN_NUMBER", None)`), damit deterministisch `GITHUB_RUN_ID` genutzt wird.
- **Verification:** `pytest -q tests/test_run_gui_live_auth_analyze_route_set_preflight.py tests/test_gui_dev_live_auth_analyze_smoke_workflow.py tests/test_validate_gui_live_auth_analyze_secrets_script.py` → **9 passed**.

## 05:16–05:26 CET — ROI: gemeinsame Route-Matrix für Login-Smokes entkoppelt
- Ich habe mit `scripts/smoke/gui_smoke_routes.sh` eine gemeinsame Route-Matrix + Artifact-Suffix-Mapping eingeführt, damit Deploy-Login-Smoke und Live-Auth-Route-Set nie mehr auseinanderlaufen.
- Ich habe `scripts/smoke/run_login_start_smoke_bundle.sh` auf einen Loop über `GUI_SMOKE_ROUTES` umgestellt und die bisherigen Artifact-Namen vollständig kompatibel beibehalten.
- Ich habe `scripts/smoke/run_gui_live_auth_analyze_route_set.sh` auf dieselbe Shared-Route-Matrix migriert und den ordinalen Run-ID-Mechanismus unverändert gelassen.
- Ich habe die Vertrags-/Workflow-Tests auf das Shared-Route-Setup angepasst (`tests/test_run_login_start_smoke_bundle_script_contract.py`, `tests/test_gui_dev_live_auth_analyze_smoke_workflow.py`) und alle betroffenen Tests grün verifiziert.
- Ich habe den DEV-Login-Start-Bundle-Livecheck gegen `https://www.dev.georanking.ch` über alle neun Routen erfolgreich erneut durchlaufen lassen.

## 06:00–06:08 CET — ROI: Full-Regression-Preflight stabilisiert (UI-nah)
- Problem identifiziert: `scripts/run_dev_ui_live_full_regression.mjs --help` crashte sofort mit `ERR_MODULE_NOT_FOUND` (top-level `playwright` import), bevor Preflight/Guidance greift. Das bremst lokale Nacht-Worker-Runs in clean Worktrees ohne Node-Setup.
- Umsetzung auf Branch `fix/ui-full-regression-preflight-contract-20260323`:
  - Playwright-Laden auf **dynamischen Import** umgestellt (`loadChromium()`), inkl. klarer Install-Hinweise (`npm ci` + `npx playwright install --with-deps chromium`).
  - `--help`/`-h` Contract ergänzt (Usage + required/optional ENV), damit schnelle CLI-Preflight-Checks ohne Secrets/Playwright möglich sind.
  - Required-ENV-Validierung (`DEV_UI_BASE_URL`, `DEV_UI_SMOKE_USERNAME`, `DEV_UI_SMOKE_PASSWORD`) in main-Flow gezogen; Fehler landen jetzt zuverlässig im Evidence-JSON statt unstrukturiertem Stacktrace.
  - Safe-Cleanup gehärtet: `context/browser` werden nur geschlossen, wenn initialisiert.
- Tests/Verifikation:
  - erweitert: `tests/test_run_dev_ui_live_full_regression_script_contract.py`
    - dynamic import + actionable hint
    - `--help` exits 0 ohne ENV/Playwright
    - missing credentials erzeugt Evidence-JSON vor Browser-Boot
  - `pytest -q tests/test_run_dev_ui_live_full_regression_script_contract.py tests/test_run_dev_ui_auth_analyze_smoke_script_contract.py tests/test_check_ui_login_start.py` → **38 passed**.
  - Live-Contract-Check: `scripts/smoke/check_ui_login_start.py --base-url https://www.dev.georanking.ch --next /gui --reason night_worker_probe ...` → **ok=true** (302 auf IdP authorize).

## Nächste Schritte
- Commit + Push des Preflight-Hardening-Branches.
- PR öffnen und CI grünziehen; danach Merge auf `main` für robustere UI-Full-Regression-Operator-UX.

## 06:45–06:52 CET — ROI: Route-Set Runner CLI contract + blocker fallback guidance
- Kontext: manueller Aufruf mit Parametern (`--base-url`, `--output-dir`, `--headless`) wurde bisher stillschweigend ignoriert; bei fehlenden Secrets blieb nur ein harter Abort ohne direkten Fallback-Pfad.
- Umsetzung auf Branch `night/worker-20260323-0645`:
  - `scripts/smoke/run_gui_live_auth_analyze_route_set.sh`
    - echte CLI-Optionen ergänzt (`--base-url`, `--output-dir`, `--timeout-ms`, `--address-file`, `--login-reason`, `--run-id-base`, `--headless/--headful`, `--help`)
    - unbekannte Optionen liefern jetzt klaren Fehler + Usage (kein stilles Ignorieren mehr)
    - bei Secret-Blocker now actionable Hint auf `run_login_start_smoke_bundle.sh` inkl. `--base-url`/`--env-name`
  - `scripts/run_dev_ui_auth_analyze_smoke.mjs`
    - optionaler Evidence-Ordner via `DEV_UI_SMOKE_EVIDENCE_DIR` (CLI: `--output-dir`)
  - Tests erweitert (`tests/test_run_gui_live_auth_analyze_route_set_preflight.py`) und Docs aktualisiert (`docs/testing/GUI_DEV_LIVE_AUTH_ANALYZE_SMOKE.md`)
- Verifikation:
  - `pytest -q tests/test_run_gui_live_auth_analyze_route_set_preflight.py tests/test_gui_dev_live_auth_analyze_smoke_docs.py tests/test_gui_dev_live_auth_analyze_smoke_workflow.py tests/test_run_dev_ui_auth_analyze_smoke_script_contract.py` → **16 passed**
  - Runtime: `run_gui_live_auth_analyze_route_set.sh ... --headless` ohne Secrets erzeugt Blocker-Evidence + neuen Login-Start-Hint
  - Runtime fallback: `run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev ...` über alle 9 Routen grün (302→IdP)
- UI-Browser-Blocker bleibt extern: `browser start` timeout; `openclaw gateway status` weiterhin mit Config-Fehler `Cannot access 'ANTHROPIC_MODEL_ALIASES' before initialization`. Deshalb weiter API/Smoke-basiertes UI-Monitoring ohne Leerlauf.

## 07:20–07:33 CET — ROI: CLI-Fehlerbild im Login-Start-Bundle entstört
- Beobachtung: `scripts/smoke/run_login_start_smoke_bundle.sh --base-url` (ohne Wert) terminierte zuvor mit Exit-Code `1` **ohne** Fehltext/Usage (Bash-`shift`-Abort). Das kostet Zeit bei manuellen Deploy-/Smoke-Runs und erschwert schnelle Fehlerdiagnose.
- Umsetzung auf Branch `night/worker-20260323-0720`:
  - `scripts/smoke/run_login_start_smoke_bundle.sh`
    - neue Guard-Funktion `require_option_value` für alle Flags mit Pflichtwert (`--base-url`, `--env-name`, `--output-dir`, `--reason`, `--timeout`, `--max-attempts`, `--retry-delay`)
    - bei fehlendem Wert jetzt konsistent: `::error::Missing value for <flag>` + Usage + Exit-Code `2`
  - `tests/test_run_login_start_smoke_bundle_script_contract.py`
    - zwei Runtime-Regressionstests ergänzt (fehlender Wert bei `--base-url` und `--timeout`)
- Verifikation:
  - `pytest -q tests/test_run_login_start_smoke_bundle_script_contract.py tests/test_run_gui_live_auth_analyze_route_set_preflight.py tests/test_check_ui_login_start.py` → **31 passed**
  - Live-Retest gegen DEV: `run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev ...` → **alle 9 Routen grün** (302 auf IdP authorize)
- UI-Monitoring:
  - `browser open` auf `https://www.dev.georanking.ch` weiterhin blockiert (`gateway timeout`); daher UI-Verifikation erneut über Live-Smoke/API weitergeführt (kein Idle trotz Browser-Blocker).

## 07:45–07:58 CET — ROI: Route-Set CLI-Parsing gegen Flag-as-Value gehärtet
- Beobachtung: `run_gui_live_auth_analyze_route_set.sh` akzeptierte bisher bei Wert-Optionen (`--base-url`, `--output-dir`, `--timeout-ms`, `--address-file`, `--login-reason`, `--run-id-base`) ein nachfolgendes Flag (`--headless`) fälschlich als Wert.
  - Folge: irreführende Fehlbilder (späterer Preflight-Blocker statt sofortiger CLI-Fehler).
- Umsetzung auf Branch `night/worker-20260323-0745`:
  - `scripts/smoke/run_gui_live_auth_analyze_route_set.sh`
    - neue Guard-Funktion `require_option_value` eingeführt
    - Guard prüft jetzt für alle Wert-Optionen: Wert muss vorhanden sein **und** darf nicht mit `--` beginnen
    - bei Verstoß konsistent: `ERROR: Missing value for <flag>` + Usage + Exit-Code `2`
  - `tests/test_run_gui_live_auth_analyze_route_set_preflight.py`
    - parametrisierter Runtime-Contract-Test ergänzt: jede Wert-Option mit `--headless` als Folgetoken wird sauber mit Exit `2` abgewiesen
- Verifikation:
  - `pytest -q tests/test_run_gui_live_auth_analyze_route_set_preflight.py` → **9 passed**
  - `pytest -q tests/test_run_dev_ui_auth_analyze_smoke_script_contract.py tests/test_gui_dev_live_auth_analyze_smoke_workflow.py tests/test_gui_dev_live_auth_analyze_smoke_docs.py` → **13 passed**
- Live-DEV-UI Smoke (Fallback ohne Browser-Tool) gegen `https://www.dev.georanking.ch` erneut ausgeführt:
  - `scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name 20260323T0745Z-dev --output-dir artifacts/nightworker`
  - Ergebnis: **PASS** für alle 9 Login-Start-Routen (302 → `auth.dev.georanking.ch`)
