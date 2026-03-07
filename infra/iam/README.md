# IAM Least-Privilege Deploy-Role (BL-03)

Status: ✅ **Dev: Final abgeschlossen** (2026-02-25/26) — OIDC-Role live, Policy verifiziert, E2E nachgewiesen  
Status: 📝 **Staging: Policy-Artefakte bereit** (2026-03-07, Issue #1326) — JSON-Templates committed; AWS-Anlage ausstehend (siehe `docs/staging-environment-setup.md`)

Diese Artefakte dokumentieren die minimale IAM-Berechtigungsmenge für den GitHub-Actions-Deploy-Principal dieses Repos — für Dev (aktiv) und Staging (bereit zum Anlegen).

---

## Artefakte

| Datei | Umgebung | Inhalt |
|---|---|---|
| `deploy-policy.json` | **Dev** (live) | Least-Privilege Permission-Policy (live als `swisstopo-dev-github-deploy-policy` v2) |
| `trust-policy.json` | **Dev** (live) | Trust-Policy der OIDC-Deploy-Role (repo-scoped, `main`-only) |
| `staging-deploy-policy.json` | **Staging** (bereit) | Permission-Policy für Staging-Deploy-Role (analog Dev, Staging-Ressourcen) |
| `staging-trust-policy.json` | **Staging** (bereit) | Trust-Policy für Staging-Deploy-Role (GitHub-Environment-scoped) |

---

## Scope

Aktueller Workflow-Flow (dev, `.github/workflows/deploy.yml`):

1. GitHub OIDC Token → `sts:AssumeRoleWithWebIdentity` → `swisstopo-dev-github-deploy-role`
2. ECR Login
3. Docker Image bauen + nach ECR pushen
4. ECS Service lesen (aktuelle Task Definition)
5. Neue Task-Definition registrieren
6. ECS Service auf neue Task-Definition umstellen
7. Auf `services-stable` warten (nutzt `DescribeServices`)

## Abgeleitete Minimalrechte

Datei: `infra/iam/deploy-policy.json`

| Workflow-Schritt | Erforderliche Actions | Scope |
|---|---|---|
| Identity-Check (optional) | `sts:GetCallerIdentity` | `*` |
| ECR Login | `ecr:GetAuthorizationToken` | `*` |
| ECR Push | `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage` | nur Repos `swisstopo-dev-api` + `swisstopo-dev-ui` |
| ECS Read | `ecs:DescribeServices` | nur dev Cluster + Service |
| ECS Read | `ecs:DescribeTaskDefinition` | `*` (AWS wertet ARN/Family-Scoping nicht aus — Policy v1→v2 Fix) |
| ECS Register TaskDef | `ecs:RegisterTaskDefinition` | `*` (AWS-seitig nicht enger scoping-fähig) |
| ECS Rollout | `ecs:UpdateService` | nur dev Service/Cluster |
| PassRole für TaskDef | `iam:PassRole` | nur `swisstopo-dev-ecs-execution-role` + `swisstopo-dev-ecs-task-role` (Condition auf `ecs-tasks.amazonaws.com`) |

---

## Nachweis: Ist-Stand AWS (verifiziert 2026-02-25)

### OIDC Identity Provider

```
arn:aws:iam::523234426229:oidc-provider/token.actions.githubusercontent.com
```

### Deploy-Role

| Attribut | Wert |
|---|---|
| Role ARN | `arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role` |
| Erstellt | 2026-02-25T21:26:33 UTC |
| Zuletzt genutzt | 2026-02-25T23:05:29 UTC (eu-central-1) |
| Trust | `repo:nimeob/geo-ranking-ch:ref:refs/heads/main` — `main`-Branch only |
| Attached Policy | `swisstopo-dev-github-deploy-policy` (v2, Defaultversion) |

Trust-Policy liegt versioniert als `infra/iam/trust-policy.json`.

### Permission-Policy

```
arn:aws:iam::523234426229:policy/swisstopo-dev-github-deploy-policy
```

- Aktive Version: `v2` (Default)
- Inhalt: identisch mit `infra/iam/deploy-policy.json`
- Keine Inline Policies an der Rolle

### E2E-Nachweis

| Run | Trigger | Ergebnis |
|---|---|---|
| [`22417749775`](https://github.com/nimeob/geo-ranking-ch/actions/runs/22417749775) | `workflow_dispatch` | ✅ IAM-Fix validiert, `services-stable` + Smoke-Test |
| [`22417939827`](https://github.com/nimeob/geo-ranking-ch/actions/runs/22417939827) | `push` auf `main` | ✅ OIDC E2E, `services-stable` + Smoke-Test |

---

## Umsetzungshistorie (erledigt)

Die ursprüngliche Migrationsreihenfolge (1. Policy parallel anhängen → 2. Test per `workflow_dispatch` → 3. Alt-Policy entfernen → 4. Auf OIDC-Role umstellen) wurde vollständig durchgeführt:

- IAM-User `swisstopo-api-deploy` ist **nicht** mehr der Deploy-Principal für CI/CD
- GitHub Actions nutzt ausschließlich OIDC (`role-to-assume` in `aws-actions/configure-aws-credentials@v4`)
- Keine statischen AWS Access Keys in GitHub Secrets erforderlich

---

## Staging-IAM-Ressourcen (bereit zum Anlegen)

Die folgenden Artefakte sind committed und können direkt für `aws iam create-role` / `aws iam create-policy` verwendet werden.

### staging-trust-policy.json

Trust-Bedingung: **GitHub-Environment-scoped** (`environment:staging` statt Branch-only).  
Dies erfordert, dass das GitHub-Environment `staging` konfiguriert ist (Protection Rules optional aber empfohlen).

```
sub: repo:nimeob/geo-ranking-ch:environment:staging
```

> **Unterschied zu Dev:** Dev nutzt `ref:refs/heads/main` (Branch-only).  
> Staging nutzt `environment:staging` — damit greifen GitHub-Environment-Protection-Rules als zusätzliches Gate.

### staging-deploy-policy.json

Analog `deploy-policy.json`, aber auf Staging-Ressourcen eingeschränkt:

| Workflow-Schritt | Erforderliche Actions | Scope |
|---|---|---|
| Identity-Check | `sts:GetCallerIdentity` | `*` |
| ECR Login | `ecr:GetAuthorizationToken` | `*` |
| ECR Push | `ecr:Batch*/Complete*/Initiate*/Put*/Upload*` | nur `swisstopo-staging-api` + `swisstopo-staging-ui` |
| ECS Read | `ecs:DescribeServices` | nur Staging-Cluster + Services |
| ECS Read | `ecs:DescribeTaskDefinition` | `*` (AWS-seitig nicht enger scopeable) |
| ECS Register | `ecs:RegisterTaskDefinition` | `*` (AWS-seitig nicht enger scopeable) |
| ECS Rollout | `ecs:UpdateService` | nur Staging-Cluster + Services |
| PassRole | `iam:PassRole` | nur `swisstopo-staging-ecs-execution-role` + `swisstopo-staging-ecs-task-role` |
| Secrets (DB/OIDC) | `secretsmanager:GetSecretValue` | nur `/swisstopo/staging/*` |
| CloudWatch (Trace-Debug) | `logs:FilterLogEvents`, `logs:GetLogEvents`, `logs:Describe*` | nur `/swisstopo/staging/*` Log Groups |

### AWS-Anlage-Runbook (Kurzfassung)

```bash
# 1. Policy anlegen
aws iam create-policy \
  --policy-name swisstopo-staging-github-deploy-policy \
  --policy-document file://infra/iam/staging-deploy-policy.json

# 2. Role anlegen
aws iam create-role \
  --role-name swisstopo-staging-github-deploy-role \
  --assume-role-policy-document file://infra/iam/staging-trust-policy.json

# 3. Policy anhängen
aws iam attach-role-policy \
  --role-name swisstopo-staging-github-deploy-role \
  --policy-arn arn:aws:iam::523234426229:policy/swisstopo-staging-github-deploy-policy
```

Vollständige Staging-Prerequisites: [`docs/staging-environment-setup.md`](../../docs/staging-environment-setup.md)  
Promotion-Strategie: [`docs/ENV_PROMOTION_STRATEGY.md`](../../docs/ENV_PROMOTION_STRATEGY.md)
