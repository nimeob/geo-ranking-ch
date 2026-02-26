# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in diesem Dokument festgehalten.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).
Dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

---

## [Unreleased]

### Added
- Projektdokumentation: README.md, ARCHITECTURE.md, DEPLOYMENT_AWS.md, OPERATIONS.md
- Basis-Verzeichnisstruktur (`docs/`, `scripts/`, `.github/workflows/`)
- GitHub Actions Placeholder-Workflow für CI/CD

### Added (2026-02-25 — BL-12 HTTP Uptime Probe aktiv)
- **`infra/lambda/health_probe/lambda_function.py`:** Lambda-Probe (Python 3.12). Löst öffentliche IP des laufenden ECS-Tasks dynamisch auf (kein ALB/stabile Domain erforderlich), führt HTTP GET `/health` durch, publiziert CloudWatch-Metrik `HealthProbeSuccess` (1=ok, 0=fail). Kein externer Dependency-Overhead (nur stdlib + boto3).
- **`scripts/setup_health_probe_dev.sh`:** Idempotentes Setup-Script. Erstellt IAM-Role (`swisstopo-dev-health-probe-role`, Minimal-Privilege), Lambda `swisstopo-dev-health-probe`, EventBridge Scheduled Rule (rate 5 min) und CloudWatch Alarm (`swisstopo-dev-api-health-probe-fail` → SNS → Telegram). Kein `zip`-Binary nötig (ZIP via Python stdlib). Inkl. sofortigem Lambda-Testlauf nach Deployment.
- **`scripts/check_health_probe_dev.sh`:** Read-only Status-Check: Lambda-State, EventBridge-Rule, letzte Invocations, HealthProbeSuccess-Metrik, Alarm-Zustand. Exit Codes: `0` OK, `10` Warn, `20` kritisch.
- **AWS (live, non-destructive):** IAM-Role, Lambda, EventBridge Rule, CW Alarm erstellt und verifiziert. Erster Testlauf erfolgreich: IP dynamisch aufgelöst (`18.184.115.244`), HTTP 200 erhalten, `HealthProbeSuccess = 1` publiziert.
- **`docs/OPERATIONS.md`:** Sektion 3 „HTTP Health Check Guidance" vollständig durch operativen Probe-Abschnitt ersetzt (Architektur, Ressourcen, Kommandos, Kosten, ALB-Hinweis).
- **`docs/DEPLOYMENT_AWS.md`:** Ressourcen-Tabelle um Lambda + EventBridge erweitert; Monitoring-Tabelle aktualisiert (`Uptime/HTTP Health` = ✅ aktiv); neue Sektion „HTTP Uptime Probe — GET /health (BL-12)" mit Komponenten, Setup-Kommandos und Testnachweis.
- **`docs/BACKLOG.md`:** BL-12 neu angelegt und als abgeschlossen markiert.

### Added (2026-02-26 — BL-11 AWS-Inventory & Konfigurationsdokumentation)
- **`docs/AWS_INVENTORY.md`:** Vollständiges, verifiziertes AWS-Ressourcen-Inventar für die `dev`-Umgebung. Enthält alle Bereiche (IAM, ECR, ECS, CloudWatch, S3, Lambda, SNS, SSM, Netzwerk/VPC) mit Name/ARN, Region, Zweck, Tags, zentralen Konfig-Parametern, IaC-Status (`🔧 Terraform` vs. `🖐️ Manuell`) und Rebuild-Hinweisen inkl. Abhängigkeitsreihenfolge. Alle Werte direkt via read-only AWS-Abfragen verifiziert. Keine Secrets oder sensitiven Inhalte enthalten.
- **`README.md`:** Doku-Index und Projektbaum um `docs/AWS_INVENTORY.md` erweitert.
- **`docs/DEPLOYMENT_AWS.md`:** Verweis auf `docs/AWS_INVENTORY.md` als zentrales Ressourcen-Inventar ergänzt.
- **`docs/BACKLOG.md`:** BL-11 auf abgeschlossen gesetzt inkl. Nachweis.

