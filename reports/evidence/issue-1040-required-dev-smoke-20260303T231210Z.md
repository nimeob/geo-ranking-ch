# Issue #1040 — Required Dev-Smoke Gate (Evidence)

- Timestamp (UTC): 20260303T231210Z
- Branch: `worker-a/issue-1040-required-dev-smoke`

## Änderungen

1. Neuer PR-Workflow:
   - `.github/workflows/dev-smoke-required.yml`
   - Stabiler Jobname/Status-Check: `dev-smoke-required`
   - Führt den kanonischen Runner aus:
     - `python3 ./scripts/run_deploy_smoke.py --profile pr --flow sync`

2. Doku aktualisiert:
   - `docs/testing/DEPLOY_TEST_TIERS.md`
   - `docs/OPERATIONS.md`
   - Required-Check-Zielzustand ergänzt um `dev-smoke-required`

3. Guard-Tests erweitert:
   - `tests/test_pr_fast_gates_config.py`

## Verifikation (lokal)

```bash
python3 ./scripts/run_deploy_smoke.py --profile pr --flow sync
pytest -q tests/test_pr_fast_gates_config.py tests/test_markdown_links.py tests/test_user_docs.py
```

Ergebnis:
- Dev-Smoke: **pass**
  - Evidence JSON: `artifacts/bl334/20260303T231211Z-bl334-split-smokes.json`
  - API-Log: `artifacts/bl334/20260303T231211Z-api-smoke.log`
  - UI-Log: `artifacts/bl334/20260303T231211Z-ui-smoke.log`
- Tests: **14 passed**

## Hinweis Branch-Protection API

Direktes Setzen/Lesen von Branch-Protection via GitHub-App ist weiterhin eingeschränkt (`403 Resource not accessible by integration`).
Die Required-Check-Konfiguration ist daher in `docs/OPERATIONS.md` als Admin-Schritt dokumentiert.
