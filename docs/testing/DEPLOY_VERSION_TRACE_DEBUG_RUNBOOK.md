# Deploy-Runbook — Version-Drift & Trace-Debug Verifikation (Issue #534)

Ziel: Nach jedem Dev-Deploy reproduzierbar nachweisen, dass

1. die neue UI/API-Version wirklich live ist und
2. der Request-ID-Debug-Flow (`request_id` → `/debug/trace`) funktioniert.

Die CI führt dieselben Checks automatisiert über `scripts/check_deploy_version_trace.py` aus (Workflow: `.github/workflows/deploy.yml`).

---

## 1) Voraussetzungen

- `SERVICE_APP_BASE_URL` zeigt auf die Dev-UI (z. B. `https://www.dev.georanking.ch`)
- `SERVICE_API_BASE_URL` zeigt auf die Dev-API (z. B. `https://api.dev.georanking.ch`)
- (optional) `SERVICE_HEALTH_URL` als expliziter API-Health-Override
- Erwartete Deploy-Version: `${GITHUB_SHA::7}`
- Für Trace-Checks zusätzlich:
  - API-Runtime mit `TRACE_DEBUG_ENABLED=true`
  - optional `TRACE_DEBUG_LOOKBACK_SECONDS=86400`
  - optional `TRACE_DEBUG_MAX_EVENTS=500`

---

## 2) Verifikationscheckliste (verbindlich)

### A) Deploy-Verifikation (Version)

- [ ] `GET ${SERVICE_APP_BASE_URL}/healthz` liefert HTTP `200`
- [ ] Feld `version` entspricht exakt der erwarteten Short-SHA `${GITHUB_SHA::7}`
- [ ] (optional) `GET ${SERVICE_HEALTH_URL}` bzw. `${SERVICE_API_BASE_URL}/health` liefert HTTP `200`
- [ ] Bei Version-Drift: Hard-Reload durchführen und ECS TaskDef/Image-Tag gegen erwartete SHA prüfen

### B) Trace-Debug-Funktion

- [ ] Eine echte Anfrage über UI/API auslösen, damit eine `request_id` vorliegt
- [ ] `GET ${SERVICE_API_BASE_URL}/debug/trace?request_id=<id>&lookback_seconds=86400&max_events=500` liefert HTTP `200`
- [ ] Response enthält `ok=true`
- [ ] Response ist **nicht** `debug_trace_disabled`

### C) Regression-Schutz (CI)

- [ ] Workflow-Step `Post-deploy verification (version + trace-debug)` läuft nach dem UI-Smoke
- [ ] Ergebnis wird in `$GITHUB_STEP_SUMMARY` protokolliert
- [ ] JSON-Evidenz liegt unter `artifacts/deploy/<sha>-post-deploy-verify.json`

---

## 3) Lokale/Ad-hoc Ausführung

```bash
SERVICE_APP_BASE_URL="https://www.dev.georanking.ch" \
SERVICE_API_BASE_URL="https://api.dev.georanking.ch" \
EXPECTED_UI_VERSION="$(git rev-parse --short HEAD)" \
TRACE_DEBUG_EXPECT_ENABLED="1" \
TRACE_DEBUG_SMOKE_JSON="/tmp/bl18.1-smoke.json" \
python3 scripts/check_deploy_version_trace.py
```

Optional: expliziten Request-ID-Wert statt Smoke-Artefakt setzen:

```bash
TRACE_DEBUG_REQUEST_ID="req-demo-123" python3 scripts/check_deploy_version_trace.py
```

Exit-Codes:

- `0` = alle aktivierten Checks erfolgreich
- `1` = mindestens ein Check fehlgeschlagen
- `2` = ungültige Eingabe/Parameter