### Changed (2026-02-26 — BL-14 abgeschlossen: Terraform-Plan verifiziert, Import-Runbook präzisiert)
- **`infra/terraform/health_probe.tf`:** Terraform-Definition für Health-Probe finalisiert (Fix `target_id` statt ungültigem `id` bei `aws_cloudwatch_event_target`; `statement_id` auf bestehenden Wert `allow-eventbridge-health-probe` abgestimmt; Beschreibungen auf Live-Setup harmonisiert).
- **`infra/terraform/outputs.tf`:** Safe-Output-Fix: fehlerhafte `coalesce(...)`-Ausdrücke durch robuste `try(..., null)`-Varianten ersetzt, damit `terraform plan` im Safe-Default (`manage_* = false`) ohne Fehler läuft.
- **`infra/terraform/README.md`:** Vollständige Import-Reihenfolge für BL-14 ergänzt (inkl. `aws_iam_role_policy`, `aws_iam_role_policy_attachment`, `aws_lambda_permission`).
- **`docs/DEPLOYMENT_AWS.md`:** Terraform-Import-Kommandos für Health-Probe vervollständigt; BL-14-Status auf verifiziert abgeschlossen aktualisiert.
- **`docs/BACKLOG.md`:** BL-14 von „in Umsetzung“ auf ✅ abgeschlossen gesetzt; Nachweis um ausgeführte Terraform-Validierung und Plan-Ergebnis ergänzt (**0 add / 4 change / 0 destroy**, keine destruktiven Aktionen).

### Changed (2026-02-26 — BL-13 gestartet und abgeschlossen: Doku-Konsistenz nach Nacht-Plan)
- **`docs/BACKLOG.md`:** Neue Folge-Sequenz nach abgeschlossenem Nacht-Plan angelegt (`BL-13` bis `BL-15`), `BL-13` als abgeschlossen dokumentiert und Nachweise ergänzt.
- **`docs/DEPLOYMENT_AWS.md`:** Abschnitt „Offene Punkte / TODOs“ konsolidiert; veralteter Restpunkt zur bereits aktiven HTTP-Uptime-Probe entfernt; Backlog-Referenz auf aktuelle BL-Range (`BL-01` bis `BL-15`) aktualisiert.

### Changed (2026-02-26 — BL-03 final abgeschlossen, Least-Privilege OIDC-Doku finalisiert)
- **`infra/iam/trust-policy.json`:** Neu — Trust-Policy der OIDC-Deploy-Role versioniert (`repo:nimeob/geo-ranking-ch:ref:refs/heads/main`, verifiziert identisch mit live AWS-Konfiguration).
- **`infra/iam/README.md`:** Status auf `✅ Final abgeschlossen` aktualisiert; bisheriger „Vorbereitung"-Hinweis (misleading) entfernt; neuen Nachweis-Abschnitt ergänzt (Role ARN, Policy-Version, Trust-Bedingung, E2E-Run-Links, Policy-Drift-Verifikation — kein Drift); Hinweise für Staging/Prod-OIDC-Rollen ergänzt.
- **`docs/DEPLOYMENT_AWS.md`:** AWS-Basis-Tabelle: OIDC-Deploy-Role als aktueller CI/CD-Principal eingetragen; IAM-User `swisstopo-api-deploy` als Legacy markiert (nicht mehr für CI/CD genutzt). IAM-Sektion umbenannt auf „OIDC Deploy-Role — BL-03 ✅ abgeschlossen"; Minimalrechte-Tabelle um Scope-Spalte ergänzt.
- **`docs/BACKLOG.md`:** BL-03 finaler Eintrag ergänzt (Trust-Policy-Artefakt, README/Doku-Update als Done nachgeführt).

### Changed (2026-02-25 — BL-08 final abgeschlossen, Empfangsnachweis erbracht)
- **`docs/BACKLOG.md`:** BL-08 von „in Umsetzung“ auf **abgeschlossen** gesetzt; Blocker/Next-Actions entfernt; Deploy- + Empfangsnachweis (`ALARM` und `OK`) dokumentiert.
- **`docs/DEPLOYMENT_AWS.md`:** Status für Lambda/Alert-Kanal auf **verifiziert aktiv** aktualisiert; offene Punkte entsprechend bereinigt.
- **`docs/OPERATIONS.md`:** Monitoring-Kapitel um klaren End-to-End-Status ergänzt (`CloudWatch → SNS → Lambda → Telegram` verifiziert).

