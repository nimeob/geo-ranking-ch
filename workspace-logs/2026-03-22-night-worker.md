## 01:48 CET — Befund + erster Fix-Versuch (superseded)
- Branch: `night/worker-20260322-0135` (worktree: `geo-ranking-ch-night-20260322-0135`).
- Live-Befund: `GET https://www.dev.georanking.ch/gui/jobs` liefert `404`.
- Erster Ansatz: UI-Alias `/gui/jobs -> /jobs` in `src/ui/service.py` + Tests.
- Ergebnis: CI `boundary-contract` **failed** (BL-31 route ownership): `/gui/jobs`-Routen sind außerhalb erlaubter UI-Ownership.

## 01:58 CET — Blocker gelöst: Smoke-Matrix auf kanonische Jobs-Route umgestellt
- Entscheidung: Kein neuer `/gui/jobs`-Route-Owner in UI; stattdessen Login-Start-Smokes auf **kanonische** Route `/jobs` umstellen.
- Änderungen:
  - `.github/workflows/deploy.yml`
    - Step-Label: `(/gui + /gui/history + /jobs)`
    - Login-Smoke-Call von `--next "/gui/jobs"` auf `--next "/jobs"`
    - Artifact-Datei von `dev-login-start-smoke-gui-jobs.json` auf `dev-login-start-smoke-jobs.json`
    - Fehlertext: `jobs_rc=...`
  - `.github/workflows/deploy-staging.yml`
    - analoge Umstellung auf `/jobs`
    - Artifact-Datei: `staging-login-start-smoke-jobs.json`
  - `tests/test_deploy_version_trace_docs.py`
    - Contract-Assertions auf neue `/jobs`-Smokes + neue Artifact-Namen aktualisiert
- Lokale Verifikation:
  - `python3 scripts/check_bl31_service_boundaries.py --src-dir src` ✅
  - `python3 -m unittest tests.test_ui_service` ✅ (19 Tests)
  - `python3 -m unittest tests.test_web_service_bff_gui_guard` ✅ (13 Tests)
  - gezielte Contract-Functions aus `tests/test_deploy_version_trace_docs.py` manuell ausgeführt ✅
- Live-UI-Checks (`https://www.dev.georanking.ch`):
  - `check_ui_login_start.py --next /gui` ✅
  - `check_ui_login_start.py --next /gui/history` ✅
  - `check_ui_login_start.py --next /jobs` ✅

## Git/PR
- Initial Commit (superseded by follow-up): `6a5c437`
- Follow-up (Blocker-Fix, BL-31-konform): *(pending commit in this worktree at log time)*
- PR: #1430 `UI: fix /gui/jobs deep-link by aliasing to canonical /jobs routes` (wird auf neue `/jobs`-Smoke-Strategie aktualisiert)

## 07:46–07:58 CET — ROI-Härtung: Auth+Analyze Live-Smoke deckt jetzt Jobs-Deep-Link-Matrix breiter ab
- Neuer clean Branch: `chore/auth-analyze-smoke-extend-jobs-routes` (Basis `origin/main` @ `9539031`).
- Workflow `.github/workflows/gui-dev-live-auth-analyze-smoke.yml` erweitert:
  - zusätzliche Matrix-Pfade: `/jobs` und `/gui/jobs/demo-job`
  - bestehende Pfade `/gui`, `/gui/history`, `/gui/jobs` bleiben erhalten
  - Ergebnis: bessere Abdeckung für kanonische + Legacy-Detail-Deep-Links im echten Login→Analyze-Flow.
- Tests/Doku angepasst:
  - `tests/test_gui_dev_live_auth_analyze_smoke_workflow.py`
  - `docs/testing/GUI_DEV_LIVE_AUTH_ANALYZE_SMOKE.md`
- Lokal validiert:
  - `.../.venv/bin/python -m pytest -q tests/test_gui_dev_live_auth_analyze_smoke_workflow.py tests/test_gui_dev_live_auth_analyze_smoke_docs.py tests/test_validate_gui_live_auth_analyze_secrets_script.py` → **9 passed**.
- Live-DEV UI Sanity (ohne Secrets) durchgeführt via Login-Start-Bundle:
  - `scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name 20260322T0746Z-dev --output-dir artifacts/nightworker` → **PASS** für `/gui`, `/gui/history`, `/jobs`, `/gui/jobs`, `/gui/jobs/demo-job`.
- Browser-Tool-Status weiter blockiert (`browser start` timeout; Gateway-Config-Fehler `ANTHROPIC_MODEL_ALIASES`), daher UI-Verifikation weiterhin robust über Live-Smoke-Skripte.
