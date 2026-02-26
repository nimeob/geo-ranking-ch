# AWS Inventory & Konfigurationsdokumentation

> **Projekt:** geo-ranking-ch (internes AWS-Naming: `swisstopo`)  
> **Account:** `523234426229`  
> **Region:** `eu-central-1` (Frankfurt)  
> **Umgebung:** `dev` (einzige aktive Umgebung; `staging`/`prod` noch nicht angelegt)  
> **Stand:** 2026-02-26 — vollständig verifiziert via read-only AWS-Abfragen  

---

## Konventionen

| Symbol | Bedeutung |
|---|---|
| ✅ | Direkt via AWS CLI verifiziert |
| ⚠️ | Annahme / noch zu validieren |
| 🔧 **Terraform** | IaC-managed (Terraform, `infra/terraform/`) — Änderungen via `terraform apply` |
| 🖐️ **Manuell** | Manuell angelegt / nicht im IaC-Scope |
| 🔑 **SSM** | Secret in AWS SSM Parameter Store — niemals im Repo |

---

## Read-only Erfassungskommandos

Diese Befehle sind rein lesend und können zur Verifikation jederzeit ausgeführt werden.  
**Keine Secrets oder sensitiven Werte werden ausgegeben.**

```bash
# Identität prüfen
aws sts get-caller-identity

# ECS Cluster
aws ecs describe-clusters --clusters swisstopo-dev --region eu-central-1

# ECS Service
aws ecs describe-services --cluster swisstopo-dev --services swisstopo-dev-api --region eu-central-1

# Aktive Task Definition
aws ecs describe-task-definition --task-definition swisstopo-dev-api --region eu-central-1

# ECR Repository
aws ecr describe-repositories --repository-names swisstopo-dev-api --region eu-central-1

# CloudWatch Log Groups
aws logs describe-log-groups --log-group-name-prefix /swisstopo --region eu-central-1

# CloudWatch Metric Filters
aws logs describe-metric-filters --log-group-name /swisstopo/dev/ecs/api --region eu-central-1

# CloudWatch Alarme
aws cloudwatch describe-alarms --alarm-name-prefix swisstopo-dev-api --region eu-central-1

# SNS Topics
aws sns list-topics --region eu-central-1

# SNS Subscriptions
aws sns list-subscriptions --region eu-central-1

# Lambda Funktion
aws lambda get-function --function-name swisstopo-dev-sns-to-telegram --region eu-central-1

# S3 Bucket Tags
aws s3api get-bucket-tagging --bucket swisstopo-dev-523234426229

# Netzwerk: VPC
aws ec2 describe-vpcs --region eu-central-1

# Netzwerk: Subnets (ECS)
aws ec2 describe-subnets \
  --subnet-ids subnet-03651caf25115a6c1 subnet-00901e503e078e7c9 subnet-07cfbfe0d181ed329 \
  --region eu-central-1

# Security Group
aws ec2 describe-security-groups --group-ids sg-092e0616ffb0663c3 --region eu-central-1

# SSM Parameter (Existenz prüfen, kein Wert)
aws ssm describe-parameters \
  --parameter-filters Key=Name,Values=/swisstopo/dev/telegram-bot-token \
  --region eu-central-1
```

---

## Tagging-Standard

Alle Ressourcen dieses Projekts tragen folgende Pflicht-Tags:

| Key | Wert |
|---|---|
| `Project` | `swisstopo` |
| `Environment` | `dev` |
| `Owner` | `nico` |
| `ManagedBy` | `openclaw` |

Details und Audit: [`docs/TAGGING_AUDIT.md`](TAGGING_AUDIT.md)

---

## 1. IAM

### 1.1 Deploy-User (Legacy)

