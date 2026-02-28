# BL-31 Deploy-/Rollback-Runbook (API + UI getrennt) — Issue #330

## Ziel
Verbindlicher Ablauf für:
1. API-only Deployment
2. UI-only Deployment
3. kombiniertes Deployment (API → UI)
4. service-lokalen Rollback (API oder UI)

Gültig für die BL-31 Zielarchitektur mit getrennten ECS-Services:
- API-Service: `swisstopo-dev-api`
- UI-Service: `swisstopo-dev-ui`

---

## 1) Voraussetzungen

```bash
export AWS_REGION="eu-central-1"
export ECS_CLUSTER="swisstopo-dev"
export API_SERVICE="swisstopo-dev-api"
export UI_SERVICE="swisstopo-dev-ui"

# Domain-/Smoke-Konfiguration
export BL31_API_BASE_URL="https://api.<domain>"
export BL31_APP_BASE_URL="https://app.<domain>"
export BL31_CORS_ORIGIN="https://app.<domain>"
```

Zusätzlich nötig:
- AWS CLI Zugriff auf ECS/ECR
- `aws`, `curl`, `python3`
- Repo-Root als Arbeitsverzeichnis

Pflicht-Endpoints für jede Abnahme:
- API Health: `GET /health`
- UI Health: `GET /healthz`

---

## 2) API-only Deployment (service-lokal)

Primärpfad über den BL-31 Split-Runner (`api|ui|both`):

```bash
# 1) Pflicht: zuerst Dry-Run-Plan prüfen (keine AWS-Änderung)
python3 scripts/run_bl31_split_deploy.py --mode api

# 2) Ausführen (update-service + services-stable + strict smoke)
python3 scripts/run_bl31_split_deploy.py --mode api --execute
```

Erwartung:
- nur `swisstopo-dev-api` wird aktualisiert,
- `swisstopo-dev-ui` TaskDef bleibt unverändert (Guardrail),
- Smoke-Artefakt wird automatisch geschrieben (`artifacts/bl31/*-bl31-split-deploy-api-smoke.json`).

---

## 3) UI-only Deployment (service-lokal)

Primärpfad über den BL-31 Split-Runner:

```bash
# 1) Pflicht: Dry-Run-Plan
python3 scripts/run_bl31_split_deploy.py --mode ui

# 2) Ausführen (update-service + services-stable + strict smoke)
python3 scripts/run_bl31_split_deploy.py --mode ui --execute
```

Erwartung:
- nur `swisstopo-dev-ui` wird aktualisiert,
- `swisstopo-dev-api` TaskDef bleibt unverändert (Guardrail),
- Smoke-Artefakt wird automatisch geschrieben (`artifacts/bl31/*-bl31-split-deploy-ui-smoke.json`).

---

## 4) Kombiniertes Deployment (API + UI)

Verbindliche Reihenfolge bleibt API → UI und wird im Runner automatisch erzwungen.

```bash
# 1) Pflicht: Dry-Run-Plan (Reihenfolge + Guardrails prüfen)
python3 scripts/run_bl31_split_deploy.py --mode both

# 2) Ausführen (API-Step -> strict smoke -> UI-Step -> strict smoke)
python3 scripts/run_bl31_split_deploy.py --mode both --execute
```

Erwartung:
- Steps laufen deterministisch in Reihenfolge `api`, dann `ui`.
- Pro Step wird ein separates Strict-Smoke-Artefakt erzeugt:
  - `artifacts/bl31/*-bl31-split-deploy-api-smoke.json`
  - `artifacts/bl31/*-bl31-split-deploy-ui-smoke.json`

### 4.1 Fallback (Runner nicht verfügbar)

Falls der Split-Runner temporär nicht verfügbar ist, sind manuelle AWS-Kommandos zulässig — **aber nur**, wenn danach dieselben Guardrails und Strict-Smokes dokumentiert werden (inkl. Before/After-TaskDef für beide Services).

---

## 5) Service-lokaler Rollback

### 5.1 API-Rollback

```bash
CURRENT_API_TD="$(aws ecs describe-services \
  --cluster "${ECS_CLUSTER}" \
  --services "${API_SERVICE}" \
  --query 'services[0].taskDefinition' \
  --output text \
  --region "${AWS_REGION}")"

PREV_API_TD="$(aws ecs list-task-definitions \
  --family-prefix swisstopo-dev-api \
  --sort DESC \
  --max-items 2 \
  --query 'taskDefinitionArns[1]' \
  --output text \
  --region "${AWS_REGION}")"

aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${API_SERVICE}" \
  --task-definition "${PREV_API_TD}" \
  --region "${AWS_REGION}"

aws ecs wait services-stable \
  --cluster "${ECS_CLUSTER}" \
  --services "${API_SERVICE}" \
  --region "${AWS_REGION}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BL31_OUTPUT_JSON="artifacts/bl31/${STAMP}-rollback-api.json" \
BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh
```

