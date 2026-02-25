# IAM Least-Privilege Deploy-Role (BL-03)

Status: ✅ **Final abgeschlossen** (2026-02-25/26) — OIDC-Role live, Policy verifiziert, E2E nachgewiesen

Diese Artefakte dokumentieren die minimale IAM-Berechtigungsmenge für den GitHub-Actions-Deploy-Principal dieses Repos.

---

## Artefakte

| Datei | Inhalt |
|---|---|
| `deploy-policy.json` | Least-Privilege Permission-Policy (live als `swisstopo-dev-github-deploy-policy` v2) |
| `trust-policy.json` | Trust-Policy der OIDC-Deploy-Role (repo-scoped, `main`-only) |

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
| ECR Push | `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage` | nur Repo `swisstopo-dev-api` |
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

## Hinweise für Staging/Prod

Für `staging`/`prod` ist eine **eigene OIDC-Deploy-Role** mit scope auf den jeweiligen Branch/Umgebung anzulegen:

- Trust-Bedingung: `repo:nimeob/geo-ranking-ch:ref:refs/heads/staging` (bzw. `main` mit `environment:`-Gate)
- Separate Permission-Policy mit Scope auf `staging`/`prod`-Ressourcen
- Empfehlung: GitHub Environment-Protection-Rules als zusätzliches Gate (`environment: staging`)

Siehe [`docs/ENV_PROMOTION_STRATEGY.md`](../../docs/ENV_PROMOTION_STRATEGY.md) für den Promotion-Pfad.