> Der IAM-User `swisstopo-api-deploy` ist weiterhin vorhanden und aktiv nutzbar. Der produktive CI/CD-Standardpfad läuft zwar über OIDC (1.2), aber der Legacy-User wird aktuell weiterhin in lokalen/Runner-basierten AWS-Läufen verwendet.

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-api-deploy` | ✅ |
| ARN | `arn:aws:iam::523234426229:user/swisstopo-api-deploy` | ✅ |
| Zweck | Legacy-Principal (historisch Deploy; heute noch in Nutzung) | ✅ |
| IaC | 🖐️ Manuell angelegt | — |
| Decommission-Status | Readiness dokumentiert, Abschaltung noch nicht freigegeben | 🟡 |

**Aktueller Rechtestand (verifiziert 2026-02-26):**
- Managed Policies: `IAMFullAccess`, `PowerUserAccess`
- Inline Policy: `swisstopo-dev-ecs-passrole` (PassRole nur für ECS Task-/Execution-Role)

**Decommission-Readiness (BL-15):**
- Details, Evidenz und Go/No-Go-Template: [`docs/LEGACY_IAM_USER_READINESS.md`](LEGACY_IAM_USER_READINESS.md)
- Reproduzierbarer Repo-Consumer-Check: `./scripts/audit_legacy_aws_consumer_refs.sh`

---

### 1.2 GitHub OIDC Deploy-Rolle ✅ (aktiver CI/CD-Pfad)

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-github-deploy-role` | ✅ |
| ARN | `arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role` | ✅ |
| Zweck | GitHub Actions OIDC — CI/CD Deploy (ECR Push + ECS Rollout) | ✅ |
| Attached Policy | `swisstopo-dev-github-deploy-policy` (v2 aktiv) | ✅ |
| Policy-Artefakt | [`infra/iam/deploy-policy.json`](../infra/iam/deploy-policy.json) | ✅ |
| IaC | 🖐️ Manuell angelegt (OIDC Trust + Policy) | — |
| Herleitung | [`infra/iam/README.md`](../infra/iam/README.md) | ✅ |

**Policy-Scope (aus `deploy-policy.json`):**

| Action | Ressource |
|---|---|
| `sts:GetCallerIdentity` | `*` |
| `ecr:GetAuthorizationToken` | `*` |
| `ecr:BatchCheck/InitiateUpload/PutImage…` | `arn:…:repository/swisstopo-dev-api` |
| `ecs:DescribeServices` | Cluster + Service ARN (dev) |
| `ecs:DescribeTaskDefinition` | `*` (AWS-seitig nicht einengbar) |
| `ecs:RegisterTaskDefinition` | `*` |
| `ecs:UpdateService` | Cluster + Service ARN (dev) |
| `iam:PassRole` | Nur `swisstopo-dev-ecs-execution-role` + `swisstopo-dev-ecs-task-role` (Condition: `ecs-tasks.amazonaws.com`) |

**Rebuild-Hinweis:**
1. OIDC-Provider für GitHub in AWS IAM anlegen (Trust auf `token.actions.githubusercontent.com`).
2. Rolle mit Trust-Policy für `repo:nimeob/geo-ranking-ch:ref:refs/heads/main` anlegen.
3. Policy aus `infra/iam/deploy-policy.json` als managed Policy anlegen und anhängen.
4. Rollen-ARN im Workflow (`.github/workflows/deploy.yml`, `role-to-assume`) aktualisieren.

---

### 1.3 ECS Execution-Role

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-ecs-execution-role` | ✅ (via TaskDef verifiziert) |
| ARN | `arn:aws:iam::523234426229:role/swisstopo-dev-ecs-execution-role` | ✅ |
| Zweck | Erlaubt ECS/Fargate-Control-Plane: ECR Pull, CloudWatch Logs schreiben | ✅ |
| IaC | 🖐️ Manuell angelegt | — |

**Erwartete Rechte (⚠️ Annahme, nicht direkt verifiziert — IAM-Introspection verweigert):**
- `AmazonECSTaskExecutionRolePolicy` (AWS-managed) → ECR pull + CloudWatch Logs

**Rebuild-Hinweis:** Neue Rolle anlegen, `AmazonECSTaskExecutionRolePolicy` anhängen, Trust auf `ecs-tasks.amazonaws.com`.

---

### 1.4 ECS Task-Role

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-ecs-task-role` | ✅ (via TaskDef verifiziert) |
| ARN | `arn:aws:iam::523234426229:role/swisstopo-dev-ecs-task-role` | ✅ |
| Zweck | Anwendungslaufzeit-Rechte für den Container (aktuell: stateless, vermutlich keine spezifischen Policies) | ⚠️ |
| IaC | 🖐️ Manuell angelegt | — |