### Changed (2026-02-25 — BL-08 Telegram-Alerting IaC implementiert)
- **`infra/lambda/sns_to_telegram/lambda_function.py`:** Lambda-Handler (Python 3.12) für CloudWatch-Alarm → Telegram. Liest Bot-Token sicher aus SSM SecureString zur Laufzeit. Nachrichtenformat: Alarmname, State, Reason, Region, Account, Timestamp — robust bei fehlenden Feldern. Kein externer Dependency-Overhead (nur stdlib + boto3).
- **`infra/terraform/lambda_telegram.tf`:** Terraform-Ressourcen für Lambda-Funktion, IAM-Role (Minimal-Privilege: CloudWatch Logs + SSM GetParameter + KMS Decrypt), Lambda-Permission für SNS und SNS → Lambda-Subscription. Aktivierung via Flag `manage_telegram_alerting = true`. Zip wird automatisch via `archive_file` erzeugt.
- **`infra/terraform/variables.tf`:** Neue Variablen `manage_telegram_alerting`, `aws_account_id`, `sns_topic_arn`, `telegram_chat_id`.
- **`infra/terraform/outputs.tf`:** Neue Outputs `telegram_lambda_arn`, `telegram_lambda_function_name`, `telegram_sns_subscription_arn`, erweitertes `resource_management_flags`.
- **`infra/terraform/terraform.tfvars.example`:** Telegram-Alerting-Block mit Kommentaren zu manueller SSM-Anlage und Aktivierungsschritten ergänzt.
- **`scripts/setup_telegram_alerting_dev.sh`:** Neu — idempotentes Setup-Script als Fallback zu Terraform. Legt SSM-Parameter, IAM-Role, Lambda und SNS-Subscription in einem Durchgang an. Erwartet `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID` als Umgebungsvariablen (nie auf Disk oder im Repo).
- **`scripts/check_monitoring_baseline_dev.sh`:** Telegram-Alerting-Checks ergänzt: Lambda-State, SNS-Subscription aktiv, `TELEGRAM_CHAT_ID` in Lambda-Env, SSM-Parameter-Existenz.
- **`docs/DEPLOYMENT_AWS.md`:** Monitoring-Tabelle auf Telegram-Status aktualisiert; neue Sektion „Telegram-Alerting — Architektur & Deployment" mit Deploy-Optionen A/B, Testalarm-Kommandos und Secret-Hinweis.
- **`docs/OPERATIONS.md`:** Alarm-Kanal-Sektion auf SNS + Lambda → Telegram erweitert; Kontrollierter Testalarm und SNS-Publish-Snippet ergänzt.
- **`docs/BACKLOG.md`:** BL-08 auf aktuellen Stand gebracht: Telegram-IaC als umgesetzt; konkrete Next-Actions für Nico (SSM anlegen → Deploy → Testalarm → Verifikation).

### Changed (2026-02-25 — BL-08 Monitoring-Checklauf operationalisiert)
- **`scripts/check_monitoring_baseline_dev.sh`:** Neues read-only Prüfscript ergänzt (ECS/Logs/Metric-Filters/Alarme/SNS inkl. Subscriber-Status) mit klaren Exit-Codes (`0` OK, `10` Warn, `20` Fail).
- **`docs/OPERATIONS.md`:** Monitoring-Abschnitt um den Baseline-Check inkl. Exit-Code-Interpretation erweitert.
- **`docs/DEPLOYMENT_AWS.md`:** Ops-Helper und Alert-Kanal-Status um den neuen Read-only Check ergänzt.
- **`docs/BACKLOG.md`:** BL-08 Fortschritt und aktueller Checkstand dokumentiert (`keine SNS Subscriber vorhanden`).

### Changed (2026-02-25 — BL-09 Promotion-Strategie für staging/prod vorbereitet)
- **`docs/ENV_PROMOTION_STRATEGY.md`:** Neu angelegt mit Zielarchitektur pro Umgebung, Promotion-Gates (`dev`→`staging`→`prod`), Freigaberegeln und Rollback-Standard.
- **`docs/BACKLOG.md`:** BL-09 auf abgeschlossen gesetzt und Nachweisdokument verlinkt.
- **`README.md` / `docs/ARCHITECTURE.md` / `docs/DEPLOYMENT_AWS.md`:** Referenzen auf die neue Promotion-Strategie ergänzt.

