# Staging-Environment Setup — Prerequisites & Aktivierungsanleitung

Stand: 2026-03-07  
Erstellt: Issue #1325 (Worker A)  
Referenz-Strategie: [`docs/ENV_PROMOTION_STRATEGY.md`](ENV_PROMOTION_STRATEGY.md)  
Deploy-Workflow: [`.github/workflows/deploy-staging.yml`](../.github/workflows/deploy-staging.yml)

---

## Übersicht

Das Workflow-File `deploy-staging.yml` ist fertig und vollständig getestet.  
Vor dem ersten Trigger müssen folgende Schritte abgeschlossen sein:

1. GitHub Environment `staging` konfigurieren (Vars + Secrets)
2. AWS-Infra bereitstellen (ECS, ECR, ALB, Cognito, RDS, DNS/ACM)
3. OIDC-Deploy-Role für Staging anlegen (analog `swisstopo-dev-github-deploy-role`)
4. Smoketest-Grundlage herstellen (Domain DNS, Health-URL erreichbar)

---

## Phase 1 — GitHub Environment konfigurieren

### 1.1 Environment anlegen

```
GitHub → Repo → Settings → Environments → New environment → Name: "staging"
```

Optional: Protection Rules (required reviewers, deployment branches) für `main` setzen.

### 1.2 Erforderliche Variables (Environment `staging`)

| Variable | Beispielwert | Beschreibung |
|---|---|---|
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::<ACCOUNT>:role/swisstopo-staging-github-deploy-role` | OIDC-Deploy-Role ARN (Staging) |
| `ECS_CLUSTER` | `swisstopo-staging` | ECS Cluster-Name |
| `ECS_API_SERVICE` | `swisstopo-staging-api` | ECS API-Service-Name |
| `ECS_UI_SERVICE` | `swisstopo-staging-ui` | ECS UI-Service-Name |
| `ECS_API_CONTAINER_NAME` | `swisstopo-staging-api` | Containername in der API-TaskDef |
| `ECS_UI_CONTAINER_NAME` | `swisstopo-staging-ui` | Containername in der UI-TaskDef |
| `ECR_API_REPOSITORY` | `swisstopo-staging-api` | ECR Repo für API-Images |
| `ECR_UI_REPOSITORY` | `swisstopo-staging-ui` | ECR Repo für UI-Images |
| `SERVICE_API_BASE_URL` | `https://api.staging.georanking.ch` | Öffentliche API-Base-URL |
| `SERVICE_HEALTH_URL` | `https://api.staging.georanking.ch/health` | Health-Check-Endpoint |
| `SERVICE_APP_BASE_URL` | `https://www.staging.georanking.ch` | Öffentliche UI-Base-URL |
| `TRACE_DEBUG_ENABLED` | `true` | Trace-Debug im API aktivieren |
| `TRACE_DEBUG_LOOKBACK_SECONDS` | `86400` | Lookback-Fenster Trace-Debug |
| `TRACE_DEBUG_MAX_EVENTS` | `500` | Max. Events für Trace-Debug |
| `TRACE_DEBUG_CW_LOG_GROUP` | `/swisstopo/staging/ecs/api` | CloudWatch Log Group (API) |
| `TRACE_DEBUG_CW_LOG_STREAM_PREFIX` | `ecs/swisstopo-staging-api` | Log Stream Prefix (optional) |

> **Hinweis:** Alle 8 erforderlichen Variablen werden im Workflow via `validate_required_deploy_env.py` geprüft und führen zu `exit 1` bei Fehlen.

### 1.3 Erforderliche Secrets (Environment `staging`)

| Secret | Beschreibung |
|---|---|
| `SERVICE_API_AUTH_TOKEN` | Phase-1-Auth-Token für API-Smoketests (optional aber empfohlen) |

> Ohne `SERVICE_API_AUTH_TOKEN` laufen Analyze- und Async-Job-Smoketests im `::notice::`-Modus durch (kein Fehler, kein Nachweis).

---

## Phase 2 — AWS-Infra Mindestanforderungen

Die folgende Tabelle listet alle AWS-Komponenten, die vor dem ersten Staging-Deploy existieren müssen.  
Terraform-Basis: analog `infra/` (dev), neue `staging`-Varianten erstellen.

### 2.1 ECR Repositories

| Ressource | Name | Notizen |
|---|---|---|
| ECR Repo (API) | `swisstopo-staging-api` | `eu-central-1`; Lifecycle-Policy: 10 untagged Images |
| ECR Repo (UI) | `swisstopo-staging-ui` | `eu-central-1`; Lifecycle-Policy: 10 untagged Images |

### 2.2 VPC & Netzwerk

| Ressource | Beschreibung | Notizen |
|---|---|---|
| VPC | Staging-VPC oder getrennt von Dev | Empfohlen: eigene VPC; alternativ: isoliertes Subnet in Dev-VPC |
| Private Subnets (×2) | AZ-redundant | für ECS-Tasks (kein public IP) |
| Public Subnets (×2) | AZ-redundant | für ALB |
| Internet Gateway | für Public Subnets | |
| NAT Gateway (×1) | für Private-Subnet-Egress (swisstopo API etc.) | |
| Security Groups | API (8080 inbound vom ALB), UI (8080 inbound vom ALB), ALB (80/443 public) | |

