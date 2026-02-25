# Backlog (konsolidiert)

> Quelle: konsolidierte offene Punkte aus `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT_AWS.md`, `docs/OPERATIONS.md`.
> Stand: 2026-02-25

## Legende

- **Priorität:** `P0` (kritisch/zeitnah), `P1` (wichtig), `P2` (nachgelagert)
- **Aufwand:** `S` (≤ 0.5 Tag), `M` (1–3 Tage), `L` (> 3 Tage)

---

## Backlog-Items

### BL-01 — IaC als Source of Truth für `dev`
- **Priorität:** P0
- **Aufwand:** L
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - Infrastruktur für `dev` ist in IaC abgebildet (CDK, Terraform oder CloudFormation).
  - IaC-Definitionen versioniert im Repository und reproduzierbar ausführbar.
  - Mindestens ein dokumentierter Apply/Deploy-Lauf für `dev` ist nachvollziehbar.
- **Nachweis:**
  - ✅ IaC-Artefakte für dev-Kernressourcen versioniert: `infra/terraform/*` (ECS, ECR, CloudWatch Logs, S3) inkl. Import-first-Runbook.
  - ✅ Reproduzierbarer Read-only-Precheck + Import-Hilfe: `scripts/check_import_first_dev.sh`.
  - ✅ Dokumentierter dev-Deploy-Lauf: GitHub Actions `push` Run `22417939827` (Rollout `services-stable` + Smoke-Test erfolgreich), siehe `docs/DEPLOYMENT_AWS.md`.

### BL-02 — CI/CD-Deploy in `dev` faktisch verifizieren
- **Priorität:** P0
- **Aufwand:** S
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - Mindestens ein erfolgreicher GitHub-Workflow-Run per Push auf `main` ist nachgewiesen.
  - ECS-Rollout endet auf `services-stable`.
  - Smoke-Test über `SERVICE_HEALTH_URL` auf `/health` ist erfolgreich dokumentiert.
- **Nachweis:** Run-URL + Ergebnis werden in `docs/DEPLOYMENT_AWS.md` oder `docs/OPERATIONS.md` festgehalten.

### BL-03 — Separaten Deploy-User mit Least-Privilege aufsetzen
- **Priorität:** P0
- **Aufwand:** M
- **Abhängigkeiten:** BL-01
- **Akzeptanzkriterien:**
  - Dedizierter IAM-Deploy-User/Rolle für dieses Repo existiert.
  - Rechte sind auf notwendige Aktionen (ECR/ECS/ggf. IaC) begrenzt.
  - GitHub-Secrets sind auf den neuen Principal umgestellt.
- **Status (finalisiert 2026-02-26):** ✅ abgeschlossen
  - ✅ Workflow-basierte Minimalrechte hergeleitet und als Artefakte abgelegt: `infra/iam/deploy-policy.json` + `infra/iam/README.md`
  - ✅ OIDC-Deploy-Role `swisstopo-dev-github-deploy-role` bestätigt und mit der Repo-Policy `swisstopo-dev-github-deploy-policy` verbunden
  - ✅ Policy-Fix ausgerollt: `ecs:DescribeTaskDefinition` auf `Resource: "*"` gesetzt (AWS IAM Version `v2` als Default)
  - ✅ End-to-End Nachweis erfolgreich: `workflow_dispatch` Run `22417749775` + `push` Run `22417939827` jeweils mit `services-stable` und erfolgreichem Smoke-Test
  - ✅ **BL-03 final:** Trust-Policy versioniert (`infra/iam/trust-policy.json`), `infra/iam/README.md` auf finalen Stand gebracht (OIDC live, Policy-Drift-Check, E2E-Nachweis), `docs/DEPLOYMENT_AWS.md` Deploy-Principal korrigiert (OIDC-Role als aktueller Principal, IAM-User als Legacy markiert)