### Changed (2026-02-25 — BL-08 Monitoring-Baseline umgesetzt, externer Receiver offen)
- **`scripts/setup_monitoring_baseline_dev.sh`:** Neues idempotentes Setup-Script für dev-Monitoring (SNS Topic, Log Metric Filters, Alarme für Service-Ausfall + 5xx-Fehlerquote, SNS-Testpublishing).
- **AWS (live, non-destructive):** Topic `swisstopo-dev-alerts`, Metric Filters (`HttpRequestCount`, `Http5xxCount`) und Alarme (`swisstopo-dev-api-running-taskcount-low`, `swisstopo-dev-api-http-5xx-rate-high`) angelegt; Kanaltest via SNS Publish durchgeführt.
- **`docs/BACKLOG.md`:** BL-08 auf „in Umsetzung“ gesetzt inkl. Blocker (kein bestätigter externer Subscriber) und konkreten Next Actions.
- **`docs/DEPLOYMENT_AWS.md` / `docs/OPERATIONS.md`:** Monitoring-Status auf tatsächlich angelegte Ressourcen aktualisiert; Setup-/Runbook-Kommandos ergänzt.

### Changed (2026-02-25 — BL-06/BL-07 Datenhaltung & API-Sicherheit abgeschlossen)
- **`docs/DATA_AND_API_SECURITY.md`:** Neu angelegt mit verbindlicher Entscheidung „stateless in dev“, definiertem DynamoDB-first-Pfad bei Persistenztriggern sowie AuthN/AuthZ-, Rate-Limit- und Secret-Handling-Standards für `/analyze`.
- **`docs/BACKLOG.md`:** BL-06 und BL-07 auf abgeschlossen gesetzt, Nachweis auf das neue Entscheidungsdokument verlinkt.
- **`docs/ARCHITECTURE.md` / `docs/DEPLOYMENT_AWS.md` / `README.md`:** Referenzen auf das neue Sicherheits-/Datenhaltungsdokument ergänzt.

### Changed (2026-02-25 — BL-05 Netzwerk-/Ingress-Zielbild abgeschlossen)
- **`docs/NETWORK_INGRESS_DECISIONS.md`:** Neu angelegt mit verifiziertem Ist-Stand (Default VPC/public subnets, SG-Ingress) und beschlossenem Zielbild (ALB vor ECS, private Tasks, Route53/ACM-Pflicht in `staging`/`prod`).
- **`docs/BACKLOG.md`:** BL-05 auf abgeschlossen gesetzt und Nachweisdokument verlinkt.
- **`docs/ARCHITECTURE.md`:** Architekturentscheid um Referenz auf Netzwerk-/Ingress-Zielbild ergänzt.
- **`README.md`:** Doku-Index und Projektbaum um `docs/NETWORK_INGRESS_DECISIONS.md` erweitert.

### Changed (2026-02-25 — BL-01 IaC dev Source-of-Truth abgeschlossen)
- **`infra/terraform/main.tf` / `variables.tf` / `outputs.tf` / `terraform.tfvars.example`:** Import-first-IaC auf dev-Kernressourcen erweitert (zusätzlich `aws_s3_bucket.dev`), Drift-arme Defaults an verifizierten Ist-Stand angepasst (`managed_by=openclaw`, Log Group `/swisstopo/dev/ecs/api`, Retention 30d, `ecs_container_insights_enabled=false`).
- **`infra/terraform/README.md`:** Runbook auf ECS+ECR+CloudWatch+S3 aktualisiert, inkl. verifiziertem Ist-Stand und Import-IDs.
- **`scripts/check_import_first_dev.sh`:** Read-only-Precheck um S3-Bucket erweitert; zusätzliche tfvars-Empfehlungen + Import-Kommando ergänzt.
- **`docs/BACKLOG.md`:** BL-01 auf abgeschlossen gesetzt, Nachweise (IaC-Artefakte + Deploy-Run) ergänzt.
- **`docs/DEPLOYMENT_AWS.md`:** BL-02/BL-01 Nachweisteile aktualisiert (Run `22417749775` und `22417939827` als erfolgreich, Terraform-Scope inkl. S3 + Precheck-Script).
- **`docs/ARCHITECTURE.md`:** IaC-Fundament von ECS/ECR/CloudWatch auf ECS/ECR/CloudWatch/S3 präzisiert.

