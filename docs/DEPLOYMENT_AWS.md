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

## 3. IAM-Berechtigungen (Deploy-User) — BL-03 Vorarbeit

Aktueller Workflow (`.github/workflows/deploy.yml`) benötigt für den ECS-Deploy in `dev` nur ECR+ECS+`iam:PassRole` (kein S3-/Lambda-/CloudFormation-Write im Workflow).

Vorbereitete Artefakte (IaC-nah):

- `infra/iam/deploy-policy.json` — konkrete Least-Privilege Policy für aktuellen dev-Stack
- `infra/iam/README.md` — Herleitung, Scope und sichere Umsetzungsreihenfolge

### Deploy-Principal (Ist-Stand, read-only geprüft)

- ✅ `aws sts get-caller-identity` liefert:
  - `arn:aws:iam::523234426229:user/swisstopo-api-deploy`
- ✅ ECS/ECR Read-Aufrufe funktionieren (`DescribeServices`, `DescribeTaskDefinition`, `DescribeRepositories`)
- ⚠️ IAM-Introspection nicht erlaubt (`iam:GetUser`, `iam:ListAttachedUserPolicies`, `iam:ListUserPolicies` => `AccessDenied`)

### Ableitung Minimalrechte aus aktuellem Workflow

| Schritt | Benötigte AWS Actions |
|---|---|
| ECR Login | `ecr:GetAuthorizationToken` |
| Docker Push nach ECR | `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage` |
| ECS Ist-TaskDef lesen | `ecs:DescribeServices`, `ecs:DescribeTaskDefinition` |
| Neue Revision registrieren | `ecs:RegisterTaskDefinition` + `iam:PassRole` (Execution-/Task-Role) |
| ECS Service umstellen + Wait | `ecs:UpdateService`, `ecs:DescribeServices` |

> Umsetzungshinweis (ohne Risiko): Neue Policy zuerst parallel anhängen und via `workflow_dispatch` validieren; produktive Secrets erst nach erfolgreichem Test umstellen.

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
| 2026-02-25 | https://github.com/nimeob/geo-ranking-ch/actions/runs/22417749775 | `workflow_dispatch` | 🔄 In Progress (Validierung) | Nach IAM-Policy-Fix läuft `Register new task definition revision` wieder erfolgreich; aktueller Wartepunkt: `Wait for service stability` |

Kurzfazit BL-02:
- Trigger per `push` auf `main`: ✅ nachgewiesen.
- `services-stable` erfolgreich: ✅ in Run `22416418587`.
- Smoke-Test `/health` erfolgreich: ✅ in Run `22416418587`.
- Regression `ecs:DescribeTaskDefinition` wurde in IAM-Policy adressiert (OIDC-Role, Policy-Version `v2`); Validierungsrun `22417749775` bestätigt den ehemals fehlerhaften Schritt als grün.

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

## 6. Monitoring & Observability (MVP-Stand)

| Komponente | Tool | Status |
|---|---|---|
| Logs | CloudWatch Logs | ⚠️ Log-Group-/Retention-Standard dokumentiert (siehe `docs/OPERATIONS.md`), im AWS-Account noch zu verifizieren |
| Metriken | CloudWatch Metrics | ⚠️ Für minimale Alarme definiert, technische Anlage via CLI noch offen |
| Alarme | CloudWatch Alarms | ⚠️ MVP-Alarmdefinitionen dokumentiert (Service unhealthy + Deployment-Stuck-Indicator), Umsetzung im Account noch offen |
| Uptime/HTTP Health | Externe Probe oder CloudWatch Synthetics | ⚠️ Guidance dokumentiert (`/health`), produktive Probe noch offen |
| Ops-Helper | `scripts/check_ecs_service.sh`, `scripts/tail_logs.sh` | ✅ Read-only Scripts für Incident-Triage vorhanden |
| Tracing | X-Ray | ⚠️ zu evaluieren |

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

Offene Deployment-Themen werden zentral im [`docs/BACKLOG.md`](BACKLOG.md) gepflegt (insb. **BL-01** bis **BL-10**), um doppelte Pflege zu vermeiden.

Status-Updates zu umgesetzten Teilaspekten bitte in der jeweiligen BL-ID in `docs/BACKLOG.md` nachführen.

- ✅ IaC-Fundament (Terraform, dev) umgesetzt: `infra/terraform/` mit Import-first-Runbook.
- ✅ Monitoring-MVP in `docs/OPERATIONS.md` dokumentiert (Log-Group/Retention-Standard, minimale Alarmdefinitionen, Incident-Runbook mit AWS CLI).
- ✅ Read-only Ops-Helper-Skripte ergänzt: `scripts/check_ecs_service.sh`, `scripts/tail_logs.sh`.
- ⏳ Noch offen: Alarme tatsächlich im AWS-Account anlegen + AlarmActions (SNS/ChatOps) verdrahten.
- ⏳ Noch offen: HTTP-Uptime-Probe auf `/health` produktiv aktivieren.
