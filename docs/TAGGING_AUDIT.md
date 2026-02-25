# AWS Tagging Audit (BL-04)

Stand: 2026-02-25  
Scope: `dev`-Ressourcen in `eu-central-1`  
Account: `523234426229`

## Ziel-Tagging-Standard

| Key | Sollwert |
|---|---|
| `Environment` | `dev` |
| `ManagedBy` | `openclaw` |
| `Owner` | `nico` |
| `Project` | `swisstopo` |

## Inventar + Audit-Ergebnis

| Ressourcentyp | Ressource | Identifier | Tag-Status nach Audit | Aktion |
|---|---|---|---|---|
| ECS Cluster | `swisstopo-dev` | `arn:aws:ecs:eu-central-1:523234426229:cluster/swisstopo-dev` | ✅ alle 4 Standard-Tags vorhanden | keine Änderung nötig |
| ECS Service | `swisstopo-dev-api` | `arn:aws:ecs:eu-central-1:523234426229:service/swisstopo-dev/swisstopo-dev-api` | ✅ alle 4 Standard-Tags vorhanden | keine Änderung nötig |
| ECS Task Definition Family | `swisstopo-dev-api` (aktive Revisionen `:1`–`:10`) | z. B. `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:10` | ✅ alle 4 Standard-Tags auf allen aktiven Revisionen vorhanden | **fehlende Tags ergänzt** via `aws ecs tag-resource` auf Revisionen `:1`–`:10` |
| ECR Repository | `swisstopo-dev-api` | `arn:aws:ecr:eu-central-1:523234426229:repository/swisstopo-dev-api` | ✅ alle 4 Standard-Tags vorhanden | keine Änderung nötig |
| CloudWatch Log Group | `/swisstopo/dev/ecs/api` | `arn:aws:logs:eu-central-1:523234426229:log-group:/swisstopo/dev/ecs/api:*` | ✅ alle 4 Standard-Tags vorhanden | keine Änderung nötig |
| CloudWatch Log Group | `/swisstopo/dev/app` | `arn:aws:logs:eu-central-1:523234426229:log-group:/swisstopo/dev/app:*` | ✅ alle 4 Standard-Tags vorhanden | keine Änderung nötig |

## Durchgeführte Änderungen

- Nicht-destruktive Tagging-Ergänzung auf ECS Task Definitions der Family `swisstopo-dev-api`:
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:1`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:2`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:3`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:4`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:5`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:6`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:7`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:8`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:9`
  - `arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:10`

Verwendete Keys: nur `Environment`, `ManagedBy`, `Owner`, `Project`.

## Verifikation (nach Umsetzung)

Für alle oben gelisteten Ressourcen gilt:
- Fehlende Keys (`Environment`, `ManagedBy`, `Owner`, `Project`) = `[]`
- Keine Lösch-/Replace-Operationen durchgeführt.
