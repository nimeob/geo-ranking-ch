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
- **AWS Ressourcen:** Fehlende Standard-Tags (`Environment`, `ManagedBy`, `Owner`, `Project`) auf aktiven ECS Task Definitions `swisstopo-dev-api:1` bis `:7` ergänzt (nicht-destruktiv).
- **`docs/BACKLOG.md`:** BL-04 auf „abgeschlossen“ gesetzt und auf Audit-Dokument verlinkt.

---

## [0.1.0] — 2026-02-25

### Added
- Initial Commit: Repository-Grundstruktur angelegt

[Unreleased]: https://github.com/nimeob/geo-ranking-ch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nimeob/geo-ranking-ch/releases/tag/v0.1.0
