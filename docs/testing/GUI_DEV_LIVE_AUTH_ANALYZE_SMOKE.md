# GUI DEV Live Auth+Analyze Smoke

## Ziel
Dieser Smoke gilt nur als **grün**, wenn im echten DEV-System alle Schritte durchlaufen wurden:

1. Login startet über die Live-UI (`/login?...&start=1`) und geht auf den echten IdP.
2. Login mit echten Credentials kommt zurück nach `/gui`.
3. Pro Lauf wird eine neue Schweizer Adresse aus einem rotierenden Pool ausgewählt.
4. Die Adresse wird wirklich per `POST /analyze` abgeschickt (Payload-Check auf exakten Query-String).
5. Vollständige Resultate kommen zurück (`ok=true`, `result.data.modules`, `match`, `suitability`).
6. Kein `401`, kein `session_expired`/`no_session` und kein Idle-Fallback im Analyze-Flow.

## Implementierung
- Script: `scripts/run_dev_ui_auth_analyze_smoke.mjs`
- Address-Pool: `scripts/smoke/ch_live_addresses.txt`
- Workflow: `.github/workflows/gui-dev-live-auth-analyze-smoke.yml`
- Artifact: `gui-dev-live-auth-analyze-smoke-artifacts`

Das Script erzeugt JSON-Evidence + Screenshot:
- `reports/evidence/dev-ui-auth-analyze-smoke-<timestamp>.json`
- `reports/evidence/dev-ui-auth-analyze-smoke-<timestamp>.png`

## Erforderliche Secrets (GitHub Actions)
- `DEV_UI_SMOKE_USERNAME`
- `DEV_UI_SMOKE_PASSWORD`

Ohne diese Secrets schlägt der Workflow absichtlich mit klarer Fehlermeldung fehl, statt ein falsches „grün“ zu liefern.
Zusätzlich wird ein Blocker-Evidence-File erzeugt:
- `reports/evidence/dev-ui-auth-analyze-smoke-blocked-<run_id>.json`

## Lokaler Lauf
```bash
npm ci
npx playwright install --with-deps chromium
BASE_URL="https://www.dev.georanking.ch" \
DEV_UI_SMOKE_USERNAME="<username>" \
DEV_UI_SMOKE_PASSWORD="<password>" \
DEV_UI_SMOKE_RUN_ID="$(date +%s)" \
node scripts/run_dev_ui_auth_analyze_smoke.mjs
```

Optional:
- `DEV_UI_SMOKE_ADDRESS_FILE=/abs/path/to/addresses.txt`
- `DEV_UI_SMOKE_TIMEOUT_MS=90000`
- `DEV_UI_SMOKE_HEADFUL=1`
