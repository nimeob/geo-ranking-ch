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
- `docker`, `curl`, `python3`
- Repo-Root als Arbeitsverzeichnis

Pflicht-Endpoints für jede Abnahme:
- API Health: `GET /health`
- UI Health: `GET /healthz`

---

## 2) API-only Deployment (service-lokal)

```bash
IMAGE_TAG="$(git rev-parse --short HEAD)"
AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

# 1) API-Image bauen + pushen
docker build -t swisstopo-dev-api:${IMAGE_TAG} .
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker tag swisstopo-dev-api:${IMAGE_TAG} \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/swisstopo-dev-api:${IMAGE_TAG}"
docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/swisstopo-dev-api:${IMAGE_TAG}"

# 2) API-Service ausrollen (UI bleibt unverändert)
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${API_SERVICE}" \
  --force-new-deployment \
  --region "${AWS_REGION}"

aws ecs wait services-stable \
  --cluster "${ECS_CLUSTER}" \
  --services "${API_SERVICE}" \
  --region "${AWS_REGION}"
```

Pflicht-Smoke nach API-only Deploy (inkl. UI-Reachability/CORS):

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BL31_OUTPUT_JSON="artifacts/bl31/${STAMP}-deploy-api.json" \
BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh
```

---

## 3) UI-only Deployment (service-lokal)

```bash
IMAGE_TAG="$(git rev-parse --short HEAD)"
AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

# 1) UI-Image bauen + pushen
docker build \
  -f Dockerfile.ui \
  --build-arg APP_VERSION="${IMAGE_TAG}" \
  --build-arg UI_API_BASE_URL="${BL31_API_BASE_URL}" \
  -t swisstopo-dev-ui:${IMAGE_TAG} .

aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker tag swisstopo-dev-ui:${IMAGE_TAG} \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/swisstopo-dev-ui:${IMAGE_TAG}"
docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/swisstopo-dev-ui:${IMAGE_TAG}"

# 2) UI-Service ausrollen (API bleibt unverändert)
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${UI_SERVICE}" \
  --force-new-deployment \
  --region "${AWS_REGION}"

aws ecs wait services-stable \
  --cluster "${ECS_CLUSTER}" \
  --services "${UI_SERVICE}" \
  --region "${AWS_REGION}"
```

Pflicht-Smoke nach UI-only Deploy:

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BL31_OUTPUT_JSON="artifacts/bl31/${STAMP}-deploy-ui.json" \
BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh
```

---

## 4) Kombiniertes Deployment (API + UI)

Verbindliche Reihenfolge:
1. API deployen
2. API/UI/CORS Smoke (`strict`) erfolgreich
3. UI deployen
4. API/UI/CORS Smoke (`strict`) erfolgreich

```bash
# A) API deployen
# (Abschnitt 2 ausführen)

# B) Strict-Smoke nach API
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BL31_OUTPUT_JSON="artifacts/bl31/${STAMP}-deploy-combined-step-api.json" \
BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh

# C) UI deployen
# (Abschnitt 3 ausführen)

# D) Strict-Smoke nach UI
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BL31_OUTPUT_JSON="artifacts/bl31/${STAMP}-deploy-combined-step-ui.json" \
BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh
```

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
- Smoke command: `BL31_STRICT_CORS=1 ./scripts/run_bl31_routing_tls_smoke.sh`
- Smoke artifact: `artifacts/bl31/<timestamp>-<run-type>.json`
- Smoke result: <pass|fail>
- Run/Log refs: <GitHub Actions URL oder CLI-Logpfad>
- Notes: <optional, z. B. CORS-Fix/Hotfix-Hinweis>
```

Minimalanforderung für „fertig“:
- TaskDefinition-Delta dokumentiert (before/after)
- Strict-Smoke-Nachweis mit Artefaktpfad
- Referenz auf Run/Log (CI oder CLI)

---

## 7) Verlinkte Detail-Runbooks

- Routing/TLS/CORS Smoke Catch-up: [`docs/testing/bl31-routing-tls-smoke-catchup.md`](./testing/bl31-routing-tls-smoke-catchup.md)
- Allgemeines Deployment: [`docs/DEPLOYMENT_AWS.md`](./DEPLOYMENT_AWS.md)
- Betriebs-/Incident-Rahmen: [`docs/OPERATIONS.md`](./OPERATIONS.md)