### BL-04 — AWS-Tagging-Standard auf Bestandsressourcen durchsetzen
- **Priorität:** P1
- **Aufwand:** S
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Umsetzungshinweis:** Audit + Maßnahmen dokumentiert in [`docs/TAGGING_AUDIT.md`](TAGGING_AUDIT.md).
- **Akzeptanzkriterien:**
  - Relevante `dev`-Ressourcen tragen die Tags `Environment`, `ManagedBy`, `Owner`, `Project`.
  - Abweichungen sind bereinigt oder als Ausnahme dokumentiert.

### BL-05 — Netzwerk- und Ingress-Zielbild festlegen
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-01
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - Entscheidung zu VPC-Topologie (Public/Private Subnets, Security Groups) dokumentiert.
  - Entscheidung dokumentiert, ob API Gateway benötigt wird oder ALB direkt genügt.
  - Entscheidung zu Domain/Route53 (inkl. Bedingungen für öffentliche API) dokumentiert.
- **Nachweis:** [`docs/NETWORK_INGRESS_DECISIONS.md`](NETWORK_INGRESS_DECISIONS.md)

### BL-06 — Datenhaltungsbedarf klären (RDS/DynamoDB)
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-05
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - Entscheidung dokumentiert, ob persistente Datenbankkomponenten benötigt werden.
  - Falls ja: gewählter Dienst (RDS oder DynamoDB) mit Minimaldesign und Betriebsfolgen beschrieben.
  - Falls nein: Begründung und Konsequenzen (z. B. Stateless-Betrieb) dokumentiert.
- **Nachweis:** [`docs/DATA_AND_API_SECURITY.md`](DATA_AND_API_SECURITY.md)

### BL-07 — API-Sicherheitskonzept konkretisieren
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-05
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - AuthN/AuthZ-Ansatz für `/analyze` dokumentiert.
  - Rate-Limit-Strategie inklusive Durchsetzungspunkt festgelegt.
  - Mindestanforderungen für Secret-/Token-Handling dokumentiert.
- **Nachweis:** [`docs/DATA_AND_API_SECURITY.md`](DATA_AND_API_SECURITY.md)

### BL-08 — Monitoring & Alerting-Baseline in `dev`
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-02
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - CloudWatch Logs und Kernmetriken sind aktiv und geprüft. ✅
  - Mindestens Alarme für Service-Ausfall und Fehlerquote existieren. ✅
  - Alarm-Empfänger/Kanal ist definiert und getestet. ✅ (Telegram-Bot Empfangsnachweis erbracht)
- **Umgesetzt:**
  - ✅ Baseline-Script `scripts/setup_monitoring_baseline_dev.sh` angelegt und ausgeführt.
  - ✅ SNS Topic `arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts` erstellt.
  - ✅ CloudWatch Metric Filters aktiv: `HttpRequestCount`, `Http5xxCount` (Namespace `swisstopo/dev-api`).
  - ✅ CloudWatch Alarme aktiv: `swisstopo-dev-api-running-taskcount-low`, `swisstopo-dev-api-http-5xx-rate-high`.
  - ✅ Kanaltest durchgeführt via `sns publish` (MessageId `7ebdaccb-bba3-5a62-b442-ced2c32900b7`).
  - ✅ Read-only Prüfscript `scripts/check_monitoring_baseline_dev.sh` ergänzt (inkl. Telegram-Checks: Lambda-State, SNS-Sub, Chat-ID, SSM-Parameter).
  - ✅ Telegram-Alerting vollständig als IaC vorbereitet (2026-02-25):
    - Lambda-Quellcode: `infra/lambda/sns_to_telegram/lambda_function.py`
    - Terraform: `infra/terraform/lambda_telegram.tf` (Lambda + IAM + SNS-Sub, Flag `manage_telegram_alerting`)
    - Setup-Script: `scripts/setup_telegram_alerting_dev.sh` (Fallback ohne Terraform)
    - Nachrichtenformat: Alarmname, State, Reason, Region, Account, Timestamp (robust bei fehlenden Feldern)
    - Secret-Verwaltung: Bot-Token in SSM SecureString (`/swisstopo/dev/telegram-bot-token`), NICHT im State/Repo
  - ✅ Deployment durchgeführt (SSM + Lambda + SNS-Subscription aktiv) und Testalarm ausgelöst (`ALARM` → `OK`).
  - ✅ Empfang in Telegram-Chat bestätigt (Alarmzustände `ALARM` und `OK` sichtbar).

