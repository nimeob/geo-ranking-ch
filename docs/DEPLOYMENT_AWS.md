# AWS Deployment — geo-ranking-ch

> **Konventionen in diesem Dokument:**
> - ✅ **Verifiziert** — direkt via AWS CLI bestätigt (Stand: 2026-02-25)
> - ⚠️ **Annahme** — sinnvolle Annahme basierend auf Projektkontext; zu validieren
> - ❌ **Noch nicht vorhanden** — Ressource existiert noch nicht oder nicht gefunden

---

## 1. Ist-Stand der Infrastruktur

### AWS-Basis

| Parameter | Wert | Status |
|---|---|---|
| AWS Account ID | `523234426229` | ✅ Verifiziert |
| Region | `eu-central-1` (Frankfurt) | ✅ Verifiziert |
| CI/CD Deploy-Principal | `arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role` (OIDC) | ✅ Verifiziert |
| IAM Deploy-User | `arn:aws:iam::523234426229:user/swisstopo-api-deploy` | ⚠️ Legacy — nicht mehr für CI/CD genutzt |

### AWS-Naming-Konvention

> AWS-Ressourcen dieses Projekts heißen intern **`swisstopo`** — obwohl das Repository `geo-ranking-ch` heißt. Das ist bewusst so und muss nicht geändert werden. Die AWS-Namen sind intern und nicht öffentlich exponiert.

### Umgebungen

> **Aktueller Stand:** Es existiert ausschließlich eine **`dev`-Umgebung**. `staging` und `prod` sind noch nicht aufgebaut.

### Netzwerk-/Ingress-Entscheidungen

Das Zielbild für VPC-/Ingress-Design ist in [`docs/NETWORK_INGRESS_DECISIONS.md`](NETWORK_INGRESS_DECISIONS.md) dokumentiert (BL-05).

### Datenhaltung & API-Sicherheit

Die verbindlichen Entscheidungen zu Persistenzbedarf (BL-06) und API-Sicherheitskontrollen für `/analyze` (BL-07) sind in [`docs/DATA_AND_API_SECURITY.md`](DATA_AND_API_SECURITY.md) festgehalten.

### `staging`/`prod` Vorbereitung

Promotion-Zielbild inkl. Gates und Rollback-Prozess ist in [`docs/ENV_PROMOTION_STRATEGY.md`](ENV_PROMOTION_STRATEGY.md) dokumentiert (BL-09).

### TLS-Zertifikats-Migrationspfad (Dev → Official)

