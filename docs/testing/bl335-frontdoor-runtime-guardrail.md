# BL-335 Frontdoor Runtime Guardrail

Dieses Guardrail prüft den **Live-Runtime-Zustand** gegen die Frontdoor-Konfiguration:

1. UI-Health (`/healthz`) advertized `api_base_url` muss exakt auf die erwartete HTTPS-API-Domain zeigen.
2. API-CORS-Preflight (`OPTIONS /analyze`) muss für alle erwarteten UI-Origin(s) einen passenden `Access-Control-Allow-Origin` liefern.

Script: [`scripts/check_bl335_frontdoor_runtime.py`](../../scripts/check_bl335_frontdoor_runtime.py)

## Nutzung

```bash
python3 scripts/check_bl335_frontdoor_runtime.py \
  --ui-health-url "https://www.dev.georanking.ch/healthz" \
  --api-analyze-url "https://api.dev.georanking.ch/analyze" \
  --expected-api-base-url "https://api.dev.georanking.ch" \
  --expected-ui-origin "https://www.dev.georanking.ch" \
  --expected-ui-origin "https://www.dev.geo-ranking.ch" \
  --output-json "artifacts/bl335/frontdoor-runtime-check.json"
```

## Erwartetes Ergebnis

- Exit `0`: Guardrail bestanden (UI-API-Base stimmt, CORS für alle Origins grün)
- Exit `1`: fachlicher Fail (Mismatch, fehlender CORS-Header, non-2xx-Preflight)
- Exit `2`: Parameter-/Validierungsfehler

## CI/Regression

Abgesichert durch:

- `tests/test_check_bl335_frontdoor_runtime.py`
