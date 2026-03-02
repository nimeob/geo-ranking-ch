# Dev DB → ECS Secrets Wiring (INFRA-NET-0-dev)

Dieses Runbook beschreibt, wie DB-Zugangsdaten sicher aus AWS Secrets Manager in die ECS Task Definition (dev) injiziert werden — ohne Klartextwerte in Terraform State, Task Definition oder Logs.

---

## Überblick

| Variable     | Typ             | Quelle                                    |
|--------------|-----------------|-------------------------------------------|
| `DB_HOST`    | `environment`   | `aws_db_instance.dev_postgres.address` (Terraform-local, kein Secret) |
| `DB_PORT`    | `environment`   | `var.dev_db_port` (kein Secret)           |
| `DB_NAME`    | `environment`   | `var.dev_db_name` (kein Secret)           |
| `DB_USERNAME`| `environment`   | `var.dev_db_master_username` (kein Secret) |
| `DB_PASSWORD`| `secrets`       | Secrets Manager ARN → JSON-Key `password` |

> `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USERNAME` sind **nicht geheim** — sie landen als Plaintext-Env in der Task Definition.
> `DB_PASSWORD` wird **nie im Terraform State** gespeichert; ECS zieht es zur Laufzeit direkt aus Secrets Manager.

---

## Voraussetzungen

1. **RDS Instanz provisioniert** (`manage_dev_db = true`)
   - `manage_master_user_password = true` → AWS legt automatisch einen Secrets Manager Secret an
   - Secret ARN ist als Terraform-Output verfügbar: `dev_db_master_user_secret_arn`

2. **ECS Execution Role** mit den notwendigen IAM Permissions (siehe unten)

---

## Secret ARN auflösen

### Fall 1: RDS im gleichen Terraform-Workspace (Standard)

```bash
# Nach terraform apply:
terraform output dev_db_master_user_secret_arn
# arn:aws:secretsmanager:eu-central-1:523234426229:secret:rds!db-...
```

Terraform nutzt den ARN **automatisch** (kein manuelles Setzen nötig, `dev_db_master_user_secret_arn_override = ""`).

### Fall 2: RDS in einem anderen Workspace (Cross-Workspace)

Den ARN aus dem anderen Workspace entnehmen und in `terraform.dev.tfvars` eintragen:

```hcl
dev_db_master_user_secret_arn_override = "arn:aws:secretsmanager:eu-central-1:523234426229:secret:rds!db-<suffix>"
```

---

## IAM Permissions für die ECS Execution Role

Die **Execution Role** (nicht die Task Role) benötigt folgende Rechte, damit ECS beim Container-Start das Secret auflösen kann:

### Minimal-Policy (Secrets Manager)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowGetDBMasterSecret",
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:eu-central-1:523234426229:secret:rds!db-*"
    }
  ]
}
```

> Empfehlung: ARN so spezifisch wie möglich (kein `*`). RDS-auto-managed Secrets haben das Prefix `rds!db-`.

### Optional: KMS Decrypt (nur bei CMK-verschlüsselten Secrets)

```json
{
  "Sid": "AllowKMSDecrypt",
  "Effect": "Allow",
  "Action": "kms:Decrypt",
  "Resource": "arn:aws:kms:eu-central-1:523234426229:key/<key-id>"
}
```

### Task Role

Die **Task Role** benötigt für die DB-Verbindung selbst **keine** Secrets-Manager-Rechte — Netzwerkzugang (VPC SG) ist ausreichend.

---

## Wiring-Überblick (Terraform)

```
aws_db_instance.dev_postgres
  └── master_user_secret[0].secret_arn
          │
          ▼
local.dev_db_secret_arn_effective
          │
          ▼
container_definitions.secrets[0]
  name      = "DB_PASSWORD"
  valueFrom = "<ARN>:password::"
          │
          ▼
ECS Container ENV: DB_PASSWORD = <plaintext at runtime, injected by ECS agent>
```

---

## Smoke-Check (nach Deploy)

```bash
# 1. Task-Definition prüfen (kein Passwort im Klartext!)
aws ecs describe-task-definition \
  --task-definition swisstopo-dev-api \
  --region eu-central-1 \
  | jq '.taskDefinition.containerDefinitions[0] | {environment, secrets}'

# Erwartung:
# - secrets: [{name: "DB_PASSWORD", valueFrom: "arn:...:password::"}]
# - environment: enthält DB_HOST, DB_PORT, DB_NAME, DB_USERNAME — kein DB_PASSWORD!

# 2. Kein DB_PASSWORD sollte in CloudWatch Logs erscheinen.
aws logs filter-log-events \
  --log-group-name "/swisstopo/dev/ecs/api" \
  --filter-pattern "DB_PASSWORD" \
  --region eu-central-1 \
  | jq '.events | length'
# Erwartung: 0
```

---

## Namenskonventionen (SSM/SecretsManager)

| Ressource                          | Naming Pattern                                           |
|------------------------------------|----------------------------------------------------------|
| RDS-auto-managed Master Secret     | `rds!db-<rds-instance-id>-<suffix>` (AWS vergeben)      |
| Manuell angelegte DB-Secrets (SSM) | `/<project>/<env>/db-<component>`                        |
| API Auth Token (SSM)               | `/<project>/<env>/api-auth-token`                        |
| Telegram Bot Token (SSM)           | `/<project>/<env>/telegram-bot-token`                    |

> **Kein Secret** darf direkt in `*.tfvars`, `docker-compose.yml` oder Commit-Messages landen.

---

## Abhängigkeiten

- **Voraussetzung:** INFRA-NET-0-dev (#860) — Terraform Network + DB Skeleton
- **Folge-Task:** Migration Runbook → [DEV_DB_RUNBOOK.md](./DEV_DB_RUNBOOK.md)

---

*Erstellt im Rahmen von INFRA-NET-0-dev (#860), 2026-03-02.*
