# Operations — geo-ranking-ch

Arbeitsmodus, Branching-Strategie, Commit-Regeln und Release-Checkliste.

> **Umgebungen:** Aktuell existiert ausschließlich eine **`dev`-Umgebung** auf AWS. `staging` und `prod` sind noch nicht aufgebaut. Alle Deploy-Schritte in dieser Dokumentation beziehen sich auf `dev`, sofern nicht anders angegeben.

> **AWS-Naming:** AWS-Ressourcen heißen intern `swisstopo` (z. B. Cluster `swisstopo-dev`). Das ist so gewollt — der Repo-Name `geo-ranking-ch` und das interne AWS-Naming divergieren bewusst.

> **Offene Umsetzungs-/Operations-Themen:** zentral in [`docs/BACKLOG.md`](BACKLOG.md) pflegen (hier keine separaten TODO-Listen).

> **Sicherheits-/Datenhaltungsentscheidungen für API-Betrieb:** siehe [`docs/DATA_AND_API_SECURITY.md`](DATA_AND_API_SECURITY.md).

---

## Branching-Strategie

Dieses Projekt verwendet **Trunk-Based Development** mit kurzlebigen Feature-Branches.

```
main          ──●──●──●──●──●──▶  (immer deploybar)
                 ↑  ↑
feature/xyz ──●──┘  │
fix/abc     ──●──●──┘
```

| Branch-Typ | Namensschema | Lebensdauer |
|---|---|---|
| Feature | `feature/<kurze-beschreibung>` | bis Merge, max. 3 Tage |
| Bugfix | `fix/<kurze-beschreibung>` | bis Merge |
| Hotfix | `hotfix/<issue-id>` | sofort mergen |
| Release | `release/v<x.y.z>` | bis Tag + Merge, dann löschen |

**Regeln:**
- `main` ist immer deploybar
- Keine direkten Commits auf `main` (außer kleinen Doku-Änderungen)
- Feature-Branches werden via Pull Request gemergt
- Branches nach dem Merge löschen

---

## Commit-Konventionen

