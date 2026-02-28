# BL-335 Frontdoor Redeploy-Abnahme (WP3 / Issue #379)

## Ziel
Reproduzierbare End-to-End-Abnahme für BL-335 nach Infra-Cutover:

1. HTTPS-Health über stabile Domains (`app`/`api`)
2. Runtime-Guardrail für UI `api_base_url` + API-CORS
3. API- und UI-Redeploy ohne manuelle IP-Anpassungen
4. Abschluss-Evidenz für Parent-Issue [`#376`](https://github.com/nimeob/geo-ranking-ch/issues/376)

## Voraussetzungen

```bash
export BL31_API_BASE_URL="https://api.dev.georanking.ch"
export BL31_APP_BASE_URL="https://www.dev.georanking.ch"
export BL31_CORS_ORIGIN="https://www.dev.georanking.ch"

# optional: zweite erlaubte UI-Origin für CORS-Guardrail
export BL335_ALT_UI_ORIGIN="https://www.dev.geo-ranking.ch"
```

## 1) HTTPS-Health über Frontdoor verifizieren

```bash
curl -fsS "${BL31_APP_BASE_URL}/healthz"
curl -fsS "${BL31_API_BASE_URL}/health"
```

Erwartung:
- beide Commands liefern Exit `0`
- JSON enthält jeweils `"ok": true`

## 2) Runtime-Guardrail (UI_API_BASE_URL + CORS) prüfen

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUNTIME_EVIDENCE="artifacts/bl335/${STAMP}-frontdoor-runtime-check.json"

python3 scripts/check_bl335_frontdoor_runtime.py \
  --ui-health-url "${BL31_APP_BASE_URL}/healthz" \
  --api-analyze-url "${BL31_API_BASE_URL}/analyze" \
  --expected-api-base-url "${BL31_API_BASE_URL}" \
  --expected-ui-origin "${BL31_CORS_ORIGIN}" \
  --expected-ui-origin "${BL335_ALT_UI_ORIGIN}" \
  --output-json "${RUNTIME_EVIDENCE}"
```

Erwartung:
- Exit `0`
- JSON enthält:
  - `overall.status = "pass"`
  - `checks.ui_health.status = "pass"`
  - `checks.cors_preflight.status = "pass"`

## 3) API-only Redeploy mit expliziten Smoke-URLs

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
API_DEPLOY_EVIDENCE="artifacts/bl31/${STAMP}-bl31-split-deploy-api-execute.json"

python3 scripts/run_bl31_split_deploy.py \
  --mode api \
  --execute \
  --smoke-api-base-url "${BL31_API_BASE_URL}" \
  --smoke-app-base-url "${BL31_APP_BASE_URL}" \
  --smoke-cors-origin "${BL31_CORS_ORIGIN}" \
  --output-json "${API_DEPLOY_EVIDENCE}"
```

Erwartung:
- Exit `0`
- Evidence-JSON enthält `result = "pass"`
- `smokeConfig.BL31_API_BASE_URL` und `smokeConfig.BL31_APP_BASE_URL` sind auf Frontdoor-HTTPS gesetzt

## 4) UI-only Redeploy mit expliziten Smoke-URLs

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
UI_DEPLOY_EVIDENCE="artifacts/bl31/${STAMP}-bl31-split-deploy-ui-execute.json"

python3 scripts/run_bl31_split_deploy.py \
  --mode ui \
  --execute \
  --smoke-api-base-url "${BL31_API_BASE_URL}" \
  --smoke-app-base-url "${BL31_APP_BASE_URL}" \
  --smoke-cors-origin "${BL31_CORS_ORIGIN}" \
  --output-json "${UI_DEPLOY_EVIDENCE}"
```

Erwartung:
- Exit `0`
- Evidence-JSON enthält `result = "pass"`
- keine service-fremde TaskDef-Änderung (Guardrail bleibt grün)

## 5) Post-Redeploy Runtime-Guardrail erneut ausführen

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
POST_RUNTIME_EVIDENCE="artifacts/bl335/${STAMP}-frontdoor-runtime-post-redeploy.json"

python3 scripts/check_bl335_frontdoor_runtime.py \
  --ui-health-url "${BL31_APP_BASE_URL}/healthz" \
  --api-analyze-url "${BL31_API_BASE_URL}/analyze" \
  --expected-api-base-url "${BL31_API_BASE_URL}" \
  --expected-ui-origin "${BL31_CORS_ORIGIN}" \
  --expected-ui-origin "${BL335_ALT_UI_ORIGIN}" \
  --output-json "${POST_RUNTIME_EVIDENCE}"
```

Erwartung:
- Exit `0`
- weiterhin `overall.status = "pass"`

## 6) Parent-Abschluss-Checkliste (#376)

Für den Abschlusskommentar in Parent-Issue #376 diese Checkliste verwenden:

```markdown
### BL-335 Abschlussnachweis (WP3)
- [ ] HTTPS Health app/api grün (`/healthz`, `/health`)
- [ ] Runtime-Guardrail vor Redeploy grün (`check_bl335_frontdoor_runtime.py`)
- [ ] API-only Redeploy mit expliziten Frontdoor-Smoke-URLs grün
- [ ] UI-only Redeploy mit expliziten Frontdoor-Smoke-URLs grün
- [ ] Runtime-Guardrail nach Redeploy grün
- [ ] Evidence-Artefakte verlinkt (`artifacts/bl31/*`, `artifacts/bl335/*`)
```

Empfohlene Verlinkung im Parent:
- dieses Runbook: [`docs/testing/bl335-frontdoor-redeploy-acceptance-runbook.md`](./bl335-frontdoor-redeploy-acceptance-runbook.md)
- Runtime-Guardrail-Details: [`docs/testing/bl335-frontdoor-runtime-guardrail.md`](./bl335-frontdoor-runtime-guardrail.md)
