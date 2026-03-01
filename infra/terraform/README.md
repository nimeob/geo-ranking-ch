# Terraform (dev) — Import-first Runbook

Dieses Verzeichnis ist ein **sicherer Terraform-Einstieg** für die bestehenden dev-Kernressourcen:

- ECS Cluster `swisstopo-dev`
- ECR Repository `swisstopo-dev-api`
- CloudWatch Log Group `/swisstopo/dev/ecs/api`
- S3 Bucket `swisstopo-dev-523234426229`

Optionale Erweiterungen (ebenfalls import-first):
- Telegram-Alerting (Lambda + SNS Subscription)
- HTTP-Health-Probe (Lambda + EventBridge + CloudWatch Alarm)

Ziel: erst **read-only prüfen**, dann **importieren**, erst danach (bei sauberem Plan) aktiv verwalten.

## Environments (dev + staging)

Dieses Terraform-Setup ist **env-parametrisierbar** (Variable `environment` + Var-Files):

- dev: `terraform.dev.tfvars.example` (Alias/Legacy: `terraform.tfvars.example`)
- staging: `terraform.staging.tfvars.example` (Skeleton)

Für lokales Arbeiten ohne State-Kollisionen (dev/staging parallel) **Terraform Workspaces** verwenden:

```bash
cd infra/terraform
terraform init

# dev
cp terraform.dev.tfvars.example terraform.dev.tfvars
terraform workspace select dev || terraform workspace new dev
terraform plan -var-file=terraform.dev.tfvars
# terraform apply -var-file=terraform.dev.tfvars

# staging
cp terraform.staging.tfvars.example terraform.staging.tfvars
terraform workspace select staging || terraform workspace new staging
terraform plan -var-file=terraform.staging.tfvars
# terraform apply -var-file=terraform.staging.tfvars
```

> Apply bleibt bewusst ein separater Schritt und sollte erst nach geprüftem Plan ausgeführt werden.

## Sicherheitsprinzip

- Alle `manage_*` Flags stehen standardmässig auf `false`.
- Damit ist ein erster `terraform plan` neutral (kein unbeabsichtigtes Create/Destroy).
- Bestehende Ressourcen werden zuerst importiert.
- Ressourcenblöcke setzen `lifecycle.prevent_destroy = true`.

> **Kein blindes `terraform apply` auf bestehender Infrastruktur.**

---

## Verifizierter Ist-Stand (read-only AWS-Checks, 2026-02-25)

Read-only geprüft via AWS CLI (`describe*` / `list*`):

| Ressource | Ist-Wert |
|---|---|
| ECS Cluster | `swisstopo-dev` (ACTIVE) |
| ECS `containerInsights` | `disabled` |
| ECR Repository | `swisstopo-dev-api` |
| CloudWatch Log Group | `/swisstopo/dev/ecs/api` |
| Log Retention | `30` Tage |
| S3 Bucket | `swisstopo-dev-523234426229` |
| Standard-Tags | `Environment=dev`, `ManagedBy=openclaw`, `Owner=nico`, `Project=swisstopo` |

Die Terraform-Defaults sind darauf abgestimmt, um Drift direkt nach Import zu minimieren.

---

## Enthaltene Ressourcenblöcke

- `aws_ecs_cluster.dev` (optional managed)
- `aws_ecr_repository.api` (optional managed)
- `aws_cloudwatch_log_group.api` (optional managed)
- `aws_s3_bucket.dev` (optional managed)
- `aws_lambda_function.sns_to_telegram` + IAM + SNS Subscription (`manage_telegram_alerting=true`)
- `aws_lambda_function.health_probe` + IAM + EventBridge + Alarm (`manage_health_probe=true`)
- optionale Read-only-Data-Sources (`lookup_existing_resources=true`)

---

## Reproduzierbarer Ablauf (init → read-only plan → import → plan)

### 1) Vorbereiten

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
```

### 2) Read-only Validierung (ohne Management)

In `terraform.tfvars` sicherstellen:

- `lookup_existing_resources = true`
- `manage_ecs_cluster = false`
- `manage_ecr_repository = false`
- `manage_cloudwatch_log_group = false`
- `manage_s3_bucket = false`

Dann:

```bash
terraform plan
```

### 3) Import pro Ressource

Pro Ressource einzeln vorgehen:

1. passendes `manage_*` Flag auf `true`
2. Import ausführen
3. `terraform plan` prüfen

Import-IDs:

```bash
# ECS Cluster
terraform import 'aws_ecs_cluster.dev[0]' swisstopo-dev

# ECR Repository
terraform import 'aws_ecr_repository.api[0]' swisstopo-dev-api

# CloudWatch Log Group
terraform import 'aws_cloudwatch_log_group.api[0]' /swisstopo/dev/ecs/api

# S3 Bucket
terraform import 'aws_s3_bucket.dev[0]' swisstopo-dev-523234426229
```

Optional (BL-14, nur bei `manage_health_probe=true`):

```bash
# IAM Role + Policies
terraform import 'aws_iam_role.health_probe[0]' swisstopo-dev-health-probe-role
terraform import 'aws_iam_role_policy.health_probe_inline[0]' 'swisstopo-dev-health-probe-role:health-probe-inline'
terraform import 'aws_iam_role_policy_attachment.health_probe_basic_execution[0]' 'swisstopo-dev-health-probe-role/arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'

# Lambda + EventBridge Invoke Permission
terraform import 'aws_lambda_function.health_probe[0]' swisstopo-dev-health-probe
terraform import 'aws_lambda_permission.health_probe_eventbridge_invoke[0]' 'swisstopo-dev-health-probe/allow-eventbridge-health-probe'

# EventBridge Rule + Target
terraform import 'aws_cloudwatch_event_rule.health_probe_schedule[0]' swisstopo-dev-health-probe-schedule
terraform import 'aws_cloudwatch_event_target.health_probe_lambda[0]' swisstopo-dev-health-probe-schedule/health-probe-lambda

# CloudWatch Alarm
terraform import 'aws_cloudwatch_metric_alarm.health_probe_fail[0]' swisstopo-dev-api-health-probe-fail
```

### 4) Erster Management-Plan

```bash
terraform plan
```

Nur wenn fachlich geprüft und explizit freigegeben:

```bash
terraform apply
```

---

## Helper-Script (read-only + Import-Hilfe)

Für reproduzierbare Vorprüfung und Import-Kommandos:

```bash
./scripts/check_import_first_dev.sh
```

Das Script macht nur Read-only AWS-Aufrufe und gibt:

- verifizierten Ist-Stand
- erkannte Drift-Risiken
- vorbereitete `terraform import` Befehle

---

## Nächster Ausbau (später)

- ECS Service / Task Definition als Terraform-Ressourcen ergänzen
- Weitere CloudWatch Alarme/Dashboards (über aktuelle Baseline hinaus) ergänzen
- Remote State + Locking (S3 + DynamoDB) definieren