### BL-09 — `staging`/`prod` und Promotion-Strategie vorbereiten
- **Priorität:** P2
- **Aufwand:** L
- **Abhängigkeiten:** BL-01, BL-05, BL-07, BL-08
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - Zielarchitektur für `staging` und `prod` ist definiert.
  - Promotion-Pfad (`dev` → `staging` → `prod`) inkl. Gates dokumentiert.
  - Rollback- und Freigabeprozess pro Umgebung ist festgelegt.
- **Nachweis:** [`docs/ENV_PROMOTION_STRATEGY.md`](ENV_PROMOTION_STRATEGY.md)

### BL-10 — Lokale Dev-Baseline konsolidieren (Python-Version + pre-commit)
- **Priorität:** P2
- **Aufwand:** S
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - Unterstützte Python-Version ist verbindlich dokumentiert (ohne „zu verifizieren“).
  - `.pre-commit-config.yaml` ist vorhanden oder bewusst verworfen (mit kurzer Begründung).
  - `docs/OPERATIONS.md` Setup-Abschnitt ist entsprechend bereinigt.

### BL-11 — AWS-Inventory & Konfigurations-Dokumentation (nachbaubar)
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-01
- **Status:** ✅ abgeschlossen (2026-02-26)
- **Ziel:** Alle für dieses Projekt in AWS erstellten Ressourcen inkl. zentraler Konfiguration so dokumentieren, dass Dritte den Stand nachvollziehen und strukturiert nachbauen können.
- **Akzeptanzkriterien:**
  - Zentrales Inventar-Dokument vorhanden (z. B. `docs/AWS_INVENTORY.md`) mit Ressourcen nach Bereichen (IAM, ECR, ECS, CloudWatch, S3, Networking, optional Route53/API Gateway). ✅
  - Pro Ressource mindestens enthalten: Name/ARN, Region, Zweck, owner/relevante Tags, zentrale Konfig-Parameter. ✅
  - Für kritische Ressourcen sind Rebuild-Hinweise dokumentiert (Reihenfolge, Abhängigkeiten, benötigte Variablen). ✅
  - Klar markiert, was IaC-managed ist und was noch manuell betrieben wird. ✅
  - Read-only Erfassungs-/Exportkommandos sind dokumentiert (keine Secrets im Repo). ✅
- **Nachweis:** [`docs/AWS_INVENTORY.md`](AWS_INVENTORY.md) — vollständig verifiziert via read-only AWS-Abfragen (Stand 2026-02-26)

### BL-12 — HTTP Uptime Probe für `/health` aktivieren (dev)
- **Priorität:** P1
- **Aufwand:** S
- **Abhängigkeiten:** BL-08
- **Status:** ✅ abgeschlossen (2026-02-25)
- **Akzeptanzkriterien:**
  - Produktive HTTP-Probe auf `GET /health` läuft in dev.
  - Probe integriert in bestehenden Alarm → SNS → Telegram Stack.
  - Prüfbarer Nachweis (Logs, Metrik, Alarm).
  - Doku in OPERATIONS.md, DEPLOYMENT_AWS.md aktualisiert.