Der verbindliche Runbook-Pfad für den Übergang von self-signed Dev-Zertifikaten auf offizielle Zertifikate (ACM/Let's Encrypt/Corporate CA), inklusive TLS-Baseline (>= TLS 1.2, bevorzugt TLS 1.3), Rotation, Rollback und Incident-Hinweisen, ist in [`docs/TLS_CERTIFICATE_MIGRATION_RUNBOOK.md`](TLS_CERTIFICATE_MIGRATION_RUNBOOK.md) dokumentiert.

### Aktuelle Ressourcen (dev)

| Ressource | Name / ARN | Status |
|---|---|---|
| S3 Bucket | `swisstopo-dev-523234426229` | ✅ Verifiziert |
| ECS Cluster | `swisstopo-dev` | ✅ Verifiziert |
| ECS Service | `swisstopo-dev-api` | ✅ Verifiziert |
| ECR Repository | `523234426229.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-api` | ✅ Verifiziert |
| Lambda Functions | `swisstopo-dev-sns-to-telegram`, `swisstopo-dev-health-probe` | ✅ Verifiziert |
| EventBridge Rules | `swisstopo-dev-health-probe-schedule` (rate 5 min) | ✅ Verifiziert |
| CloudFormation Stacks | — | ❌ Nicht gefunden |
| API Gateway | — | ⚠️ Zu prüfen |
| RDS / DynamoDB | — | ⚠️ Zu prüfen |

---

## 2. Tagging Standard

Alle AWS-Ressourcen dieses Projekts **müssen** mit folgenden Tags versehen werden. Diese Tags sind verbindlich und dienen Kostenübersicht, Ownership und Automatisierung.

| Tag-Key | Tag-Value | Beschreibung |
|---|---|---|
| `Environment` | `dev` | Aktuell einzige Umgebung |
| `ManagedBy` | `openclaw` | Verwaltungsebene / Agent |
| `Owner` | `nico` | Verantwortliche Person |
| `Project` | `swisstopo` | Interner Projektname (AWS-seitig) |

> **Hinweis:** Der Tag `Project=swisstopo` spiegelt das interne AWS-Naming wider. Der Repo-Name `geo-ranking-ch` ist davon unabhängig.

### Tags per AWS CLI setzen (Beispiel S3)

```bash
aws s3api put-bucket-tagging \
  --bucket swisstopo-dev-523234426229 \
  --tagging 'TagSet=[
    {Key=Environment,Value=dev},
    {Key=ManagedBy,Value=openclaw},
    {Key=Owner,Value=nico},
    {Key=Project,Value=swisstopo}
  ]'
```

### Tags per AWS CLI setzen (Beispiel ECS Cluster)

```bash
aws ecs tag-resource \
  --resource-arn arn:aws:ecs:eu-central-1:523234426229:cluster/swisstopo-dev \
  --tags \
    key=Environment,value=dev \
    key=ManagedBy,value=openclaw \
    key=Owner,value=nico \
    key=Project,value=swisstopo
```

> Bei IaC (CDK/Terraform): Tags auf Stack-Ebene definieren, damit sie automatisch auf alle Ressourcen vererbt werden.

---

## 3. IAM-Berechtigungen (OIDC Deploy-Role) — BL-03 ✅ abgeschlossen

Aktueller Workflow (`.github/workflows/deploy.yml`) nutzt GitHub OIDC — keine statischen AWS Access Keys erforderlich.

Artefakte (versioniert in `infra/iam/`):

- `infra/iam/deploy-policy.json` — Least-Privilege Permission-Policy (identisch mit live v2)
- `infra/iam/trust-policy.json` — Trust-Policy der OIDC-Deploy-Role (repo-scoped, `main`-only)
- `infra/iam/README.md` — Herleitung, Nachweis, Hinweise für Staging/Prod

### Deploy-Principal (Ist-Stand, verifiziert 2026-02-25)

- ✅ OIDC-Role `swisstopo-dev-github-deploy-role` existiert und ist korrekt konfiguriert
- ✅ Attached Policy: `swisstopo-dev-github-deploy-policy` (v2, Defaultversion)
- ✅ Policy-Inhalt identisch mit `infra/iam/deploy-policy.json` (kein Drift)
- ✅ Trust-Condition: `repo:nimeob/geo-ranking-ch:ref:refs/heads/main` (nur `main`-Branch)
- ✅ Keine Inline Policies, keine weiteren angehängten Policies

### Minimalrechte (implementiert, kein Handlungsbedarf)

| Schritt | Benötigte AWS Actions | Scope |
|---|---|---|
| ECR Login | `ecr:GetAuthorizationToken` | `*` |
| Docker Push nach ECR | `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage` | nur `swisstopo-dev-api`-Repo |
| ECS Ist-TaskDef lesen | `ecs:DescribeServices`, `ecs:DescribeTaskDefinition` | Service/Cluster scoped (DescribeServices); `*` für DescribeTaskDefinition (AWS-IAM-Constraint) |
| Neue Revision registrieren | `ecs:RegisterTaskDefinition` + `iam:PassRole` (Execution-/Task-Role) | `*` für Register; PassRole nur auf die zwei Task-Roles |
| ECS Service umstellen + Wait | `ecs:UpdateService`, `ecs:DescribeServices` | nur dev Cluster + Service |

> Vollständiger Nachweis in `infra/iam/README.md`.

---

## 4. Deploy-Runbook

> ⚠️ Dieses Runbook ist ein Template und wird aktualisiert, sobald der Stack definiert ist.

### Voraussetzungen

```bash
# AWS CLI konfiguriert und Zugriff verifiziert
aws sts get-caller-identity

# Docker vorhanden (falls Container-Deployment)
docker --version

# Korrekte Region gesetzt
export AWS_DEFAULT_REGION=eu-central-1
export AWS_ACCOUNT_ID=523234426229
```

### Initialer Setup (First-Time Deployment)

```bash
# 1. ECR Repository anlegen (⚠️ angepasst an finalen Stack)
aws ecr create-repository \
  --repository-name geo-ranking-ch-api \
  --region eu-central-1

# 2. S3 Bucket anlegen
aws s3 mb s3://geo-ranking-ch-${AWS_ACCOUNT_ID} \
  --region eu-central-1

# 3. IaC deployen (Beispiel CDK — Stack muss erst erstellt werden)
# cd infra/ && cdk deploy --all
```

### Runtime-Konvention (MVP Webservice)

- Container-Port: `8080`
- Healthcheck-Endpoint: `GET /health`
- Version-Endpoint: `GET /version`

### BL-31 Zielbild (2-Container: API + UI)

Für BL-31 wird das Deployment von einem Single-Service-MVP auf zwei getrennte ECS-Services erweitert:

| Bereich | API (bestehend) | UI (neu) |
|---|---|---|
| ECS Service | `swisstopo-dev-api` | `swisstopo-dev-ui` |
| ECR Repository | `swisstopo-dev-api` | `swisstopo-dev-ui` |
| Health Endpoint | `/health` | `/healthz` |
| Ingress | `api.<domain>` | `app.<domain>` |

Verbindliche Betriebsregeln:
- API und UI werden **separat** gebaut, ausgerollt und zurückgerollt.
- Bei kombinierten Änderungen gilt als sichere Reihenfolge: **API deployen → API smoke → UI deployen → UI smoke**.
- CORS-Allowlist wird auf UI-Origin eingeschränkt; keine globale `*`-Freigabe.

Verbindlicher Ablauf inkl. service-lokaler Rollback-Kommandos und Evidenzformat:
- [`docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md`](BL31_DEPLOY_ROLLBACK_RUNBOOK.md)

**Runtime-ENV (API, BL-31.3 relevant):**

| ENV | Default | Zweck |
|---|---|---|
| `CORS_ALLOW_ORIGINS` | _(leer)_ | Komma-separierte CORS-Allowlist für `POST/OPTIONS /analyze` (z. B. `https://app.<domain>`). |

### BL-31.2 Artefakt-Basis für UI-Service

BL-31.2 legt die technische Basis für ein eigenes UI-Artefakt fest:

- UI-Dockerfile: [`Dockerfile.ui`](../Dockerfile.ui)
- UI-Runtime-Entrypoint: `python -m src.ui_service`
- ECS-Task-Template: [`infra/ecs/taskdef.swisstopo-dev-ui.json`](../infra/ecs/taskdef.swisstopo-dev-ui.json)
- Ziel-ECR-Repository: **`swisstopo-dev-ui`**

**Build-Args (UI):**

| Build-Arg | Default | Zweck |
|---|---|---|
| `UI_PORT` | `8080` | Container-Port der UI-Runtime |
| `APP_VERSION` | `dev` | Version im UI-Header + `/healthz` |
| `UI_API_BASE_URL` | _(leer)_ | Absolute API-Basis (z. B. `https://api.<domain>`) |

**Runtime-ENV (UI):**

| ENV | Herkunft | Zweck |
|---|---|---|
| `PORT` | aus `UI_PORT` | Bind-Port des UI-Service |
| `APP_VERSION` | aus Build-Arg / Task-ENV | UI-Versionierung |
| `UI_API_BASE_URL` | aus Build-Arg / Task-ENV | API-Ziel für GUI-Analyze-Requests |

Beispiel Build + Push für UI-Artefakt:

```bash
IMAGE_TAG=$(git rev-parse --short HEAD)

# 1) UI-Image bauen (separat vom API-Image)
docker build \
  -f Dockerfile.ui \
  --build-arg APP_VERSION=${IMAGE_TAG} \
  --build-arg UI_API_BASE_URL="https://api.<domain>" \
  -t swisstopo-dev-ui:${IMAGE_TAG} .

# 2) ECR Login (wie API)
aws ecr get-login-password --region eu-central-1 \
  | docker login --username AWS \
    --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com

# 3) UI-Image pushen
docker tag swisstopo-dev-ui:${IMAGE_TAG} \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-ui:${IMAGE_TAG}
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-ui:${IMAGE_TAG}
```

Wenn lokal kein nutzbarer Docker-Daemon verfügbar ist (z. B. OpenClaw-Worker ohne Socket), kann derselbe Pfad reproduzierbar über CodeBuild + AWS CLI gefahren werden:

```bash
./scripts/setup_bl31_ui_artifact_path.sh
```

Das Skript führt idempotent aus:
- ECR-Repo + benötigte CodeBuild-Push-Policy prüfen/setzen,
- Source-ZIP nach `s3://swisstopo-dev-523234426229/codebuild-src/geo-ranking-ch-main.zip` hochladen,
- `swisstopo-dev-api-openclaw-build` mit `Dockerfile.ui` starten,
- UI-Image mit reproduzierbarem Tag nach `swisstopo-dev-ui` pushen,
- ECS-Task-Definition `swisstopo-dev-ui` mit konkreter Image-Revision registrieren (Fallback via `openclaw-ops-role` bei fehlendem `iam:PassRole`/`ecs:RegisterTaskDefinition` auf dem aktuellen Principal),
- Evidenz als JSON unter `artifacts/bl31/*-bl31-ui-artifact-path.json` schreiben.

Task-Definition-Hinweis:
- Das Template `infra/ecs/taskdef.swisstopo-dev-ui.json` ist als revisionsfähige Basis gedacht.
- Platzhalter (`__IMAGE_TAG__`, `__APP_VERSION__`, `__DOMAIN__`) vor `register-task-definition` ersetzen.
- Healthcheck für UI läuft auf `GET /healthz`.

### BL-31.3 Routing/TLS + CORS Abnahmepfad

Host-basiertes Zielrouting (ALB):
- `Host: api.<domain>` → API Target Group
- `Host: app.<domain>` → UI Target Group

TLS-Basis:
- Ein ACM-Zertifikat (SAN oder Wildcard) deckt **beide** Hosts (`api.*`, `app.*`) ab.
- HTTP-Listener leitet via 301/308 auf HTTPS um.

CORS-Härtung (API):
- `CORS_ALLOW_ORIGINS` auf UI-Origin(s) setzen, z. B.:

```bash
CORS_ALLOW_ORIGINS="https://app.<domain>"
```

- `OPTIONS /analyze` liefert bei erlaubter Origin `204` + `Access-Control-Allow-Origin`.
- Nicht erlaubte Origins werden mit `403 cors_origin_not_allowed` abgewiesen.

Reproduzierbare Verifikation (Strict-Modus):

```bash
BL31_API_BASE_URL="https://api.<domain>" \
BL31_APP_BASE_URL="https://app.<domain>" \
BL31_CORS_ORIGIN="https://app.<domain>" \
BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh
```

Erwartung: alle Checks `pass`, Exit-Code `0`.

### Reguläres Deployment (nach erstem Setup)

```bash
# 1. Docker Image bauen
IMAGE_TAG=$(git rev-parse --short HEAD)
docker build -t swisstopo-dev-api:${IMAGE_TAG} .

# 2. ECR Login
aws ecr get-login-password --region eu-central-1 \
  | docker login --username AWS \
    --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com

# 3. Image pushen (ECR-Repo: swisstopo-dev-api — internes AWS-Naming)
docker tag swisstopo-dev-api:${IMAGE_TAG} \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-api:${IMAGE_TAG}
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-api:${IMAGE_TAG}

# 4. ECS Service aktualisieren (Cluster: swisstopo-dev, Service: swisstopo-dev-api)
aws ecs update-service \
  --cluster swisstopo-dev \
  --service swisstopo-dev-api \
  --force-new-deployment \
  --region eu-central-1
```

### Deployment via GitHub Actions

CI/CD-Workflow für ECS (dev) ist in `.github/workflows/deploy.yml` umgesetzt (Trigger: **Push auf `main`** + manueller `workflow_dispatch`). Er baut ein Docker-Image, pusht nach ECR, rolled den ECS-Service auf eine neue Task-Definition und wartet auf `services-stable`.

Danach läuft ein Smoke-Test gegen `SERVICE_HEALTH_URL` (HTTP-Check auf `/health`). Wenn die Variable leer oder nicht gesetzt ist, wird der Smoke-Test mit Hinweis übersprungen (kein Hard-Fail).

**Benötigte GitHub Secrets (zu setzen unter Settings → Secrets):**

| Secret | Beschreibung |
|---|---|
| _(keine erforderlich)_ | AWS Auth läuft via GitHub OIDC Role Assume (`aws-actions/configure-aws-credentials@v4`) |

**Benötigte GitHub Variables (zu setzen unter Settings → Variables):**

| Variable | Beschreibung |
|---|---|
| `ECR_REPOSITORY` | Ziel-Repository in ECR (z. B. `swisstopo-dev-api`) |
| `ECS_CLUSTER` | ECS Cluster (z. B. `swisstopo-dev`) |
| `ECS_SERVICE` | ECS Service (z. B. `swisstopo-dev-api`) |
| `ECS_CONTAINER_NAME` | Container-Name in der Task-Definition |
| `SERVICE_HEALTH_URL` | Vollständige Health-URL für Smoke-Test (z. B. `https://<alb-dns>/health`) |

**OIDC-Rollenbindung (AWS):**
- Workflow verwendet `aws-actions/configure-aws-credentials@v4` mit
  `role-to-assume: arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role`.
- Erforderliche Minimalrechte siehe `infra/iam/deploy-policy.json`.

> `SERVICE_HEALTH_URL` ist optional: fehlt die Variable, wird der Smoke-Test im Workflow sauber übersprungen.

### BL-02 Verifikationsnachweise (CI/CD Deploy via Push auf `main`)

| Datum (UTC) | Run | Trigger | Ergebnis | Relevante Schritte |
|---|---|---|---|---|
| 2026-02-25 | https://github.com/nimeob/geo-ranking-ch/actions/runs/22416418587 | `push` auf `main` | ✅ Success | `Wait for service stability` = ✅, `Smoke-Test /health` = ✅ |
| 2026-02-25 | https://github.com/nimeob/geo-ranking-ch/actions/runs/22416878804 | `push` auf `main` | ❌ Failure | `Build and push image` fehlgeschlagen (`AWS_ACCOUNT_ID` leer), nachgelagerte Schritte inkl. `services-stable`/Smoke-Test wurden übersprungen |
| 2026-02-25 | https://github.com/nimeob/geo-ranking-ch/actions/runs/22416930879 | `push` auf `main` | ❌ Failure | `Register new task definition revision` fehlgeschlagen (`AccessDeniedException` auf `ecs:DescribeTaskDefinition`), `services-stable`/Smoke-Test übersprungen |
| 2026-02-25 | https://github.com/nimeob/geo-ranking-ch/actions/runs/22417749775 | `workflow_dispatch` | ✅ Success | IAM-Policy-Fix validiert (`Register new task definition revision` wieder grün), `services-stable` + Smoke-Test erfolgreich |
| 2026-02-25 | https://github.com/nimeob/geo-ranking-ch/actions/runs/22417939827 | `push` auf `main` | ✅ Success | End-to-End OIDC-Deploy mit `services-stable` + Smoke-Test erfolgreich |

Kurzfazit BL-02:
- Trigger per `push` auf `main`: ✅ nachgewiesen.
- `services-stable` erfolgreich: ✅ mehrfach bestätigt (`22416418587`, `22417939827`).
- Smoke-Test `/health` erfolgreich: ✅ mehrfach bestätigt (`22416418587`, `22417939827`).
- Regression `ecs:DescribeTaskDefinition` wurde in IAM-Policy adressiert (OIDC-Role, Policy-Version `v2`) und per Validierungsrun `22417749775` sowie folgendem Push-Run `22417939827` bestätigt.

> ⚠️ Niemals Secrets direkt in Code oder Dokumente schreiben.

### Terraform IaC-Startpaket (dev)

Ein minimales, bewusst nicht-destruktives Terraform-Startpaket liegt unter:

- `infra/terraform/`

Inhalt:
- Skelett für ECS Cluster, ECR Repository, CloudWatch Log Group und dev-S3-Bucket
- sichere Flags (`manage_* = false` als Default)
- Import-first-Dokumentation in `infra/terraform/README.md`
- read-only Vorprüf-Script `scripts/check_import_first_dev.sh`

Empfohlene Reihenfolge: **`init` → `plan` → `import` → `apply`**.

> Für bestehende dev-Ressourcen: **kein blindes apply**; zuerst Import pro Ressource.

---

## 5. Rollback-Prozedur

### ECS Service Rollback (service-lokal)

```bash
# API: vorherige Task-Definition-Revision ermitteln
aws ecs describe-services \
  --cluster swisstopo-dev \
  --services swisstopo-dev-api \
  --query 'services[0].deployments'

# API: auf vorherige Revision zurückwechseln
PREV_API_REVISION=<nummer>
aws ecs update-service \
  --cluster swisstopo-dev \
  --service swisstopo-dev-api \
  --task-definition swisstopo-dev-api:${PREV_API_REVISION} \
  --region eu-central-1

# UI: analog (sobald BL-31 UI-Service live ist)
PREV_UI_REVISION=<nummer>
aws ecs update-service \
  --cluster swisstopo-dev \
  --service swisstopo-dev-ui \
  --task-definition swisstopo-dev-ui:${PREV_UI_REVISION} \
  --region eu-central-1
```

Rollback-Regel BL-31:
- Nur den betroffenen Service zurückrollen (kein unnötiger Dual-Rollback).
- Nach jedem Rollback sofort service-spezifischen Smoke laufen lassen (`api.<domain>/health` bzw. `app.<domain>/healthz`).
- Für BL-31 gilt der vollständige, reproduzierbare Rollback-Ablauf aus [`docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md`](BL31_DEPLOY_ROLLBACK_RUNBOOK.md) (inkl. Strict-Smoke + Evidenzformat für Issue/PR-Kommentare).

### Lambda Rollback (⚠️ falls Serverless-Architektur gewählt)

```bash
# Vorherige Version aktivieren
aws lambda update-alias \
  --function-name geo-ranking-ch-handler \
  --name live \
  --function-version <vorherige-versionsnummer>
```

### Notfall-Rollback via Git

```bash
# Letzten stabilen Tag finden
git tag -l | sort -V | tail -5

# Auf Tag deployen
git checkout v<stabile-version>
# Dann obiges Deploy-Runbook ausführen
```

---

## 6. Monitoring & Observability (MVP-Stand)

| Komponente | Tool | Status |
|---|---|---|
| Logs | CloudWatch Logs | ✅ Log Group `/swisstopo/dev/ecs/api` aktiv, Retention 30 Tage verifiziert |
| Metriken | CloudWatch Metrics | ✅ Custom Metrics via Log Metric Filters aktiv (`HttpRequestCount`, `Http5xxCount` in `swisstopo/dev-api`) |
| Alarme | CloudWatch Alarms | ✅ Alarme aktiv: `swisstopo-dev-api-running-taskcount-low` (Service-Ausfall) + `swisstopo-dev-api-http-5xx-rate-high` (Fehlerquote) |
| Alert-Kanal | SNS + Lambda → Telegram | ✅ Aktiv und getestet (ALARM/OK im Telegram-Chat bestätigt, 2026-02-25) |
| Telegram-Alerting | Lambda `swisstopo-dev-sns-to-telegram` | ✅ Aktiv (SSM SecureString + SNS-Subscription + Lambda-Permission verifiziert) |
| Uptime/HTTP Health | Lambda `swisstopo-dev-health-probe` + EventBridge (rate 5 min) | ✅ Aktiv und getestet (2026-02-25) — dynamische ECS-IP-Auflösung, Metrik `HealthProbeSuccess`, Alarm `swisstopo-dev-api-health-probe-fail` |
| Ops-Helper | `scripts/check_ecs_service.sh`, `scripts/tail_logs.sh`, `scripts/setup_monitoring_baseline_dev.sh`, `scripts/check_monitoring_baseline_dev.sh`, `scripts/setup_telegram_alerting_dev.sh`, `scripts/setup_health_probe_dev.sh`, `scripts/check_health_probe_dev.sh`, `scripts/setup_bl31_ui_artifact_path.sh`, `scripts/setup_bl31_ui_monitoring_baseline.sh`, `scripts/check_bl31_ui_monitoring_baseline.sh` | ✅ Triage + Baseline-Provisioning + Read-only Monitoring-Checks + Uptime Probe vorhanden (inkl. BL-31.5 UI-Monitoring-Baseline und BL-31.6.a Artefakt-/Taskdef-Setup) |
| Tracing | X-Ray | ⚠️ zu evaluieren |

### Telegram-Alerting — Architektur & Deployment (BL-08)

**Datenfluss:** `CloudWatch Alarm → SNS Topic → Lambda → Telegram Bot API`

**Komponenten:**

| Ressource | Name / Pfad | Notizen |
|---|---|---|
| Lambda-Funktion | `swisstopo-dev-sns-to-telegram` | Python 3.12, Quelle: `infra/lambda/sns_to_telegram/` |
| IAM-Role | `swisstopo-dev-sns-to-telegram-role` | Minimal-Privilege: Logs + SSM-Read |
| SNS-Subscription | Lambda-Endpoint auf `swisstopo-dev-alerts` | Terraform oder Script |
| SSM-Parameter | `/swisstopo/dev/telegram-bot-token` | SecureString — **manuell anlegen, NICHT per Terraform** |
| Chat-ID | Lambda-Umgebungsvariable `TELEGRAM_CHAT_ID` | kein Secret, numerisch |

**Secret-Verwaltung:** Bot-Token liegt als SSM-Parameter `SecureString`. Er wird weder im Repo noch im Terraform-State als Klartext gespeichert. Terraform referenziert nur den Parameternamen; der Wert wird zur Lambda-Laufzeit via `boto3 ssm.get_parameter(WithDecryption=True)` gelesen.

**Deploy-Option A — Terraform (empfohlen, idempotent):**

```bash
# Schritt 1: SSM-Parameter manuell anlegen (einmalig)
aws ssm put-parameter \
  --region eu-central-1 \
  --name /swisstopo/dev/telegram-bot-token \
  --type SecureString \
  --value "<BOT_TOKEN>" \
  --description "Telegram Bot Token für swisstopo-dev Alerting"

# Schritt 2: terraform.tfvars anpassen
# manage_telegram_alerting = true
# telegram_chat_id         = "8614377280"

# Schritt 3: Apply
cd infra/terraform
terraform plan
terraform apply
```

**Deploy-Option B — Setup-Script (schnell, ohne Terraform):**

```bash
export TELEGRAM_BOT_TOKEN="<BOT_TOKEN>"
export TELEGRAM_CHAT_ID="8614377280"
./scripts/setup_telegram_alerting_dev.sh
```

Das Script legt SSM-Parameter, IAM-Role, Lambda-Funktion und SNS-Subscription in einem Schritt an (idempotent).

**Testalarm kontrolliert auslösen:**

```bash
# Alarm auf ALARM setzen
aws cloudwatch set-alarm-state \
  --region eu-central-1 \
  --alarm-name swisstopo-dev-api-running-taskcount-low \
  --state-value ALARM \
  --state-reason "Kontrollierter Testalarm"

# Nach Empfang im Telegram zurücksetzen
aws cloudwatch set-alarm-state \
  --region eu-central-1 \
  --alarm-name swisstopo-dev-api-running-taskcount-low \
  --state-value OK \
  --state-reason "Reset nach Testalarm"
```

**Baseline-Check inkl. Telegram-Verdrahtung:**

```bash
./scripts/check_monitoring_baseline_dev.sh
```

Prüft jetzt zusätzlich: Lambda-State, SNS-Subscription, TELEGRAM_CHAT_ID in Env, SSM-Parameter-Existenz.

### HTTP Uptime Probe — `GET /health` (BL-12)

**Status (2026-02-25):** ✅ Aktiv und getestet

**Datenfluss:** `EventBridge (rate 5 min) → Lambda swisstopo-dev-health-probe → HTTP GET /health → CloudWatch HealthProbeSuccess → Alarm → SNS → Telegram`

**Besonderheit:** Kein ALB vorhanden → Task-IP ist ephemer. Lambda löst die öffentliche IP des laufenden ECS-Tasks dynamisch auf (ListTasks → DescribeTasks → DescribeNetworkInterfaces).

**Komponenten:**

| Ressource | Name / Pfad | Notizen |
|---|---|---|
| Lambda-Funktion | `swisstopo-dev-health-probe` | Python 3.12, Quelle: `infra/lambda/health_probe/` |
| IAM-Role | `swisstopo-dev-health-probe-role` | Minimal: ECS/EC2 IP-Lookup + CW PutMetricData + Logs |
| EventBridge Rule | `swisstopo-dev-health-probe-schedule` | rate(5 minutes), ENABLED |
| CloudWatch Metrik | `swisstopo/dev-api / HealthProbeSuccess` | Dim: Service + Environment |
| CloudWatch Alarm | `swisstopo-dev-api-health-probe-fail` | Min < 1 in 3/3 Perioden → SNS |

**Setup (idempotent):**

Option A (Script, schnell):

```bash
AWS_ACCOUNT_ID=523234426229 ./scripts/setup_health_probe_dev.sh
```

Option B (Terraform, IaC-Parität seit BL-14):

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars  # falls noch nicht vorhanden

# Aktivieren:
#   manage_health_probe = true

terraform init
terraform import 'aws_iam_role.health_probe[0]' swisstopo-dev-health-probe-role
terraform import 'aws_iam_role_policy.health_probe_inline[0]' 'swisstopo-dev-health-probe-role:health-probe-inline'
terraform import 'aws_iam_role_policy_attachment.health_probe_basic_execution[0]' 'swisstopo-dev-health-probe-role/arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
terraform import 'aws_lambda_function.health_probe[0]' swisstopo-dev-health-probe
terraform import 'aws_lambda_permission.health_probe_eventbridge_invoke[0]' 'swisstopo-dev-health-probe/allow-eventbridge-health-probe'
terraform import 'aws_cloudwatch_event_rule.health_probe_schedule[0]' swisstopo-dev-health-probe-schedule
terraform import 'aws_cloudwatch_event_target.health_probe_lambda[0]' swisstopo-dev-health-probe-schedule/health-probe-lambda
terraform import 'aws_cloudwatch_metric_alarm.health_probe_fail[0]' swisstopo-dev-api-health-probe-fail
terraform plan
```

**Status-Check:**

```bash
./scripts/check_health_probe_dev.sh
# Exit 0 = ok | 10 = Warn | 20 = kritisch
```

### BL-31.5 UI-Monitoring-Baseline (separater UI-Service)

Für den separaten UI-Service (`swisstopo-dev-ui`) werden zwei eigenständige Baseline-Signale geführt:
- `swisstopo-dev-ui-running-taskcount-low` (RunningTaskCount < 1)
- `swisstopo-dev-ui-health-probe-fail` (Reachability via `/healthz`)

**Setup (idempotent):**

```bash
AWS_ACCOUNT_ID=523234426229 ./scripts/setup_bl31_ui_monitoring_baseline.sh
```

Das Setup nutzt intern das generische Health-Probe-Setup mit UI-spezifischen Namen (`swisstopo-dev-ui-health-probe*`) und Namespace `swisstopo/dev-ui`.

**Read-only Check (UI):**

```bash
./scripts/check_bl31_ui_monitoring_baseline.sh
# Exit 0 = ok | 10 = Warn | 20 = kritisch
```

**Erster verifizierter Testlauf (2026-02-25):**
- IP `18.184.115.244` dynamisch aufgelöst
- HTTP 200, `{"ok": true, "service": "geo-ranking-ch", ...}` erhalten
- Metrik `HealthProbeSuccess = 1` in CloudWatch publiziert
- Alarm `INSUFFICIENT_DATA` → nach ~15 Min `OK` (erwartetes Verhalten bei Ersterstellung)

**Kosten:** ~€0.01/Monat (alles im Free Tier / Mikrokosten).

---

## 7. Kosten-Übersicht (Schätzung)

> ⚠️ Alle Angaben sind Schätzungen basierend auf dem swisstopo-Dev-Pattern im gleichen Account.

| Service | Geschätzte Kosten/Monat | Basis |
|---|---|---|
| ECS Fargate | ~ €10–30 | Abhängig von Task-Größe und Laufzeit |
| ECR | ~ €0.10 | Speicherkosten pro GB |
| S3 | ~ €0.05–1 | Abhängig von Datenmenge |
| CloudWatch | ~ €1–5 | Logs + Metriken |

> Tatsächliche Kosten nach Deployment prüfen via AWS Cost Explorer.

---

## 8. Offene Punkte / TODOs

Offene Deployment-Themen werden zentral im [`docs/BACKLOG.md`](BACKLOG.md) gepflegt (aktuell **BL-01** bis **BL-18**), um doppelte Pflege zu vermeiden.

> **AWS-Ressourcen-Inventar:** Eine vollständige, verifizierte Übersicht aller AWS-Ressourcen (Name/ARN, Region, Zweck, Tags, Konfig-Parameter, IaC-Status, Rebuild-Hinweise) findet sich in [`docs/AWS_INVENTORY.md`](AWS_INVENTORY.md).

Status-Updates zu umgesetzten Teilaspekten bitte in der jeweiligen BL-ID in `docs/BACKLOG.md` nachführen.

Aktueller Stand (Deployment-relevant):
- ✅ IaC-Fundament (`infra/terraform/`) für dev-Kernressourcen umgesetzt.
- ✅ Monitoring/Alerting-Baseline inkl. SNS → Telegram produktiv aktiv.
- ✅ HTTP-Uptime-Probe auf `/health` produktiv aktiv (BL-12 abgeschlossen).
- ✅ Health-Probe-IaC-Parität verifiziert (BL-14 abgeschlossen): Terraform `validate` grün; Default-Plan ohne Infrastrukturänderungen; Import-first-Plan mit `manage_health_probe=true` zeigt **0 add / 4 change / 0 destroy** (nur in-place Drift-Korrekturen).
- ⏳ Nächster offener Gesamt-Block: **BL-15** (Legacy-IAM-Readiness, read-only) — aktueller Arbeitsstand inkl. Consumer-Inventar (`scripts/audit_legacy_aws_consumer_refs.sh`), Runtime-Baseline (`scripts/audit_legacy_runtime_consumers.sh`), CloudTrail-Fingerprint-Audit (`scripts/audit_legacy_cloudtrail_consumers.sh`), externer Consumer-Matrix (`docs/LEGACY_CONSUMER_INVENTORY.md`) und Go/No-Go-Template: `docs/LEGACY_IAM_USER_READINESS.md`.
