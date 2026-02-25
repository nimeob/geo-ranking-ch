# IAM Least-Privilege Vorarbeit (BL-03)

Status: **Vorbereitung abgeschlossen** (noch **nicht** auf produktive Secrets umgestellt)

Diese Artefakte leiten aus dem aktuellen GitHub-Deploy-Workflow (`.github/workflows/deploy.yml`) eine minimale IAM-Berechtigungsmenge für den Deploy-Principal ab.

## Scope

Aktueller Workflow-Flow (dev):

1. AWS Credentials laden (Access Key / Secret)
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
| ECS Read | `ecs:DescribeServices`, `ecs:DescribeTaskDefinition` | nur dev Cluster/Service + TaskDef-Family |
| ECS Register TaskDef | `ecs:RegisterTaskDefinition` | `*` (AWS-seitig nicht enger scoping-fähig) |
| ECS Rollout | `ecs:UpdateService` | nur dev Service/Cluster |
| PassRole für TaskDef | `iam:PassRole` | nur `swisstopo-dev-ecs-execution-role` + `swisstopo-dev-ecs-task-role` (Condition auf `ecs-tasks.amazonaws.com`) |

## Read-only Bestandscheck (`swisstopo-api-deploy`)

Durchgeführt mit vorhandenen Credentials (nur read-only Aufrufe):

- ✅ `sts:GetCallerIdentity` bestätigt Principal:
  - `arn:aws:iam::523234426229:user/swisstopo-api-deploy`
- ✅ ECS/ECR Read-Aufrufe funktionieren (u. a. `DescribeServices`, `DescribeTaskDefinition`, `DescribeRepositories`)
- ⚠️ IAM-Introspection ist **nicht** erlaubt (`iam:GetUser`, `iam:ListAttachedUserPolicies`, `iam:ListUserPolicies` → `AccessDenied`)

### Grobe Rechte-Drift (nur indirekt bewertbar)

Direkte Policy-Drift kann ohne IAM-List-Rechte nicht sicher verifiziert werden.
Indirekter Hinweis auf potenziell breitere Leserechte: folgende zusätzlichen Read-APIs sind erlaubt, obwohl sie im Deploy-Workflow nicht benötigt werden:

- `s3api list-buckets`
- `cloudformation list-stacks`
- `lambda list-functions`

=> Empfehlung: Vor produktiver Umschaltung einmalig mit Admin-Rechten die aktuell angehängten Policies auslesen und gegen `deploy-policy.json` diffen.

## Sichere Umsetzungsreihenfolge (ohne Breaking Change)

1. Policy als neue managed policy anlegen (noch nicht exklusiv umschalten).
2. Testweise **zusätzlich** an Deploy-User hängen.
3. Manuellen `workflow_dispatch` Deploy ausführen.
4. CloudTrail/Workflow auf `AccessDenied` prüfen und Policy ggf. feinjustieren.
5. Erst danach Alt-Policy entfernen und GitHub-Secrets final auf den neuen Principal standardisieren (oder OIDC-Rolle einführen).

Wichtig: Diese Vorarbeit ändert **keine** laufenden Secrets oder aktive Pipeline-Konfiguration.