### 5.2 UI-Rollback

```bash
CURRENT_UI_TD="$(aws ecs describe-services \
  --cluster "${ECS_CLUSTER}" \
  --services "${UI_SERVICE}" \
  --query 'services[0].taskDefinition' \
  --output text \
  --region "${AWS_REGION}")"

PREV_UI_TD="$(aws ecs list-task-definitions \
  --family-prefix swisstopo-dev-ui \
  --sort DESC \
  --max-items 2 \
  --query 'taskDefinitionArns[1]' \
  --output text \
  --region "${AWS_REGION}")"

aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${UI_SERVICE}" \
  --task-definition "${PREV_UI_TD}" \
  --region "${AWS_REGION}"

aws ecs wait services-stable \
  --cluster "${ECS_CLUSTER}" \
  --services "${UI_SERVICE}" \
  --region "${AWS_REGION}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BL31_OUTPUT_JSON="artifacts/bl31/${STAMP}-rollback-ui.json" \
BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh
```

Guardrail:
- Nie blind beide Services zurückrollen.
- Immer zuerst den betroffenen Service lokal stabilisieren.
- Nach jedem Rollback ist `run_bl31_routing_tls_smoke.sh` im Strict-Modus Pflicht.

---

## 6) Evidenzformat (Issue-/PR-Kommentar, verbindlich)

Für Deploy- und Rollback-Läufe wird dieses Schema verwendet:

```markdown
### BL-31 Deploy/Rollback Evidence
- Type: <deploy-api|deploy-ui|deploy-combined|rollback-api|rollback-ui>
- Timestamp (UTC): <YYYY-MM-DDTHH:MM:SSZ>
- Environment: <dev|staging|prod>
- Service(s): <swisstopo-dev-api / swisstopo-dev-ui>
- Before taskDefinition(s): <arn/revision>
- After taskDefinition(s): <arn/revision>
- Smoke command: `python3 scripts/run_bl31_split_deploy.py --mode <api|ui|both> --execute` (enthält strict smoke je Step)
- Smoke artifact: `artifacts/bl31/<timestamp>-bl31-split-deploy-<api|ui>-smoke.json`
- Smoke result: <pass|fail>
- Run/Log refs: <GitHub Actions URL oder CLI-Logpfad>
- Notes: <optional, z. B. CORS-Fix/Hotfix-Hinweis>
```

Minimalanforderung für „fertig“:
- TaskDefinition-Delta dokumentiert (before/after)
- Strict-Smoke-Nachweis mit Artefaktpfad
- Referenz auf Run/Log (CI oder CLI)

### 6.1 Smoke-/Evidence-Matrix (API-only, UI-only, Combined)

Für einen reproduzierbaren Matrix-Lauf über alle drei Modi:

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
python3 scripts/run_bl31_split_deploy.py --mode api  --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-api.json"
python3 scripts/run_bl31_split_deploy.py --mode ui   --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-ui.json"
python3 scripts/run_bl31_split_deploy.py --mode both --output-json "artifacts/bl31/${STAMP}-bl31-split-deploy-both.json"
```

Pflicht-Mindestfelder pro Artefakt:
- `mode`
- `taskDefinitionBefore`
- `taskDefinitionAfter`
- `result`
- `timestampUtc`

Format-/Feldkonsistenz kann automatisiert geprüft werden:

```bash
python3 scripts/check_bl31_smoke_evidence_matrix.py \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-api.json" \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-ui.json" \
  "artifacts/bl31/${STAMP}-bl31-split-deploy-both.json"
```

Bei produktiven Deploy-Läufen die gleichen Aufrufe mit `--execute` fahren.

---

## 7) Verlinkte Detail-Runbooks

- Routing/TLS/CORS Smoke Catch-up: [`docs/testing/bl31-routing-tls-smoke-catchup.md`](./testing/bl31-routing-tls-smoke-catchup.md)
- Smoke-/Evidence-Matrix (api/ui/both): [`docs/testing/bl31-smoke-evidence-matrix.md`](./testing/bl31-smoke-evidence-matrix.md)
- Allgemeines Deployment: [`docs/DEPLOYMENT_AWS.md`](./DEPLOYMENT_AWS.md)
- Betriebs-/Incident-Rahmen: [`docs/OPERATIONS.md`](./OPERATIONS.md)
