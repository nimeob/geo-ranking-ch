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
