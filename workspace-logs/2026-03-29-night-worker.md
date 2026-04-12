# 2026-03-29 – Night Worker Log

## 07:22 CET — Statuscheck (Architektur/Issues/Jobs)
- `origin/main` gefetched und frischen Night-Worker-Branch gestartet:
  - `night/worker-20260329-0722-ui-roi`
- GitHub-Check (via `./scripts/gha`):
  - offene Issues: **0**
  - offene PRs: **0**
  - letzte Deploy/Smoke-Runs: **grün** (kein akuter CI-Blocker)

## 07:28 CET — UI-Check auf DEV durchgeführt
- Browser-Check auf `https://www.dev.georanking.ch`:
  - GUI lädt stabil (`Version f7a683a` sichtbar).
  - Unauth-Flow korrekt: Analyse-Start führt zu Cognito-Login (`/oauth2/authorize`).
- Deep-Link geprüft:
  - `https://www.dev.georanking.ch/gui?view=trace&request_id=req-smoke`
  - Trace-Debug-Panel wird gerendert, request_id wird übernommen.

## 07:35 CET — ROI-Entscheidung & Umsetzung
**Entscheidung:** Login-Start-Smoke-Matrix um Trace-Debug-Deep-Link erweitern.

**Warum ROI:**
- `Trace-Debug-View` ist produktionsrelevant für Incident-/RCA-Arbeit.
- Bisher fehlte dedizierte Login-Start-Coverage für diesen GUI-Deep-Link.
- Kleine Änderung mit hoher Wirkung auf Deploy-Gates (Auth/Deep-Link-Regressionsschutz).

**Änderungen umgesetzt:**
1. `scripts/smoke/gui_smoke_routes.sh`
   - Route ergänzt: `"/gui?view=trace&request_id=req-smoke"`
   - Suffix-Mapping ergänzt: `login-start-smoke-gui-trace-view`
2. Workflow-Artefaktlisten ergänzt:
   - `.github/workflows/deploy.yml`
     - `artifacts/dev-login-start-smoke-gui-trace-view.json`
     - `artifacts/dev-alias-login-start-smoke-gui-trace-view.json`
   - `.github/workflows/deploy-staging.yml`
     - `artifacts/staging-login-start-smoke-gui-trace-view.json`
3. Test-Contracts angepasst:
   - `tests/test_run_login_start_smoke_bundle_script_contract.py`
   - `tests/test_gui_dev_live_auth_analyze_smoke_workflow.py`
   - `tests/test_deploy_version_trace_docs.py`

## 07:44 CET — Verifikation
- Targeted Tests:
  - `pytest -q tests/test_run_login_start_smoke_bundle_script_contract.py tests/test_gui_dev_live_auth_analyze_smoke_workflow.py tests/test_deploy_version_trace_docs.py`
  - Ergebnis: **31 passed**
- Live-Smoke gegen DEV (inkl. neuer Trace-Route):
  - `./scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev`
  - Ergebnis: **PASS**
- Live-Smoke gegen Alias-Host:
  - `./scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.geo-ranking.ch --env-name dev-alias`
  - Ergebnis: **PASS**

## Nächster sinnvoller Schritt
- Branch pushen + PR erstellen (UI/Auth-Smoke-Matrix Erweiterung), damit der neue Trace-Deep-Link dauerhaft im Deploy-Gate abgesichert ist.