**Rebuild-Hinweis:** Neue Rolle anlegen, Trust auf `ecs-tasks.amazonaws.com`. Falls stateless: leere Rolle genügt als Platzhalter.

---

### 1.5 Lambda IAM-Role (Telegram-Alerting)

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-sns-to-telegram-role` | ✅ |
| ARN | `arn:aws:iam::523234426229:role/swisstopo-dev-sns-to-telegram-role` | ✅ (via Lambda verifiziert) |
| Zweck | Lambda-Ausführungsrolle für Telegram-Alerting (CloudWatch Logs + SSM Read + KMS Decrypt) | ✅ |
| IaC | 🔧 Terraform (`infra/terraform/lambda_telegram.tf`) | ✅ |

**Inline-Policy-Scope (aus Terraform):**

| Action | Ressource |
|---|---|
| `logs:CreateLogGroup/Stream/PutLogEvents` | `/aws/lambda/swisstopo-dev-sns-to-telegram` |
| `ssm:GetParameter` | `arn:…:parameter/swisstopo/dev/telegram-bot-token` |
| `kms:Decrypt` | `arn:…:key/aws/ssm` |

---

## 2. ECR (Elastic Container Registry)

### 2.1 API Repository

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-api` | ✅ |
| ARN | `arn:aws:ecr:eu-central-1:523234426229:repository/swisstopo-dev-api` | ✅ |
| Registry URI | `523234426229.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-api` | ✅ |
| Erstellt | 2026-02-25 | ✅ |
| Image Tag Mutability | `MUTABLE` | ✅ |
| Scan on Push | `true` | ✅ |
| Encryption | `AES256` (AWS-managed) | ✅ |
| Zweck | Container-Images für ECS Fargate Service `swisstopo-dev-api` | ✅ |
| Tags | Project=swisstopo, Environment=dev, Owner=nico, ManagedBy=openclaw | ✅ |
| IaC | 🔧 Terraform (`infra/terraform/main.tf`, Resource `aws_ecr_repository.api`) | ✅ |

**Rebuild-Hinweis:**
```bash
# Import bestehende Ressource in Terraform-State (vor erstem apply)
terraform import aws_ecr_repository.api swisstopo-dev-api

# Oder neu anlegen (nur wenn nicht vorhanden)
aws ecr create-repository \
  --repository-name swisstopo-dev-api \
  --region eu-central-1 \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256
```

---

## 3. ECS (Elastic Container Service)

### 3.1 ECS Cluster

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev` | ✅ |
| ARN | `arn:aws:ecs:eu-central-1:523234426229:cluster/swisstopo-dev` | ✅ |
| Status | `ACTIVE` | ✅ |
| Running Tasks | 1 | ✅ |
| Active Services | 1 | ✅ |
| Container Insights | `disabled` | ✅ |
| Capacity Providers | keine (Fargate-Default) | ✅ |
| Zweck | Fargate-Cluster für swisstopo-dev API-Service | ✅ |
| Tags | alle 4 Standard-Tags | ✅ |
| IaC | 🔧 Terraform (`infra/terraform/main.tf`, Resource `aws_ecs_cluster.dev`) | ✅ |

---

### 3.2 ECS Service

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-api` | ✅ |
| ARN | `arn:aws:ecs:eu-central-1:523234426229:service/swisstopo-dev/swisstopo-dev-api` | ✅ |
| Cluster | `swisstopo-dev` | ✅ |
| Launch Type | `FARGATE` | ✅ |
| Desired Count | 1 | ✅ |
| Running Count | 1 | ✅ |
| Network Mode | `awsvpc` | ✅ |
| Assign Public IP | `ENABLED` (⚠️ nicht Zielbild — siehe BL-05) | ✅ |
| Subnets | `subnet-03651caf25115a6c1`, `subnet-00901e503e078e7c9`, `subnet-07cfbfe0d181ed329` | ✅ |
| Security Group | `sg-092e0616ffb0663c3` | ✅ |
| Load Balancer | keiner (⚠️ kein ALB — MVP-Stand, nicht Zielbild) | ✅ |
| Tags | alle 4 Standard-Tags | ✅ |
| IaC | 🖐️ Manuell angelegt (kein Terraform für ECS Service) | ⚠️ |

