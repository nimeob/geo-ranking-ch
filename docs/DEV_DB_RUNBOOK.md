# Dev DB Runbook

**Issue:** [#859](https://github.com/nimeob/geo-ranking-ch/issues/859) — INFRA-DB-0-dev.wp3
**Parent:** [#855](https://github.com/nimeob/geo-ranking-ch/issues/855) — INFRA-DB-0-dev
**Stand:** 2026-03-03
**Status:** Betriebs-Runbook für Dev-DB (copy/paste-fähig, operator-ready)

---

## Überblick

Dieses Runbook beschreibt den Betrieb der Dev-Datenbank (RDS Postgres) inkl. Verbindung, Migration, Rotation, Restore und sauberem Cleanup.

- Infrastruktur-Dateien:
  - `infra/terraform/dev_network.tf`
  - `infra/terraform/dev_db.tf`
  - `infra/terraform/dev_ecs_compute.tf`
- Secrets/Datenpfade:
  - RDS Master Secret via AWS-managed Secrets Manager (`manage_master_user_password = true`)
  - ECS Task-Definition nutzt `DB_PASSWORD` als Secret (`valueFrom`), nicht als plain env

> **Voraussetzungen**
> - AWS CLI + Terraform (>=1.5) + `jq` + `psql`
> - IAM-Rechte für VPC/RDS/ECS/SSM/SecretsManager/CloudWatch
> - Arbeitsverzeichnis: Repo-Root

---

## Vorbereitungen

```bash
export AWS_REGION="eu-central-1"
export AWS_ACCOUNT_ID="523234426229"
export PROJECT="swisstopo"
export ENV="dev"
export TF_DIR="infra/terraform"

aws sts get-caller-identity
```

---

## Verbindung herstellen

### Option A — Direkt aus privatem Netz (Bastion/Runner in gleicher VPC)

```bash
cd "${TF_DIR}"
DB_HOST=$(terraform output -raw dev_db_endpoint)
DB_PORT=$(terraform output -raw dev_db_port)
DB_NAME=$(terraform output -raw dev_db_name)
DB_USER=$(terraform output -raw dev_db_master_username)
SECRET_ARN=$(terraform output -raw dev_db_master_user_secret_arn)

DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "${SECRET_ARN}" \
  --region "${AWS_REGION}" \
  | jq -r '.SecretString | fromjson | .password')

PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST}" -p "${DB_PORT}" \
  -U "${DB_USER}" -d "${DB_NAME}" \
  -c "SELECT version();"
```

### Option B — Über SSM-Session auf Bastion

```bash
aws ssm start-session --target <BASTION_INSTANCE_ID> --region "${AWS_REGION}"
# dann in der Session dieselben psql-Befehle wie oben ausführen
```

---

## Credentials

### Master-Secret prüfen

```bash
cd "${TF_DIR}"
SECRET_ARN=$(terraform output -raw dev_db_master_user_secret_arn)

aws secretsmanager describe-secret \
  --secret-id "${SECRET_ARN}" \
  --region "${AWS_REGION}" \
  | jq '{Name, ARN, LastChangedDate, RotationEnabled}'

aws secretsmanager get-secret-value \
  --secret-id "${SECRET_ARN}" \
  --region "${AWS_REGION}" \
  | jq '.SecretString | fromjson | keys'
# Erwartung: ["password", "username"]
```

### ECS-Secrets-Wiring prüfen

```bash
aws ecs describe-task-definition \
  --task-definition "${PROJECT}-${ENV}-api" \
  --region "${AWS_REGION}" \
  | jq '.taskDefinition.containerDefinitions[0] | {
      env_db: [.environment[]? | select(.name|startswith("DB_"))],
      db_password_secret: [.secrets[]? | select(.name=="DB_PASSWORD")]
    }'
```

---

## Migrationen

### Terraform Apply (falls noch nicht erfolgt)

```bash
cd "${TF_DIR}"
cp -n terraform.dev.tfvars.example terraform.dev.tfvars
terraform init -upgrade
terraform plan -var-file="terraform.dev.tfvars" -out="dev-db.tfplan"
terraform apply "dev-db.tfplan"
```

### Core-Schema anwenden

```bash
cd "${TF_DIR}"
DB_HOST=$(terraform output -raw dev_db_endpoint)
DB_PORT=$(terraform output -raw dev_db_port)
DB_NAME=$(terraform output -raw dev_db_name)
DB_USER=$(terraform output -raw dev_db_master_username)
SECRET_ARN=$(terraform output -raw dev_db_master_user_secret_arn)
DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "${SECRET_ARN}" \
  --region "${AWS_REGION}" \
  | jq -r '.SecretString | fromjson | .password')

PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST}" -p "${DB_PORT}" \
  -U "${DB_USER}" -d "${DB_NAME}" \
  -v ON_ERROR_STOP=1 \
  -f "docs/sql/db_core_schema_v1.sql"

PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST}" -p "${DB_PORT}" \
  -U "${DB_USER}" -d "${DB_NAME}" \
  -c "\\dt"
```

### Optional: Async-Job-Schema

```bash
PGPASSWORD="${DB_PASS}" psql \
  -h "${DB_HOST}" -p "${DB_PORT}" \
  -U "${DB_USER}" -d "${DB_NAME}" \
  -v ON_ERROR_STOP=1 \
  -f "docs/sql/async_jobs_schema_v1.sql"
```

---

## Passwort-Rotation

1. Neues Passwort im Master-Secret setzen (oder AWS Rotation triggern).
2. ECS-Service neu deployen, damit neue Secret-Version gelesen wird.
3. Connectivity-Smoketest ausführen.

```bash
# 1) Secret (JSON) aktualisieren
aws secretsmanager put-secret-value \
  --secret-id "${SECRET_ARN}" \
  --secret-string '{"username":"swisstopo","password":"<NEW_PASSWORD>"}' \
  --region "${AWS_REGION}"

# 2) ECS redeploy triggern
aws ecs update-service \
  --cluster "${PROJECT}-${ENV}" \
  --service "${PROJECT}-${ENV}-api" \
  --force-new-deployment \
  --region "${AWS_REGION}"

# 3) Stabilität prüfen
aws ecs wait services-stable \
  --cluster "${PROJECT}-${ENV}" \
  --services "${PROJECT}-${ENV}-api" \
  --region "${AWS_REGION}"
```

---

## Backup & Restore

### Backup-Status prüfen

```bash
aws rds describe-db-instances \
  --db-instance-identifier "${PROJECT}-${ENV}-postgres" \
  --region "${AWS_REGION}" \
  | jq '.DBInstances[0] | {DBInstanceIdentifier, BackupRetentionPeriod, LatestRestorableTime, DBInstanceStatus}'
```

### Manuellen Snapshot erstellen

```bash
SNAP_ID="${PROJECT}-${ENV}-postgres-manual-$(date +%Y%m%d-%H%M%S)"
aws rds create-db-snapshot \
  --db-instance-identifier "${PROJECT}-${ENV}-postgres" \
  --db-snapshot-identifier "${SNAP_ID}" \
  --region "${AWS_REGION}"
```

### Restore (neue Instanz)

```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier "${PROJECT}-${ENV}-postgres-restore" \
  --db-snapshot-identifier "${SNAP_ID}" \
  --region "${AWS_REGION}"
```

---

## Smoke Checks

```bash
API_URL="https://<alb-dns-or-dev-api-url>"

# Health
curl -sf "${API_URL}/health" | jq .

# History (Bearer aus SSM)
API_TOKEN=$(aws ssm get-parameter \
  --name "/${PROJECT}/${ENV}/api-auth-token" \
  --with-decryption \
  --region "${AWS_REGION}" \
  --query 'Parameter.Value' --output text)

curl -sf \
  -H "Authorization: Bearer ${API_TOKEN}" \
  "${API_URL}/analyze/history" | jq '{ok, count: (.results|length)}'

# Log-Leak-Check (kein DB_PASSWORD)
aws logs filter-log-events \
  --log-group-name "/${PROJECT}/${ENV}/ecs/api" \
  --filter-pattern "DB_PASSWORD" \
  --region "${AWS_REGION}" \
  | jq '.events | length'
```

---

## Troubleshooting

### SG blockiert DB-Zugriff

```bash
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${PROJECT}-${ENV}-db-sg" \
  --region "${AWS_REGION}" \
  | jq '.SecurityGroups[0].IpPermissions'
```

### ECS Task kann Secret nicht lesen

```bash
aws ecs describe-tasks \
  --cluster "${PROJECT}-${ENV}" \
  --tasks "<TASK_ARN>" \
  --region "${AWS_REGION}" \
  | jq '.tasks[0] | {stoppedReason, taskRoleArn, executionRoleArn, containers: [.containers[]?.reason]}'
```

### RDS-Status prüfen

```bash
aws rds describe-db-instances \
  --db-instance-identifier "${PROJECT}-${ENV}-postgres" \
  --region "${AWS_REGION}" \
  | jq '.DBInstances[0] | {DBInstanceStatus, Endpoint, EngineVersion}'
```

---

## Cleanup

```bash
cd "${TF_DIR}"
terraform plan -destroy -var-file="terraform.dev.tfvars" -out="dev-destroy.tfplan"
terraform apply "dev-destroy.tfplan"
```

> Falls `prevent_destroy` auf RDS aktiv ist, zuerst den Schutz bewusst entfernen und den Vorgang dokumentieren.

---

## Test-/Validierungshinweise zu diesem Runbook

Für die Doku-Regression (Pflichtsektionen + Schlüsselkommandos):

```bash
pytest -q tests/test_dev_db_runbook_docs.py
```

Für lokale Terraform-Lint/Validierung:

```bash
terraform -chdir=infra/terraform validate
```

Für NAT-Egress-Rollout (Import/Plan/Apply/Checks) siehe zusätzlich:

- [DEV_NETWORK_NAT_ROLLOUT_RUNBOOK.md](./DEV_NETWORK_NAT_ROLLOUT_RUNBOOK.md)
