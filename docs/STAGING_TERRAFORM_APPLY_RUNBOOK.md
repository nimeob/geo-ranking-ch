# Runbook: Terraform Apply (Staging) — DB + ECS + ECR + ALB

Stand: 2026-03-07  
Quelle: Issue [#1331](https://github.com/nimeob/geo-ranking-ch/issues/1331)

Ziel
- reproduzierbarer Operator-Flow für `terraform plan/apply` im **staging** Workspace
- Reihenfolge + Guardrails dokumentieren (keine Secrets, kein blindes Apply)

Referenzen
- Staging Prereqs + GitHub Env Vars/Secrets: [`docs/staging-environment-setup.md`](staging-environment-setup.md)
- Terraform Overview: [`infra/terraform/README.md`](../infra/terraform/README.md)
- Staging ECS wiring: Issues [#1328](https://github.com/nimeob/geo-ranking-ch/issues/1328), [#1329](https://github.com/nimeob/geo-ranking-ch/issues/1329), [#1330](https://github.com/nimeob/geo-ranking-ch/issues/1330)

---

## Preflight Checklist (vor jedem Apply)

- [ ] Du arbeitest im Repo-Root auf aktuellem `main` (kein lokaler Drift)
- [ ] Terraform >= 1.6 installiert
- [ ] AWS Credentials aktiv (Operator) und Konto/Region stimmen
- [ ] Workspace ist korrekt: `staging`
- [ ] `terraform.staging.tfvars` ist vorhanden (gitignored) und enthält mindestens:
  - [ ] `environment = "staging"`
  - [ ] `aws_region = "eu-central-1"`
  - [ ] relevante `manage_staging_*` Flags (siehe unten)
- [ ] State-Backup erstellt (kopiere `terraform.tfstate` oder nutze Remote-State-Backup Mechanismus)

---

## Verbindliche Reihenfolge (Apply Sequenz)

> Network/VPC (`manage_staging_network`) ist eine Vorbedingung für ECS Compute + DB.  
> Falls das Netzwerk noch nicht existiert, zuerst das Network-Skeleton applyen.

1. **ECR** (API + UI Repositories)
2. **ECS Cluster** (`aws_ecs_cluster.staging`)
3. **ECS Compute** (SG + TaskDefs + Services)
4. **DB** (RDS Postgres + SG/Subnet Group)
5. **ALB / Ingress** (staging ALB + Listener + Routing — falls bereits im Terraform-Modul vorhanden)

---

## Setup: init + Workspace

```bash
cd infra/terraform
terraform init
terraform workspace select staging || terraform workspace new staging

# Operator file (gitignored)
cp terraform.staging.tfvars.example terraform.staging.tfvars  # einmalig
```

Plan (read-only) zum Einstieg:

```bash
terraform plan -var-file=terraform.staging.tfvars
```

---

## Manage-Flags (staging)

Diese Flags steuern, welche Ressourcen Terraform **anlegt/verwaltet** (Default: false in example file).

| Flag | Zweck |
|---|---|
| `manage_staging_network` | VPC/Subnets/IGW/Routes (Voraussetzung für DB/ECS Compute) |
| `manage_staging_ingress` | ALB/Listener (falls implementiert) |
| `manage_staging_ecs_cluster` | Staging ECS Cluster (`aws_ecs_cluster.staging`) |
| `manage_staging_ecs_compute` | ECS Compute Skeleton (SG + TaskDefs + Services) |
| `manage_staging_db` | RDS Postgres Skeleton |
| `manage_ecr_repository` | ECR Repo API |
| `manage_ecr_repository_ui` | ECR Repo UI |

---

## Schritt 1 — ECR Apply (API + UI)

Empfohlen: targeted plan/apply (kleinster Scope).

```bash
terraform plan \
  -var-file=terraform.staging.tfvars \
  -target=aws_ecr_repository.api \
  -target=aws_ecr_repository.ui

terraform apply \
  -var-file=terraform.staging.tfvars \
  -target=aws_ecr_repository.api \
  -target=aws_ecr_repository.ui
```

Post-check (AWS CLI, optional):

```bash
aws ecr describe-repositories --repository-names swisstopo-staging-api swisstopo-staging-ui
```

---

## Schritt 2 — ECS Cluster Apply

```bash
terraform plan \
  -var-file=terraform.staging.tfvars \
  -target=aws_ecs_cluster.staging

terraform apply \
  -var-file=terraform.staging.tfvars \
  -target=aws_ecs_cluster.staging
```

Post-check:

```bash
aws ecs describe-clusters --clusters swisstopo-staging
```

---

## Schritt 3 — ECS Compute Apply (API + UI)

> Voraussetzung: `manage_staging_network=true` (Subnets/VPC existieren).

Targeted Apply (Skeleton):

```bash
terraform plan \
  -var-file=terraform.staging.tfvars \
  -target=aws_security_group.staging_ecs_service \
  -target=aws_ecs_task_definition.staging_api \
  -target=aws_ecs_service.staging_api \
  -target=aws_ecs_task_definition.staging_ui \
  -target=aws_ecs_service.staging_ui

terraform apply \
  -var-file=terraform.staging.tfvars \
  -target=aws_security_group.staging_ecs_service \
  -target=aws_ecs_task_definition.staging_api \
  -target=aws_ecs_service.staging_api \
  -target=aws_ecs_task_definition.staging_ui \
  -target=aws_ecs_service.staging_ui
```

Post-check:

```bash
aws ecs describe-services \
  --cluster swisstopo-staging \
  --services swisstopo-staging-api swisstopo-staging-ui
```

---

## Schritt 4 — DB Apply (RDS)

> Achtung: Kostenpflichtig. Erst nach geprüftem Plan applyen.

```bash
terraform plan \
  -var-file=terraform.staging.tfvars \
  -target=aws_db_instance.staging_postgres

terraform apply \
  -var-file=terraform.staging.tfvars \
  -target=aws_db_instance.staging_postgres
```

Post-check:

```bash
aws rds describe-db-instances \
  --db-instance-identifier swisstopo-staging-postgres
```

Wenn `manage_master_user_password=true`, Secret wird von AWS erzeugt; ARN kann via Terraform Output oder AWS Console nachgeschlagen werden.

---

## Schritt 5 — ALB / Ingress Apply

Falls `manage_staging_ingress=true` und Ingress-Ressourcen bereits vorhanden sind:

```bash
terraform plan \
  -var-file=terraform.staging.tfvars \
  -target=aws_lb.staging

terraform apply \
  -var-file=terraform.staging.tfvars \
  -target=aws_lb.staging
```

Post-check: DNS/Health URLs wie in [`docs/staging-environment-setup.md`](staging-environment-setup.md) beschrieben.

---

## Rollback / Fehlerfälle

- Terraform-Module sind mit `lifecycle.prevent_destroy=true` und (bei DB) `deletion_protection=true` gehärtet.
- Ein "Rollback" ist daher typischerweise:
  1. Fehlerursache beheben (Vars/Permissions/Dependencies)
  2. erneut `terraform plan` → `terraform apply`

Wenn eine Ressource versehentlich erstellt wurde und entfernt werden muss:
- **nicht** blind `terraform destroy` (kann am prevent_destroy scheitern)
- stattdessen: bewusstes manuelles Deprovisioning + State-Cleanup nach Runbook/Review

---

## Post-Apply Verifikation (Minimum)

- Terraform: `terraform output` enthält plausible Werte (keine null-ARNS, wo erwartet)
- ECS Services sind `ACTIVE` und stabil
- DB ist `available`
- GitHub Environment `staging` ist konfiguriert (siehe Runbook #1332)
- Deploy-Workflow kann manuell getriggert werden: `.github/workflows/deploy-staging.yml`