---

### 3.3 ECS Task Definition

| Parameter | Wert | Status |
|---|---|---|
| Family | `swisstopo-dev-api` | ✅ |
| Aktive Revision | `:26` (Stand 2026-02-26) | ✅ |
| ARN | `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:26` | ✅ |
| Requires Compatibility | `FARGATE` | ✅ |
| Network Mode | `awsvpc` | ✅ |
| CPU | `256` (0.25 vCPU) | ✅ |
| Memory | `512` MB | ✅ |
| Execution Role | `arn:aws:iam::523234426229:role/swisstopo-dev-ecs-execution-role` | ✅ |
| Task Role | `arn:aws:iam::523234426229:role/swisstopo-dev-ecs-task-role` | ✅ |
| IaC | 🖐️ Wird bei jedem CI/CD-Deploy automatisch als neue Revision registriert (kein Terraform) | — |

**Container `api`:**

| Parameter | Wert |
|---|---|
| Name | `api` |
| Image | `523234426229.dkr.ecr.eu-central-1.amazonaws.com/swisstopo-dev-api:<git-sha7>` |
| Port | `8080/tcp` |
| Log Driver | `awslogs` |
| Log Group | `/swisstopo/dev/ecs/api` |
| Log Stream Prefix | `api` |
| Log Region | `eu-central-1` |

**Rebuild-Hinweis Task Definition:**
```bash
# Aktuell aktive TaskDef auslesen
aws ecs describe-task-definition \
  --task-definition swisstopo-dev-api \
  --query 'taskDefinition' \
  --region eu-central-1 > taskdef-backup.json

# Beim Rebuild: als Ausgangsbasis verwenden, nicht-registrierbare Felder entfernen
# (taskDefinitionArn, revision, status, requiresAttributes, compatibilities,
#  registeredAt, registeredBy) — dieser Schritt ist im CI/CD-Workflow automatisiert
```

---

## 4. CloudWatch

### 4.1 Log Group — ECS API

| Parameter | Wert | Status |
|---|---|---|
| Name | `/swisstopo/dev/ecs/api` | ✅ |
| ARN | `arn:aws:logs:eu-central-1:523234426229:log-group:/swisstopo/dev/ecs/api:*` | ✅ |
| Retention | 30 Tage | ✅ |
| Zweck | ECS Fargate Container-Logs (awslogs driver) | ✅ |
| Tags | alle 4 Standard-Tags | ✅ |
| IaC | 🔧 Terraform (`infra/terraform/main.tf`, Resource `aws_cloudwatch_log_group.api`) | ✅ |

---

### 4.2 Log Group — App

| Parameter | Wert | Status |
|---|---|---|
| Name | `/swisstopo/dev/app` | ✅ |
| ARN | `arn:aws:logs:eu-central-1:523234426229:log-group:/swisstopo/dev/app:*` | ✅ |
| Retention | 30 Tage | ✅ |
| Zweck | Allgemeine Applikations-Logs (Verwendung aktuell offen) | ⚠️ |
| Tags | alle 4 Standard-Tags | ✅ |
| IaC | 🖐️ Manuell angelegt | ⚠️ |

