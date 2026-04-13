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
- Shared Route-Matrix: `scripts/smoke/gui_smoke_routes.sh` (Single Source of Truth für kanonische + Legacy-Login-Pfade inkl. Legacy-`/history` und Artifact-Suffix-Mapping)
- Route-Set Runner: `scripts/smoke/run_gui_live_auth_analyze_route_set.sh` (führt den gemeinsamen Route-Satz seriell in **einem** Workflow-Job aus und startet mit einem integrierten Secrets-Preflight; Standard bleibt harter Abbruch bei fehlenden Credentials, optional mit degradierter Login-Start-Fallback-Coverage)
- Workflow: `.github/workflows/gui-dev-live-auth-analyze-smoke.yml` (manuelle Inputs: `base_url`, `routes`, `route_presets`, `timeout_ms`, `login_reason`, `fallback_login_start_on_preflight_fail`, Alias: `allow_login_start_fallback`)
- Artifact: `gui-dev-live-auth-analyze-smoke-artifacts`

Das Script erzeugt JSON-Evidence + Screenshot:
- Standard (lokal ohne expliziten Run-Token): `reports/evidence/dev-ui-auth-analyze-smoke-<timestamp>.json`
- Standard (lokal ohne expliziten Run-Token): `reports/evidence/dev-ui-auth-analyze-smoke-<timestamp>.png`
- Mit Run-Marker (z. B. CI-Run oder `DEV_UI_SMOKE_RUN_ID`): `...-<timestamp>-<run_marker>.json|png`

Der UI-Contract wartet auf ein **terminales UI-Signal** (Phase `success`/`error`, sichtbare Error-Box oder gerenderte Result-Zeilen), statt starr nur auf einen einzigen Locator (`#phase-pill[data-phase="success"]`). Damit bleiben echte Produktfehler sichtbar, aber false negatives durch zu enge Locator-Waits werden reduziert.

Wenn `DEV_UI_SMOKE_GUI_PATH` auf eine Route ohne direkt sichtbares Analyze-Form zeigt (z. B. `/gui/history`), wechselt das Script nach erfolgreichem Return-Path-Check automatisch in die Analyze-Shell (`/gui`) und fährt dort mit Auth/Analyze-Checks fort. Für kanonisierte Legacy-Pfade (z. B. `/gui/jobs` → `/jobs`) akzeptiert der Return-Path-Check den dokumentierten Successor.

## Erforderliche Secrets (GitHub Actions)
- `DEV_UI_SMOKE_USERNAME`
- `DEV_UI_SMOKE_PASSWORD`

Ohne diese Secrets schlägt der Workflow absichtlich mit klarer Fehlermeldung fehl, statt ein falsches „grün“ zu liefern.
Zusätzlich wird ein Blocker-Evidence-File erzeugt:
- `reports/evidence/dev-ui-auth-analyze-smoke-blocked-<run_id>.json`

Wenn der degradierte Login-Start-Fallback aktiv ist, entstehen zusätzlich Login-Start-Artefakte:
- `reports/evidence/<env>-login-start-smoke*.json` (z. B. `dev-login-start-smoke-root.json`)
- `reports/evidence/<env>-login-start-smoke-bundle-summary.json`
- `reports/evidence/<env>-ui-auth-analyze-route-set-summary.json`

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

Hinweis: `https://dev.georanking.ch` (ohne `www`) ist für diesen Smoke kein unterstützter DEV-UI-Origin mehr (TLS-Zertifikat abgelaufen). Falls gesetzt, kanonisiert das Script intern auf `https://www.dev.georanking.ch`.

Wenn lokal **keine Live-Credentials** verfügbar sind, kann derselbe Script-Lauf optional in einen Login-Start-Fallback wechseln (degraded mode statt harter Abbruch):
```bash
BASE_URL="https://www.dev.georanking.ch" \
DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1 \
DEV_UI_SMOKE_RUN_ID="$(date +%s)-fallback" \
node scripts/run_dev_ui_auth_analyze_smoke.mjs
```
Dann werden `/login?...&start=1` und der Entry-Pfad `/login?...` per HTTP-Redirect auf den IdP geprüft; echte Analyze-Coverage wird dabei bewusst **nicht** simuliert.

CLI-Hinweise für das Single-Route-Script:
```bash
node scripts/run_dev_ui_auth_analyze_smoke.mjs --help
node scripts/run_dev_ui_auth_analyze_smoke.mjs --fallback-login-start
```
`--fallback-login-start` ist äquivalent zu `DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1`.
`--run-token` ist ein Legacy-Alias für `--run-id`.

Alternativ direkt per CLI-Overrides (statt ENV-Export):
```bash
node scripts/run_dev_ui_auth_analyze_smoke.mjs \
  --base-url https://www.dev.georanking.ch \
  --username "<username>" \
  --password "<password>" \
  --gui-path /gui/history \
  --run-id manual-$(date +%s) \
  --timeout-ms 90000 \
  --output-dir artifacts/dev-ui-live-smoke
```

Für den vollständigen Route-Satz lokal/manuell:
```bash
BASE_URL="https://www.dev.georanking.ch" \
DEV_UI_SMOKE_USERNAME="<username>" \
DEV_UI_SMOKE_PASSWORD="<password>" \
./scripts/smoke/run_gui_live_auth_analyze_route_set.sh
```