### Added (2026-02-25 — GitHub App Auth Wrapper + Agent-Autopilot)
- **`scripts/gh_app_token.sh`:** Erzeugt on-demand GitHub App Installation Tokens aus `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, `GITHUB_APP_PRIVATE_KEY_PATH`.
- **`scripts/gha`:** Wrapper für `gh` mit frischem App-Token (`GH_TOKEN`), damit CLI-Operationen ohne User-Login laufen.
- **`scripts/gpush`:** Wrapper für `git push` über HTTPS + App-Token (`x-access-token`), ohne persistente User-Credentials.
- **`docs/AUTONOMOUS_AGENT_MODE.md`:** Verbindlicher Arbeitsmodus für Nipa (Subagent-first, Parallelisierung, Modellvorgabe `openai-codex/gpt-5.3-codex` + `thinking=high` bei komplexen Aufgaben).
- **`README.md` / `docs/OPERATIONS.md`:** Verlinkung und Kurzreferenz auf den neuen Agent-Autopilot-Standard ergänzt.

### Changed (2026-02-25 — BL-03 OIDC Least-Privilege Korrektur)
- **`infra/iam/deploy-policy.json`:** ECS-Leserechte präzisiert; `ecs:DescribeTaskDefinition` auf `Resource: "*"` umgestellt (kompatibel mit API-IAM-Evaluierung), `ecs:DescribeServices` scoped auf dev-Service belassen.
- **AWS IAM (live):** `swisstopo-dev-github-deploy-policy` auf Version `v2` aktualisiert und als Default gesetzt.
- **`docs/DEPLOYMENT_AWS.md` / `docs/BACKLOG.md`:** Validierungsstand ergänzt; ehemals fehlerhafter Deploy-Schritt `Register new task definition revision` im Run `22417749775` als erfolgreich dokumentiert.

### Changed (2026-02-25 — CI/CD Doku auf OIDC aktualisiert)
- **`README.md`:** Falsche ECS-Deploy-Voraussetzung mit statischen AWS-Secrets entfernt; OIDC-Role-Assume als aktueller Standard dokumentiert.
- **`docs/DEPLOYMENT_AWS.md`:** GitHub-Secrets-Sektion auf OIDC-Realität korrigiert (`keine AWS Access Keys erforderlich`), OIDC-Role-ARN + Verweis auf Minimalrechte ergänzt.
- **`docs/ARCHITECTURE.md`:** Abschnitt „Secrets & Variables“ auf OIDC umgestellt (keine statischen AWS-Keys, Role-Assume dokumentiert).

### Changed (2026-02-25 — BL-02 CI/CD-Deploy-Verifikation)
- **`.github/workflows/deploy.yml`:** Push-Trigger auf `main` wieder aktiviert (zusätzlich zu `workflow_dispatch`), damit BL-02 per Commit/Push verifiziert werden kann.
- **`.github/workflows/deploy.yml`:** ECR-Image-URI auf feste AWS Account ID (`523234426229`) umgestellt, um leere `AWS_ACCOUNT_ID`-Repo-Variable im Build-Schritt zu umgehen.
- **`docs/DEPLOYMENT_AWS.md`:** Verifikationsnachweis mit Run-URLs ergänzt (`22416418587`, `22416878804`, `22416930879`) inkl. Ergebnis und Schrittstatus (`services-stable`, Smoke-Test `/health`).

### Added (2026-02-25 — Terraform IaC-Fundament für dev)
- **`infra/terraform/`:** Minimales Terraform-Startpaket ergänzt (`versions.tf`, `providers.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `terraform.tfvars.example`).
- **`infra/terraform/README.md`:** Sicheres Import-first-Runbook ergänzt (`init` → `plan` → `import` → `apply`) inkl. Hinweise zu bestehenden dev-Ressourcen.
- **`docs/DEPLOYMENT_AWS.md`:** Terraform-Startpaket und sichere Reihenfolge (`init/plan/import/apply`) dokumentiert.
- **`docs/ARCHITECTURE.md`:** IaC-Fundament als aktueller Architekturbaustein ergänzt.

### Added (2026-02-25 — Container + Webservice MVP)
- **`Dockerfile`:** Container-Build für ECS/Fargate ergänzt (Python 3.12, Port 8080).
- **`src/web_service.py`:** Minimaler HTTP-Service mit Endpoints `/health`, `/version`, `/analyze`.