---

### 4.3 Metric Filter — HTTP-Request-Count

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-api-http-total` | ✅ |
| Log Group | `/swisstopo/dev/ecs/api` | ✅ |
| Filter Pattern | `[ip, ident, user, ts, request, status_code, bytes]` | ✅ |
| Metric Name | `HttpRequestCount` | ✅ |
| Metric Namespace | `swisstopo/dev-api` | ✅ |
| Metric Value | `1` (Count) | ✅ |
| IaC | 🖐️ Via `scripts/setup_monitoring_baseline_dev.sh` angelegt | — |

---

### 4.4 Metric Filter — HTTP-5xx-Count

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-api-http-5xx` | ✅ |
| Log Group | `/swisstopo/dev/ecs/api` | ✅ |
| Filter Pattern | `[ip, ident, user, ts, request, status_code = 5*, bytes]` | ✅ |
| Metric Name | `Http5xxCount` | ✅ |
| Metric Namespace | `swisstopo/dev-api` | ✅ |
| Metric Value | `1` (Count) | ✅ |
| IaC | 🖐️ Via `scripts/setup_monitoring_baseline_dev.sh` angelegt | — |

---

### 4.5 CloudWatch Alarm — RunningTaskCount (Service-Ausfall)

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-api-running-taskcount-low` | ✅ |
| ARN | `arn:aws:cloudwatch:eu-central-1:523234426229:alarm:swisstopo-dev-api-running-taskcount-low` | ✅ |
| Metric | `RunningTaskCount` / `AWS/ECS` | ✅ |
| Threshold | `< 1` (LessThanThreshold: 1.0) | ✅ |
| Evaluation Periods | 3 × 60 Sekunden | ✅ |
| Aktueller State | `ALARM` (Stand 2026-02-26) | ✅ |
| Alarm Action | `arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts` | ✅ |
| IaC | 🖐️ Via `scripts/setup_monitoring_baseline_dev.sh` angelegt | — |

> ⚠️ **Hinweis:** State `ALARM` könnte kurzfristig durch Deployment-Rollover entstehen; manuell verifizieren ob Service aktuell stabil läuft (`runningCount: 1` laut ECS describe).

---

### 4.6 CloudWatch Alarm — HTTP-5xx-Rate (Fehlerquote)

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-api-http-5xx-rate-high` | ✅ |
| ARN | `arn:aws:cloudwatch:eu-central-1:523234426229:alarm:swisstopo-dev-api-http-5xx-rate-high` | ✅ |
| Metric | `Http5xxCount` / `swisstopo/dev-api` (custom) | ✅ |
| Threshold | `> 5` (GreaterThanThreshold: 5.0) | ✅ |
| Evaluation Periods | 2 | ✅ |
| Aktueller State | `OK` | ✅ |
| Alarm Action | `arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts` | ✅ |
| IaC | 🖐️ Via `scripts/setup_monitoring_baseline_dev.sh` angelegt | — |

---

## 5. S3

### 5.1 Dev-Bucket

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-523234426229` | ✅ |
| ARN | `arn:aws:s3:::swisstopo-dev-523234426229` | ✅ |
| Region | `eu-central-1` | ✅ |
| Zweck | Allgemeiner Dev-Bucket (Artifact-Storage, Deploymentartefakte; konkrete Nutzung aktuell offen) | ⚠️ |
| Tags | Project=swisstopo, Environment=dev, Owner=nico, ManagedBy=openclaw | ✅ |
| IaC | 🔧 Terraform (`infra/terraform/main.tf`, Resource `aws_s3_bucket.dev`) | ✅ |

**Rebuild-Hinweis:**
```bash
# Import bestehende Ressource in Terraform-State (vor erstem apply)
terraform import aws_s3_bucket.dev swisstopo-dev-523234426229

