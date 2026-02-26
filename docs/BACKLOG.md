# Backlog (konsolidiert)

> Quelle: konsolidierte offene Punkte aus `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT_AWS.md`, `docs/OPERATIONS.md`.
> Stand: 2026-02-26

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
- **Status:** ✅ abgeschlossen (2026-02-26)
- **Akzeptanzkriterien:**
  - Health-Probe-Ressourcen (Lambda, IAM, EventBridge, Alarm) als optionale Terraform-Ressourcen modelliert. ✅
  - Existing Setup-Script bleibt als Fallback dokumentiert. ✅
  - `terraform plan` ist drift-arm und ohne destruktive Default-Änderungen. ✅
- **Nachweis:**
  - ✅ IaC-Ressourcen vollständig in `infra/terraform/health_probe.tf` modelliert (inkl. EventBridge-Permission + IAM-Policies) mit `manage_health_probe=false` als Safe-Default.
  - ✅ Terraform-Validierung erfolgreich ausgeführt (`terraform validate` mit Terraform v1.11.4).
  - ✅ Default-Plan verifiziert: keine Infrastrukturänderungen (nur Output-State bei leerem Statefile).
  - ✅ Import-first-Plan verifiziert (`manage_health_probe=true` + vollständige Imports): **0 add / 4 change / 0 destroy** (nur in-place Drift-Korrekturen, keine destruktiven Aktionen).
  - ✅ Import-Kommandos für alle Health-Probe-Objekte erweitert in `infra/terraform/README.md` und `docs/DEPLOYMENT_AWS.md` (inkl. `aws_lambda_permission`, `aws_iam_role_policy`, `aws_iam_role_policy_attachment`).

### BL-15 — Legacy-IAM-User Decommission-Readiness (read-only)
- **Priorität:** P2
- **Aufwand:** S
- **Abhängigkeiten:** BL-03
- **Status:** 🟡 in Umsetzung (2026-02-26)
- **Akzeptanzkriterien:**
  - Read-only Evidenz zu aktueller Nutzung des Legacy-Users `swisstopo-api-deploy` dokumentiert. ✅
  - Risikoarme Decommission-Checkliste (ohne direkte Abschaltung) liegt vor. ✅
  - Entscheidungsvorlage in `docs/AWS_INVENTORY.md` oder dediziertem Runbook verlinkt. ✅