### Added (2026-02-25 — BL-03 Least-Privilege IAM Vorarbeit)
- **`infra/iam/deploy-policy.json`:** Konkrete Least-Privilege-Policy für den aktuellen ECS/ECR-dev-Deploypfad ergänzt (inkl. `iam:PassRole` nur für Task/Execution-Role).
- **`infra/iam/README.md`:** Herleitung aus GitHub-Workflow, sichere Migrationsreihenfolge ohne Breaking Change und read-only Drift-Check-Notizen ergänzt.

### Changed (2026-02-25 — BL-03 Statusdoku aktualisiert)
- **`docs/DEPLOYMENT_AWS.md`:** IAM-Sektion auf workflow-basierte Minimalrechte umgestellt und auf neue Artefakte unter `infra/iam/` verlinkt; Hinweis auf risikoarme Umsetzung (keine sofortige Secret-Umschaltung) ergänzt.
- **`docs/BACKLOG.md`:** BL-03 mit Statusnotiz „Track D Vorarbeit“ ergänzt (erledigte Vorarbeiten + offene Restschritte bis Done).

### Changed (2026-02-25 — ECS Deploy Workflow umgesetzt)
- **`.github/workflows/deploy.yml`:** Deploy-Job auf ECS/Fargate (dev) konkretisiert: ECR Login, Docker Build+Push, neue ECS Task-Definition registrieren, Service-Update, Stabilitäts-Wait.
- **`README.md`:** CI/CD-Sektion auf ECS-Deploy aktualisiert inkl. benötigter GitHub Secrets/Variables.
- **`README.md`:** Lokale Docker-/Webservice-Nutzung dokumentiert.
- **`docs/DEPLOYMENT_AWS.md`:** Stack-Entscheid auf ECS/Fargate dokumentiert; Runtime-Konvention (Port 8080, Healthcheck) ergänzt.

### Changed (2026-02-25 — Lizenzstatus korrigiert)
- **README.md:** Lizenz-Badge von `MIT` auf `proprietär` geändert.
- **README.md:** Lizenzsektion auf „vorerst proprietär (alle Rechte vorbehalten)“ umgestellt; Verweis auf nicht vorhandene `LICENSE`-Datei entfernt.

### Changed (2026-02-25 — CI/CD Workflow aktiviert)
- **`.github/workflows/deploy.yml`:** Workflow aus `scripts/ci-deploy-template.yml` nach `.github/workflows/` überführt und aktiviert. Trigger: ausschliesslich `workflow_dispatch` (manuell). Auto-Trigger (push/release) bleibt deaktiviert bis Secrets und Stack-Schritte konfiguriert sind. Keine Secrets eingetragen.
- **`README.md`:** CI/CD-Badge und neue Sektion „CI/CD" mit Setup-Checkliste ergänzt; Verzeichnisbaum aktualisiert.

### Changed (2026-02-25 — Doku-Update: AWS-Naming, Tagging, Umgebungen)
- **DEPLOYMENT_AWS.md:** Neue Sektion „Tagging Standard" mit verbindlichen AWS-Tags (`Environment=dev`, `ManagedBy=openclaw`, `Owner=nico`, `Project=swisstopo`)
- **DEPLOYMENT_AWS.md:** Ist-Stand-Ressourcen (`swisstopo-dev-*`) als verifiziert eingetragen; ECS/ECR-Befehle auf korrekte Cluster-/Service-Namen aktualisiert
- **DEPLOYMENT_AWS.md:** Klarstellung: AWS-Naming `swisstopo` ist intern und intentional; keine Umbenennung nötig
- **DEPLOYMENT_AWS.md:** Explizit festgehalten: nur `dev`-Umgebung vorhanden; `staging` und `prod` noch nicht aufgebaut
- **ARCHITECTURE.md:** Swisstopo-Ressourcen korrekt als Ressourcen dieses Projekts (nicht Schwesterprojekt) eingetragen; Naming-Konvention und Umgebungs-Status ergänzt
- **README.md:** Hinweise zu AWS-Naming (`swisstopo`) und aktuellem Umgebungs-Stand (`dev` only) ergänzt
- **OPERATIONS.md:** Hinweise zu Umgebung (`dev` only) und AWS-Naming an prominenter Stelle ergänzt; Post-Release-Checkliste auf `dev`-Deployment angepasst

