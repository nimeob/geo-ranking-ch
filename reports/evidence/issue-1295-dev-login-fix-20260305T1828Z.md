# Issue #1295 – DEV Login End-to-End Fix (2026-03-05)

## Ziel
DEV-Login über `https://www.dev.georanking.ch/login?...&start=1` muss wieder den echten OIDC-Flow starten (kein `login_unavailable`) und reproduzierbar bis `/gui` funktionieren.

## Root Cause

### 1) API-BFF in DEV war auf Runtime-Ebene deaktiviert
Aktive DEV-API Task-Definition **vor Fix** (`swisstopo-dev-api:268`) hatte **keine** `BFF_OIDC_*` Variablen.

```bash
aws ecs describe-task-definition --task-definition swisstopo-dev-api:268 --region eu-central-1 \
| jq '.taskDefinition.containerDefinitions[] | select(.name=="api") | .environment | map(select(.name|startswith("BFF_OIDC_")))'
# => []
```

Konsequenz: `is_bff_oidc_enabled()==false`, `/auth/login` liefert `403` (`bff_oidc_disabled`) und der UI-Startpfad fällt auf `reason=login_unavailable` zurück.

### 2) Cognito App Client war nicht für Hosted-UI Auth Code Flow konfiguriert
Vor Fix war `AllowedOAuthFlowsUserPoolClient=false` (aus `describe-user-pool-client`), d. h. kein nutzbarer Browser-Login-Flow.

## Implementierter Fix (live in DEV)

### A) Cognito Domain + App Client für Code-Flow aktiviert
- User Pool Domain erstellt: `georanking-dev-523234426229`
- App Client `2308nspfjmffrba3urvje9skai` auf OAuth Code Flow konfiguriert
  - `AllowedOAuthFlowsUserPoolClient=true`
  - `AllowedOAuthFlows=[code]`
  - Callback URLs: `https://www.dev.georanking.ch/auth/callback`, `https://dev.georanking.ch/auth/callback`
  - Logout URLs: `https://www.dev.georanking.ch/login`, `https://dev.georanking.ch/login`

### B) DEV API ECS TaskDef auf BFF-OIDC umgestellt + deployt
Neue TaskDef: `swisstopo-dev-api:269` (Service `swisstopo-dev-api` stable).

```bash
aws ecs describe-task-definition --task-definition swisstopo-dev-api:269 --region eu-central-1 \
| jq '.taskDefinition.containerDefinitions[] | select(.name=="api") | .environment | map(select(.name|startswith("BFF_OIDC_")))'
```

Ergebnis enthält:
- `BFF_OIDC_ISSUER=https://georanking-dev-523234426229.auth.eu-central-1.amazoncognito.com`
- `BFF_OIDC_CLIENT_ID=2308nspfjmffrba3urvje9skai`
- `BFF_OIDC_REDIRECT_URI=https://www.dev.georanking.ch/auth/callback`
- `BFF_OIDC_POST_LOGOUT_REDIRECT_URI=https://www.dev.georanking.ch/login`

## Regression-Guard im Repo ergänzt

1. Neuer Smoke-Checker: `scripts/smoke/check_ui_login_start.py`
   - Verifiziert: `/login?...&start=1` => `302` auf `authorize`
   - Failt explizit bei `reason=login_unavailable`

2. Neue Tests: `tests/test_check_ui_login_start.py`
   - Pass-Fall (authorize)
   - Fail-Fall (`login_unavailable`)
   - Fail-Fall (kein 302)

3. CI-Deploy erweitert (`.github/workflows/deploy.yml`)
   - Neuer Schritt nach UI-Healthcheck:
     `Smoke-Test UI login start redirects to IdP authorize`

## Verifikation (Akzeptanzkriterien)

### AC1 – Startpfad leitet zu IdP authorize
```bash
python3 scripts/smoke/check_ui_login_start.py \
  --base-url https://www.dev.georanking.ch \
  --next /gui --reason manual_login \
  --output-json reports/evidence/issue-1295-login-start-smoke-20260305T182441Z.json
```
Ergebnis: `ok=true`, `status_code=302`, `location=.../oauth2/authorize?...` (kein `login_unavailable`).

### AC2 – Erfolgreicher Login bis `/gui` reproduzierbar
Headless Playwright E2E mit DEV-Cognito User `worker-a-smoke`:
- Start: `/login?...&start=1`
- Redirect auf Cognito Login
- Credentials submit
- Rückkehr auf `https://www.dev.georanking.ch/gui`
- `/auth/me` => `200`, `authenticated=true`

Artefakte:
- `reports/evidence/issue-1295-login-e2e-20260305T182431Z.json`
- `reports/evidence/issue-1295-login-e2e-20260305T182431Z.png`

### AC3 – Smoke-/E2E Nachweis dokumentiert
Siehe diese Datei + obige JSON/PNG Artefakte.

---
Status: **Fix live in DEV verifiziert**.
