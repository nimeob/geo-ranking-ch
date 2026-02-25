# Terraform (dev) — IaC-Startpaket

Dieses Verzeichnis ist ein **minimaler, sicherer Terraform-Startpunkt** für die dev-Umgebung.
Fokus: Grundlagen für **ECS / ECR / CloudWatch Logs** als künftige Source of Truth.

## Sicherheitsprinzip (wichtig)

- Standardmässig sind alle `manage_*` Flags auf `false`.
- Damit führt ein erster `terraform plan` **keine unbeabsichtigten Create/Destroy-Aktionen** aus.
- Bestehende dev-Ressourcen sollen **zuerst importiert** werden, bevor Terraform sie aktiv verwaltet.
- Zusätzlich setzen die vorhandenen Ressourcenblöcke `lifecycle.prevent_destroy = true`.

> **Kein blindes `terraform apply` auf bestehender Infrastruktur.**

---

## Enthaltene Ressourcenblöcke

- `aws_ecs_cluster.dev` (optional managed)
- `aws_ecr_repository.api` (optional managed)
- `aws_cloudwatch_log_group.api` (optional managed)
- optionale Read-only-Data-Sources für bestehende Ressourcen (`lookup_existing_resources=true`)

---

## Empfohlene Reihenfolge (init → plan → import → apply)

### 1) Initialisieren

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
```

### 2) Sicherer Erst-Plan (ohne Management)

Prüfen, dass keine Ressourcen gemanagt werden:

```bash
terraform plan
```

Optional: bestehende Ressourcen nur lesen (Read-only), noch ohne Management:

1. In `terraform.tfvars` setzen:
   - `lookup_existing_resources = true`
   - alle `manage_* = false` belassen
2. Dann:

```bash
terraform plan
```

### 3) Import vorbereiten (pro Ressource)

Für jede Ressource, die künftig Terraform verwalten soll:

1. entsprechendes `manage_*` in `terraform.tfvars` auf `true` setzen
2. Import durchführen
3. danach `terraform plan` prüfen (sollte möglichst geringe/keine Änderungen zeigen)

Beispiele für dev:

```bash
# ECS Cluster
terraform import 'aws_ecs_cluster.dev[0]' swisstopo-dev

# ECR Repository
terraform import 'aws_ecr_repository.api[0]' swisstopo-dev-api

# CloudWatch Log Group
terraform import 'aws_cloudwatch_log_group.api[0]' /ecs/swisstopo-dev-api
```

### 4) Erstes Apply (nur nach sauberem Plan)

```bash
terraform plan
terraform apply
```

Nur ausführen, wenn der Plan fachlich geprüft ist.

---

## Hinweise zu bestehender dev-Infrastruktur

Gemäss Projektdokumentation existieren bereits dev-Ressourcen (`swisstopo-dev`, `swisstopo-dev-api`, `/ecs/swisstopo-dev-api`).

Daher gilt:

1. **Import-first** statt Neu-Erstellung
2. Änderungen schrittweise aktivieren (Ressource für Ressource)
3. Nach jedem Import `terraform plan` kontrollieren
4. Keine destruktiven Änderungen ohne explizite Review

---

## Nächster Ausbau (später)

- ECS Service / Task Definition als Terraform-Ressourcen ergänzen
- Alarme/Dashboards in CloudWatch ergänzen
- Remote State + Locking (z. B. S3 + DynamoDB) definieren
