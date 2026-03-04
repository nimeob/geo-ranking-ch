# Issue #1046 — Deploy/Auth Secret-Preflight Evidence

- Timestamp (UTC): 20260304T000430Z
- Issue: https://github.com/nimeob/geo-ranking-ch/issues/1046

## Änderungen
- `.github/workflows/deploy.yml`
  - Neuer Preflight-Step `Validate required GitHub secrets (deploy/auth preflight)` vor AWS-Deploy.
  - Pflicht-Secret `SERVICE_API_AUTH_TOKEN` wird auf fehlend/leer geprüft.
  - API-Analyze-Smoke läuft als fester Schritt mit Token.
- `docs/DEPLOYMENT_AWS.md`
  - Pflicht-Secret-Liste für Dev-Deploy aktualisiert (`SERVICE_API_AUTH_TOKEN` Pflicht + Preflight-Verhalten).
- `tests/test_deploy_version_trace_docs.py`
  - Neue Guardrail-Tests für Secret-Preflight + Doku-Nachweis.

## Verifikation

Test command:

```bash
pytest -q tests/test_deploy_version_trace_docs.py tests/test_markdown_links.py
```

Result:

- exit code: `0`
- output: `8 passed in 0.11s`