### Changed (2026-02-25 — ECS Smoke-Test + Push-Trigger)
- **`.github/workflows/deploy.yml`:** Trigger für Push auf `main` aktiviert (zusätzlich zu `workflow_dispatch`).
- **`.github/workflows/deploy.yml`:** Nach `aws ecs wait services-stable` Smoke-Test auf `SERVICE_HEALTH_URL` ergänzt (HTTP-Check auf `/health`); bei fehlender/leer gesetzter Variable wird der Schritt mit Notice übersprungen.
- **`README.md`:** CI/CD-Beschreibung auf aktiven Push-Trigger aktualisiert; neue Variable `SERVICE_HEALTH_URL` dokumentiert.
- **`docs/DEPLOYMENT_AWS.md`:** Workflow-Trigger, Smoke-Test-Schritt und Variable `SERVICE_HEALTH_URL` ergänzt.

### Changed (2026-02-25 — Architektur-Doku auf Ist-Stand gebracht)
- **`docs/ARCHITECTURE.md`:** Von Planungsstand auf aktuellen MVP-Betriebsstand aktualisiert (ECS/Fargate Deploy via GitHub Actions, Trigger, Webservice-Endpunkte, Task-Definition-Update-Flow, optionale Smoke-Tests, relevante GitHub Secrets/Variables).

### Changed (2026-02-25 — Backlog-Konsolidierung)
- **`docs/BACKLOG.md`:** Neu angelegt; alle offenen Punkte aus README + `docs/*.md` in priorisierten, umsetzbaren Backlog überführt (P0/P1/P2, Aufwand, Abhängigkeiten, Akzeptanzkriterien).
- **`docs/ARCHITECTURE.md`:** Redundante Liste „Offene Punkte“ auf zentrale Backlog-Pflege umgestellt.
- **`docs/DEPLOYMENT_AWS.md`:** Redundante TODO-Liste auf zentrale Backlog-Pflege umgestellt.
- **`docs/OPERATIONS.md`:** Verweis auf zentrale Backlog-Pflege ergänzt; lokaler TODO-Hinweis im Setup auf Backlog referenziert.
- **`README.md`:** Dokumentationsübersicht um `docs/BACKLOG.md` ergänzt.

### Changed (2026-02-25 — Monitoring/Alerting MVP für ECS)
- **`docs/OPERATIONS.md`:** Monitoring-MVP ergänzt (CloudWatch Log Group + Retention-Standard, minimale Alarmdefinitionen, HTTP-Health-Check-Guidance, Incident-Runbook mit konkreten AWS-CLI-Kommandos).
- **`docs/DEPLOYMENT_AWS.md`:** Monitoring-Status auf MVP-Stand aktualisiert; Teilfortschritt für BL-08 dokumentiert (inkl. klarer Restarbeiten).

### Added (2026-02-25 — Read-only Ops Scripts)
- **`scripts/check_ecs_service.sh`:** Read-only ECS-Triage-Helper (Service-Status, letzte Events, laufende Tasks/Containerzustände).
- **`scripts/tail_logs.sh`:** Read-only CloudWatch-Log-Tail-Helper (Region/LogGroup/Since/Follow parametrisierbar).

### Changed (2026-02-25 — BL-04 Tagging-Audit abgeschlossen)
- **`docs/TAGGING_AUDIT.md`:** Neu angelegt mit Inventar und Audit-Tabelle für dev-Ressourcen (ECS Cluster/Service, Task Definition Family inkl. aktiver Revisionen, ECR, relevante CloudWatch Log Groups).
- **AWS Ressourcen:** Fehlende Standard-Tags (`Environment`, `ManagedBy`, `Owner`, `Project`) auf aktiven ECS Task Definitions `swisstopo-dev-api:1` bis `:10` ergänzt (nicht-destruktiv).
- **`docs/BACKLOG.md`:** BL-04 auf „abgeschlossen“ gesetzt und auf Audit-Dokument verlinkt.

---

## [0.1.0] — 2026-02-25

### Added
- Initial Commit: Repository-Grundstruktur angelegt

[Unreleased]: https://github.com/nimeob/geo-ranking-ch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nimeob/geo-ranking-ch/releases/tag/v0.1.0
