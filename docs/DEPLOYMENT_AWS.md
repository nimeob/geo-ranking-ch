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

### geo-ranking-ch Ressourcen

> Bei Ausführung von `aws lambda list-functions`, `aws ecs list-clusters`, `aws s3 ls`, `aws ecr describe-repositories` (alle in `eu-central-1`) wurden **keine dedizierten Ressourcen für geo-ranking-ch gefunden**.

| Ressource | Name / ARN | Status |
|---|---|---|
| S3 Bucket | — | ❌ Noch nicht angelegt |
| ECS Cluster | — | ❌ Noch nicht angelegt |
| ECS Service | — | ❌ Noch nicht angelegt |
| ECR Repository | — | ❌ Noch nicht angelegt |
| Lambda Functions | — | ❌ Nicht gefunden |
| CloudFormation Stacks | — | ❌ Nicht gefunden |
| API Gateway | — | ⚠️ Zu prüfen |
| RDS / DynamoDB | — | ⚠️ Zu prüfen |

**Mögliche Ursachen:**
- Projekt befindet sich noch in der Pre-Deployment-Phase
- Ressourcen existieren unter einem anderen AWS-Profil oder Account
- Deployment läuft über ein IaC-Tool, das noch nicht ausgeführt wurde

### Referenz: Swisstopo-Dev-Infrastruktur (gleicher Account)

Diese Ressourcen gehören zum Schwesterprojekt und dienen als Referenz-Pattern:

| Ressource | Name |
|---|---|
| S3 Bucket | `swisstopo-dev-523234426229` |
| ECS Cluster | `swisstopo-dev` |
| ECS Service | `swisstopo-dev-api` |
| ECR Repository | `523234426229.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-api` |

---

## 2. IAM-Berechtigungen (Deploy-User)

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

## 3. Deploy-Runbook

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

### Reguläres Deployment (nach erstem Setup)

```bash
# 1. Docker Image bauen
IMAGE_TAG=$(git rev-parse --short HEAD)
docker build -t geo-ranking-ch-api:${IMAGE_TAG} .

# 2. ECR Login
aws ecr get-login-password --region eu-central-1 \
  | docker login --username AWS \
    --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com

# 3. Image pushen
docker tag geo-ranking-ch-api:${IMAGE_TAG} \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com/geo-ranking-ch-api:${IMAGE_TAG}
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-central-1.amazonaws.com/geo-ranking-ch-api:${IMAGE_TAG}

# 4. ECS Service aktualisieren (⚠️ Cluster/Service-Namen zu verifizieren)
aws ecs update-service \
  --cluster geo-ranking-ch \
  --service geo-ranking-ch-api \
  --force-new-deployment \
  --region eu-central-1
```

### Deployment via GitHub Actions (Zielzustand)

CI/CD ist noch nicht konfiguriert. Placeholder-Workflow vorhanden in `.github/workflows/deploy.yml`.

**Benötigte GitHub Secrets (zu setzen unter Settings → Secrets):**

| Secret | Beschreibung |
|---|---|
| `AWS_ACCESS_KEY_ID` | Deploy-User Access Key |
| `AWS_SECRET_ACCESS_KEY` | Deploy-User Secret Key |
| `AWS_ACCOUNT_ID` | `523234426229` |
| `AWS_REGION` | `eu-central-1` |

> ⚠️ Niemals Secrets direkt in Code oder Dokumente schreiben.

---

## 4. Rollback-Prozedur

### ECS Service Rollback (⚠️ zu verifizieren sobald ECS läuft)

```bash
# Vorherige Task-Definition-Revision ermitteln
aws ecs describe-services \
  --cluster geo-ranking-ch \
  --services geo-ranking-ch-api \
  --query 'services[0].deployments'

# Auf vorherige Revision zurückwechseln
PREV_REVISION=<nummer>
aws ecs update-service \
  --cluster geo-ranking-ch \
  --service geo-ranking-ch-api \
  --task-definition geo-ranking-ch-api:${PREV_REVISION} \
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

## 5. Monitoring & Observability (Zielzustand)

| Komponente | Tool | Status |
|---|---|---|
| Logs | CloudWatch Logs | ⚠️ zu konfigurieren |
| Metriken | CloudWatch Metrics | ⚠️ zu konfigurieren |
| Alarme | CloudWatch Alarms | ❌ noch nicht vorhanden |
| Tracing | X-Ray | ⚠️ zu evaluieren |
| Uptime | CloudWatch Synthetics / externe Probe | ⚠️ zu evaluieren |

---

## 6. Kosten-Übersicht (Schätzung)

> ⚠️ Alle Angaben sind Schätzungen basierend auf dem swisstopo-Dev-Pattern im gleichen Account.

| Service | Geschätzte Kosten/Monat | Basis |
|---|---|---|
| ECS Fargate | ~ €10–30 | Abhängig von Task-Größe und Laufzeit |
| ECR | ~ €0.10 | Speicherkosten pro GB |
| S3 | ~ €0.05–1 | Abhängig von Datenmenge |
| CloudWatch | ~ €1–5 | Logs + Metriken |

> Tatsächliche Kosten nach Deployment prüfen via AWS Cost Explorer.

---

## 7. Offene Punkte / TODOs

- [ ] Stack-Typ entscheiden: ECS Fargate vs. Lambda vs. S3 Static
- [ ] IaC-Code erstellen (CDK / Terraform / CloudFormation)
- [ ] GitHub Actions Workflow fertigstellen (Placeholder ersetzen)
- [ ] Separaten IAM Deploy-User für geo-ranking-ch anlegen
- [ ] Environment-Trennung klären (dev / staging / prod)
- [ ] Monitoring + Alerting konfigurieren
- [ ] Domain / Route53 prüfen (falls öffentliche API geplant)
- [ ] Netzwerk: VPC-Konfiguration prüfen (Public vs. Private Subnets)
