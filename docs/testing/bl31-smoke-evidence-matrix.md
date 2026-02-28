# BL-31 Smoke-/Evidence-Matrix (API-only, UI-only, Combined)

## Ziel
Reproduzierbarer Nachweis, dass für alle Deploy-Modi (`api`, `ui`, `both`) konsistente Evidence-Artefakte mit Mindestfeldern vorliegen.

## Matrix-Lauf (Dry-Run)

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
export BL31_SMOKE_API_BASE_URL="https://api.<domain>"
export BL31_SMOKE_APP_BASE_URL="https://app.<domain>"
export BL31_SMOKE_CORS_ORIGIN="https://app.<domain>"

python3 scripts/run_bl31_split_deploy.py --mode api  --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-api.json"
python3 scripts/run_bl31_split_deploy.py --mode ui   --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-ui.json"
python3 scripts/run_bl31_split_deploy.py --mode both --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-both.json"
```

## Matrix-Lauf (Execute)

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
export BL31_SMOKE_API_BASE_URL="https://api.<domain>"
export BL31_SMOKE_APP_BASE_URL="https://app.<domain>"
export BL31_SMOKE_CORS_ORIGIN="https://app.<domain>"

python3 scripts/run_bl31_split_deploy.py --mode api  --execute --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-api.json"
python3 scripts/run_bl31_split_deploy.py --mode ui   --execute --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-ui.json"
python3 scripts/run_bl31_split_deploy.py --mode both --execute --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-both.json"
```

## Pflicht-Mindestfelder pro Artefakt
- `mode`
- `taskDefinitionBefore`
- `taskDefinitionAfter`
- `result`
- `timestampUtc`

Interpretation:
- `result=planned` → Dry-Run-Plan erzeugt, keine AWS-Änderung.
- `result=pass` → Lauf erfolgreich abgeschlossen.
- `result=fail` → nur zulässig, wenn der Lauf mit Fehlerbeleg dokumentiert wird.

## Format-Validator

```bash
python3 scripts/check_bl31_smoke_evidence_matrix.py \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-api.json" \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-ui.json" \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-both.json"
```

Default ohne Pfade (scannt nur kanonische Split-Deploy-Artefakte `*-bl31-split-deploy-{api,ui,both}.json`):

```bash
python3 scripts/check_bl31_smoke_evidence_matrix.py
```

Hinweis: Andere Artefaktklassen (z. B. `*-ui-smoke.json`) werden im Default-Scan bewusst nicht ausgewertet.
