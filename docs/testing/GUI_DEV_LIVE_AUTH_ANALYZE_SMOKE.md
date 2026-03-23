# GUI DEV Live Auth+Analyze Smoke

## Ziel
Dieser Smoke gilt nur als **grün**, wenn im echten DEV-System alle Schritte durchlaufen wurden:

1. Login startet über die Live-UI (`/login?...&start=1`) und geht auf den echten IdP.
2. Login mit echten Credentials kommt zur angeforderten GUI-Route zurück (Default: `/gui`, optional z. B. `/gui/history`).
3. Pro Route wird eine neue Schweizer Adresse aus einem rotierenden Pool ausgewählt (Workflow-Run-Marker: `<run_number>-<run_attempt>-<route_ordinal>` für stabile Rotation auch bei Re-Runs).
4. Die Adresse wird wirklich per `POST /analyze` abgeschickt (Payload-Check auf exakten Query-String).
5. Vollständige Resultate kommen zurück (`ok=true`, `result.data.modules`, `match`, `suitability`).
6. Kein `401`, kein `session_expired`/`no_session` und kein Idle-Fallback im Analyze-Flow.

## Implementierung
- Script: `scripts/run_dev_ui_auth_analyze_smoke.mjs`
- Preflight (Secrets + Blocker-Evidence): `scripts/smoke/validate_gui_live_auth_analyze_secrets.sh`
- Address-Pool: `scripts/smoke/ch_live_addresses.txt`
- Shared Route-Matrix: `scripts/smoke/gui_smoke_routes.sh` (Single Source of Truth für kanonische + Legacy-Login-Pfade und Artifact-Suffix-Mapping)
- Route-Set Runner: `scripts/smoke/run_gui_live_auth_analyze_route_set.sh` (führt den gemeinsamen Route-Satz seriell in **einem** Workflow-Job aus und startet mit einem integrierten Secrets-Preflight, damit lokale/manual Runs bei fehlenden Credentials sofort und eindeutig abbrechen)
- Workflow: `.github/workflows/gui-dev-live-auth-analyze-smoke.yml`
- Artifact: `gui-dev-live-auth-analyze-smoke-artifacts`

Das Script erzeugt JSON-Evidence + Screenshot:
- `reports/evidence/dev-ui-auth-analyze-smoke-<timestamp>.json`
- `reports/evidence/dev-ui-auth-analyze-smoke-<timestamp>.png`

Der UI-Contract wartet auf ein **terminales UI-Signal** (Phase `success`/`error`, sichtbare Error-Box oder gerenderte Result-Zeilen), statt starr nur auf einen einzigen Locator (`#phase-pill[data-phase="success"]`). Damit bleiben echte Produktfehler sichtbar, aber false negatives durch zu enge Locator-Waits werden reduziert.

Wenn `DEV_UI_SMOKE_GUI_PATH` auf eine Route ohne direkt sichtbares Analyze-Form zeigt (z. B. `/gui/history`), wechselt das Script nach erfolgreichem Return-Path-Check automatisch in die Analyze-Shell (`/gui`) und fährt dort mit Auth/Analyze-Checks fort. Für kanonisierte Legacy-Pfade (z. B. `/gui/jobs` → `/jobs`) akzeptiert der Return-Path-Check den dokumentierten Successor.

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

Für den vollständigen Route-Satz lokal/manuell:
```bash
BASE_URL="https://www.dev.georanking.ch" \
DEV_UI_SMOKE_USERNAME="<username>" \
DEV_UI_SMOKE_PASSWORD="<password>" \
./scripts/smoke/run_gui_live_auth_analyze_route_set.sh
```

Optional:
- `DEV_UI_SMOKE_GUI_PATH=/gui` (oder jede Route aus `scripts/smoke/gui_smoke_routes.sh`, z. B. `/gui/history`, `/gui/jobs`, `/jobs?source=smoke`, `/jobs/demo-job`, `/results/demo-result`)
- `DEV_UI_SMOKE_ADDRESS_FILE=/abs/path/to/addresses.txt`
- `DEV_UI_SMOKE_TIMEOUT_MS=90000`
- `DEV_UI_SMOKE_HEADFUL=1`