### 2.3 IAM / OIDC

| Ressource | Beschreibung |
|---|---|
| OIDC Provider | `token.actions.githubusercontent.com` (bereits für Dev vorhanden — wiederverwendbar) |
| IAM Role | `swisstopo-staging-github-deploy-role` mit Trust-Policy auf `repo:nimeob/geo-ranking-ch:ref:refs/heads/main` |
| IAM Policy | `swisstopo-staging-github-deploy-policy` — analog `infra/iam/deploy-policy.json` aber auf Staging-Ressourcen scope begrenzen |

Pflicht-Permissions (analog Dev):
- `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `ecr:PutImage`, ...
- `ecs:RegisterTaskDefinition`, `ecs:UpdateService`, `ecs:DescribeServices`, `ecs:DescribeTaskDefinition`
- `iam:PassRole` auf ECS Task Execution Role (Staging)
- `secretsmanager:GetSecretValue` auf Staging-Secrets

### 2.4 ECS

| Ressource | Name | Notizen |
|---|---|---|
| ECS Cluster | `swisstopo-staging` | Fargate |
| Task Execution Role | `swisstopo-staging-ecs-execution-role` | AmazonECSTaskExecutionRolePolicy + SecretsManager-Zugriff |
| Task Role (API) | `swisstopo-staging-ecs-task-role` | CloudWatch Logs-Schreibrecht |
| Task Def (API) | Initial-TaskDef mit Platzhalter-Image | Minimalkonfiguration ausreichend; Workflow updated das Image |
| Task Def (UI) | Initial-TaskDef mit Platzhalter-Image | |
| ECS Service (API) | `swisstopo-staging-api` | Fargate, private Subnets, ALB-TG |
| ECS Service (UI) | `swisstopo-staging-ui` | Fargate, private Subnets, ALB-TG |

### 2.5 ALB (Application Load Balancer)

| Ressource | Beschreibung |
|---|---|
| ALB | `swisstopo-staging-alb` in Public Subnets |
| Listener HTTP (80) | Redirect to HTTPS |
| Listener HTTPS (443) | ACM-Zertifikat, Routing-Rules API/UI |
| Target Group (API) | Port 8080, Health `/health` |
| Target Group (UI) | Port 8080, Health `/healthz` |

Routing-Regel (Host-based):
- `api.staging.georanking.ch` → TG API
- `www.staging.georanking.ch` → TG UI

### 2.6 Auth / Cognito

| Ressource | Beschreibung |
|---|---|
| Cognito User Pool | `swisstopo-staging-users` (eigene Instanz) |
| App Client | für BFF-OIDC-Flow (mit PKCE) |
| Callback-URLs | `https://www.staging.georanking.ch/auth/callback` |
| Logout-URLs | `https://www.staging.georanking.ch` |
| Cognito Domain | `swisstopo-staging.auth.eu-central-1.amazoncognito.com` |
| ECS-Secrets | `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`, `COGNITO_ISSUER_URL` |

### 2.7 RDS (PostgreSQL)

| Ressource | Beschreibung |
|---|---|
| RDS Instance | `swisstopo-staging-postgres` (db.t3.micro genügt) |
| Engine | PostgreSQL 15+ |
| Subnet Group | Private Subnets Staging |
| Security Group | DB-SG: 5432 nur von ECS-SG (Staging) |
| Secrets Manager | `swisstopo-staging/db-password` |
| Migrations | `001_core_tables.sql`, `002_async_jobs_schema.sql`, `003_async_jobs_results.sql` via `scripts/db-migrate.py` |

### 2.8 DNS & TLS

| Ressource | Beschreibung |
|---|---|
| Route53 / Easyname | `api.staging.georanking.ch` → ALB-DNS |
| Route53 / Easyname | `www.staging.georanking.ch` → ALB-DNS |
| ACM Certificate | `*.staging.georanking.ch` oder `api.staging.georanking.ch` + `www.staging.georanking.ch` |

### 2.9 CloudWatch

| Ressource | Beschreibung |
|---|---|
| Log Group (API) | `/swisstopo/staging/ecs/api` mit Retention 30d |
| Log Group (UI) | `/swisstopo/staging/ecs/ui` mit Retention 30d |
| Alarm | `staging-api-running-taskcount-low` (analog Dev-Baseline aus BL-08) |

---

## Phase 3 — ECS Task Definitions initiale Konfiguration

Bevor der Workflow läuft, müssen beide Task-Definitions mit einer Minimalkonfiguration existieren (das Workflow-Script liest die aktuelle TaskDef, patcht das Image und registriert eine neue Revision).

Empfehlung: Initial-TaskDefs über Terraform-Modul erstellen (analog Dev in `infra/terraform/`).

Mindest-Env-Variablen in der API-TaskDef:

