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

Ergebnis:
- API-Testfälle (`API.*`) werden in der Matrix von `planned` auf `pass|fail|blocked` fortgeschrieben.
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
- Die Checks decken Homepage-Load, Kernnavigation/Form-Render, Client-Side-Validierungsfehler und UI/API-Fehlerkonsistenz ab.
