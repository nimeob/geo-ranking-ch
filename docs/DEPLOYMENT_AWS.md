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
| IAM Deploy-User | `arn:aws:iam::523234426229:user/swisstopo-api-deploy` | ✅ Verifiziert |

### AWS-Naming-Konvention

> AWS-Ressourcen dieses Projekts heißen intern **`swisstopo`** — obwohl das Repository `geo-ranking-ch` heißt. Das ist bewusst so und muss nicht geändert werden. Die AWS-Namen sind intern und nicht öffentlich exponiert.

### Umgebungen

> **Aktueller Stand:** Es existiert ausschließlich eine **`dev`-Umgebung**. `staging` und `prod` sind noch nicht aufgebaut.

### Aktuelle Ressourcen (dev)

| Ressource | Name / ARN | Status |
|---|---|---|
| S3 Bucket | `swisstopo-dev-523234426229` | ✅ Verifiziert |
| ECS Cluster | `swisstopo-dev` | ✅ Verifiziert |
| ECS Service | `swisstopo-dev-api` | ✅ Verifiziert |
| ECR Repository | `523234426229.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-api` | ✅ Verifiziert |
| Lambda Functions | — | ❌ Nicht gefunden |
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

## 3. IAM-Berechtigungen (Deploy-User)

> ⚠️ Annahme: Der User `swisstopo-api-deploy` wird auch für geo-ranking-ch genutzt.  
> Erforderliche Mindest-Berechtigungen für ein typisches Deployment (zu verifizieren):

```
ecr:GetAuthorizationToken, ecr:BatchCheckLayerAvailability, ecr:PutImage, ...
ecs:RegisterTaskDefinition, ecs:UpdateService, ecs:DescribeServices, ...
s3:PutObject, s3:GetObject, s3:ListBucket, s3:DeleteObject
cloudformation:* (für IaC-Deployments)
lambda:UpdateFunctionCode, lambda:PublishVersion (falls Serverless)
```

> Für Principle-of-Least-Privilege sollte ein separater `geo-ranking-ch-deploy` User erstellt werden.

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
| `AWS_ACCESS_KEY_ID` | Deploy-User Access Key |
| `AWS_SECRET_ACCESS_KEY` | Deploy-User Secret Key |
| `AWS_ACCOUNT_ID` | `523234426229` |
| `AWS_REGION` | `eu-central-1` |

**Benötigte GitHub Variables (zu setzen unter Settings → Variables):**

| Variable | Beschreibung |
|---|---|
| `ECR_REPOSITORY` | Ziel-Repository in ECR (z. B. `swisstopo-dev-api`) |
| `ECS_CLUSTER` | ECS Cluster (z. B. `swisstopo-dev`) |
| `ECS_SERVICE` | ECS Service (z. B. `swisstopo-dev-api`) |
| `ECS_CONTAINER_NAME` | Container-Name in der Task-Definition |
| `SERVICE_HEALTH_URL` | Vollständige Health-URL für Smoke-Test (z. B. `https://<alb-dns>/health`) |

> `SERVICE_HEALTH_URL` ist optional: fehlt die Variable, wird der Smoke-Test im Workflow sauber übersprungen.

> ⚠️ Niemals Secrets direkt in Code oder Dokumente schreiben.

### Terraform IaC-Startpaket (dev)

Ein minimales, bewusst nicht-destruktives Terraform-Startpaket liegt unter:

- `infra/terraform/`

Inhalt:
- Skelett für ECS Cluster, ECR Repository, CloudWatch Log Group
- sichere Flags (`manage_* = false` als Default)
- Import-first-Dokumentation in `infra/terraform/README.md`

Empfohlene Reihenfolge: **`init` → `plan` → `import` → `apply`**.

> Für bestehende dev-Ressourcen: **kein blindes apply**; zuerst Import pro Ressource.

---

## 5. Rollback-Prozedur

### ECS Service Rollback

```bash
# Vorherige Task-Definition-Revision ermitteln
aws ecs describe-services \
  --cluster swisstopo-dev \
  --services swisstopo-dev-api \
  --query 'services[0].deployments'

# Auf vorherige Revision zurückwechseln
PREV_REVISION=<nummer>
aws ecs update-service \
  --cluster swisstopo-dev \
  --service swisstopo-dev-api \
  --task-definition swisstopo-dev-api:${PREV_REVISION} \
  --region eu-central-1
```

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

## 6. Monitoring & Observability (Zielzustand)

| Komponente | Tool | Status |
|---|---|---|
| Logs | CloudWatch Logs | ⚠️ zu konfigurieren |
| Metriken | CloudWatch Metrics | ⚠️ zu konfigurieren |
| Alarme | CloudWatch Alarms | ❌ noch nicht vorhanden |
| Tracing | X-Ray | ⚠️ zu evaluieren |
| Uptime | CloudWatch Synthetics / externe Probe | ⚠️ zu evaluieren |

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

Offene Deployment-Themen werden zentral im [`docs/BACKLOG.md`](BACKLOG.md) gepflegt (insb. **BL-01** bis **BL-09**), um doppelte Pflege zu vermeiden.

Status-Updates zu umgesetzten Teilaspekten bitte in der jeweiligen BL-ID in `docs/BACKLOG.md` nachführen.

- ✅ IaC-Fundament (Terraform, dev) umgesetzt: `infra/terraform/` mit Import-first-Runbook.