| Name | Wert |
|---|---|
| `PORT` | `8080` |
| `DB_HOST` | RDS Endpoint |
| `DB_PORT` | `5432` |
| `DB_NAME` | `geo_ranking` |
| `DB_USERNAME` | `swisstopo` |
| `DB_PASSWORD` | via SecretsManager `valueFrom` |
| `COGNITO_CLIENT_ID` | via SecretsManager `valueFrom` |
| `COGNITO_CLIENT_SECRET` | via SecretsManager `valueFrom` |
| `COGNITO_ISSUER_URL` | z. B. `https://cognito-idp.eu-central-1.amazonaws.com/<pool-id>` |
| `ASYNC_STORE_BACKEND` | `db` ← **setzt DB-Backend aktivieren** |
| `DATABASE_URL` | `postgresql://swisstopo:<pw>@<rds-endpoint>:5432/geo_ranking` |

> **Wichtig:** Im Unterschied zu Dev sollte Staging von Anfang an mit `ASYNC_STORE_BACKEND=db` laufen, um File-Store-Migration zu vermeiden.

---

## Phase 4 — Aktivierungsreihenfolge

```
1. AWS-Infra provisionen (ECR, VPC, IAM, ECS, ALB, Cognito, RDS, DNS, CW)
2. DNS und ACM-Zertifikat verifizieren (api.staging.georanking.ch + www.staging.georanking.ch)
3. Initial-TaskDefs via Terraform registrieren (API + UI)
4. DB-Migrations anwenden: DATABASE_URL=... python3 scripts/db-migrate.py --apply
5. GitHub Environment `staging` mit Vars/Secrets befüllen (Phase 1)
6. deploy-staging.yml manuell triggern:
   Actions → Deploy to AWS (ECS staging) → Run workflow → Branch: main
7. Post-Deploy-Checks (mindestens):
   - GET https://api.staging.georanking.ch/health → 200
   - GET https://www.staging.georanking.ch/healthz → 200
   - POST https://api.staging.georanking.ch/analyze + Bearer-Token → 200
8. Staging-Lite-Promote-Gate-Nachweis erstellen (optional):
   python3 scripts/run_staging_lite_promote_gate.py \
     --candidate-digest sha256:<digest> --approved-digest sha256:<digest> \
     --smoke-command "./scripts/run_remote_api_smoketest.sh" \
     --artifact-dir artifacts/staging-lite
```

---

## Phase 5 — Smoketest-Kriterien (Gate G1 erfüllt)

| Check | Erwartung |
|---|---|
| `GET /health` (API) | `{"ok": true}` HTTP 200 |
| `GET /healthz` (UI) | HTTP 200 |
| `GET /analyze/history` ohne Token | HTTP 401 |
| `POST /analyze` mit gültigem Bearer-Token | HTTP 200, `ok: true` |
| CloudWatch Logs `/swisstopo/staging/ecs/api` | Logs vorhanden, kein `ERROR`-Spam |
| RDS-Verbindung | DB-Connection im API-Log `connected` |

---

## Audit-Ergebnis: `deploy-staging.yml`

**Status: ✅ Vollständig, keine Lücken identifiziert.**

Der Workflow wurde am 2026-03-07 (Issue #1325) auditiert:

- Alle 8 erforderlichen Variablen werden via `validate_required_deploy_env.py` geprüft ✅
- API-Image Build + Push vollständig ✅
- UI-Image Build + Push vollständig ✅
- TaskDef-Patching (API + UI) vollständig ✅
- ECS-Deploy + Stability-Wait (API + UI getrennt) vollständig ✅
- Trace-Debug-Wiring-Verifikation nach Deploy ✅
- API Smoke `/health` verpflichtend ✅
- Analyze-Smoke + Async-Jobs-Smoke (optional, kein Fehler bei fehlendem Token) ✅
- UI Smoke `/healthz` verpflichtend ✅
- BL31 Strict Split Smoke (optional) ✅
- Post-Deploy Version+Trace-Verifikation ✅
- Deployment Summary ✅

**Einzige Ergänzung empfohlen:** nach erstem erfolgreichen Deploy ASYNC_STORE_BACKEND=db in TaskDef explizit setzen und dokumentieren (nicht im Workflow automatisiert — Betreiber-Entscheidung).

---

## Referenzen

- [`docs/ENV_PROMOTION_STRATEGY.md`](ENV_PROMOTION_STRATEGY.md) — Promotion-Strategie und Gates
- [`docs/DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md) — AWS-Deploy-Übersicht (Dev-Referenz)
- [`docs/testing/DEV_STAGE_CUTOVER_RUNBOOK.md`](testing/DEV_STAGE_CUTOVER_RUNBOOK.md) — Dev→Stage-Cutover-Runbook
- [`docs/testing/STAGING_LITE_PROMOTE_GATE.md`](testing/STAGING_LITE_PROMOTE_GATE.md) — Promote-Gate ohne vollständiges Staging
- [`infra/iam/README.md`](../infra/iam/README.md) — IAM-Deploy-Role (Dev, als Vorlage)
- [`infra/iam/deploy-policy.json`](../infra/iam/deploy-policy.json) — Policy-Vorlage (Dev)
