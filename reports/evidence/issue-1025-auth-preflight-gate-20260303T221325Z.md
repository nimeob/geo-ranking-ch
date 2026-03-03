# Issue #1025 — Deploy-Gate Auth-Preflight Integration + blocked-by-auth Reporting

## Scope
- verpflichtende Auth-Preflight-Integration im Deploy/Nightly-Smoke-Entrypoint (`scripts/run_deploy_smoke.py`)
- klare Gate-Klassifikation `reason=blocked-by-auth` bei fehlender Auth-Konfiguration
- Doku-Sync der verpflichtenden Pipeline-/Script-Pfade

## Code-/Doku-Änderungen
- `scripts/run_deploy_smoke.py`
  - neuer verpflichtender Check `auth_preflight` vor Sync/Async-Smokes in Deploy/Nightly-Profilen
  - Default-Preflight-Contract: `SMOKE_AUTH_MODE=oidc_client_credentials`, `SMOKE_AUTH_OUTPUT_FILE=artifacts/smoke_auth.env`
  - fail-fast bei Preflight-Fehlern mit `reason=blocked-by-auth`
  - Dry-Run-/Report-Ausgabe erweitert um `kind` (`auth_preflight|smoke`) und check-spezifische `reason`
- `tests/test_run_deploy_smoke.py`
  - Dry-Run-Erwartungen auf Preflight-Schritt erweitert
  - Regressionstest für blocked-by-auth-Failfast (Returncode `42`, Report-Reason)
- `docs/testing/REMOTE_API_SMOKE_RUNBOOK.md`
  - Preflight für Deploy/Nightly als verpflichtend dokumentiert
  - `reason=blocked-by-auth` als Report-Signal ergänzt
- `docs/testing/DEPLOY_TEST_TIERS.md`
  - Deploy-Gate-Abschnitt um verpflichtenden Preflight-Pfad via `run_deploy_smoke.py` ergänzt

## Verifikation

### 1) Unit-/Doku-Regression
```bash
pytest -q tests/test_run_deploy_smoke.py tests/test_markdown_links.py tests/test_user_docs.py
```
Ergebnis: `15 passed`

### 2) Fail-fast-Nachweis blocked-by-auth
```bash
DEV_BASE_URL="https://api.dev.example.test" \
SMOKE_AUTH_MODE="oidc_client_credentials" \
python3 scripts/run_deploy_smoke.py \
  --profile deploy --target dev --flow sync \
  --output-json reports/evidence/issue-1025-deploy-smoke-blocked-by-auth-20260303T221325Z.json
```
Ergebnis:
- Exit-Code: `42`
- Report: `status=fail`, `reason=blocked-by-auth`
- Check: `deploy-dev-auth-preflight`, `kind=auth_preflight`, `reason=blocked-by-auth`

### 3) Dry-run-Nachweis verpflichtender Preflight im Plan
```bash
DEV_BASE_URL="https://api.dev.example.test" \
python3 scripts/run_deploy_smoke.py \
  --profile nightly --dry-run \
  --output-json reports/evidence/issue-1025-deploy-smoke-plan-20260303T221325Z.json
```
Ergebnis:
- erster geplanter Check ist `nightly-dev-auth-preflight`
- danach Sync/Async-Smokes

## Artefakte
- `reports/evidence/issue-1025-deploy-smoke-blocked-by-auth-20260303T221325Z.json`
- `reports/evidence/issue-1025-deploy-smoke-plan-20260303T221325Z.json`
- `reports/evidence/issue-1025-auth-preflight-gate-20260303T221325Z.md`