- **Nachweis:**
  - ✅ Neues Runbook `docs/LEGACY_IAM_USER_READINESS.md` mit verifizierter Ist-Lage (aktiver Key, Last-Used, Policy-Set), Access-Advisor-Auszug und CloudTrail-Hinweisen.
  - ✅ Decommission-Checkliste in 3 Phasen (Vorbereitung, Controlled Cutover, Finalisierung) inkl. klarer Rollback-Strategie dokumentiert.
  - ✅ Entscheidungs-Template („Go/No-Go") ergänzt; aktueller Vorschlag: **No-Go**, solange aktive Consumer nicht vollständig migriert sind.
  - ✅ Repo-scope Consumer-Inventar via `scripts/audit_legacy_aws_consumer_refs.sh` ergänzt (Workflow-/Script-Referenzen + aktiver Caller-ARN).
  - ✅ Host-level Runtime-Baseline via `scripts/audit_legacy_runtime_consumers.sh` ergänzt (Environment/Cron/Systemd/OpenClaw-Config read-only geprüft; keine persistierten Key-Referenzen auf dem Host gefunden).
  - ✅ Externe Consumer-Matrix/Tracking ergänzt: `docs/LEGACY_CONSUMER_INVENTORY.md` (Known Consumers, offene externe Targets, Exit-Kriterien).
  - ✅ CloudTrail-Fingerprint-Audit ergänzt: `scripts/audit_legacy_cloudtrail_consumers.sh` (read-only, gruppiert Events nach `source_ip` + `user_agent`, `LookupEvents` standardmäßig gefiltert).
  - ✅ Read-only Recheck ausgeführt (2026-02-26): `audit_legacy_aws_consumer_refs.sh` => Exit `10`; `audit_legacy_runtime_consumers.sh` => Exit `30`; `LOOKBACK_HOURS=6 audit_legacy_cloudtrail_consumers.sh` => Exit `10` (Legacy-Aktivität weiter aktiv, primärer Non-AWS-Fingerprint `76.13.144.185`, zusätzlich AWS-Service-Delegation via `lambda.amazonaws.com`).
  - ✅ Recheck vertieft (2026-02-26, 8h): `LOOKBACK_HOURS=8 audit_legacy_cloudtrail_consumers.sh` => Exit `10` (404 ausgewertete Events; Fingerprints stabil), `check_bl17_oidc_assumerole_posture.sh` => Exit `30` (OIDC-Workflow korrekt, Runtime-Caller weiterhin Legacy); zusätzlich `sts:AssumeRole`-Events auf demselben Fingerprint sichtbar.
- **Blocker:**
  - Aktive Nutzung des Legacy-Users ist weiterhin nachweisbar (CloudTrail/AccessKeyLastUsed + aktueller Caller-ARN), daher noch keine sichere Abschaltfreigabe.
  - Runtime-Audit zeigt weiterhin gesetzte AWS-Key-Variablen im laufenden Kontext; Quelle der Injection ist noch nicht final eliminiert.
  - CloudTrail-Fingerprints zeigen wiederkehrende Non-AWS-Quelle (`76.13.144.185`); trotz sichtbarer `sts:AssumeRole`-Events ist AssumeRole-first im Runtime-Default noch nicht erreicht und externe/weitere Runner außerhalb dieses Hosts sind weiterhin nicht vollständig ausgeschlossen.
- **Next Actions:**
  1. ✅ Repo-scope Consumer-Inventar abgeschlossen (Workflow OIDC-konform, lokale/Runner-Skripte als offene Consumer identifiziert).
  2. 🟡 Runtime-Consumer außerhalb des Repos vollständig inventarisieren (Host-Baseline + CloudTrail-Fingerprints erledigt; Trackingfile `docs/LEGACY_CONSUMER_INVENTORY.md` angelegt; externe Runner/Hosts + Fremd-Cron-Umgebungen pro Target gegen Fingerprint `76.13.144.185` verifizieren).
  3. Für offene Consumer auf OIDC/AssumeRole migrieren (zuerst bekannte OpenClaw-Runtime-Credential-Injection entfernen und AWS-Ops standardmäßig über `scripts/aws_exec_via_openclaw_ops.sh` routen, dann externe Targets).
  4. Geplantes Wartungsfenster: Key nur deaktivieren (nicht löschen), 24h beobachten, dann Entscheidung zur Finalisierung.

### BL-17 — OpenClaw AWS-Betrieb auf OIDC-first umstellen (Legacy nur Fallback)
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-03, BL-15
- **Status:** 🟡 in Umsetzung (2026-02-26)
- **Akzeptanzkriterien:**
  - Primärpfad für AWS-Operationen läuft über GitHub Actions OIDC.
  - Legacy-Key wird nur als dokumentierter Fallback genutzt.
  - Fallback-Nutzung wird protokolliert und schrittweise auf 0 reduziert.
  - OIDC-first/Fallback-Runbook ist dokumentiert (Pfad wird bei BL-17-Start final fixiert).
- **Umgesetzt (laufend):**
  - `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md` auf Hybrid-Standard präzisiert (OIDC für CI/CD + AssumeRole-first für direkte OpenClaw-Ops).
  - `scripts/aws_exec_via_openclaw_ops.sh` ergänzt (führt beliebige AWS-CLI-Subcommands in temporärer `openclaw-ops-role` Session aus).
  - `scripts/check_bl17_oidc_assumerole_posture.sh` ergänzt (OIDC-Workflow-Marker, statische-Key-Checks, Caller-Klassifikation + Kontext-Audits in einem Lauf).

### BL-18 — Service funktional weiterentwickeln + als Webservice E2E testen
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-17
- **Status:** 🟡 in Umsetzung (2026-02-26)
- **Akzeptanzkriterien:**
  - Mindestens ein fachlicher Ausbau am Service ist implementiert und dokumentiert.
  - API-/Webservice-Endpunkte sind per End-to-End-Tests validiert (lokal + dev).
  - Negativfälle (4xx/5xx), Timeouts und Auth-Fälle sind in Tests abgedeckt.
  - Testergebnisse sind nachvollziehbar dokumentiert (Runbook/CI-Output).
- **Umgesetzt (Iteration 2026-02-26):**
  - `src/web_service.py`: optionales Bearer-Auth-Gate (`API_AUTH_TOKEN`), Timeout-Parameterisierung (`timeout_seconds`, `ANALYZE_*_TIMEOUT_SECONDS`) inkl. endlicher Numerik-Validierung (`nan`/`inf` → `400 bad_request`), Mode-Validierung und `TimeoutError -> 504` Mapping ergänzt.
  - `tests/test_web_e2e.py`: lokale E2E-Abdeckung inkl. 200/400/401/404/500/504 aufgebaut (inkl. Negativfall non-finite `timeout_seconds`).
  - `tests/test_web_e2e_dev.py`: dev-E2E gegen `DEV_BASE_URL` ergänzt (mit optionalem `DEV_API_AUTH_TOKEN`).
  - `scripts/run_webservice_e2e.sh`: einheitlicher Runner für lokal + optional dev.
  - `docs/BL-18_SERVICE_E2E.md`: Ist-Analyse + Runbook dokumentiert.

### BL-18.1 — Erfolgreicher API-Test über Internet (OpenClaw-Agent)
- **Priorität:** P1
- **Aufwand:** S
- **Abhängigkeiten:** BL-18
- **Status:** 🟡 in Umsetzung (2026-02-26)
- **Akzeptanzkriterien:**
  - Reproduzierbarer Smoke-Test ruft `POST /analyze` über öffentliche URL auf.
  - Test prüft mindestens HTTP-Status `200`, `ok=true` und vorhandenes `result`-Objekt.
  - Test ist per Script ausführbar (inkl. optionalem Bearer-Token).
  - Kurzer Nachweislauf ist dokumentiert (stdout/Runbook-Eintrag).
- **Umgesetzt (Iteration 2026-02-26, laufend):**
  - `scripts/run_remote_api_smoketest.sh` ergänzt und gehärtet (Retry-Handling, Request-ID, optionale JSON-Artefaktausgabe via `SMOKE_OUTPUT_JSON`, default Echo-Validierung von Request-ID in Header + JSON).
  - `src/web_service.py` um Request-Korrelation für `/analyze` erweitert (erste nicht-leere ID aus `X-Request-Id`/`X-Correlation-Id` wird in Response-Header + JSON-Feld `request_id` gespiegelt) für reproduzierbare Remote-Diagnosen.
  - `scripts/run_remote_api_stability_check.sh` ergänzt (Mehrfachlauf mit NDJSON-Report + Fail-Threshold für kurze Stabilitäts-/Abnahmeläufe).
  - `tests/test_remote_smoke_script.py` ergänzt (lokale E2E-Validierung des Smoke-Skripts inkl. Auth-Pfad/Fehlpfad + Request-ID-Echo-Nachweis) und um Happy-Paths für `DEV_BASE_URL=.../health`, verkettete Suffixe (`.../health/analyze`), gemischte Suffix-Reihenfolge (`.../analyze/health//`), wiederholte Suffix-Ketten (`.../health/analyze/health/analyze///`), wiederholte Reverse-Suffix-Ketten mit Schema-Case + Whitespace (`"  HTTP://.../AnAlYzE/health/analyze/health///  "`) sowie deren Variante mit internem Double-Slash (`"  HTTP://.../AnAlYzE//health/analyze/health///  "`), wiederholte Forward-Suffix-Ketten mit internem Double-Slash (`"  HTTP://.../health//analyze/health/analyze///  "`), case-insensitive Suffixe (`.../HeAlTh/AnAlYzE`), getrimmte Whitespace-Inputs (`"  http://.../health  "`), die kombinierte Normalisierung (`"  HTTP://.../HeAlTh/AnAlYzE/  "`), die kombinierte Reverse-Suffix-Kette (`"  HTTP://.../AnAlYzE/health//  "`), redundante trailing-Slash-Ketten (`.../health//analyze//`) sowie grossgeschriebenes HTTP-Schema (`HTTP://...`) erweitert (URL-Normalisierung + Schema-Handling auf `/analyze` reproduzierbar abgesichert).
  - `tests/test_remote_smoke_script.py` enthält zusätzlich Negativfälle für `DEV_BASE_URL` mit Query/Fragment sowie whitespace-only Inputs (jeweils reproduzierbarer `exit 2`).
  - `tests/test_remote_smoke_script.py` deckt jetzt auch Fehlkonfigurationen für `CURL_RETRY_DELAY=-1`, `SMOKE_ENFORCE_REQUEST_ID_ECHO=2` sowie zu lange `SMOKE_REQUEST_ID`-Werte (`>128` Zeichen) reproduzierbar mit `exit 2` ab.
  - `tests/test_remote_smoke_script.py` ergänzt einen Negativfall für eingebettete Whitespaces in `DEV_BASE_URL` (z. B. `http://.../hea lth`) und sichert fail-fast `exit 2` mit klarer CLI-Fehlermeldung.
  - `scripts/run_remote_api_smoketest.sh` validiert `DEV_BASE_URL` jetzt zusätzlich auf eingebettete Whitespaces/Steuerzeichen und bricht bei fehlerhaften Inputs früh mit `exit 2` ab.
  - `scripts/run_remote_api_smoketest.sh` validiert `SMOKE_REQUEST_ID` fail-fast (Whitespace-only, Steuerzeichen und IDs >128 Zeichen werden mit `exit 2` abgewiesen; valide IDs werden vor Echo-Check getrimmt).
  - `scripts/run_remote_api_smoketest.sh` URL-Normalisierung ergänzt (trimmt führende/trailing Whitespaces, normalisiert `/health`/`/analyze`-Suffixe auch verkettet und case-insensitive) + robuste http(s)-Schema-Validierung (inkl. grossgeschriebener Schemata wie `HTTP://`) zur Runbook-Reproduzierbarkeit.
  - `scripts/run_remote_api_smoketest.sh` rejectet `DEV_BASE_URL` mit Query/Fragment (`?`/`#`) jetzt fail-fast mit `exit 2`, damit der abgeleitete `/analyze`-Pfad reproduzierbar bleibt.
  - `scripts/run_remote_api_smoketest.sh` rejectet `DEV_BASE_URL` mit Userinfo (`user:pass@host`) fail-fast mit `exit 2`, um Credential-Leaks in Shell-History/Logs zu vermeiden.
  - `scripts/run_remote_api_smoketest.sh` validiert `DEV_BASE_URL` nach Normalisierung zusätzlich auf gültigen Host/Port (`hostname` + parsbarer Port), damit Fehlkonfigurationen wie `:abc` oder out-of-range Ports (`:70000`) früh mit `exit 2` statt späterem curl-Fehler scheitern.
  - `scripts/run_remote_api_smoketest.sh` validiert Eingabeparameter strikt (`SMOKE_TIMEOUT_SECONDS`/`CURL_MAX_TIME` = endliche Zahl > 0, `CURL_RETRY_COUNT`/`CURL_RETRY_DELAY` Ganzzahl >= 0) und bricht bei Fehlwerten reproduzierbar mit `exit 2` ab.
  - `tests/test_remote_smoke_script.py` um Negativfälle für ungültige Timeout-/Retry-Parameter erweitert (früher Blocker/Traceback → jetzt klare CLI-Fehlermeldung).
  - `tests/test_remote_smoke_script.py` deckt jetzt auch ungültige Ports in `DEV_BASE_URL` (`:abc`, `:70000`) reproduzierbar mit `exit 2` ab.
  - `tests/test_remote_stability_script.py` ergänzt (lokale E2E-Validierung des Stabilitätsrunners inkl. Stop-on-first-fail-, NDJSON- und Request-ID-Korrelationsnachweis) und um Guard-Fälle erweitert: fehlendes Smoke-JSON trotz `rc=0` **sowie** Smoke-Reports mit `status!=pass` werden reproduzierbar als Fehlrun erkannt.
  - `scripts/run_remote_api_stability_check.sh` validiert `STABILITY_STOP_ON_FIRST_FAIL` strikt (`0|1`), unterstützt optionales Script-Override via `STABILITY_SMOKE_SCRIPT` (Tests/Debug) und behandelt fehlende/leer gebliebene Smoke-Reports sowie Non-PASS-Reports fail-safe als Fehlrun.
  - `.github/workflows/deploy.yml` um optionalen `/analyze`-Smoke-Test nach Deploy erweitert (gesteuert via `SERVICE_BASE_URL` + optional `SERVICE_API_AUTH_TOKEN`).
  - `docs/BL-18_SERVICE_E2E.md` um Reproduzierbarkeit/Stabilitäts-Runbook erweitert (inkl. lokalem 2-Run-Nachweis: `pass=2`, `fail=0`).
  - `tests/test_web_e2e.py` um API-E2E-Guard erweitert: ist `X-Request-Id` leer/whitespace, fällt der Service deterministisch auf `X-Correlation-Id` zurück und spiegelt diese ID in Header+JSON.
  - `scripts/run_remote_api_smoketest.sh` unterstützt jetzt `SMOKE_REQUEST_ID_HEADER=request|correlation` (default `request`) und erlaubt damit reproduzierbare Remote-Fallback-Checks über `X-Correlation-Id`; Header-/Echo-Flags werden vor Validierung zusätzlich getrimmt, ungültige Modi bleiben fail-fast mit `exit 2`.
  - `tests/test_remote_smoke_script.py` ergänzt Happy-Path-Abdeckung für `SMOKE_REQUEST_ID_HEADER=correlation` sowie für getrimmte Eingaben (`"  Correlation  "`, `SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 "`) und enthält weiterhin den Negativtest für ungültige Header-Modi.
  - Real-Run-Nachweis aktualisiert (lokal, 2026-02-26): `run_remote_api_smoketest.sh` Exit `0` + `run_remote_api_stability_check.sh` Exit `0` mit Request-ID-Echo in Header+JSON bestätigt; zuletzt im Worker-C-Langlauf mit **getrimmtem** Correlation-Header-Mode (`SMOKE_REQUEST_ID_HEADER="  Correlation  "`), verketteter Base-URL (`DEV_BASE_URL="  HTTP://127.0.0.1:56915/health/analyze/health///  "`) und erweitertem Stabilitätslauf (`STABILITY_RUNS=5`), Evidenz in `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772096909.json` + `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772096909.ndjson` (`pass=5`, `fail=0`, Stability-Run-IDs mit PID-Suffix).
  - Reproduzierbarkeits-Check erneuert: `./scripts/run_webservice_e2e.sh` erneut erfolgreich (`53 passed`, Exit `0`) direkt vor dem dedizierten Worker-C-Langlauf (Smoke + 5x Stabilität).

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

1. **BL-13** (Doku-Konsistenz) ✅
2. **BL-14** (Health-Probe IaC-Parität) ✅
3. **BL-15** (Legacy-IAM-Readiness) 🟡
4. **BL-17** (OpenClaw OIDC-first + Legacy-Fallback) ⏳
5. **BL-18** (Service weiterentwickeln + Webservice E2E-Tests) ⏳
