# Issue #1026 – Runbook/Troubleshooting Evidence

## Änderungen
- `docs/testing/REMOTE_API_SMOKE_RUNBOOK.md`
  - ENV-Contract für Auth-Preflight ergänzt (`SMOKE_AUTH_MODE`, `OIDC_*`, Output `SMOKE_BEARER_TOKEN`)
  - Verlinkung auf realen Runner + Pipeline-Schritt (`scripts/run_deploy_smoke.py`, `scripts/smoke/auth_preflight.sh`, `.github/workflows/deploy.yml`)
  - Lokale Verifikation (Quick Path) ergänzt
  - Troubleshooting für häufige Fehler ergänzt (`auth-preflight-failed`, `blocked-by-auth`, Token-Endpoint-Fehler)
- `tests/test_remote_api_smoke_runbook_docs.py`
  - Guard-Test auf Pflichtmarker/Contract/Troubleshooting ergänzt

## Verifikation
### 1) Doku- und Link-Tests
```bash
./.venv/bin/python -m pytest -q tests/test_remote_api_smoke_runbook_docs.py tests/test_markdown_links.py
```
Ergebnis: `2 passed`

### 2) Deploy-Smoke Dry-Run (lokaler Nachweis)
```bash
DEV_BASE_URL="https://api.dev.example.invalid" \
python3 ./scripts/run_deploy_smoke.py \
  --profile deploy \
  --target dev \
  --flow sync \
  --dry-run \
  --output-json artifacts/issue-1026-deploy-smoke-dryrun.json
```
Artefakte:
- `reports/evidence/issue-1026-deploy-smoke-dryrun-20260303T222256Z.json`
- `reports/evidence/issue-1026-deploy-smoke-dryrun-20260303T222256Z.stdout.json`

## Erwartete Nachweis-Properties
- erster geplanter Check mit `kind=auth_preflight`
- `status=planned`, `reason=dry_run`
- `runner=deploy-smoke-entrypoint`
