# Staging DB Runbook

**Issue:** [#827](https://github.com/nimeob/geo-ranking-ch/issues/827) — INFRA-DB-0.wp3
**Parent:** [#804](https://github.com/nimeob/geo-ranking-ch/issues/804) — INFRA-DB-0
**Stand:** 2026-03-02
**Status:** Manuelles Runbook (MVP); reproduzierbar und copy-paste-fähig.

---

## Überblick

Dieses Runbook beschreibt die vollständige Staging-DB-Einrichtung in vier Phasen:

| Phase | Beschreibung |
|-------|--------------|
| 1     | Terraform Apply — RDS + Netzwerk + ECS Secrets Wiring |
| 2     | Secrets Management — Secrets Manager + SSM prüfen und anlegen |
| 3     | Migration — Kanonisches Schema gegen Staging-DB anwenden |
| 4     | Smoke Checks — DB-Konnektivität aus ECS, `/healthz`, `/analyze/history` |

> **Voraussetzungen:**
> - INFRA-DB-0.wp1 (#825): Terraform RDS Skeleton vorhanden (`infra/terraform/staging_db.tf`)
> - INFRA-DB-0.wp2 (#826): ECS Secrets Wiring konfiguriert (`infra/terraform/staging_ecs_compute.tf`)
> - AWS CLI konfiguriert + ausreichende IAM Permissions (RDS, ECS, Secrets Manager, SSM, VPC)
> - Terraform ≥ 1.5 installiert

---

## Vorbereitungen

```bash
export AWS_REGION="eu-central-1"
export AWS_ACCOUNT_ID="523234426229"
export PROJECT="swisstopo"
export ENV="staging"
export TF_DIR="infra/terraform"

# Identität prüfen
aws sts get-caller-identity
```

---

## Phase 1 — Terraform Apply (RDS + ECS Wiring)

### 1.1 Var-File anlegen / prüfen

```bash
cd "${TF_DIR}"

# Beispiel-Datei als Vorlage nehmen (falls nicht vorhanden)
cp terraform.staging.tfvars.example terraform.staging.tfvars
```

Mindeständerungen in `terraform.staging.tfvars`:

```hcl
# DB aktivieren (nach Netzwerk-Setup mit manage_staging_network=true)
manage_staging_db          = true
manage_staging_ecs_compute = true   # für Secrets-Wiring
manage_staging_network     = true   # Voraussetzung

# Optional: DB-Sizing explizit setzen (Defaults sind sinnvoll für staging)
# staging_db_instance_class       = "db.t4g.micro"
# staging_db_allocated_storage_gb = 20
# staging_db_engine_version       = "16"   # "" => AWS Default
```

> **Sicherheitsnote:** Kein Passwort in `terraform.staging.tfvars` erforderlich —
> `manage_master_user_password = true` delegiert die Passwortverwaltung vollständig an AWS
> Secrets Manager. Das Passwort erscheint **nie im Terraform State**.

### 1.2 Plan prüfen

```bash
cd "${TF_DIR}"

terraform init -upgrade

terraform plan \
  -var-file="terraform.staging.tfvars" \
  -out=staging-db.tfplan

# Erwartete neue Ressourcen:
# + aws_db_subnet_group.staging[0]
# + aws_security_group.staging_db[0]
# + aws_security_group_rule.staging_db_ingress_from_sgs["sg-..."]  (ECS SG)
# + aws_db_instance.staging_postgres[0]
```

**Checkliste Plan-Review:**

- [ ] Keine unerwarteten Destroys (`-/+` bei existierenden Ressourcen)
- [ ] `aws_db_instance.staging_postgres[0]` wird neu erstellt (oder ist schon importiert)
- [ ] `manage_master_user_password = true` → kein `password` im Plan sichtbar
- [ ] Security Group: Ingress nur von ECS Service SG auf Port 5432
- [ ] `deletion_protection = true` und `lifecycle { prevent_destroy = true }` gesetzt

### 1.3 Apply

```bash
terraform apply staging-db.tfplan
```

> **Dauer:** RDS-Erstellung dauert typischerweise 5–10 Minuten.

### 1.4 Outputs prüfen

```bash
terraform output staging_db_endpoint
# → swisstopo-staging-postgres.<hash>.eu-central-1.rds.amazonaws.com

terraform output staging_db_port
# → 5432

terraform output staging_db_name
# → swisstopo

terraform output staging_db_master_username
# → swisstopo

terraform output staging_db_master_user_secret_arn
# → arn:aws:secretsmanager:eu-central-1:523234426229:secret:rds!db-<suffix>
```

> Secrets Manager ARN merken — wird in Phase 2 und für ECS Wiring benötigt.

---

## Phase 2 — Secrets Management

### 2.1 DB Master-Passwort (AWS-managed) prüfen

```bash
SECRET_ARN=$(terraform output -raw staging_db_master_user_secret_arn)

# Secret-Metadaten prüfen (kein Klartext-Passwort hier anzeigen!)
aws secretsmanager describe-secret \
  --secret-id "${SECRET_ARN}" \
  --region "${AWS_REGION}" \
  | jq '{Name, ARN, CreatedDate, LastAccessedDate}'

# Prüfen, dass Passwort-Feld existiert (Rotation check):
aws secretsmanager get-secret-value \
  --secret-id "${SECRET_ARN}" \
  --region "${AWS_REGION}" \
  | jq '.SecretString | fromjson | keys'
# Erwartung: ["password","username"]  (Klartext NICHT in Logs/Protokollen festhalten)
```

### 2.2 ECS Task Definition – Secrets Wiring verifizieren

```bash
# Prüfen, dass DB_PASSWORD als Secret (nicht Env) konfiguriert ist
aws ecs describe-task-definition \
  --task-definition "${PROJECT}-${ENV}-api" \
  --region "${AWS_REGION}" \
  | jq '.taskDefinition.containerDefinitions[0] | {
      environment: [.environment[] | select(.name | startswith("DB_"))],
      secrets:     [.secrets[]     | select(.name == "DB_PASSWORD")]
    }'

# Erwartetes Ergebnis:
# {
#   "environment": [
#     {"name": "DB_HOST",     "value": "swisstopo-staging-postgres.....rds.amazonaws.com"},
#     {"name": "DB_PORT",     "value": "5432"},
#     {"name": "DB_NAME",     "value": "swisstopo"},
#     {"name": "DB_USERNAME", "value": "swisstopo"}
#   ],
#   "secrets": [
#     {"name": "DB_PASSWORD", "valueFrom": "arn:...:rds!db-...:password::"}
#   ]
# }
```

### 2.3 OIDC-Konfiguration (SSM) prüfen

Falls Cognito bereits eingerichtet ist (OIDC-0.wp3, #819):

```bash
# JWKS URL für JWT-Validierung
aws ssm get-parameter \
  --name "/${PROJECT}/${ENV}/oidc-jwks-url" \
  --region "${AWS_REGION}" \
  --query 'Parameter.Value' --output text

# Issuer URL
aws ssm get-parameter \
  --name "/${PROJECT}/${ENV}/oidc-jwt-issuer" \
  --region "${AWS_REGION}" \
  --query 'Parameter.Value' --output text
```

> Falls noch nicht gesetzt, siehe [OIDC Cognito Staging Runbook](./OIDC_COGNITO_STAGING_RUNBOOK.md).

### 2.4 SSM Namenskonventionen (Referenz)

| Parameter                              | Typ           | Wert-Herkunft                        |
|----------------------------------------|---------------|--------------------------------------|
| `/{project}/{env}/db-host`             | String        | Terraform output (optional, redundant) |
| `/{project}/{env}/oidc-jwks-url`       | String        | Cognito User Pool JWKS Endpoint      |
| `/{project}/{env}/oidc-jwt-issuer`     | String        | Cognito User Pool Issuer URL         |
| `/{project}/{env}/oidc-jwt-audience`   | String        | Cognito App Client ID                |
| `/{project}/{env}/telegram-bot-token`  | SecureString  | Manuell angelegt (kein TF)           |
| `/{project}/{env}/api-auth-token`      | SecureString  | Manuell angelegt (kein TF)           |

> **Regel:** Secrets werden **nie** per Terraform angelegt (kein Klartext im State).
> Alle SecureString-Werte manuell via `aws ssm put-parameter --type SecureString`.

---

## Phase 3 — Migration (Kanonisches Schema)

> **Voraussetzung:** Direkte Netzwerkverbindung zur RDS-Instanz (privates Subnetz).
> Optionen: (a) EC2 Bastion / SSM Session, (b) ECS Task Run, (c) lokales Port-Forwarding via SSM.

### 3.1 Verbindungsdetails auflösen

```bash
DB_HOST=$(terraform output -raw staging_db_endpoint)
DB_PORT=$(terraform output -raw staging_db_port)
DB_NAME=$(terraform output -raw staging_db_name)
DB_USER=$(terraform output -raw staging_db_master_username)
SECRET_ARN=$(terraform output -raw staging_db_master_user_secret_arn)

# Passwort aus Secrets Manager holen (nur für aktiven Migrations-Schritt, nicht loggen!)
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "${SECRET_ARN}" \
  --region "${AWS_REGION}" \
  | jq -r '.SecretString | fromjson | .password')
```

### 3.2 Verbindung testen

```bash
# Option A: psql (direkt, wenn Netz erreichbar)
PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST}" -p "${DB_PORT}" \
  -U "${DB_USER}" -d "${DB_NAME}" \
  -c "SELECT version();"

# Option B: Via SSM + EC2 Bastion
# aws ssm start-session --target <instance-id>
# (dann psql innerhalb der Bastion-Session)
```

### 3.3 Schema v1 anwenden (Core Tables)

```bash
# Canonical schema (organizations/users/memberships/api_keys)
# Datei: docs/sql/db_core_schema_v1.sql

PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST}" -p "${DB_PORT}" \
  -U "${DB_USER}" -d "${DB_NAME}" \
  -v ON_ERROR_STOP=1 \
  -f docs/sql/db_core_schema_v1.sql

# Erwartung: BEGIN / CREATE TABLE / COMMIT (keine Fehler)
```

### 3.4 Schema verifizieren

```bash
PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST}" -p "${DB_PORT}" \
  -U "${DB_USER}" -d "${DB_NAME}" \
  -c "\dt" 2>&1

# Erwartete Tabellen:
#  organizations
#  users
#  memberships
#  api_keys
```

### 3.5 Async Jobs Schema anwenden (optional, für ASYNC-DB-0)

```bash
# Datei: docs/sql/async_jobs_schema_v1.sql
# Nur anwenden wenn ASYNC-DB-0 (#803) bereits umgesetzt ist.

PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST}" -p "${DB_PORT}" \
  -U "${DB_USER}" -d "${DB_NAME}" \
  -v ON_ERROR_STOP=1 \
  -f docs/sql/async_jobs_schema_v1.sql
```

> **Hinweis:** Migration-Runner für automatisierte Anwendung (CI/CD) ist in DB-0.wp2 (#813) geplant.
> Bis dahin ist manuelle Ausführung via psql der dokumentierte Pfad.

---

## Phase 4 — Smoke Checks

### 4.1 DB-Konnektivität aus ECS Task prüfen

```bash
# ECS Task mit `exec` starten (wenn AWS ECS Exec aktiviert ist)
aws ecs execute-command \
  --cluster "${PROJECT}-${ENV}" \
  --task "<TASK_ARN>" \
  --container "swisstopo-${ENV}-api" \
  --interactive \
  --command "/bin/sh"

# Im Container:
# echo "DB_HOST: $DB_HOST"
# echo "DB_PORT: $DB_PORT"
# nc -zv $DB_HOST $DB_PORT && echo "TCP OK"
```

### 4.2 /healthz Endpoint

```bash
# API Base URL (aus ALB DNS oder direktem ECS-IP)
API_URL="https://<alb-dns-name>"    # oder http://<ecs-ip>:8080

curl -sf "${API_URL}/healthz" | jq .
# Erwartung:
# {"status": "ok", "build": "...", "timestamp": "..."}
```

### 4.3 /analyze/history mit Bearer Token

```bash
# Phase 1 Auth Token (aus SSM oder lokal bekannt)
API_TOKEN=$(aws ssm get-parameter \
  --name "/${PROJECT}/${ENV}/api-auth-token" \
  --with-decryption \
  --region "${AWS_REGION}" \
  --query 'Parameter.Value' --output text)

curl -sf \
  -H "Authorization: Bearer ${API_TOKEN}" \
  "${API_URL}/analyze/history" | jq '{ok, count: (.results | length)}'

# Erwartung: {"ok": true, "count": 0}  (leere History nach frischer Migration)
# NICHT: 401 Unauthorized, 500 Internal Server Error
```

### 4.4 /analyze Endpoint (Smoke-Query)

```bash
curl -sf \
  -X POST \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query": "__ok__"}' \
  "${API_URL}/analyze" | jq '{ok, job_id}'

# Erwartung: {"ok": true, "job_id": "..."}
```

### 4.5 CloudWatch Logs prüfen (kein Passwort-Leak)

```bash
LOG_GROUP="/swisstopo/${ENV}/ecs/api"

aws logs filter-log-events \
  --log-group-name "${LOG_GROUP}" \
  --filter-pattern "DB_PASSWORD" \
  --region "${AWS_REGION}" \
  | jq '.events | length'
# Erwartung: 0  (Passwort darf nie in Logs erscheinen)
```

---

## Troubleshooting

### RDS nicht erreichbar (Timeout)

1. Security Group prüfen: ECS Service SG muss als Ingress-Quelle in der DB SG eingetragen sein.
   ```bash
   aws ec2 describe-security-groups \
     --filters "Name=group-name,Values=${PROJECT}-${ENV}-db-sg" \
     --region "${AWS_REGION}" \
     | jq '.SecurityGroups[0].IpPermissions'
   ```
2. VPC/Subnet prüfen: ECS Tasks müssen im selben VPC/Private-Subnet wie RDS laufen.
3. DB Status prüfen:
   ```bash
   aws rds describe-db-instances \
     --db-instance-identifier "${PROJECT}-${ENV}-postgres" \
     --region "${AWS_REGION}" \
     | jq '.DBInstances[0] | {DBInstanceStatus, Endpoint}'
   ```

### ECS Task startet nicht (Secret-Fetch-Fehler)

```bash
# Task Stop-Reason aus CloudWatch Events / ECS Events holen
aws ecs describe-tasks \
  --cluster "${PROJECT}-${ENV}" \
  --tasks "<TASK_ARN>" \
  --region "${AWS_REGION}" \
  | jq '.tasks[0] | {stoppedReason, containers: [.containers[].reason]}'

# Häufige Ursachen:
# - Execution Role fehlt secretsmanager:GetSecretValue
# - Secret ARN in Task Definition veraltet (nach Secret-Rotation)
```

> Für IAM-Permissions-Details: [STAGING_DB_ECS_SECRETS_RUNBOOK.md](./STAGING_DB_ECS_SECRETS_RUNBOOK.md)

### Migration schlägt fehl (pgcrypto nicht verfügbar)

```sql
-- pgcrypto Extension manuell aktivieren (Superuser erforderlich)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

> Bei RDS Postgres ist `pgcrypto` standardmäßig verfügbar, benötigt aber explizites `CREATE EXTENSION`.

---

## Abhängigkeiten / Folge-Tasks

| Richtung      | Issue | Beschreibung |
|---------------|-------|--------------|
| Voraussetzung | #825  | INFRA-DB-0.wp1: Terraform RDS Skeleton |
| Voraussetzung | #826  | INFRA-DB-0.wp2: ECS Secrets Wiring |
| Folge-Task    | #833  | INFRA-DB-0.wp4: Lokale Dev-DB (docker-compose) für Offline-Dev |
| Folge-Task    | #813  | DB-0.wp2: Migration Runner + CI Harness (geblockt auf #804) |
| Folge-Task    | #803  | ASYNC-DB-0: Async Job History in DB persistieren |

---

*Erstellt im Rahmen von INFRA-DB-0.wp3 (#827), 2026-03-02.*
