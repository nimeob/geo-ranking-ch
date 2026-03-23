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
