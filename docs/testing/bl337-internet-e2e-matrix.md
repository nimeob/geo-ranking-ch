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