- **Umgesetzt:**
  - ✅ Lambda `swisstopo-dev-health-probe` (Python 3.12): löst ECS-Task-IP dynamisch auf (kein ALB nötig), prüft HTTP GET `/health`, publiziert CloudWatch-Metrik `HealthProbeSuccess`.
  - ✅ IAM-Role `swisstopo-dev-health-probe-role` (Minimal-Privilege: ECS/EC2 IP-Lookup + CW PutMetricData + Logs).
  - ✅ EventBridge Scheduled Rule `swisstopo-dev-health-probe-schedule` (rate 5 min, ENABLED).
  - ✅ CloudWatch Alarm `swisstopo-dev-api-health-probe-fail` (HealthProbeSuccess < 1, 3/3 Perioden, treat-missing=breaching) → SNS `swisstopo-dev-alerts` → Telegram.
  - ✅ Erster Testlauf erfolgreich: IP `18.184.115.244` aufgelöst, HTTP 200, `HealthProbeSuccess = 1` publiziert.
  - ✅ Scripts: `scripts/setup_health_probe_dev.sh` (idempotent), `scripts/check_health_probe_dev.sh` (read-only).
  - ✅ Quellcode: `infra/lambda/health_probe/lambda_function.py`.

### BL-13 — Deployment-Doku konsolidieren (Backlog- und Statuskonsistenz)
- **Priorität:** P1
- **Aufwand:** S
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-02-26)
- **Akzeptanzkriterien:**
  - `docs/DEPLOYMENT_AWS.md` enthält keine widersprüchlichen „offen“-Aussagen zu bereits abgeschlossenen BL-Items.
  - Backlog-Referenzen sind auf aktuelle BL-Range aktualisiert.
  - Änderung ist im Changelog dokumentiert.
- **Nachweis:**
  - ✅ Abschnitt „Offene Punkte / TODOs“ in `docs/DEPLOYMENT_AWS.md` bereinigt und auf konsolidierte Backlog-Pflege umgestellt.
  - ✅ Veralteter Hinweis „HTTP-Uptime-Probe noch offen“ entfernt (BL-12 bereits abgeschlossen).
  - ✅ Referenz auf aktuelle Backlog-Spanne (`BL-01` bis `BL-15`) aktualisiert.

### BL-14 — Health-Probe in Terraform überführen (IaC-Parität)
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-12
- **Status:** ⏳ offen
- **Akzeptanzkriterien:**
  - Health-Probe-Ressourcen (Lambda, IAM, EventBridge, Alarm) als optionale Terraform-Ressourcen modelliert.
  - Existing Setup-Script bleibt als Fallback dokumentiert.
  - `terraform plan` ist drift-arm und ohne destruktive Default-Änderungen.

### BL-15 — Legacy-IAM-User Decommission-Readiness (read-only)
- **Priorität:** P2
- **Aufwand:** S
- **Abhängigkeiten:** BL-03
- **Status:** ⏳ offen
- **Akzeptanzkriterien:**
  - Read-only Evidenz zu aktueller Nutzung des Legacy-Users `swisstopo-api-deploy` dokumentiert.
  - Risikoarme Decommission-Checkliste (ohne direkte Abschaltung) liegt vor.
  - Entscheidungsvorlage in `docs/AWS_INVENTORY.md` oder dediziertem Runbook verlinkt.

---

## Nacht-Plan (abgeschlossen)

### Parallel machbar (mehrere Personen/Tracks)
- **Track A:** BL-02 (Workflow-Verifikation)
- **Track B:** BL-04 (Tagging)
- **Track C:** BL-10 (lokale Dev-Baseline)
- **Track D:** Vorarbeiten für BL-03 (IAM-Policy-Entwurf)

### Sequenziell (wegen fachlicher Abhängigkeiten)
1. **BL-01** (IaC-Basis)
2. **BL-05** (Netzwerk/Ingress-Entscheide)
3. **BL-06 + BL-07** (Datenhaltung + API-Sicherheit)
4. **BL-08** (Monitoring/Alerting auf stabiler Basis)
5. **BL-09** (staging/prod + Promotion)

## Folge-Sequenz (ab 2026-02-26)

1. **BL-13** (Doku-Konsistenz)
2. **BL-14** (Health-Probe IaC-Parität)
3. **BL-15** (Legacy-IAM-Readiness)