# Bucket-Namen ist account-unique gewählt (Name enthält Account-ID) — Pattern beibehalten
```

---

## 6. Lambda

### 6.1 SNS-to-Telegram Alerting

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-sns-to-telegram` | ✅ |
| ARN | `arn:aws:lambda:eu-central-1:523234426229:function:swisstopo-dev-sns-to-telegram` | ✅ |
| Runtime | `python3.12` | ✅ |
| Handler | `lambda_function.lambda_handler` | ✅ |
| Execution Role | `arn:aws:iam::523234426229:role/swisstopo-dev-sns-to-telegram-role` | ✅ |
| Timeout | 30 Sekunden | ✅ |
| Memory | 128 MB | ✅ |
| State | `Active` | ✅ |
| Last Modified | 2026-02-25T23:07:32Z | ✅ |
| Trigger | SNS Topic `swisstopo-dev-alerts` | ✅ |
| Zweck | Leitet CloudWatch-Alarme via SNS an Telegram-Bot-Chat weiter | ✅ |
| Tags | Project=swisstopo, Environment=dev, Owner=nico, ManagedBy=openclaw | ✅ |
| IaC | 🔧 Terraform (`infra/terraform/lambda_telegram.tf`, Flag `manage_telegram_alerting=true`) | ✅ |

**Umgebungsvariablen (Schlüssel — keine Werte):**

| Variable | Beschreibung |
|---|---|
| `TELEGRAM_CHAT_ID` | Numerische Telegram Chat-ID (kein Secret) |
| `TELEGRAM_BOT_TOKEN_SSM` | Pfad zum SSM-Parameter mit dem Bot-Token |

**Quellcode:** `infra/lambda/sns_to_telegram/lambda_function.py`

**Rebuild-Hinweis:**
```bash
# Schritt 1: SSM-Parameter anlegen (einmalig, manuell — NICHT in Terraform-State)
aws ssm put-parameter \
  --region eu-central-1 \
  --name /swisstopo/dev/telegram-bot-token \
  --type SecureString \
  --value "<BOT_TOKEN>" \
  --description "Telegram Bot Token für swisstopo-dev Alerting"

# Schritt 2: terraform.tfvars anpassen
# manage_telegram_alerting = true
# telegram_chat_id         = "<CHAT_ID>"

# Schritt 3: Terraform apply
cd infra/terraform && terraform plan && terraform apply

# Alternativ: Setup-Script (ohne Terraform)
# TELEGRAM_BOT_TOKEN="<TOKEN>" TELEGRAM_CHAT_ID="<ID>" ./scripts/setup_telegram_alerting_dev.sh
```

---

## 7. SNS

### 7.1 Alerts Topic

| Parameter | Wert | Status |
|---|---|---|
| Name | `swisstopo-dev-alerts` | ✅ |
| ARN | `arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts` | ✅ |
| Zweck | Empfängt CloudWatch-Alarm-Notifications; leitet an Lambda weiter | ✅ |
| IaC | 🖐️ Via `scripts/setup_monitoring_baseline_dev.sh` angelegt | — |

**Subscriptions:**

| Protokoll | Endpoint | Subscription ARN | Status |
|---|---|---|---|
| `lambda` | `arn:aws:lambda:eu-central-1:523234426229:function:swisstopo-dev-sns-to-telegram` | `arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts:ee06e621-bb30-493d-89da-eef31ced8b96` | ✅ Confirmed |

---

## 8. SSM Parameter Store

### 8.1 Telegram Bot-Token 🔑

| Parameter | Wert | Status |
|---|---|---|
| Name | `/swisstopo/dev/telegram-bot-token` | ✅ |
| Typ | `SecureString` (KMS-verschlüsselt) | ✅ |
| Zweck | Bot-Token für Telegram-Alerting-Lambda; wird zur Laufzeit gelesen | ✅ |
| Letztes Update | 2026-02-26T00:06:47Z | ✅ |
| IaC | 🖐️ Manuell angelegt — **absichtlich nicht in Terraform-State** | — |

