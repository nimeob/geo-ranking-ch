> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [RUNBOOKS.md](RUNBOOKS.md)

---

# BL-337 Internet-E2E Matrix (WP1 / Issue #396)

## Ziel
Ein kanonisches, reproduzierbares Format für Internet-E2E-Testfälle gegen die Dev-Frontdoors:
- API: `https://api.dev.georanking.ch`
- UI: `https://www.dev.georanking.ch`

Jeder Testfall enthält verpflichtend **Expected Result** und **Actual Result** plus Pass/Fail-Status.

## 1) Matrix erzeugen (Initialkatalog)

```bash
python3 scripts/manage_bl337_internet_e2e_matrix.py \
  --output artifacts/bl337/latest-internet-e2e-matrix.json
```

Optional mit fixem Timestamp (deterministische Artefakte in CI):

```bash
python3 scripts/manage_bl337_internet_e2e_matrix.py \
  --generated-at-utc 2026-03-01T00:00:00Z \
  --output artifacts/bl337/latest-internet-e2e-matrix.json
```

## 2) Matrix validieren (Schema + Summary)

```bash
python3 scripts/manage_bl337_internet_e2e_matrix.py \
  --validate artifacts/bl337/latest-internet-e2e-matrix.json
```

Strenger Abschlussmodus (für spätere Work-Packages):

```bash
python3 scripts/manage_bl337_internet_e2e_matrix.py \
  --validate artifacts/bl337/latest-internet-e2e-matrix.json \
  --require-actual
```

## 3) Pflichtfelder pro Testfall
- `testId`
- `area` (`api`/`ui`)
- `title`
- `preconditions`
- `steps`
- `expectedResult`
- `actualResult` (initial `null`, später Pflicht im Abschlussmodus)
- `status` (`planned`/`pass`/`fail`/`blocked`)
- `evidenceLinks`
- `notes`

## 4) Einbettung in BL-337
- Dieses Work-Package stellt nur Katalog + Format + Guardrails bereit.
- Die tatsächliche API-/UI-Ausführung erfolgt in den Folge-Issues `#397` und `#398`.
- Konsolidierter Abschluss inkl. Parent-Summary erfolgt in `#399`.

## 5) WP2 API-Frontdoor-Ausführung (Issue #397)

Reproduzierbare API-E2E-Ausführung inkl. Matrix-Update und Evidence-JSON:

```bash
python3 scripts/run_bl337_api_frontdoor_e2e.py \
  --matrix artifacts/bl337/latest-internet-e2e-matrix.json \
  --evidence-json artifacts/bl337/<timestamp>-wp2-api-frontdoor-e2e.json
```

Optional mit Auth (falls `POST /analyze` geschützt ist):

```bash
BL337_API_AUTH_TOKEN="<token>" \
python3 scripts/run_bl337_api_frontdoor_e2e.py
```

Optional für nächtliche Public-Probes ohne Token (401/403 auf Analyze wird als `blocked` dokumentiert, aber Exit-Code bleibt 0):

```bash
python3 scripts/run_bl337_api_frontdoor_e2e.py --allow-auth-blocked
```

Ergebnis:
- API-Testfälle (`API.*`) werden in der Matrix von `planned` auf `pass|fail|blocked` fortgeschrieben.
- Der Non-Basic-Sicherheitsfall `API.ANALYZE.NON_BASIC.FINAL_STATE` prüft explizit, dass `intelligence_mode=extended` deterministisch terminiert (Success **oder** strukturierter Error-State).
- `actualResult` + `evidenceLinks` werden pro API-Fall gesetzt.
- Evidence-Datei enthält pro Testfall `httpStatus`, `reason`, `responseExcerpt` und Gesamtsummary.

## 6) WP3 UI-Frontdoor-Ausführung (Issue #398)

Reproduzierbare UI-E2E-Ausführung inkl. Matrix-Update und Evidence-Artefakten:

```bash
python3 scripts/run_bl337_ui_frontdoor_e2e.py \
  --matrix artifacts/bl337/latest-internet-e2e-matrix.json \
  --evidence-json artifacts/bl337/<timestamp>-wp3-ui-frontdoor-e2e.json
```

Optional mit Override für Test-/Staging-Targets:

```bash
python3 scripts/run_bl337_ui_frontdoor_e2e.py \
  --app-base-url "https://www.dev.georanking.ch" \
  --api-base-url "https://api.dev.georanking.ch"
```

Ergebnis:
- UI-Testfälle (`UI.*`) werden in der Matrix von `planned` auf `pass|fail|blocked` fortgeschrieben.
- Pro Lauf werden drei Evidence-Artefakte erzeugt: `*-wp3-ui-frontdoor-e2e.json`, `*-home.html`, `*-api-probe.json`.
- Die Checks decken Homepage-Load, Kernnavigation/Form-Render **inkl. Karten-Basemap-Marker (Tile-Layer/Zoom-Handler)**, Client-Side-Validierungsfehler und UI/API-Fehlerkonsistenz ab.

## 7) One-shot Wrapper für Nightly/Worker-Läufe

Für autonome Runs gibt es einen kombinierten Entry-Point, der WP1+WP2+WP3 in einem Durchlauf ausführt:

```bash
./scripts/run_bl337_frontdoor_e2e.sh
```

Verhalten bei Auth:
- `BL337_AUTH_MODE=auto` (Default):
  - mit `BL337_API_AUTH_TOKEN` läuft API-WP2 strikt mit Token.
  - ohne Token versucht der Wrapper bei gesetzten OIDC-Hints (`OIDC_TOKEN_URL`, `OIDC_CLIENT_ID`) automatisch `scripts/smoke/auth_preflight.sh` und nutzt den geminteten Bearer-Token.
  - wenn kein Token verfügbar ist oder das Preflight scheitert, wird API-WP2 mit `--allow-auth-blocked` gefahren.
- `BL337_AUTH_MODE=allow`: `--allow-auth-blocked` immer aktiv.
- `BL337_AUTH_MODE=strict`: `--allow-auth-blocked` nie aktiv.

Optional relevante Overrides:
- `BL337_API_BASE_URL`, `BL337_APP_BASE_URL`
- `BL337_TIMEOUT_SECONDS`
- `BL337_MATRIX_PATH`, `BL337_API_EVIDENCE_JSON`, `BL337_UI_EVIDENCE_JSON`
- `BL337_AUTH_PREFLIGHT_SCRIPT` (z. B. für lokale/CI-Stubs)
- OIDC-Hints für Auto-Minting: `OIDC_TOKEN_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET|OIDC_CLIENT_SECRET_FILE`, optional `OIDC_SCOPE`, `OIDC_AUDIENCE`