Dieses Projekt folgt [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<typ>(<scope>): <beschreibung>

[optionaler body]

[optionaler footer: BREAKING CHANGE / Closes #issue]
```

### Typen

| Typ | Bedeutung |
|---|---|
| `feat` | Neue Funktionalität |
| `fix` | Bugfix |
| `docs` | Nur Doku-Änderungen |
| `style` | Formatierung, kein Logik-Einfluss |
| `refactor` | Refactoring ohne Funktionsänderung |
| `test` | Tests hinzufügen oder korrigieren |
| `chore` | Build, Dependencies, CI, Konfiguration |
| `perf` | Performance-Verbesserung |
| `ci` | CI/CD-Konfiguration |
| `infra` | Infrastruktur / IaC |

### Beispiele

```bash
feat(ranking): add municipality score calculation
fix(ingest): handle missing coordinates in BFS data
docs(deployment): update AWS runbook with ECS details
chore(deps): upgrade boto3 to 1.35.0
infra(ecs): add Fargate task definition for api service
```

---

## Pull-Request-Regeln

### Checkliste vor dem Öffnen eines PRs

- [ ] Branch ist aktuell mit `main` (`git rebase main` oder `git merge main`)
- [ ] Alle Tests lokal grün
- [ ] Keine Secrets / Credentials im Code
- [ ] Commit-Messages folgen Conventional Commits
- [ ] `CHANGELOG.md` aktualisiert (bei Features/Bugfixes)
- [ ] Doku aktualisiert (falls API oder Architektur sich ändert)

### PR-Beschreibung

```markdown
## Was ändert sich?
<kurze Beschreibung>

## Warum?
<Motivation / verknüpftes Issue>

## Wie testen?
<Schritte zum Testen>

## Checkliste
- [ ] Tests
- [ ] Docs
- [ ] Kein Breaking Change / Breaking Change dokumentiert
```

### Review

- Mindestens **1 Approval** vor dem Merge
- CI muss grün sein
- Squash-Merge bevorzugt für saubere `main`-History

---

## Release-Prozess

### Semantic Versioning

Das Projekt folgt [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

| Änderung | Version |
|---|---|
| Breaking Changes | MAJOR |
| Neue Funktionen (rückwärtskompatibel) | MINOR |
| Bugfixes | PATCH |

### Release-Checkliste

```bash
# 1. Release-Branch erstellen
git checkout -b release/v<x.y.z>

# 2. Version bumpen (falls vorhanden)
# vim pyproject.toml / package.json / version.py

# 3. CHANGELOG.md aktualisieren
#    - Abschnitt für neue Version anlegen
#    - Datum eintragen
#    - Änderungen aus Commits zusammenfassen

# 4. Commit
git commit -am "chore(release): prepare v<x.y.z>"

# 5. PR auf main öffnen und mergen

# 6. Tag setzen
git checkout main && git pull
git tag -a v<x.y.z> -m "Release v<x.y.z>"
git push origin v<x.y.z>

# 7. GitHub Release erstellen (optional)
#    → GitHub UI: Releases → Draft new release → Tag auswählen
```

### Post-Release

- [ ] Deployment in `dev` ausgelöst (via Tag-triggered CI oder manuell)
- [ ] Smoke-Test in `dev` durchgeführt
- [ ] _(prod/staging: noch nicht vorhanden — entfällt aktuell)_
- [ ] Release-Branch gelöscht
- [ ] Team informiert (falls relevant)

---

## Agent-Autopilot (Nipa)

Der verbindliche Arbeitsmodus für autonome Weiterarbeit ist in [`docs/AUTONOMOUS_AGENT_MODE.md`](AUTONOMOUS_AGENT_MODE.md) dokumentiert.

Kurzfassung:
- GitHub-Operationen über GitHub App Wrapper (`scripts/gha`, `scripts/gpush`), nicht über User-Login.
- Komplexe Aufgaben via Subagents mit `openai-codex/gpt-5.3-codex` und `thinking=high`.
- Parallelisierung nutzen, wenn Aufgaben unabhängig sind.

## Lokale Entwicklung

### Setup

```bash
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

# Verbindliche lokale Baseline: Python 3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Hooks für Format/Lint aktivieren
pre-commit install

# Lokale Checks
pytest tests/ -v
pre-commit run --all-files
```

### Empfohlene Tools

| Tool | Zweck | Pflicht |
|---|---|---|
| `pre-commit` | Linting/Formatierung vor Commit | empfohlen |
| `black` / `ruff` | Python-Formatierung/Linting (via pre-commit) | empfohlen |
| `pytest` | Tests | ja |
| `docker` | Lokale Container-Tests | empfohlen |
| `aws-vault` | Sichere AWS-Credential-Verwaltung | empfohlen |

---

## Monitoring & Alerting (ECS `dev` MVP)

Die folgenden Standards sind absichtlich minimal gehalten und passen zum aktuellen Ist-Stand:
- ein ECS-Service (`swisstopo-dev-api`) in Cluster `swisstopo-dev`
- CloudWatch Logs vorhanden/konfigurierbar
- keine riskanten Änderungen am Live-Setup ohne Incident-Bedarf

### 1) CloudWatch Logs Standard (Log Group + Retention)

**Log-Group-Namensschema (Standard):**
- projektspezifisch: `/swisstopo/<env>/ecs/<service>`
- Für den aktuellen Service: `/swisstopo/dev/ecs/api`

**Retention-Standard:**
- `dev`: **30 Tage**
- `staging`/`prod` (später): mindestens 30–90 Tage je nach Compliance-Bedarf

**Checks/Kommandos:**

```bash
export AWS_REGION=eu-central-1
export ECS_CLUSTER=swisstopo-dev
export ECS_SERVICE=swisstopo-dev-api
export LOG_GROUP=/swisstopo/dev/ecs/api

# Log Group prüfen
aws logs describe-log-groups   --region "$AWS_REGION"   --log-group-name-prefix "$LOG_GROUP"   --query 'logGroups[].{name:logGroupName,retention:retentionInDays,storedBytes:storedBytes}'

# Falls nötig: Retention auf 30 Tage setzen
aws logs put-retention-policy   --region "$AWS_REGION"   --log-group-name "$LOG_GROUP"   --retention-in-days 30
```

### 2) Minimale Alarme (MVP)

> Ziel: Frühe Erkennung von „Service unhealthy“ und „Deployment hängt/fehlschlägt" ohne komplexes Observability-Setup.

#### Alarm A — Service unhealthy (RunningTaskCount < 1)

Für den aktuellen MVP mit Desired Count = 1:

```bash
aws cloudwatch put-metric-alarm   --region "$AWS_REGION"   --alarm-name "swisstopo-dev-api-running-taskcount-low"   --alarm-description "ECS service unhealthy: running tasks < 1"   --namespace AWS/ECS   --metric-name RunningTaskCount   --dimensions Name=ClusterName,Value=swisstopo-dev Name=ServiceName,Value=swisstopo-dev-api   --statistic Minimum   --period 60   --evaluation-periods 3   --datapoints-to-alarm 3   --threshold 1   --comparison-operator LessThanThreshold   --treat-missing-data breaching
```

#### Alarm B — Deployment Failure Indicator (PendingTaskCount > 0 für längere Zeit)

Detektiert typische Fälle, in denen neue Tasks nicht sauber starten (Image Pull, Healthcheck-Fail, Capacity-Probleme):

```bash
aws cloudwatch put-metric-alarm   --region "$AWS_REGION"   --alarm-name "swisstopo-dev-api-pending-taskcount-stuck"   --alarm-description "Deployment likely stuck/failing: pending tasks > 0"   --namespace AWS/ECS   --metric-name PendingTaskCount   --dimensions Name=ClusterName,Value=swisstopo-dev Name=ServiceName,Value=swisstopo-dev-api   --statistic Maximum   --period 60   --evaluation-periods 15   --datapoints-to-alarm 10   --threshold 0   --comparison-operator GreaterThanThreshold   --treat-missing-data notBreaching
```

> Sobald Autoscaling >1 eingeführt wird, Alarm A auf „RunningTaskCount < DesiredTaskCount" (Metric Math) umstellen.

### 3) HTTP Health Check Guidance

- Der Deploy-Workflow nutzt bereits optional `SERVICE_HEALTH_URL` für Smoke-Tests.
- Für Monitoring zusätzlich eine externe Probe (z. B. UptimeRobot, Better Stack oder CloudWatch Synthetics) auf `GET /health` einrichten.
- Interner Minimal-Check via CLI:

```bash
# Erwartet HTTP 200 und optional JSON-Status
curl -fsS "$SERVICE_HEALTH_URL"
```

- Wenn ein ALB eingesetzt wird: zusätzlich CloudWatch-Alarm auf `AWS/ApplicationELB -> UnHealthyHostCount > 0` für das Target Group/Load Balancer Paar ergänzen.

---

## Incident-Prozess (Runbook mit AWS CLI)

1. **Erkennen:** CloudWatch Alarm oder User-Report
2. **Triagieren:** Impact und Scope bestimmen
3. **Mitigieren:** Quick-Fix (Redeploy/Rollback)
4. **Kommunizieren:** Status intern dokumentieren
5. **Nachbereitung:** Ursache + Follow-ups festhalten

### 0) Vorbereitende Variablen

```bash
export AWS_REGION=eu-central-1
export ECS_CLUSTER=swisstopo-dev
export ECS_SERVICE=swisstopo-dev-api
export LOG_GROUP=/swisstopo/dev/ecs/api
```

### 1) Service-Schnellcheck

```bash
# Kurzstatus (desired/running/pending + rollout)
aws ecs describe-services   --region "$AWS_REGION"   --cluster "$ECS_CLUSTER"   --services "$ECS_SERVICE"   --query 'services[0].{status:status,desired:desiredCount,running:runningCount,pending:pendingCount,taskDef:taskDefinition,rollout:deployments[0].rolloutState,rolloutReason:deployments[0].rolloutStateReason}'

# Letzte Service-Events
aws ecs describe-services   --region "$AWS_REGION"   --cluster "$ECS_CLUSTER"   --services "$ECS_SERVICE"   --query 'services[0].events[0:15].[createdAt,message]'
```

Alternativ (Helper-Script):

```bash
./scripts/check_ecs_service.sh
```

### 2) Laufende Tasks und Exit-Codes prüfen

```bash
TASK_ARNS=$(aws ecs list-tasks   --region "$AWS_REGION"   --cluster "$ECS_CLUSTER"   --service-name "$ECS_SERVICE"   --query 'taskArns'   --output text)

aws ecs describe-tasks   --region "$AWS_REGION"   --cluster "$ECS_CLUSTER"   --tasks $TASK_ARNS   --query 'tasks[].{task:taskArn,last:lastStatus,health:healthStatus,stoppedReason:stoppedReason,containers:containers[].{name:name,last:lastStatus,exit:exitCode,reason:reason}}'
```

### 3) Logs live verfolgen

```bash
# letzte 30 Minuten + Follow
aws logs tail "$LOG_GROUP" --region "$AWS_REGION" --since 30m --follow
```

Alternativ (Helper-Script):

```bash
./scripts/tail_logs.sh
```

### 4) HTTP-Health manuell verifizieren

```bash
curl -i "$SERVICE_HEALTH_URL"
```

### 5) Mitigation

```bash
# A) Neuer Rollout derselben Task-Definition
aws ecs update-service   --region "$AWS_REGION"   --cluster "$ECS_CLUSTER"   --service "$ECS_SERVICE"   --force-new-deployment

# B) Falls weiterhin fehlerhaft: Rollback auf vorherige Revision
# siehe DEPLOYMENT_AWS.md Abschnitt "Rollback-Prozedur"
```

Rollback-Prozedur: siehe [`DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md#5-rollback-prozedur)