> 🔑 **Der Wert dieses Parameters wird niemals im Repository, in Logs oder in Dokumenten gespeichert.**  
> Beim Rebuild: manuell mit `aws ssm put-parameter` anlegen (siehe oben, Abschnitt 6.1).

---

## 9. Netzwerk

### 9.1 VPC

| Parameter | Wert | Status |
|---|---|---|
| VPC-ID | `vpc-05377592c517f09f4` | ✅ |
| CIDR | `172.31.0.0/16` | ✅ |
| Typ | **Default-VPC** (⚠️ nicht Zielbild — dedizierte VPC geplant, siehe BL-05) | ✅ |
| Tags | keine | ✅ |
| IaC | 🖐️ AWS-Default, nicht verwaltet | — |

> ⚠️ **Zielbild laut BL-05:** Dedizierte App-VPC mit 2 Public + 2 Private Subnets, ECS in Private Subnets, Ingress nur via ALB. Noch nicht umgesetzt.

---

### 9.2 Subnets (ECS-Service)

Alle drei Subnets gehören zur Default-VPC und liegen in verschiedenen AZs:

| Subnet-ID | CIDR | AZ | Public IP on Launch |
|---|---|---|---|
| `subnet-03651caf25115a6c1` | `172.31.0.0/20` | `eu-central-1c` | `true` ⚠️ |
| `subnet-00901e503e078e7c9` | `172.31.32.0/20` | `eu-central-1b` | `true` ⚠️ |
| `subnet-07cfbfe0d181ed329` | `172.31.16.0/20` | `eu-central-1a` | `true` ⚠️ |

> ⚠️ Public IPs sind aktiviert — entspricht nicht dem Zielbild (Private Subnets, kein Public IP). Aktuell funktional für MVP-Betrieb.

---

### 9.3 Security Group — ECS API

| Parameter | Wert | Status |
|---|---|---|
| Group-ID | `sg-092e0616ffb0663c3` | ✅ |
| Name | `swisstopo-dev-api-sg` | ✅ |
| VPC | `vpc-05377592c517f09f4` | ✅ |
| Beschreibung | `swisstopo dev api sg` | ✅ |
| IaC | 🖐️ Manuell angelegt | — |

**Inbound-Regeln:**

| Protokoll | Port | Quelle | Hinweis |
|---|---|---|---|
| TCP | 8080 | `0.0.0.0/0` | ⚠️ Offen aus Internet — kein ALB davor, MVP-Stand |

> ⚠️ **Zielbild:** Port 8080 nur von ALB-Security-Group (nicht öffentlich). Noch nicht umgesetzt.

---

## 10. Route53 / API Gateway

| Service | Status |
|---|---|
| Route53 Custom Domain | ❌ Für `dev` nicht konfiguriert (bewusst, laut BL-05) |
| API Gateway | ❌ Nicht vorhanden (bewusst — ALB-direkt genügt für aktuellen Scope) |

> Für `staging`/`prod`: Route53 + ACM-Zertifikat + Alias auf ALB **verpflichtend** (laut [`docs/ENV_PROMOTION_STRATEGY.md`](ENV_PROMOTION_STRATEGY.md)).

---

## 11. Rebuild-Reihenfolge (kritische Abhängigkeiten)

Wenn die gesamte `dev`-Infrastruktur neu aufgebaut werden muss:

```
1. IAM Roles vorbereiten
   ├─ swisstopo-dev-ecs-execution-role  (benötigt von ECS TaskDef)
   ├─ swisstopo-dev-ecs-task-role       (benötigt von ECS TaskDef)
   └─ swisstopo-dev-github-deploy-role  (benötigt für CI/CD)

2. ECR Repository anlegen
   └─ swisstopo-dev-api                 (benötigt für Docker Push + ECS Image)

3. CloudWatch Log Group anlegen
   └─ /swisstopo/dev/ecs/api            (benötigt von ECS Task Definition)

4. S3 Bucket anlegen
   └─ swisstopo-dev-523234426229        (unabhängig, kann parallel zu 2/3)

5. ECS Cluster anlegen
   └─ swisstopo-dev                     (benötigt vor ECS Service)

6. ECS Service + Task Definition via CI/CD-Deploy
   └─ Trigger: Push auf main            (setzt 1–5 voraus)

7. Monitoring-Baseline
   ├─ SNS Topic swisstopo-dev-alerts
   ├─ CloudWatch Metric Filters
   └─ CloudWatch Alarme
   (Skript: scripts/setup_monitoring_baseline_dev.sh)

8. SSM Parameter anlegen (manuell, Secret)
   └─ /swisstopo/dev/telegram-bot-token

9. Telegram-Alerting (Lambda + IAM + SNS-Sub)
   └─ Via Terraform (manage_telegram_alerting=true) oder
      scripts/setup_telegram_alerting_dev.sh
```

---

## 12. IaC-Managed vs. Manuell — Übersicht

| Ressource | IaC-Status | Artefakt |
|---|---|---|
| ECS Cluster `swisstopo-dev` | 🔧 Terraform (Import empfohlen) | `infra/terraform/main.tf` |
| ECR Repository `swisstopo-dev-api` | 🔧 Terraform (Import empfohlen) | `infra/terraform/main.tf` |
| CloudWatch Log Group `/swisstopo/dev/ecs/api` | 🔧 Terraform (Import empfohlen) | `infra/terraform/main.tf` |
| S3 Bucket `swisstopo-dev-523234426229` | 🔧 Terraform (Import empfohlen) | `infra/terraform/main.tf` |
| Lambda `swisstopo-dev-sns-to-telegram` | 🔧 Terraform | `infra/terraform/lambda_telegram.tf` |
| Lambda IAM-Role | 🔧 Terraform | `infra/terraform/lambda_telegram.tf` |
| SNS-Subscription Lambda→SNS | 🔧 Terraform | `infra/terraform/lambda_telegram.tf` |
| ECS Service `swisstopo-dev-api` | 🖐️ Manuell | — |
| ECS Task Definition `swisstopo-dev-api` | 🖐️ Automatisch via CI/CD | `.github/workflows/deploy.yml` |
| IAM OIDC Deploy-Role | 🖐️ Manuell | Policy: `infra/iam/deploy-policy.json` |
| IAM ECS Execution-Role | 🖐️ Manuell | — |
| IAM ECS Task-Role | 🖐️ Manuell | — |
| SNS Topic `swisstopo-dev-alerts` | 🖐️ Via Script | `scripts/setup_monitoring_baseline_dev.sh` |
| CloudWatch Metric Filters | 🖐️ Via Script | `scripts/setup_monitoring_baseline_dev.sh` |
| CloudWatch Alarme | 🖐️ Via Script | `scripts/setup_monitoring_baseline_dev.sh` |
| CloudWatch Log Group `/swisstopo/dev/app` | 🖐️ Manuell | — |
| Security Group `sg-092e0616ffb0663c3` | 🖐️ Manuell | — |
| VPC, Subnets | 🖐️ AWS-Default | — |
| SSM Parameter `/swisstopo/dev/telegram-bot-token` | 🖐️ Manuell (bewusst — Secret) | — |

---

*Verwandte Dokumente:*
- [`docs/DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md) — Deploy-Runbook, CI/CD, Rollback
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — Architekturübersicht
- [`docs/TAGGING_AUDIT.md`](TAGGING_AUDIT.md) — Tag-Audit
- [`docs/NETWORK_INGRESS_DECISIONS.md`](NETWORK_INGRESS_DECISIONS.md) — Netzwerk-Zielbild
- [`infra/terraform/README.md`](../infra/terraform/README.md) — Terraform Import-first-Runbook
- [`infra/iam/README.md`](../infra/iam/README.md) — IAM Least-Privilege Herleitung