CLI-Overrides (optional, äquivalent zu ENVs):
```bash
./scripts/smoke/run_gui_live_auth_analyze_route_set.sh \
  --base-url https://www.dev.georanking.ch \
  --run-id-base manual-$(date +%s) \
  --routes /gui,/jobs?source=smoke \
  --timeout-ms 90000 \
  --headless \
  --output-dir artifacts/dev-ui-live-smoke
```

Wenn Live-Credentials fehlen, bricht der Runner nach dem Preflight standardmäßig absichtlich ab und gibt einen Fallback-Hinweis für Login-Start-Coverage aus (`run_login_start_smoke_bundle.sh`).

Optional kann für lokale Nachtläufe ein degradierter Fallback aktiviert werden:
```bash
./scripts/smoke/run_gui_live_auth_analyze_route_set.sh \
  --base-url https://www.dev.georanking.ch \
  --fallback-login-start-on-preflight-fail
```
Dann wird bei fehlenden Secrets automatisch `run_login_start_smoke_bundle.sh` ausgeführt (statt hard fail), und der Lauf endet nur dann rot, wenn auch der Fallback fehlschlägt.

Optional:
- `DEV_UI_SMOKE_ADDRESS_FILE=/abs/path/to/addresses.txt` oder `--address-file ...`
- `DEV_UI_SMOKE_TIMEOUT_MS=90000` oder `--timeout-ms 90000`
- `DEV_UI_SMOKE_HEADFUL=1` oder `--headful`
- `DEV_UI_SMOKE_LOGIN_REASON=manual_login` oder `--login-reason manual_login`
- `DEV_UI_SMOKE_EVIDENCE_DIR=artifacts/dev-ui-live-smoke` oder `--output-dir ...`
- `DEV_UI_SMOKE_SUMMARY_JSON=/abs/path/to/summary.json` oder `--summary-json <path>`
  (Legacy-Aliase: `--json-out <path>`, `--out <path>`)
- `DEV_UI_SMOKE_RUN_TOKEN=<token>` oder `--run-token <token>` (Legacy-Alias für `DEV_UI_SMOKE_RUN_ID` / `--run-id`)
- `--routes /gui,/jobs?source=smoke` (überschreibt den Standard-Route-Satz für gezielte Retests; im Workflow analog über `workflow_dispatch`-Input `routes`)
- `--route-presets core` oder `--route-presets jobs,results` (alternative Route-Auswahl ohne lange CSV; Presets: `all,core,modern,legacy,jobs,results,trace,minimal`; im Workflow analog über `workflow_dispatch`-Input `route_presets`)
- `./scripts/smoke/run_gui_live_auth_analyze_route_set.sh --summary-json <path>`
  (Legacy-Aliase: `--json-out <path>`, `--out <path>`)
- `DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_PREFLIGHT_FAIL=1` oder `--fallback-login-start-on-preflight-fail`
- Alias: `DEV_UI_SMOKE_ALLOW_LOGIN_START_FALLBACK=1` oder `--allow-login-start-fallback` (äquivalent zu `DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_PREFLIGHT_FAIL=1`)
- `DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1` (nur Single-Route-Script; nutzt Login-Start-Fallback statt hard fail)

Die Bundle-Skripte schreiben zusätzlich ein kompaktes Summary-Artefakt je Lauf:
- Login-Start: `<output-dir>/<env>-login-start-smoke-bundle-summary.json`
- Canonical Redirect: `<output-dir>/<env>-canonical-host-redirect-smoke-bundle-summary.json`

Hinweis: `run_login_start_smoke_bundle.sh` kanonisiert den Legacy-DEV-Origin
`https://dev.georanking.ch` (bzw. `https://dev.geo-ranking.ch`) automatisch auf
`https://www.dev.georanking.ch` / `https://www.dev.geo-ranking.ch` und markiert
das im Summary über `requested_base_url` + `base_url_canonicalized=true`.

Für Alias-Origin-Checks ohne Kanonisierung (z. B. direkte TLS-/Host-Validierung)
kann `--preserve-requested-base-url` gesetzt werden. Dann wird exakt der
angefragte Origin geprüft.

Der Route-Set-Runner schreibt ebenfalls ein Summary-Artefakt (für Live- und Fallback-Läufe):
- Live/Fallback-Route-Set: `<output-dir>/<env>-ui-auth-analyze-route-set-summary.json`
  - `mode=live_auth_analyze` bei echten Route-Fanout-Läufen
  - `mode=fallback_login_start` bei degradierter Login-Start-Fallback-Coverage
  - `routes[]` bleibt auch im Fallback befüllt (aus dem Login-Start-Bundle übernommen; `run_id` als `<run_id_base>-fallback-<ordinal>`)
  - `status=blocked` bei Preflight-Abbruch ohne aktivierten Fallback

### Workflow-Dispatch Beispiele

Gezielter Retest nur auf zwei Routen:
```bash
gh workflow run gui-dev-live-auth-analyze-smoke.yml \
  -f routes='/gui,/jobs?source=smoke'
```

Schneller Smoke über Presets (ohne lange Route-CSV):
```bash
gh workflow run gui-dev-live-auth-analyze-smoke.yml \
  -f route_presets='core,trace'
```

Degraded Mode (falls Live-Secrets gerade fehlen) mit längerem Timeout:
```bash
gh workflow run gui-dev-live-auth-analyze-smoke.yml \
  -f fallback_login_start_on_preflight_fail=true \
  -f timeout_ms=90000
```

Der Workflow akzeptiert dafür auch den Input-Alias:
```bash
gh workflow run gui-dev-live-auth-analyze-smoke.yml \
  -f allow_login_start_fallback=true
```
