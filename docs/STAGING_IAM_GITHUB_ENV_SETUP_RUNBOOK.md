# Runbook: Staging IAM Deploy Role + GitHub Environment Setup

Stand: 2026-03-07  
Quelle: Issue [#1332](https://github.com/nimeob/geo-ranking-ch/issues/1332)  
Voraussetzung: IAM-Artefakte aus [#1326](https://github.com/nimeob/geo-ranking-ch/issues/1326) sind im Repo vorhanden.

Ziel
- AWS IAM Role **`swisstopo-staging-github-deploy-role`** anlegen (OIDC Trust + Least-Privilege Permissions)
- GitHub Environment **`staging`** (Vars/Secrets) so konfigurieren, dass `.github/workflows/deploy-staging.yml` lauffähig ist

Referenzen
- Prerequisites/Variablen-Liste: [`docs/staging-environment-setup.md`](staging-environment-setup.md)
- IAM JSON Templates: [`infra/iam/staging-trust-policy.json`](../infra/iam/staging-trust-policy.json), [`infra/iam/staging-deploy-policy.json`](../infra/iam/staging-deploy-policy.json)
- Deploy Workflow: [`.github/workflows/deploy-staging.yml`](../.github/workflows/deploy-staging.yml)

---

## Phase 1 — IAM Role anlegen (AWS CLI)

### 1.0 Preflight

- AWS CLI ist konfiguriert (Credentials mit IAM Schreibrechten für `iam:*` auf Role/Policy Scope)
- Region ist gesetzt (für STS nicht kritisch, aber konsistent halten):

```bash
export AWS_REGION=eu-central-1
```

- Du befindest dich im Repo-Root (damit `infra/iam/*` Pfade stimmen)

### 1.1 Role erstellen (create-role)

```bash
aws iam create-role \
  --role-name swisstopo-staging-github-deploy-role \
  --assume-role-policy-document file://infra/iam/staging-trust-policy.json \
  --description "GitHub Actions OIDC deploy role for swisstopo staging" \
  --max-session-duration 3600
```

Falls die Rolle bereits existiert, stattdessen Trust Policy aktualisieren:

```bash
aws iam update-assume-role-policy \
  --role-name swisstopo-staging-github-deploy-role \
  --policy-document file://infra/iam/staging-trust-policy.json
```

### 1.2 Inline Permission Policy setzen (put-role-policy)

> Diese Runbook-Variante nutzt bewusst eine **Inline Policy** (einfacher Operator-Flow).  
> Alternativ kann die JSON auch als Managed Policy erstellt und attached werden.

```bash
aws iam put-role-policy \
  --role-name swisstopo-staging-github-deploy-role \
  --policy-name swisstopo-staging-github-deploy-policy \
  --policy-document file://infra/iam/staging-deploy-policy.json
```

### 1.3 Tags setzen (tag-role)

```bash
aws iam tag-role \
  --role-name swisstopo-staging-github-deploy-role \
  --tags \
    Key=Project,Value=swisstopo \
    Key=Environment,Value=staging \
    Key=ManagedBy,Value=openclaw
```

### 1.4 Quick sanity check

```bash
aws iam get-role --role-name swisstopo-staging-github-deploy-role --query 'Role.Arn' --output text
```

Erwartung: Ausgabe wie `arn:aws:iam::<ACCOUNT_ID>:role/swisstopo-staging-github-deploy-role`

---

## Phase 2 — GitHub Environment `staging` konfigurieren

### 2.1 Environment anlegen

GitHub → Repo → **Settings** → **Environments** → **New environment** → Name: `staging`

(Optional) Protection Rules setzen (required reviewers, deployment branches).  
Hinweis: Trust-Policy ist environment-scoped (siehe `staging-trust-policy.json`).

### 2.2 Pflicht-Variables (Environment `staging`)

Diese 8 Variablen sind im Deploy-Workflow **hard-required** (siehe Step "Validate required repo/environment variables" in `deploy-staging.yml`).

| Variable | Beispielwert | Quelle |
|---|---|---|
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::<ACCOUNT_ID>:role/swisstopo-staging-github-deploy-role` | Phase 1.4 |
| `ECS_CLUSTER` | `swisstopo-staging` | Terraform/Infra |
| `ECS_API_SERVICE` | `swisstopo-staging-api` | Terraform/Infra |
| `ECS_UI_SERVICE` | `swisstopo-staging-ui` | Terraform/Infra |
| `ECS_API_CONTAINER_NAME` | `swisstopo-staging-api` | TaskDef API |
| `ECS_UI_CONTAINER_NAME` | `swisstopo-staging-ui` | TaskDef UI |
| `ECR_API_REPOSITORY` | `swisstopo-staging-api` | ECR |
| `ECR_UI_REPOSITORY` | `swisstopo-staging-ui` | ECR |

> Die vollständige (erweiterte) Variablenliste inkl. URLs/Trace-Flags ist in [`docs/staging-environment-setup.md`](staging-environment-setup.md) dokumentiert.

### 2.3 Secrets (Environment `staging`)

Optional aber empfohlen (für API Smoketests / Analyze-Flows):

| Secret | Beschreibung |
|---|---|
| `SERVICE_API_AUTH_TOKEN` | Bearer Token für Smoketests gegen geschützte Endpunkte |

---

## Phase 3 — Smoke-Verifikation

### 3.1 AWS Assume Role funktioniert (über GitHub Actions)

1. GitHub → **Actions** → "Deploy to AWS (ECS staging)" → **Run workflow**
2. Erwartung im Log (Step "Configure AWS credentials (OIDC)"):
   - erfolgreicher OIDC AssumeRole
3. Erwartung im Log (Step "Build and push API/UI images"):
   - `aws sts get-caller-identity` funktioniert

Wenn der AssumeRole fehlschlägt:
- Trust Policy prüfen (`infra/iam/staging-trust-policy.json`)
- GitHub Environment Name exakt `staging`
- `AWS_ROLE_TO_ASSUME` ARN korrekt

### 3.2 Dry-run / No-op Validation

Wenn du nur die Preconditions prüfen willst, ohne echte Deploy-Änderungen:
- Workflow starten und nach den Preflight-Steps abbrechen (UI "Cancel workflow")

---

## Rollback / Cleanup

- Inline Policy entfernen:

```bash
aws iam delete-role-policy \
  --role-name swisstopo-staging-github-deploy-role \
  --policy-name swisstopo-staging-github-deploy-policy
```

- Role löschen:

```bash
aws iam delete-role --role-name swisstopo-staging-github-deploy-role
```

- GitHub Environment Vars/Secrets entfernen:
  - Settings → Environments → staging → Variables/Secrets löschen oder Environment komplett entfernen
