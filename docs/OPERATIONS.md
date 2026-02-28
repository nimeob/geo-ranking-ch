# Operations — geo-ranking-ch

Arbeitsmodus, Branching-Strategie, Commit-Regeln und Release-Checkliste.

> **Umgebungen:** Aktuell existiert ausschließlich eine **`dev`-Umgebung** auf AWS. `staging` und `prod` sind noch nicht aufgebaut. Alle Deploy-Schritte in dieser Dokumentation beziehen sich auf `dev`, sofern nicht anders angegeben.

> **AWS-Naming:** AWS-Ressourcen heißen intern `swisstopo` (z. B. Cluster `swisstopo-dev`). Das ist so gewollt — der Repo-Name `geo-ranking-ch` und das interne AWS-Naming divergieren bewusst.

> **Offene Umsetzungs-/Operations-Themen:** zentral in [`docs/BACKLOG.md`](BACKLOG.md) pflegen (hier keine separaten Nebenlisten).
>
> **Automation-Migration (GitHub Actions → OpenClaw):** Ist-Aufnahme + Klassifikation siehe [`docs/automation/github-actions-migration-matrix.md`](automation/github-actions-migration-matrix.md), konkretes Job-Mapping v1 in [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md).

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

Für API-only Releases zuerst die Packaging-Baseline-Checks ausführen: [`docs/PACKAGING_BASELINE.md`](./PACKAGING_BASELINE.md#basis-release-checkliste-api-only-packaging).

Zusatz für BL-20.1.k-Migration (code-first + Dictionary):
- [ ] Consumer-Status für `options.include_labels=true` dokumentiert (wer nutzt den Legacy-Pfad noch?)
- [ ] Release Notes enthalten expliziten Migrationshinweis auf Dictionary-Endpoints (`/api/v1/dictionaries*`)
- [ ] Sunset-Fortschritt im Backlog/Issue-Tracking nachgeführt (kein stilles Dauer-Feature)

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

### BL-31 Betriebsregel: getrennte UI/API-Rollouts

Sobald der UI-Service (`swisstopo-dev-ui`) live ist, gelten zusätzlich:

1. **Service-getrennte Changesets:** API- und UI-Deployments als unabhängige Artefakte behandeln.
2. **Reihenfolge bei kombinierten Releases:** API → API-Smoke → UI → UI-Smoke.
3. **Rollback nur service-lokal:** bei UI-Problemen kein automatischer API-Rollback (und umgekehrt).
4. **Runbook-Evidenz pro Service:** Deploy-/Rollback-Nachweis getrennt dokumentieren (Issue/PR-Kommentar + Artefakte).

Verbindlicher Ablauf + Kommandos + Kommentar-Template:
- [`docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md`](BL31_DEPLOY_ROLLBACK_RUNBOOK.md)

Für BL-31.6.a (UI-Artefaktpfad + Taskdef-Revision) steht zusätzlich ein automatisierter Setup-Pfad bereit:

```bash
./scripts/setup_bl31_ui_artifact_path.sh
```

Der Lauf erzeugt eine JSON-Evidenz unter `artifacts/bl31/*-bl31-ui-artifact-path.json` (CodeBuild-Run, Image-URI/Digest, Taskdef-ARN).

Für BL-31.6.b (ECS-Rollout + Stabilisierung) ist der service-lokale Rolloutpfad automatisiert:

```bash
TARGET_TASKDEF=swisstopo-dev-ui:<revision> ./scripts/setup_bl31_ui_service_rollout.sh
```

Der Check verifiziert nach dem Rollout sowohl UI (`/healthz`) als auch API (`/health`) und schreibt die Evidenz nach `artifacts/bl31/*-bl31-ui-ecs-rollout.json`.

Für BL-31.6.c (kombinierter App/API/Monitoring-Nachweis + Parent-Sync) gibt es einen aggregierten Evidence-Runner:

```bash
./scripts/openclaw_runtime_assumerole_exec.sh env \
  BL31_STRICT_CORS=0 \
  ./scripts/run_bl31_app_api_monitoring_evidence.sh
```

Er nutzt die jüngste Rollout-Evidenz als Input, führt den kombinierten App/API-Smoke (inkl. CORS-Baseline im Warn-/Strict-Modus) plus UI-Monitoring-Check aus und schreibt den Nachweis nach `artifacts/bl31/*-bl31-app-api-monitoring-evidence.json`.

#### BL-31.3 Failure-/Rollback-Hinweise (Routing/TLS)

Typische Symptome und Sofortmaßnahmen:

- **`app.<domain>` liefert 404/503, `api.<domain>` gesund:**
  - ALB Host-Rule für `app.<domain>` prüfen (Priority, Target Group)
  - UI-Service/Task health prüfen (`/healthz`)
  - nur UI-Service auf letzte stabile Revision zurückrollen

- **TLS-Fehler auf einem Host (`NET::ERR_CERT_COMMON_NAME_INVALID` o. ä.):**
  - ACM-Zertifikat auf SAN/Wildcard-Abdeckung für `api.<domain>` + `app.<domain>` prüfen
  - Listener-Zertifikatsbindung/Default-Cert kontrollieren
  - bei Bedarf letzte funktionierende Listener-Konfiguration wiederherstellen

- **Browser-CORS-Fehler bei `POST /analyze`:**
  - API-ENV `CORS_ALLOW_ORIGINS` mit UI-Origin abgleichen (`https://app.<domain>`)
  - Preflight prüfen: `OPTIONS https://api.<domain>/analyze` muss `204` + passenden `Access-Control-Allow-Origin` liefern
  - nach Korrektur Strict-Smoke ausführen: `BL31_STRICT_CORS=1 ./scripts/run_bl31_routing_tls_smoke.sh`

Rollback-Guardrail:
- Routing-/TLS-Änderungen zuerst rückgängig machen, **bevor** ein Service-Rollback ausgelöst wird.
- Nach jedem Rollback Pflicht-Smoke: `https://api.<domain>/health` und `https://app.<domain>/healthz`.

---

## Agent-Autopilot (Nipa)

Der verbindliche Arbeitsmodus für autonome Weiterarbeit ist in [`docs/AUTONOMOUS_AGENT_MODE.md`](AUTONOMOUS_AGENT_MODE.md) dokumentiert.

Kurzfassung:
- GitHub-Operationen über GitHub App Wrapper (`scripts/gha`, `scripts/gpush`), nicht über User-Login.
- Komplexe Aufgaben via Subagents mit `openai-codex/gpt-5.3-codex` und `thinking=high`.
- Parallelisierung nutzen, wenn Aufgaben unabhängig sind.
- Vor AWS-Ops-Läufen BL-17 Quick-Check ausführen: `./scripts/check_bl17_oidc_assumerole_posture.sh`.
- Direkte AWS-CLI-Aufrufe bevorzugt über `./scripts/aws_exec_via_openclaw_ops.sh <aws-subcommand...>` ausführen (AssumeRole-first, fail-fast Input-Validation für Role-ARN/Session-Parameter inklusive).
- Falls Detailanalyse nötig: `./scripts/audit_legacy_aws_consumer_refs.sh` (Repo/Caller), `./scripts/audit_legacy_runtime_consumers.sh` (Runtime-Quellen) und `LOOKBACK_HOURS=6 ./scripts/audit_legacy_cloudtrail_consumers.sh` (CloudTrail-Fingerprints) separat ausführen.
- Offene Legacy-Consumer je Lauf in `docs/LEGACY_CONSUMER_INVENTORY.md` nachführen (insb. externe Runner/Hosts).

### Automatische Blocker-Retry-Steuerung (extern/temporär)

Für externe/temporäre Fehler (z. B. Endpoint nicht erreichbar, Timeout) läuft ein technischer Supervisor:

- Script: `scripts/blocker_retry_supervisor.py`
- Empfohlen als Cron-Job: `geo-ranking-blocker-retry-supervisor-30m` (alle 30 Minuten)

Regeln (erzwingt die Policy aus `AUTONOMOUS_AGENT_MODE.md`):
- Grace-Period: **3 Stunden** nach letztem externen Fehler
- Maximal **3 Fehlversuche** pro Issue
- Nach Grace-Period: Issue zurück auf `status:todo` (nächster Retry)
- Nach 3/3 Fehlversuchen: automatisches Follow-up-Issue + Parent bleibt `status:blocked`

Manueller Lauf (Debug/On-demand):

```bash
cd /data/.openclaw/workspace/geo-ranking-ch
python3 scripts/blocker_retry_supervisor.py
```

## OpenClaw-Automation-Jobs (MVP-Migration aus GitHub Actions)

Technischer Entry-Point für migrierte Jobs:

```bash
python3 scripts/run_openclaw_migrated_job.py --job <contract-tests|crawler-regression|docs-quality>
```

Beispiel (alle drei MVP-Jobs nacheinander):

```bash
python3 scripts/run_openclaw_migrated_job.py --job contract-tests
python3 scripts/run_openclaw_migrated_job.py --job crawler-regression
python3 scripts/run_openclaw_migrated_job.py --job docs-quality
```

Erzeugte Evidenz pro Lauf:

- `reports/automation/<job-id>/latest.json`
- `reports/automation/<job-id>/latest.md`
- `reports/automation/<job-id>/history/<timestamp>.json`
- `reports/automation/<job-id>/history/<timestamp>.md`

Hinweise:
- Exit-Code ist fail-fast (erster fehlgeschlagener Step).
- `--command-override` ist nur für lokale Tests gedacht.
- Mapping/Trigger-Design bleibt in [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md) dokumentiert.

## GitHub-Actions-Cleanup + Required-Checks (BL-20.y.wp4)

Stand nach WP4:
- **Automatisch aktiv auf GitHub bleibt nur** `.github/workflows/deploy.yml`.
- Ehemalige Kosten-/Qualitäts-Workflows wurden auf **manual fallback (`workflow_dispatch`)** umgestellt:
  - `.github/workflows/contract-tests.yml`
  - `.github/workflows/crawler-regression.yml`
  - `.github/workflows/docs-quality.yml`
  - `.github/workflows/bl20-sequencer.yml` (retired/manual placeholder)
- `.github/workflows/worker-claim-priority.yml` bleibt trotz umgesetztem Event-Relay-Pfad (`#233`) bis zum dokumentierten Deaktivierungsmarker aktiv (2 saubere Live-Hybrid-Runs + Drift-Nachweis; Designgrundlage in `docs/automation/openclaw-event-relay-design.md`, #227).

### Required-Checks Zielzustand (Branch Protection `main`)

Für den OpenClaw-Migrationsbetrieb dürfen nur Checks als **required** gesetzt sein, die tatsächlich noch automatisch auf PRs laufen.

Empfohlener Minimalzustand:
- optional/required nach Teamentscheid: `deploy / Build & Test` (oder äquivalenter Deploy-Check)
- **nicht required**: `contract-tests`, `crawler-regression`, `docs-quality`, `bl20-sequencer`

### Administrative Anpassung (Repo-Owner)

Die GitHub-App des Workers hat keinen Admin-Zugriff auf Branch-Protection. Deshalb gilt:

1. `Settings` → `Branches` → Branch protection rule für `main`
2. Unter **Require status checks to pass** alle nicht mehr auto-triggernden Checks entfernen
3. Regel speichern und kurz mit Test-PR verifizieren (kein „Expected — Waiting for status to be reported“ auf retired/manual Checks)

### Recovery/Fallback bei OpenClaw-Störung

Wenn OpenClaw-Jobs temporär ausfallen, können die migrierten Checks manuell gestartet werden:

1. GitHub → `Actions` → gewünschter Workflow (`contract-tests`, `crawler-regression`, `docs-quality`)
2. `Run workflow` ausführen
3. Ergebnis in Issue/PR als temporären Fallback-Nachweis dokumentieren
4. Nach Stabilisierung wieder auf OpenClaw-Evidenzpfade (`reports/automation/...`) zurückgehen

## Event-Relay Zielpfad (Rollout-Stand #233)

Das Zielbild für schnellere Issue/PR-nahe Trigger ist in [`docs/automation/openclaw-event-relay-design.md`](automation/openclaw-event-relay-design.md) dokumentiert (Issue #227). Mit #233 ist der Repo-seitige Relay-Pfad vollständig umgesetzt: Receiver (`scripts/run_event_relay_receiver.py`) übernimmt Signatur-/Allowlist-/Dedup-Gates am Ingress, Consumer (`scripts/run_event_relay_consumer.py`) verarbeitet Queue-Events outbound in den Reconcile-Flow.

Wesentliche Betriebsannahmen:
- Kein direkter Webhook auf den OpenClaw-Container (kein Inbound erreichbar).
- Relay nimmt Events extern entgegen, validiert/signiert, schreibt in Queue.
- OpenClaw verarbeitet Events outbound per Pull-Consumer.
- Cron-Reconcile bleibt als degradierbarer Safety-Net aktiv, bis der Deaktivierungsmarker erfüllt ist (siehe unten).

### Receiver-Ingress (Webhook → Queue)

Lokaler/Container-naher Receiver-Lauf (für den externen Relay-Endpoint oder Integrationstests):

```bash
export GITHUB_WEBHOOK_SECRET="<active-secret>"
export GITHUB_WEBHOOK_SECRET_PREVIOUS="<old-secret-optional>"
export EVENT_RELAY_ALLOWED_REPOSITORIES="nimeob/geo-ranking-ch"

python3 scripts/run_event_relay_receiver.py \
  --headers-file /tmp/github_webhook_headers.json \
  --payload-file /tmp/github_webhook_payload.json \
  --queue-file /tmp/event-relay-queue.ndjson
```

Erwartung:
- ungültige Signatur/Allowlist-Verstoß ⇒ `status=rejected`, **kein** Queue-Write
- bekannte `delivery_id` innerhalb TTL ⇒ `status=duplicate`, **kein** zweiter Queue-Write
- gültiges Event ⇒ `status=accepted` + minimiertes Envelope im Queue-File

### Shadow-Run (read-only)

```bash
python3 scripts/run_event_relay_consumer.py \
  --queue-file /tmp/issue238_shadow_queue.ndjson \
  --mode dry-run \
  --state-file /tmp/issue238_shadow_state.json
```

Erwartung: Event-Routing + Dedup + Dispatch-Preview ohne GitHub-Mutationen.

### Hybrid-Run (Event-Apply + Cron-Fallback bleibt aktiv)

Produktionsnaher Apply-Pfad (mutierend gegen GitHub-API):

```bash
export GH_TOKEN="$(./scripts/gh_app_token.sh)"
python3 scripts/run_event_relay_consumer.py \
  --queue-file /tmp/event-relay-queue.ndjson \
  --mode apply
```

Sicherer Integrationslauf ohne Live-Mutation (für Verifikation/Drills):

```bash
python3 scripts/run_event_relay_consumer.py \
  --queue-file /tmp/issue238_hybrid_queue.ndjson \
  --issues-snapshot /tmp/issue238_hybrid_snapshot.json \
  --mode apply \
  --state-file /tmp/issue238_hybrid_state.json
```

### Security-Runbook (operativer Ablauf)

1. **Signaturprüfung**
   - Relay MUSS `X-Hub-Signature-256` gegen das aktuelle Webhook-Secret validieren.
   - Invalid Signature ⇒ Event verwerfen, `invalid-signature` zählen, keine Queue-Schreiboperation.
2. **Secret-Rotation**
   - Rotation mindestens quartalsweise oder sofort nach Incident.
   - Während Rotation kurze Dual-Secret-Phase erlauben (active + previous), danach old secret entfernen.
3. **Allowlist + Scope-Minimierung**
   - Nur freigegebene Event-Typen (`issues`, `pull_request`, `workflow_dispatch`) annehmen.
   - Nur freigegebene Repositories/Owner annehmen.
4. **Dedup/Replay-Schutz**
   - `delivery_id` mit TTL in dedizierter State-Store/Keyspace führen.
   - Doppelte Delivery IDs als `duplicate` markieren und nicht erneut dispatchen.
5. **Rate-Limit + Backpressure**
   - Ingress-Limits am Relay setzen (pro Quelle + global).
   - Bei Überlast: Queue-first, konsumierende Seite mit Backoff; keine ungebremsten Retry-Loops.
6. **Dead-Letter/Recovery**
   - Parsing-/Schema-/Dispatch-Fehler mit Grund codiert ablegen (`reports/automation/event-relay/` + ggf. DLQ).
   - Reprocess nur nach Fehlerklassifikation und dokumentiertem Freigabeschritt.

### Evidenz (WP3)

- Shadow-Run: `reports/automation/event-relay/history/20260227T090700Z.{json,md}`
- Hybrid-Run (Snapshot-Apply): `reports/automation/event-relay/history/20260227T090900Z.{json,md}`
- Laufende Artefakte:
  - `reports/automation/event-relay/latest.json`
  - `reports/automation/event-relay/latest.md`
  - `reports/automation/event-relay/history/<timestamp>.json`
  - `reports/automation/event-relay/history/<timestamp>.md`

### Decision Marker für Abschaltung von `.github/workflows/worker-claim-priority.yml`

`DISABLE_WORKER_CLAIM_PRIORITY_ACTION = false` solange mindestens eines der Kriterien offen ist:

- weniger als 2 aufeinanderfolgende **Live-Hybrid-Runs** (`--mode apply` gegen GitHub API) ohne `reconcile_dispatch_failed`
- nicht validierte Drift-Kontrolle zwischen Event-Path und Cron-Fallback
- kein dokumentierter Rollback-Owner für Incident-Fälle

Wenn alle Kriterien erfüllt sind, Marker auf `true` setzen, Workflow deaktivieren und Datum/Beleg in `docs/BACKLOG.md` + Migration-Matrix nachziehen.

Hinweis zur Cron-Koexistenz: Der Dispatch mutiert nur bei tatsächlichem Label-Delta (idempotente Reconcile-Regeln). Damit bleibt der periodische Cron-Fallback parallel betreibbar, ohne dauerhaftes Double-Mutation-Risiko.

Zusatzregel aus Follow-up #241: `status:in-progress` gilt als aktiver Zustand und wird im Reconcile-Pfad nicht mehr zusätzlich mit `status:todo` kombiniert.

## Consistency-Crawler (read-only) — Runbook

Zweck: Drift zwischen Vision, Backlog/Issues, Code und Doku früh erkennen, ohne automatische Mutationen als Default.

### Standardlauf (ohne GitHub-Mutationen)

```bash
cd /data/.openclaw/workspace/geo-ranking-ch
python3 scripts/github_repo_crawler.py --dry-run
```

Erwartete Artefakte:
- `reports/consistency_report.json`
- `reports/consistency_report.md`

### Regressionscheck vor/bei Crawler-Änderungen

```bash
./scripts/check_crawler_regression.sh
```

Scope des Regressionschecks (MVP):
- Workstream-Balance
- Actionable-Taskmarker-Filter (Kommentar-/Inline-Hinweise)
- Vision↔Issue-Coverage
- Code↔Doku-Drift

Hinweis: Der Crawler bleibt im MVP read-only-orientiert. Auto-Issue/Auto-Open bleibt optional und wird nur über explizite Flags/Workflow-Governance aktiviert.

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

# BL-19.8 Doku-Qualitätsgate (frisches Setup + Link-/Strukturcheck)
./scripts/check_docs_quality_gate.sh

# BL-20.2.b.r3 Schema-Drift-Check (read-only)
python3 scripts/check_source_field_mapping_drift.py
```

Schema-Drift-Check Kurz-Runbook:
- **FAILED + missing/renamed field**: Upstream-Response gegen `docs/mapping/source-field-mapping.ch.v1.json` abgleichen.
- **Wenn Upstream geändert**: Mapping-Spec + Referenz-Samples aktualisieren.
- **Wenn nur Parser/Extraction falsch**: Codepfad korrigieren, Spec unverändert lassen.
- Danach Check + relevante Tests erneut ausführen.

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

**Empfohlener Standard-Setup (idempotent):**

```bash
./scripts/setup_monitoring_baseline_dev.sh
```

Optional mit E-Mail-Subscriber:

```bash
ALERT_EMAIL="you@example.com" ./scripts/setup_monitoring_baseline_dev.sh
```

**Read-only Baseline-Check (Status + Warnungen):**

```bash
./scripts/check_monitoring_baseline_dev.sh
```

Exit Codes:
- `0`: Baseline vollständig und ohne Warnungen
- `10`: Baseline technisch vorhanden, aber mit Warnungen (z. B. kein bestätigter Subscriber)
- `20`: Kritische Baseline-Teile fehlen

### BL-31.5 Ergänzung: UI-Service separat überwachen

Sobald der UI-Service (`swisstopo-dev-ui`) live ist, wird die Monitoring-Baseline um UI-spezifische Alarme ergänzt:
- `swisstopo-dev-ui-running-taskcount-low` (Service-Ausfall)
- `swisstopo-dev-ui-health-probe-fail` (Reachability via `/healthz`)

Setup (idempotent):

```bash
AWS_ACCOUNT_ID=523234426229 ./scripts/setup_bl31_ui_monitoring_baseline.sh
```

Read-only Check:

```bash
./scripts/check_bl31_ui_monitoring_baseline.sh
# Exit 0 = ok | 10 = Warn | 20 = kritisch
```

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

> Ziel: Frühe Erkennung von **Service-Ausfall** und **erhöhter API-Fehlerquote** ohne komplexes Observability-Setup.

#### Alarm A — Service unhealthy (RunningTaskCount < 1)

Für den aktuellen MVP mit Desired Count = 1:

```bash
aws cloudwatch put-metric-alarm   --region "$AWS_REGION"   --alarm-name "swisstopo-dev-api-running-taskcount-low"   --alarm-description "ECS service unhealthy: running tasks < 1"   --namespace AWS/ECS   --metric-name RunningTaskCount   --dimensions Name=ClusterName,Value=swisstopo-dev Name=ServiceName,Value=swisstopo-dev-api   --statistic Minimum   --period 60   --evaluation-periods 3   --datapoints-to-alarm 3   --threshold 1   --comparison-operator LessThanThreshold   --treat-missing-data breaching
```

#### Alarm B — API-Fehlerquote zu hoch (5xx > 5%, bei mind. 20 Requests/5m)

Basiert auf zwei Log-Metriken in Namespace `swisstopo/dev-api`:
- `HttpRequestCount`
- `Http5xxCount`

Alarm mit Metric Math (`IF(mt>=20,(m5/mt)*100,0) > 5`):

```bash
aws cloudwatch put-metric-alarm \
  --region "$AWS_REGION" \
  --alarm-name "swisstopo-dev-api-http-5xx-rate-high" \
  --alarm-description "API error rate too high: 5xx ratio > 5% (min 20 req/5m)" \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2 \
  --treat-missing-data notBreaching \
  --metrics '[
    {"Id":"m5","MetricStat":{"Metric":{"Namespace":"swisstopo/dev-api","MetricName":"Http5xxCount"},"Period":300,"Stat":"Sum"},"ReturnData":false},
    {"Id":"mt","MetricStat":{"Metric":{"Namespace":"swisstopo/dev-api","MetricName":"HttpRequestCount"},"Period":300,"Stat":"Sum"},"ReturnData":false},
    {"Id":"er","Expression":"IF(mt>=20,(m5/mt)*100,0)","Label":"Http5xxRatePercent","ReturnData":true}
  ]' \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

> Sobald Autoscaling >1 eingeführt wird, Alarm A auf „RunningTaskCount < DesiredTaskCount" (Metric Math) umstellen.

### 2.1) Alarm-Kanal (SNS + Lambda → Telegram)

Standard-Kanal in `dev`:
- Topic: `arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts`
- Subscriber: Lambda `swisstopo-dev-sns-to-telegram` → Telegram Bot API

**Vollständiger Datenfluss:** `CloudWatch Alarm → SNS Topic → Lambda → Telegram (Chat-ID: 8614377280)`

**Telegram-Alerting einrichten (einmalig):**

```bash
# Option A: Setup-Script (schnell, vollautomatisch)
export TELEGRAM_BOT_TOKEN="<BOT_TOKEN>"
export TELEGRAM_CHAT_ID="8614377280"
./scripts/setup_telegram_alerting_dev.sh

# Option B: Terraform (IaC, idempotent)
# Zuerst SSM-Parameter anlegen (einmalig, manuell):
aws ssm put-parameter \
  --region eu-central-1 \
  --name /swisstopo/dev/telegram-bot-token \
  --type SecureString \
  --value "<BOT_TOKEN>" \
  --description "Telegram Bot Token für swisstopo-dev Alerting"
# Dann: manage_telegram_alerting=true + terraform apply
```

**Status (2026-02-25):** ✅ End-to-End verifiziert (`ALARM` und `OK` erfolgreich im Telegram-Chat empfangen).

**Kontrollierter Testalarm:**

```bash
# Alarm künstlich triggern
aws cloudwatch set-alarm-state \
  --region eu-central-1 \
  --alarm-name swisstopo-dev-api-running-taskcount-low \
  --state-value ALARM \
  --state-reason "Kontrollierter Testalarm via set-alarm-state"

# Nach Empfang im Telegram: zurücksetzen
aws cloudwatch set-alarm-state \
  --region eu-central-1 \
  --alarm-name swisstopo-dev-api-running-taskcount-low \
  --state-value OK \
  --state-reason "Reset nach Testalarm"
```

**SNS-Publish für reinen Kanal-Test:**

```bash
aws sns publish \
  --region "$AWS_REGION" \
  --topic-arn "arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts" \
  --subject "swisstopo-dev monitoring test" \
  --message '{"AlarmName":"TestAlarm","NewStateValue":"ALARM","NewStateReason":"Manueller Test","Region":"EU (Frankfurt)","AWSAccountId":"523234426229","StateChangeTime":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}'
```

> **Secret-Hinweis:** Bot-Token wird in SSM Parameter Store als SecureString gespeichert (`/swisstopo/dev/telegram-bot-token`). Er erscheint weder im Repo noch als Klartext im Terraform-State.

### 3) HTTP Uptime Probe (`/health`)

**Status (2026-02-25):** ✅ Produktiv aktiv — Lambda-basierte Self-Resolving Probe

**Architektur (kein ALB, kein stabile Domain → dynamische IP-Auflösung):**

```
EventBridge (rate 5 min)
  → Lambda swisstopo-dev-health-probe
      → ecs:ListTasks / ecs:DescribeTasks / ec2:DescribeNetworkInterfaces
      → HTTP GET http://<public-ip>:8080/health
      → cloudwatch:PutMetricData  HealthProbeSuccess (1=ok, 0=fail)
        → Alarm swisstopo-dev-api-health-probe-fail
          → SNS → Lambda → Telegram
```

**Ressourcen:**

| Ressource | Name / ARN |
|---|---|
| Lambda | `swisstopo-dev-health-probe` |
| IAM Role | `swisstopo-dev-health-probe-role` |
| EventBridge Rule | `swisstopo-dev-health-probe-schedule` (rate 5 min, ENABLED) |
| CloudWatch Alarm | `swisstopo-dev-api-health-probe-fail` |
| Metrik | `swisstopo/dev-api  /  HealthProbeSuccess` (Dim: Service, Environment) |

**Lambda-Quellcode:** `infra/lambda/health_probe/lambda_function.py`

**Setup/Update (idempotent):**

```bash
AWS_ACCOUNT_ID=523234426229 ./scripts/setup_health_probe_dev.sh
```

**Status-Check (read-only):**

```bash
./scripts/check_health_probe_dev.sh
# Exit 0 = alles ok | 10 = Warnung | 20 = kritisch
```

**Metrik manuell prüfen:**

```bash
aws cloudwatch get-metric-statistics \
  --region eu-central-1 \
  --namespace 'swisstopo/dev-api' \
  --metric-name HealthProbeSuccess \
  --dimensions Name=Service,Value=swisstopo-dev-api Name=Environment,Value=dev \
  --start-time "$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 300 \
  --statistics Minimum
```

**Alarm-Logik:** `HealthProbeSuccess < 1` in 3 von 3 aufeinanderfolgenden 5-Min-Perioden (treat-missing-data=breaching).
→ Trigger: Service nicht erreichbar **oder** kein Metrikpunkt (Lambda nicht gelaufen).

**Kosten:** ~$0.01/Monat (Lambda Free Tier, EventBridge <$0.01, CloudWatch PutMetricData <$0.01).

**Hinweis ALB:** Sobald ein ALB eingesetzt wird, ergänzend CloudWatch-Alarm auf `AWS/ApplicationELB → UnHealthyHostCount > 0` für das Target-Group/Load-Balancer-Paar hinzufügen — dann kann die Lambda-Probe vereinfacht werden (statische URL statt dynamischer IP-Auflösung).

**Manueller Smoke-Check:**

```bash
# Erwartet HTTP 200 und JSON {"ok": true, ...}
curl -fsS "$SERVICE_HEALTH_URL"
```

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
