# Backlog (konsolidiert)

> Quelle: konsolidierte offene Punkte aus `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT_AWS.md`, `docs/OPERATIONS.md`.
> Stand: 2026-03-02

## Legende

- **Priorität:** `P0` (kritisch/zeitnah), `P1` (wichtig), `P2` (nachgelagert)
- **Aufwand:** `S` (≤ 0.5 Tag), `M` (1–3 Tage), `L` (> 3 Tage)

---

<!-- NOW_NEXT_LATER:START -->
## Now / Next / Later (auto-synced)

Regelwerk:
- **Now:** aktive Arbeit (`status:in-progress` oder `worker-*-active`)
- **Next:** unblocked `status:todo` (außer `priority:P3`)
- **Later:** `status:blocked` oder `priority:P3`

### Now
- [#727](https://github.com/nimeob/geo-ranking-ch/issues/727) — WP: Refresh docs/BACKLOG.md Now/Next/Later board (priority:P1, status:todo)

### Next
- [#751](https://github.com/nimeob/geo-ranking-ch/issues/751) — Dev: Validierung der Request-Inputs härten (saubere Fehlermeldungen) (priority:P1, status:todo)
- [#750](https://github.com/nimeob/geo-ranking-ch/issues/750) — Dev: Caching-Layer für Geo-Queries (Performance, ohne Infra) (priority:P2, status:todo)

### Later
- [#550](https://github.com/nimeob/geo-ranking-ch/issues/550) — BL-16.wp2: Optionales externes Hostinger-Rollout + E2E-Verifikation (priority:P3, status:blocked)
<!-- NOW_NEXT_LATER:END -->

## Dev-Engineering (non-BL)

- ✅ abgeschlossen (2026-03-02): [#749](https://github.com/nimeob/geo-ranking-ch/issues/749) — Dev: API Smoke-Test stabilisieren (deterministische Fixtures) — Localhost-Smokes defaulten jetzt ohne explizites `SMOKE_QUERY` auf die deterministische Fixture-Query `__ok__` (sync + async) + Runbook-Sync (`docs/testing/DEV_API_SMOKE_RUNBOOK.md`) + Testabdeckung (`tests/test_async_jobs_smoke_script.py`, `tests/test_remote_smoke_script.py`). (PR #788)

- ✅ abgeschlossen (2026-03-02): [#766](https://github.com/nimeob/geo-ranking-ch/issues/766) — Dev(UI): Ergebnis-Detailansicht – Karten/Marker Lesbarkeit verbessern — GUI MVP: höherer Marker-/Crosshair-Kontrast + Legend-Layout-Wrapping für Mobile (<=520px) + HTML-Smoke-Assertions (`tests/test_web_service_gui_mvp.py`). (PR #787)

- ✅ abgeschlossen (2026-03-02): [#776](https://github.com/nimeob/geo-ranking-ch/issues/776) — UI/Prod: /analyze/history Endpoint (Recent Results) — neuer Endpoint `GET /analyze/history` (limit default 50/max 200, Tenant-Guard via `X-Org-Id`, `Cache-Control: no-store`) + Tests in `tests/test_async_jobs_runtime_skeleton.py`. (PR #781)
- ✅ abgeschlossen (2026-03-02): [#777](https://github.com/nimeob/geo-ranking-ch/issues/777) — UI/Prod: Result Page (/results/<id>) Tabs (Overview/Sources/Derived/Raw) — Result-Permalink-Page mit Tabs (Overview/Sources/Derived/Raw) + Feldprojektion (Summary/Confidence/Entity, Quellen/Attribution, Derived ohne Sources/Summary) + ui_service Smoke-Test (`tests/test_ui_service.py`). (PR #790)
- ✅ abgeschlossen (2026-03-02): [#778](https://github.com/nimeob/geo-ranking-ch/issues/778) — UI/Prod: History Page (/history) + Links zu Result Pages — separate `/history` Page (stdlib-only) lädt `GET /analyze/history` und verlinkt pro Item auf `/results/<result_id>` + ui_service Smoke-Assertion (`tests/test_ui_service.py`). (PR #795)
- ✅ abgeschlossen (2026-03-02): [#782](https://github.com/nimeob/geo-ranking-ch/issues/782) — Auth Phase 1 (Core): Bearer-Token User Mapping + AuthZ Guards (History/Results/Jobs) — Phase1 Auth Users Config (PHASE1_AUTH_USERS_JSON/FILE) + token compare via hmac.compare_digest + Guards für History/Results/Jobs (401/404) + Regressiontest `tests/test_auth_phase1_core.py`. (PR #791)
- ✅ abgeschlossen (2026-03-02): [#796](https://github.com/nimeob/geo-ranking-ch/issues/796) — Store/Auth: AsyncJobStore persist owner fields on job+result records — AsyncJobStore persistiert jetzt owner_user_id/owner_org_id auf Job+Result (schema_version 5) + Webservice übernimmt Owner aus Phase1 Token-Context; Regressiontest erweitert (`tests/test_auth_phase1_core.py`). (PR #799)
- ✅ abgeschlossen (2026-03-02): [#797](https://github.com/nimeob/geo-ranking-ch/issues/797) — Store/Auth: list_recent_results_summary filters by owner/org + legacy migration rules — Phase1 Auth: per-user Visibility enforced für History/Jobs/Results basierend auf owner_user_id (Legacy: fehlendes owner_user_id -> nicht sichtbar); Test `tests/test_auth_phase1_core.py` erweitert (shared org_id). (PR #807)
- ✅ abgeschlossen (2026-03-02): [#783](https://github.com/nimeob/geo-ranking-ch/issues/783) — Auth Phase 1 (Store): Owner persistieren + per-user History/Results Filter — Umbrella/Work-package für #796/#797/#798 (Owner-Persistenz, per-user Guards, Regressiontest). (PRs #799, #807)
- ✅ abgeschlossen (2026-03-02): [#752](https://github.com/nimeob/geo-ranking-ch/issues/752) — Dev: Frontend – Ergebnisliste sortier-/filterbar machen — GUI MVP: Ergebnisliste (Session) inkl. Sortierung (Score/Distanz/Security-Subscore), KO-/Numeric-Filter + persistente URL Query-Params (`results_*`) + minimaler HTML-Smoke-Test (`tests/test_web_service_gui_mvp.py`). (PR #772)
- ✅ abgeschlossen (2026-03-02): [#768](https://github.com/nimeob/geo-ranking-ch/issues/768) — Dev(UI): /jobs Liste – Filtern nach Status + Suche nach Job-ID — UI-Service Endpoint `GET /jobs` (LocalStorage Job-ID Liste) inkl. Status-Filter + Job-ID Suche + URL Query-Params (`jobs_status`, `jobs_q`) + /gui merkt sich neue Async-Job-IDs (`localStorage[geo-ranking-ui-job-ids]`) + Smoke-Test (`tests/test_ui_service.py`). (PR #794)
- ✅ abgeschlossen (2026-03-02): [#750](https://github.com/nimeob/geo-ranking-ch/issues/750) — Dev: Caching-Layer für Geo-Queries (Performance, ohne Infra) — opt-in dev-only LRU/TTL (+ optional disk) Cache für `_fetch_json_url` (`DEV_GEO_QUERY_CACHE_TTL_SECONDS`, `DEV_GEO_QUERY_CACHE_DISK`) + Unit-Tests (`tests/test_web_service_dev_geo_cache.py`) + Mini-Benchmark (`scripts/bench_dev_geo_query_cache.py`).
- ✅ abgeschlossen (2026-03-02): [#767](https://github.com/nimeob/geo-ranking-ch/issues/767) — Dev(API): Fehlercodes vereinheitlichen (ValidationError -> 400, NotFound -> 404) — zentraler Error-Helper (`Handler._send_error`), konsistentes Mapping in GET/POST (bad_request/not_found/internal) + gezielte Regressiontests (`tests/test_web_service_request_validation.py`) + Doku-Ergänzung (`docs/api/async-v1.md`).
- ✅ abgeschlossen (2026-03-02): [#765](https://github.com/nimeob/geo-ranking-ch/issues/765) — Dev(API): Health/Readiness Endpoint sauber machen (/healthz + Build-Info) — neuer dev-only Endpoint `GET /healthz` (no-store) mit {status, build, timestamp} + Unit-Test (`tests/test_web_service_healthz.py`) + README-Update. (PR #774)
- ✅ abgeschlossen (2026-03-02): [#751](https://github.com/nimeob/geo-ranking-ch/issues/751) — Dev: Validierung der Request-Inputs härten (saubere Fehlermeldungen) — HTTP-Regressiontests für `/analyze` (empty body, invalid JSON, non-object root, missing query, invalid intelligence_mode) + Error-Format-Referenz: `docs/user/api-usage.md`
- ✅ abgeschlossen (2026-03-02): [#753](https://github.com/nimeob/geo-ranking-ch/issues/753) — Dev: Logging-Redaction – keine PII in Logs — Redaction maskiert sensitive Keys jetzt auch dann vollständig, wenn Values verschachtelte Objekte oder Listen sind (`src/shared/structured_logging.py`), inkl. Regression in `tests/test_structured_logging.py`.
- ✅ abgeschlossen (2026-03-02): [#733](https://github.com/nimeob/geo-ranking-ch/issues/733) — WP: Retention-Cleanup prep — TTL-Config Parsing + Validation (ENV/CLI akzeptiert jetzt `7d`/`24h`/`15m`, fail-fast bei invaliden Werten)
- ✅ abgeschlossen (2026-03-02): [#734](https://github.com/nimeob/geo-ranking-ch/issues/734) — WP: Retention-Cleanup — Deletion Candidate Selection (terminal-only, TTL-guards + idempotente Metriken via `cleanup_retention` + Ops-Script)
- ✅ abgeschlossen (2026-03-02): [#735](https://github.com/nimeob/geo-ranking-ch/issues/735) — Testing: Coordinate-Input Validation — NaN/Inf/Bounds/Whitespace + HTTP-400 bad_request Error-Schema Regression
- ✅ abgeschlossen (2026-03-02): [#748](https://github.com/nimeob/geo-ranking-ch/issues/748) — Dev: Ranking-Response erweitern (Explainability: Top-Faktoren pro Score) — `suitability_light.top_factors` (max 5, signiert/normalisiert) + Propagation nach `summary_compact`; Unit-Tests (`tests/test_suitability_light.py`, `tests/test_top_factors_projection.py`). Merged via PR #764 (commit `ba87780`).

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
  - ✅ 2026-03-01: #487 abgeschlossen — Deploy-Workflow härtet TaskDef-Containerauflösung gegen Name-Drift ab (Single-Container-Fallback + expliziter Multi-Container-Fehler), Doku/Test-Guardrails ergänzt und erfolgreicher Nachweis-Redeploy per `workflow_dispatch` Run `22540919242` (`main`, Erfolg inkl. Post-Deploy-Verifikation).
  - ✅ 2026-03-01: #562 abgeschlossen — UI-TaskDef-Verifikation im Deploy-Workflow nutzt jetzt dieselbe Single-Container-Fallback-Logik wie die TaskDef-Registrierung (inkl. explizitem Multi-Container-Fehlerpfad), damit stündliche Dev-Deploys nicht mehr auf Containername-Drift (`ui` vs. `swisstopo-dev-ui`) abbrechen.
  - ✅ 2026-03-01: #596 abgeschlossen — Root-Cause im Build-&-Test-Job identifiziert (`tests/test_bl30_unit_economics_docs.py` erlaubte nur historischen/finalen BL-30-Nächster-Schritt), Regressionstest auf den aktuellen Follow-up-Pfad erweitert (`#600 → #601/#602`), Full-Testlauf lokal grün (`pytest -q`: 596 passed, 2 skipped) und Redeploy auf `main` via Workflow-Dispatch-Run `22546344609` erfolgreich verifiziert.
  - ✅ 2026-03-01: #606 abgeschlossen — Root-Cause im Build-&-Test-Job identifiziert (SHA `776b6e6`, `tests/test_bl30_unit_economics_docs.py::test_backlog_tracks_bl30_wp2_completion` scheiterte, weil `allowed_next_steps` den durch #600/#601/#602 geänderten BACKLOG-Marker nicht abdeckte); Fix bereits durch Commits #607/eef9dfee eingespielt; Full-Testlauf lokal grün (`pytest -q`: 607 passed, 2 skipped) und Redeploy auf `main` via Workflow-Dispatch-Run `22547047442` (`eef9dfee`, Build & Test ✓ + Deploy ✓) erfolgreich verifiziert.
  - ✅ 2026-03-01: #618 abgeschlossen — Root-Cause: stündlicher Dev-Deploy (Run `22548472482`, SHA `4194500`) schlug fehl, weil der BuildKit-Builder beim Checksum-Berechnen auf einen veralteten CAS-Snapshot (`2798490f-…`) aus der Zeit vor `COPY src/compliance` im Dockerfile traf — auch ein frischer Builder-Prozess zog den kaputten Snapshot aus dem ECR-Inline-Cache. Fix bereits auf `main` (spätere Commits schalteten auf `DOCKER_BUILDKIT=0` + `docker build --no-cache` um, Legacy-Builder ignoriert Inline-Cache vollständig). Redeploy via Workflow-Dispatch-Run `22549358716` (`b37bb96`, Build & Test ✓ 1m9s + Deploy ✓ 7m13s) grün. Follow-up #621 für ECS_UI_CONTAINER_NAME-Konfigurationsabgleich erstellt.
  - ✅ 2026-03-01: #621 abgeschlossen — GitHub Repo-Variable `ECS_UI_CONTAINER_NAME` von `ui` auf `swisstopo-dev-ui` korrigiert (via GitHub Actions Variables API PATCH). Ursache des Deploy-Warnings (Container-Fallback-Warnung bei jedem Stunden-Deploy) damit behoben. Nächster Deploy-Run sollte keine `container not found`-Warnung mehr zeigen.

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
  - ✅ Abschnitt „Offene Punkte“ in `docs/DEPLOYMENT_AWS.md` bereinigt und auf konsolidierte Backlog-Pflege umgestellt.
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
- **Status:** ✅ Abgeschlossen (Architekturentscheid 2026-03-01: externer Consumer `76.13.144.185` = **OpenClaw-Umgebung** (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt); bleibt dauerhaft aktiv (decision: retained), kein weiterer Handlungsbedarf)
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
  - ✅ Worker-Recheck (2026-02-26, 6h): `audit_legacy_aws_consumer_refs.sh` => Exit `10`, `audit_legacy_runtime_consumers.sh` => Exit `30`, `LOOKBACK_HOURS=6 audit_legacy_cloudtrail_consumers.sh` => Exit `10` (10 ausgewertete Legacy-Events, dominanter Fingerprint weiter `76.13.144.185`), `check_bl17_oidc_assumerole_posture.sh` => Exit `30`; außerdem Repo-Scan in `audit_legacy_aws_consumer_refs.sh` auf `git grep` mit Excludes (`artifacts/`, `.venv/`, `.terraform/`) gehärtet.
  - ✅ Worker-A-Recheck (2026-02-27, 6h): `audit_legacy_aws_consumer_refs.sh` => Exit `10`, `audit_legacy_runtime_consumers.sh` => Exit `30`, `LOOKBACK_HOURS=6 audit_legacy_cloudtrail_consumers.sh` => Exit `10` (98 Raw-Events / 90 ausgewertete Events; dominanter Fingerprint weiterhin `76.13.144.185` inkl. `logs:FilterLogEvents` und `bedrock:ListFoundationModels` Aktivität), `check_bl17_oidc_assumerole_posture.sh` => Exit `30`.
  - ✅ Testabdeckung für CloudTrail-Fingerprint-Audit ergänzt (2026-02-26, Issue #109): `tests/test_audit_legacy_cloudtrail_consumers.py` deckt Parametervalidierung, No-Events-Pfad (Exit `0`), Events-Found-Pfad (Exit `10`) und LookupEvents-Filter-Toggle (`INCLUDE_LOOKUP_EVENTS`) reproduzierbar ab.
  - ✅ 2026-02-27: #111 abgeschlossen (strukturierter Fingerprint-Evidence-Export): `scripts/audit_legacy_cloudtrail_consumers.sh` schreibt nun einen reproduzierbaren JSON-Report (`FINGERPRINT_REPORT_JSON`, Default `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`) mit Zeitfenster, Event-Counts und Top-Fingerprints; Runbook in `docs/LEGACY_IAM_USER_READINESS.md` ergänzt, Tests in `tests/test_audit_legacy_cloudtrail_consumers.py` um Export-/Pfadvalidierung erweitert.
  - ✅ 2026-02-27: #112 abgeschlossen (externe Consumer-Targets konkretisiert): `docs/LEGACY_CONSUMER_INVENTORY.md` Abschnitt 3 auf verbindliches Evidence-Schema je Target (`caller_arn`, Injection, Jobs/Skripte, Migration, Cutover, Evidence-Refs) umgestellt und initiale Registry mit stabilen `target_id`s für externe Runner/Cron/Laptop-Profile ergänzt; Cross-Refs in `docs/LEGACY_IAM_USER_READINESS.md` nachgezogen.
  - ✅ 2026-02-27: #151 abgeschlossen (standardisiertes Evidence-Bundle): neues read-only Export-Skript `scripts/export_bl15_readiness_bundle.py` erstellt versionierte Bundles unter `reports/bl15_readiness/<timestamp>/` und sammelt vorhandene BL-15/BL-17 Evidenzartefakte inkl. Manifest (`inventory.json`), Consumer-Targets-Hinweis (`consumer_targets_hint.md`) und README-Kurzinterpretation; ergänzt durch neue Testabdeckung `tests/test_export_bl15_readiness_bundle.py`.
  - ✅ 2026-02-27: #152 abgeschlossen (GO/NO-GO Decision-Matrix + Sign-off): `docs/LEGACY_IAM_USER_READINESS.md` um harte Gates (G1–G5), Entscheidungslogik (`GO`/`GO with timebox`/`NO-GO`), verlinkte BL-15-Evidenzartefakte, Sign-off-Template und synthetisch ausgefülltes Entscheidungsbeispiel ergänzt; zusätzlicher 5-Schritte-Entscheidungsablauf dokumentiert.
  - ✅ 2026-02-27: #187 abgeschlossen (CLI-Collector für Readiness-Evidence): neues Script `scripts/collect_bl15_readiness_evidence.py` führt Repo-/Runtime-/CloudTrail-Audits in einem Lauf zusammen, schreibt strukturierte JSON/MD-Berichte inkl. Log-Artefakte und liefert deterministische Exit-Codes (`0/10/20`); ergänzt durch Testabdeckung in `tests/test_collect_bl15_readiness_evidence.py`.
  - ✅ 2026-02-27: #188 abgeschlossen (Fingerprint-Korrelation als Modul): neues Shared-Modul `src/legacy_consumer_fingerprint.py` kapselt Event-Normalisierung, deterministische Fingerprint-Aggregation und Report-Rendering; `scripts/audit_legacy_cloudtrail_consumers.sh` nutzt das Modul über einen klaren Integrationspfad (inkl. optionaler Fingerprint-Dimensionen `region`/`recipient_account`), abgesichert durch `tests/test_legacy_consumer_fingerprint.py` und bestehende Script-Regressionstests.
  - ✅ 2026-03-01: #565 abgeschlossen (BL-15.r2.wp1): `docs/LEGACY_CONSUMER_INVENTORY.md` Target-Registry auf Pflichtfeld-Vollständigkeit ohne `TBD` gehärtet (inkl. `owner`-Spalte, explizite Cutover-Blocker, konkrete Next Steps je Target) und Konsistenz-Update in `docs/LEGACY_IAM_USER_READINESS.md` für Gate G3 durchgeführt.
  - ✅ 2026-03-01: #566 abgeschlossen (BL-15.r2.wp2): Runtime-Recheck dokumentiert (ambient vs. AssumeRole-first), `scripts/check_bl17_oidc_only_guard.py` um `--assume-role-first` erweitert, Testabdeckung in `tests/test_check_bl17_oidc_only_guard.py` ergänzt und temporäre, evidenzpflichtige Ausnahme-Klassifikation mit Owner/Sunset im Readiness-Runbook festgehalten (Follow-up: #570).
  - ✅ 2026-03-01: #572 abgeschlossen (BL-15.r2.wp2.a): `scripts/inventory_bl17_runtime_credential_paths.py` um forensische Source-Attribution erweitert (Detection `runtime-env-inheritance-process-chain` + `runtime-startpath-env-passthrough`, inkl. redacted `/proc`-Lineage- und Wrapper-Hinweise), testbar via neuen Overrides (`BL17_INVENTORY_PROCESS_CHAIN_JSON`, `BL17_RUNTIME_WRAPPER_HINT_PATHS`) und abgesichert durch zusätzliche Testfälle in `tests/test_inventory_bl17_runtime_credential_paths.py`; Runbook-/Inventory-Doku synchronisiert.
  - ✅ 2026-03-01: #576 abgeschlossen (BL-15.r2.wp2.b.prereq): Wartungsfenster-/Host-Zugriffspfad neu bewertet; für den aktuellen Doku-/Policy-Scope ist kein verpflichtender Host-Orchestrator-Eingriff nötig. Kriterien für den Ausnahmefall (persistente Startpfad-Änderung nur mit Wartungsfenster + Rollback) in `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md` und `docs/LEGACY_IAM_USER_READINESS.md` präzisiert.
  - ✅ 2026-03-01: #573 abgeschlossen (BL-15.r2.wp2.b): Persistenter OpenClaw-Startpfad inklusive erlaubter Runtime-Key-Setpoints (`Host-Orchestrator -> /entrypoint.sh -> node server.mjs -> openclaw -> openclaw-gateway`) dokumentiert, Security-Härtung (Rotation/Least-Privilege/Audit) verbindlich ergänzt und widersprüchliche AssumeRole-default-Formulierungen in Runbooks/Backlog als historischer Vergleichspfad korrigiert.
  - ✅ 2026-03-01: #574 abgeschlossen (BL-15.r2.wp2.c): Abschluss-Recheck mit Runtime=Key/Secret-Policy durchgeführt (`audit_legacy_runtime_consumers`, `check_bl17_oidc_assumerole_posture`, `inventory_bl17_runtime_credential_paths`, `check_bl17_oidc_only_guard`) und neue Evidenzpfade + Interpretation in `docs/LEGACY_IAM_USER_READINESS.md` sowie Status-Sync in `docs/BACKLOG.md` nachgezogen.
  - ✅ 2026-03-01: #570 abgeschlossen (BL-15.r2.wp2.followup): Parent-DoD/Checklist final synchronisiert (Child-Issues #572/#573/#574), Policy-Konsolidierung auf Zielarchitektur bestätigt und Abschlussnachweise über PRs #579/#580 sowie aktualisierte Readiness-/Backlog-Doku verlinkt.
  - ✅ 2026-03-01: #567 abgeschlossen (BL-15.r2.wp3): Disable-Canary gegen bestätigte Zielarchitektur neu bewertet; Standardentscheid als `entfällt` (kein Pflicht-Blocker) dokumentiert, optionaler Härtungs-/Failover-Pfad mit Triggern/Nachweisanforderungen in `docs/SECURITY.md` festgehalten (Abschnitt „BL-15.r2.wp3 — Legacy-Key Disable-Canary (Policy)“); Parent-Sync vorbereitet.
  - ✅ 2026-03-01: #568 abgeschlossen (BL-15.r2.wp4): finale Go/No-Go-Entscheidung in `docs/SECURITY.md` festgehalten (Abschnitt „BL-15.r2.wp4 — Finale Go/No-Go-Entscheidung“), Entscheidung **NO-GO** für Legacy-Key-Deaktivierung/Decommission im Standardpfad bestätigt und Parent-/Backlog-Sync abgeschlossen.
  - ✅ 2026-03-01: #564 abgeschlossen (BL-15.r2 Parent-Closeout): Parent-Checklist/DoD final bestätigt (wp1–wp4 erledigt), Abschlussnachweise aus PRs #582/#583 und Child-PRs #579/#580/#581 im Parent-Issue konsolidiert.
  - ✅ 2026-03-01: **Architekturentscheid** — Externer Consumer (`76.13.144.185`) = **OpenClaw-Umgebung** (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt); bleibt dauerhaft aktiv (decision: retained). Gate G3 (Consumer-Migration) entfällt als Blocking-Kriterium. BL-15 ist vollständig abgeschlossen.
- **Work-Packages (Issue #8):**
  - [x] #109 — Testabdeckung CloudTrail-Audit
  - [x] #111 — Strukturierter Fingerprint-Evidence-Export
  - [x] #112 — Externe Consumer-Targets mit Evidence-Schema
  - [x] #151 — Standardisiertes Decommission-Evidence-Bundle
  - [x] #152 — GO/NO-GO Decision-Matrix + Sign-off-Template (2026-02-27)
  - [x] #187 — CLI-Collector für Readiness-Evidence (2026-02-27)
  - [x] #188 — Fingerprint-Korrelation als wiederverwendbares Modul (2026-02-27)
- **Blocker:** ✅ Keine — Architekturentscheid 2026-03-01 aufgelöst.
- **Next Actions:** ✅ Abgeschlossen. Kein weiterer Handlungsbedarf.
  - Externer Consumer (`76.13.144.185`) = **OpenClaw-Umgebung** (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt) — bewusste Architekturentscheidung (decision: retained, dauerhaft aktiv, kein Blocking).
  - Deploy bleibt OIDC; OpenClaw-Runtime bleibt Key/Secret. Consumer-Migration als Gate entfällt.

### BL-17 — AWS-Betrieb trennen: OIDC für Deploy, Key/Secret für OpenClaw Runtime
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-03, BL-15
- **Status:** ✅ abgeschlossen (2026-02-27, Issue #2; Policy-Klarstellung 2026-03-01)
- **Hinweis (Policy-Klarstellung 2026-03-01):** Historische Einträge zu „AssumeRole-first als Runtime-Default" sind Vergleichs-/Härtungsnachweise und **kein** aktueller Betriebsstandard für die OpenClaw-Runtime.
- **Akzeptanzkriterien:**
  - CI/CD-Deploy läuft über GitHub Actions OIDC.
  - OpenClaw Runtime-Zugriffe dürfen über Access Key + Secret erfolgen (kein Runtime-OIDC-Zwang).
  - Die Trennung ist in Runbooks/Backlog konsistent dokumentiert.
- **Umgesetzt:**
  - `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md` auf Betriebsmodell mit klarer Trennung präzisiert (OIDC für CI/CD; Runtime via Key/Secret).
  - `scripts/check_bl17_oidc_assumerole_posture.sh` als OIDC-Deploy-/Runtime-Posture-Check dokumentiert.
  - ✅ 2026-02-26: #136 abgeschlossen (Wrapper-Härtung + Tests): `scripts/aws_exec_via_openclaw_ops.sh` validiert jetzt Role-ARN, Session-Dauer (`900..43200`) und Session-Name fail-fast; JSON-Parsing-/Credential-Fehler aus `assume-role` werden deterministisch abgefangen. Testabdeckung via `tests/test_aws_exec_via_openclaw_ops.py` (Missing-Args, Invalid-Duration, Invalid-Role-ARN, Parse-Error, Happy-Path).
  - ✅ 2026-02-26: #137 abgeschlossen (Fallback-Logging-Template + Nachweisformat): neues Standardformat in `docs/LEGACY_FALLBACK_LOG_TEMPLATE.md` (Markdown-Minimaltemplate + optionales JSON-Snippet + ausgefülltes Beispiel) eingeführt, in `docs/LEGACY_IAM_USER_READINESS.md` als verbindliche "Fallback-Log Entries" referenziert und im OIDC-Runbook (`docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`) als operative Regel verlinkt. Link-/Struktur-Nachweis: `python3 -m pytest -q tests/test_user_docs.py tests/test_markdown_links.py` (Exit `0`).
  - ✅ 2026-02-26: #138 abgeschlossen (Runtime-Caller-Evidence-Export): `scripts/check_bl17_oidc_assumerole_posture.sh` unterstützt jetzt optionalen JSON-Report via `--report-json <path>` oder `BL17_POSTURE_REPORT_JSON`, inkl. Pflichtfeldern für Timestamp, Caller-Klassifikation und relevante Exit-Codes (`workflow_check`, `caller_check`, Kontext-Audits, final). Reproduzierbare Nachweis-Tests über `tests/test_check_bl17_oidc_assumerole_posture.py` (Flag-/ENV-Export + Feldkonsistenz), Verifikation: `python3 -m pytest -q tests/test_check_bl17_oidc_assumerole_posture.py` (Exit `0`).
  - ✅ 2026-02-27: #144 abgeschlossen (Posture-Window-Aggregation): neues Aggregations-Script `scripts/summarize_bl17_posture_reports.py` bewertet mehrere BL-17-JSON-Reports über ein Zeitfenster (Klassifikationsverteilung, Legacy-Treffer, Ready/Not-ready-Empfehlung, Exitcode-Policy 0/10/2). Tests in `tests/test_summarize_bl17_posture_reports.py` decken Ready-, Legacy- und Invalid-Input-Pfade ab; Runbook ergänzt in `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`.
  - ✅ 2026-02-27: #145 abgeschlossen (Runtime-Credential-Injection-Inventar): neues Read-only Inventarisierungs-Script `scripts/inventory_bl17_runtime_credential_paths.py` mit strukturiertem JSON-Export (`--output-json`) und standardisierten Feldern für `effect`, `migration_next_step`, `owner`; deckt Runtime-Caller, statische Env-Keys, Profile/Config/Cron/Systemd-Pfade sowie verfügbaren AssumeRole-Migrationspfad ab. Neue Dokumentation in `docs/BL17_RUNTIME_CREDENTIAL_INJECTION_INVENTORY.md`, Runbook-Verlinkung in `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md` und Legacy-Readiness-Verknüpfung in `docs/LEGACY_IAM_USER_READINESS.md`. Testnachweis via `tests/test_inventory_bl17_runtime_credential_paths.py`.
  - ✅ 2026-02-27: #148 abgeschlossen (historischer AssumeRole-first Vergleichspfad): Wrapper-Script `scripts/openclaw_runtime_assumerole_exec.sh` kapselt Runtime-Kommandos testweise mit temporären STS-Session-Credentials; `scripts/inventory_bl17_runtime_credential_paths.py` klassifiziert Session-Credentials als low-risk (`runtime-env-session-credentials`) und meldet `runtime-env-static-keys` bei langlebigen/inkonsistenten Key-Pfaden; `scripts/audit_legacy_runtime_consumers.sh` auf dieselbe Klassifikation gehärtet. Verifizierter Read-only Nachweis im Vergleichspfad: Inventory/Audit/Posture jeweils Exit `0`. Testnachweise via `tests/test_inventory_bl17_runtime_credential_paths.py`, `tests/test_openclaw_runtime_assumerole_exec.py`, `tests/test_aws_exec_via_openclaw_ops.py`.
  - ✅ 2026-02-27: #149 abgeschlossen (OIDC-only Guard): neues Konsolidierungs-Script `scripts/check_bl17_oidc_only_guard.py` führt Posture-Check, Runtime-Credential-Inventory und CloudTrail-Legacy-Audit in einem Guard zusammen und liefert ein einheitliches `ok|warn|fail`-Schema mit `evidence_paths`; Exitcodes sind auf `0/10/20` normalisiert (`ok/fail/warn`). Runbook um Guard-Aufruf + Interpretation ergänzt (`docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`), Testfälle für clean/fail-Pfade in `tests/test_check_bl17_oidc_only_guard.py` abgesichert.
  - ✅ 2026-02-27: #150 abgeschlossen (Break-glass-Fallback-Runbook): `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md` um verbindliches Break-glass-Runbook (Triggerkriterien, Ablauf, Evidenz-Checkliste, CloudTrail-/Inventory-/Posture-Prüfpunkte und Rückweg in den regulären Runtime-Key/Secret-Betrieb) erweitert; `docs/LEGACY_IAM_USER_READINESS.md` um ein vollständig ausgefülltes synthetisches Fallback-Event (read-only) mit referenzierten Evidenzpfaden ergänzt.
  - ✅ 2026-02-27: Parent #2 finalisiert und geschlossen (alle definierten Work-Packages gemerged, Status-Sync in Backlog + Issue).
- **Work-Packages (Issue #2):**
  - [x] #136
  - [x] #137
  - [x] #138
  - [x] #144
  - [x] #145
  - [x] #148
  - [x] #149
  - [x] #150

### BL-18 — Service funktional weiterentwickeln + als Webservice E2E testen
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-17
- **Status:** ✅ abgeschlossen (2026-02-26, Issue #3)
- **Akzeptanzkriterien:**
  - Mindestens ein fachlicher Ausbau am Service ist implementiert und dokumentiert.
  - API-/Webservice-Endpunkte sind per End-to-End-Tests validiert (lokal + dev).
  - Negativfälle (4xx/5xx), Timeouts und Auth-Fälle sind in Tests abgedeckt.
  - Testergebnisse sind nachvollziehbar dokumentiert (Runbook/CI-Output).
- **Umgesetzt (Iteration 2026-02-26):**
  - ✅ 2026-02-26: #119 abgeschlossen (Bearer-Auth-Header robust normalisiert: `Bearer` case-insensitive + tolerante Leading/Trailing-/Mehrfach-Whitespace-Verarbeitung bei weiterhin exaktem Token-Match), inkl. neuer E2E-Abdeckung in `tests/test_web_e2e.py` und Doku-Nachtrag in `docs/BL-18_SERVICE_E2E.md`.
  - ✅ 2026-02-26: #120 abgeschlossen (JSON-/Body-Edgecases für `/analyze` abgesichert: malformed JSON, invalides UTF-8 sowie JSON-Array/String statt Objekt liefern deterministisch `400 bad_request`; Service-Guard in `src/web_service.py` ergänzt und E2E-Abdeckung in `tests/test_web_e2e.py` erweitert, Nachweis via `python3 -m pytest -q tests/test_web_e2e.py` mit Exit `0`).
  - ✅ 2026-02-26: #121 abgeschlossen (BL-18 Regression-Minimum als reproduzierbares Mini-Runbook in `docs/BL-18_SERVICE_E2E.md` ergänzt, inkl. lokalem Nachweislauf `python3 -m pytest -q tests/test_web_e2e.py tests/test_remote_stability_script.py` mit Exit `0`; README auf den neuen Regression-Minimum-Abschnitt verlinkt).
  - ✅ 2026-02-26: #122 abgeschlossen (Smoke-Runner auf grouped Response harmonisiert: `result_keys` validieren nun `status` + `data` statt Legacy-`query`; Nachweis via `python3 -m pytest -q tests/test_remote_smoke_script.py` und `./scripts/run_webservice_e2e.sh`, beide Exit `0`).
  - ✅ 2026-02-26: #3 abgeschlossen (Parent-Abschluss-Sync mit Finalchecks `python3 -m pytest -q tests/test_web_e2e.py tests/test_remote_stability_script.py tests/test_remote_smoke_script.py` sowie `./scripts/run_webservice_e2e.sh`, jeweils Exit `0`; Forward-Compatibility für BL-30.1/30.2/30.3 bestätigt — additive Contract-Evolution und stabile `result.status`/`result.data`-Trennung bleiben gewahrt).
  - ✅ 2026-02-26: #130 abgeschlossen (BL-18.fc1 Contract-Compatibility-Regression): dedizierte Guard-Tests für additive Evolution + Legacy-Minimalprojektion ergänzt (`tests/test_contract_compatibility_regression.py`), Stability-Policy um FC1-Regeln inkl. Verlinkung auf #3/#127 erweitert (`docs/api/contract-stability-policy.md`) und Nachweislauf `python3 -m pytest -q tests/test_contract_compatibility_regression.py tests/test_web_service_grouped_response.py tests/test_remote_smoke_script.py::TestRemoteSmokeScript::test_smoke_script_passes_with_valid_token tests/test_web_e2e.py::TestWebServiceE2E::test_analyze_happy_path` mit Exit `0` dokumentiert.
  - ✅ 2026-02-26: #131 abgeschlossen (BL-18.fc2 Request-Options-Envelope): optionalen `options`-Namespace in `src/web_service.py` robust validiert (Objektpflicht bei Presence, sonst `400 bad_request`) und additive Ignore-Policy für unbekannte Keys als No-Op abgesichert. Doku-Update in `docs/api/contract-stability-policy.md` + `docs/api/contract-v1.md` (inkl. Verlinkung #3/#107/#127), Nachweislauf `python3 -m pytest -q tests/test_web_e2e.py::TestWebServiceE2E::test_analyze_ignores_unknown_options_keys_as_additive_noop tests/test_web_e2e.py::TestWebServiceE2E::test_bad_request_options_must_be_object_when_provided tests/test_web_e2e.py::TestWebServiceE2E::test_analyze_happy_path tests/test_api_contract_v1.py` mit Exit `0`.
  - `src/web_service.py`: optionales Bearer-Auth-Gate (`API_AUTH_TOKEN`), Timeout-Parameterisierung (`timeout_seconds`, `ANALYZE_*_TIMEOUT_SECONDS`) inkl. endlicher Numerik-Validierung (`nan`/`inf` → `400 bad_request`), getrimmte/case-insensitive Mode-Normalisierung (`basic|extended|risk`) und `TimeoutError -> 504` Mapping ergänzt.
  - `tests/test_web_e2e.py`: lokale E2E-Abdeckung inkl. 200/400/401/404/500/504 aufgebaut (inkl. Negativfall non-finite `timeout_seconds`).
  - `tests/test_web_e2e_dev.py`: dev-E2E gegen `DEV_BASE_URL` ergänzt (mit optionalem `DEV_API_AUTH_TOKEN`).
  - `scripts/run_webservice_e2e.sh`: einheitlicher Runner für lokal + optional dev.
  - `docs/BL-18_SERVICE_E2E.md`: Ist-Analyse + Runbook dokumentiert.
  - `scripts/gpush` robust gegenüber bereits tokenisierten `origin`-HTTPS-URLs gemacht (Credentials werden vor Token-Injektion normalisiert statt doppelt prependet); `tests/test_gpush_script.py` deckt Nachweisfälle für plain HTTPS + bereits tokenisierte Origins ab (Issue #50, 2026-02-26).

### BL-18.1 — Erfolgreicher API-Test über Internet (OpenClaw-Agent)
- **Priorität:** P1
- **Aufwand:** S
- **Abhängigkeiten:** BL-18
- **Status:** ✅ abgeschlossen (2026-02-27, Issue #4)
- **Akzeptanzkriterien:**
  - Reproduzierbarer Smoke-Test ruft `POST /analyze` über öffentliche URL auf.
  - Test prüft mindestens HTTP-Status `200`, `ok=true` und vorhandenes `result`-Objekt.
  - Test ist per Script ausführbar (inkl. optionalem Bearer-Token).
  - Kurzer Nachweislauf ist dokumentiert (stdout/Runbook-Eintrag).
- **Freeze-Regel (verbindlich):**
  - Kein weiterer BL-18.1-Ausbau bis BL-19-MVP abgeschlossen ist.
  - Ausnahmen nur bei kritischem Produktions-/Deploy-Blocker oder expliziter Nico-Freigabe.
- **Umgesetzt (Iteration 2026-02-26, historisch):**
  - ✅ 2026-02-27: #4 abgeschlossen. Merge von PR #143 (`55e78ca`) mit Deploy-Run `22464814832` erfolgreich (`services-stable` + `/health` grün); anschließender Internet-Smoke gegen `http://18.159.133.63:8080/analyze` mit `scripts/run_remote_api_smoketest.sh` erfolgreich (Artefakt: `artifacts/bl18.1-smoke-internet-issue4-1772146927.json`, `status=pass`, `http_status=200`, `ok=true`, Request-ID-Echo konsistent).
  - ✅ 2026-02-26: kritischer Deploy-Blocker behoben (Freeze-Ausnahme): ECS-Task-Healthcheck nutzt `curl`, Image enthielt jedoch kein `curl` → Container wurde fortlaufend als unhealthy ersetzt. Fix via `Dockerfile` (`apt-get install --no-install-recommends curl`) + Regressionstest `tests/test_dockerfile_runtime_deps.py`.
  - ✅ 2026-02-26: #134 abgeschlossen (externe Blocker-Retry-Steuerung automatisiert): `scripts/blocker_retry_supervisor.py` ergänzt (3h Grace-Period, max. 3 Fehlversuche, automatisches Follow-up-Issue), Doku in `docs/AUTONOMOUS_AGENT_MODE.md` + `docs/OPERATIONS.md` nachgezogen und durch `tests/test_blocker_retry_supervisor.py` reproduzierbar abgesichert.
  - `scripts/run_remote_api_smoketest.sh` ergänzt und gehärtet (Retry-Handling, Request-ID, optionale JSON-Artefaktausgabe via `SMOKE_OUTPUT_JSON`, default Echo-Validierung von Request-ID in Header + JSON).
  - `src/web_service.py` um Request-Korrelation für `/analyze` erweitert (erste **gültige** ID aus `X-Request-Id`/`X_Request_Id` bzw. `X-Correlation-Id`/`X_Correlation_Id` wird in Response-Header + JSON-Feld `request_id` gespiegelt; leere/whitespace-only IDs, IDs mit eingebettetem Whitespace, IDs mit Steuerzeichen, IDs mit Trennzeichen `,`/`;`, Non-ASCII-IDs oder IDs mit mehr als 128 Zeichen werden verworfen) für reproduzierbare Remote-Diagnosen.
  - `scripts/run_remote_api_stability_check.sh` ergänzt (Mehrfachlauf mit NDJSON-Report + Fail-Threshold für kurze Stabilitäts-/Abnahmeläufe).
  - `tests/test_remote_smoke_script.py` ergänzt (lokale E2E-Validierung des Smoke-Skripts inkl. Auth-Pfad/Fehlpfad + Request-ID-Echo-Nachweis) und um Happy-Paths für `DEV_BASE_URL=.../health`, verkettete Suffixe (`.../health/analyze`), gemischte Suffix-Reihenfolge (`.../analyze/health//`), wiederholte Suffix-Ketten (`.../health/analyze/health/analyze///`), wiederholte Reverse-Suffix-Ketten mit Schema-Case + Whitespace (`"  HTTP://.../AnAlYzE/health/analyze/health///  "`) sowie deren Variante mit internem Double-Slash (`"  HTTP://.../AnAlYzE//health/analyze/health///  "`), wiederholte Forward-Suffix-Ketten mit internem Double-Slash (`"  HTTP://.../health//analyze/health/analyze///  "`), case-insensitive Suffixe (`.../HeAlTh/AnAlYzE`), getrimmte Whitespace-Inputs (`"  http://.../health  "`, `"\thttp://.../health\t"`) inkl. Tab-umhülltem Header-Mode (`"\tCorrelation\t"`), die kombinierte Normalisierung (`"  HTTP://.../HeAlTh/AnAlYzE/  "`), die kombinierte Reverse-Suffix-Kette (`"  HTTP://.../AnAlYzE/health//  "`), redundante trailing-Slash-Ketten (`.../health//analyze//`) sowie grossgeschriebenes HTTP-Schema (`HTTP://...`) erweitert (URL-Normalisierung + Schema-Handling auf `/analyze` reproduzierbar abgesichert).
  - `tests/test_remote_smoke_script.py` enthält zusätzlich Negativfälle für `DEV_BASE_URL` mit Query/Fragment sowie whitespace-only Inputs (jeweils reproduzierbarer `exit 2`).
  - `tests/test_remote_smoke_script.py` deckt jetzt auch Fehlkonfigurationen für `CURL_RETRY_DELAY=-1`, `SMOKE_ENFORCE_REQUEST_ID_ECHO=2`, eingebettete Whitespaces/Trennzeichen (`,`/`;`) oder Non-ASCII-Zeichen in `SMOKE_REQUEST_ID` sowie zu lange `SMOKE_REQUEST_ID`-Werte (`>128` Zeichen) reproduzierbar mit `exit 2` ab.
  - `tests/test_remote_smoke_script.py` ergänzt einen Negativfall für eingebettete Whitespaces in `DEV_BASE_URL` (z. B. `http://.../hea lth`) und sichert fail-fast `exit 2` mit klarer CLI-Fehlermeldung.
  - `scripts/run_remote_api_smoketest.sh` validiert `DEV_BASE_URL` jetzt zusätzlich auf eingebettete Whitespaces/Steuerzeichen und bricht bei fehlerhaften Inputs früh mit `exit 2` ab.
  - `scripts/run_remote_api_smoketest.sh` validiert `SMOKE_REQUEST_ID` fail-fast (Whitespace-only, eingebettete Whitespaces, Steuerzeichen, Trennzeichen `,`/`;`, Non-ASCII-Zeichen und IDs >128 Zeichen werden mit `exit 2` abgewiesen; valide IDs werden vor Echo-Check getrimmt).
  - `scripts/run_remote_api_smoketest.sh` generiert für leere/nicht gesetzte `SMOKE_REQUEST_ID` jetzt eine eindeutige Default-ID (`bl18-<epoch>-<uuid-suffix>`), damit parallele/enge Läufe reproduzierbar unterscheidbar bleiben; `tests/test_remote_smoke_script.py` sichert dies mit eingefrorener Systemzeit (`PATH`-override auf Fake-`date`) reproduzierbar ab.
  - `scripts/run_remote_api_smoketest.sh` URL-Normalisierung ergänzt (trimmt führende/trailing Whitespaces, normalisiert `/health`/`/analyze`-Suffixe auch verkettet und case-insensitive) + robuste http(s)-Schema-Validierung (inkl. grossgeschriebener Schemata wie `HTTP://`) zur Runbook-Reproduzierbarkeit.
  - `scripts/run_remote_api_smoketest.sh` rejectet `DEV_BASE_URL` mit Query/Fragment (`?`/`#`) jetzt fail-fast mit `exit 2`, damit der abgeleitete `/analyze`-Pfad reproduzierbar bleibt.
  - `scripts/run_remote_api_smoketest.sh` rejectet `DEV_BASE_URL` mit Userinfo (`user:pass@host`) fail-fast mit `exit 2`, um Credential-Leaks in Shell-History/Logs zu vermeiden.
  - `scripts/run_remote_api_smoketest.sh` validiert `DEV_BASE_URL` nach Normalisierung zusätzlich auf gültigen Host/Port (`hostname` + parsbarer Port), damit Fehlkonfigurationen wie `:abc` oder out-of-range Ports (`:70000`) früh mit `exit 2` statt späterem curl-Fehler scheitern.
  - `scripts/run_remote_api_smoketest.sh` validiert Eingabeparameter strikt (`SMOKE_TIMEOUT_SECONDS`/`CURL_MAX_TIME` = endliche Zahl > 0, `CURL_RETRY_COUNT`/`CURL_RETRY_DELAY` Ganzzahl >= 0), trimmt diese Werte jetzt vor der Validierung, erzwingt zusätzlich `CURL_MAX_TIME >= SMOKE_TIMEOUT_SECONDS` (Timeout-Konsistenz) und bricht bei Fehlwerten reproduzierbar mit `exit 2` ab.
  - `tests/test_remote_smoke_script.py` um Negativfälle für ungültige Timeout-/Retry-Parameter sowie inkonsistente Timeout-Kombinationen (`CURL_MAX_TIME < SMOKE_TIMEOUT_SECONDS`) erweitert (früher Blocker/Traceback → jetzt klare CLI-Fehlermeldung).
  - `tests/test_remote_smoke_script.py` deckt jetzt auch ungültige Ports in `DEV_BASE_URL` (`:abc`, `:70000`) reproduzierbar mit `exit 2` ab.
  - `tests/test_remote_stability_script.py` ergänzt (lokale E2E-Validierung des Stabilitätsrunners inkl. Stop-on-first-fail-, NDJSON- und Request-ID-Korrelationsnachweis) und um Guard-Fälle erweitert: fehlendes Smoke-JSON trotz `rc=0` **sowie** Smoke-Reports mit `status!=pass` werden reproduzierbar als Fehlrun erkannt; zusätzlich ist jetzt die Trim-Abdeckung für numerische Flag-Inputs (`STABILITY_RUNS=" 2 "`, `STABILITY_MAX_FAILURES=" 0 "`, `STABILITY_STOP_ON_FIRST_FAIL=" 0 "`) inkl. Tab-Varianten (`"\t2\t"`, `"\t0\t"`) enthalten, boolesche Alias-Eingaben für `STABILITY_STOP_ON_FIRST_FAIL` (`"  TrUe  "`, `"  fAlSe  "`) sind reproduzierbar abgesichert und `STABILITY_REPORT_PATH` mit Datei-Elternpfad wird deterministisch mit `exit 2` abgewiesen.
  - `scripts/run_remote_api_stability_check.sh` validiert `STABILITY_STOP_ON_FIRST_FAIL` robust (`0|1|true|false|yes|no|on|off`, normalisiert auf `0|1`), trimmt alle numerischen Runner-Flags (`STABILITY_RUNS`, `STABILITY_INTERVAL_SECONDS`, `STABILITY_MAX_FAILURES`, `STABILITY_STOP_ON_FIRST_FAIL`) vor der Validierung, trimmt `STABILITY_REPORT_PATH` vor Nutzung, erstellt fehlende Verzeichnis-Elternpfade automatisch und weist whitespace-only bzw. Control-Char-Pfade fail-fast mit `exit 2` zurück, weist zusätzlich Verzeichnisziele sowie Pfade mit Datei-Elternpfad (Parent ist kein Verzeichnis) deterministisch mit `exit 2` ab, trimmt/validiert jetzt auch das optionale Script-Override `STABILITY_SMOKE_SCRIPT` (whitespace-only + Control-Char-Overrides → `exit 2`), löst relative `STABILITY_SMOKE_SCRIPT`-Overrides robust gegen `REPO_ROOT` auf und erzwingt für das Override eine ausführbare Datei (`-f` + `-x`), sowie behandelt fehlende/leer gebliebene Smoke-Reports und Non-PASS-Reports fail-safe als Fehlrun.
  - `.github/workflows/deploy.yml` um optionalen `/analyze`-Smoke-Test nach Deploy erweitert (gesteuert via `SERVICE_BASE_URL` + optional `SERVICE_API_AUTH_TOKEN`).
  - `docs/BL-18_SERVICE_E2E.md` um Reproduzierbarkeit/Stabilitäts-Runbook erweitert (inkl. lokalem 2-Run-Nachweis: `pass=2`, `fail=0`).
  - `tests/test_web_e2e.py` um API-E2E-Guards erweitert: ist ein primärer Request-ID-Header (`X-Request-Id`/`X_Request_Id`) leer/whitespace, enthält eingebetteten Whitespace, enthält Steuerzeichen (z. B. Tab), enthält Trennzeichen (`,`/`;`), Non-ASCII-Zeichen **oder ist länger als 128 Zeichen**, fällt der Service deterministisch auf Correlation-Header (`X-Correlation-Id`/`X_Correlation_Id`) zurück und spiegelt diese ID in Header+JSON.
  - `src/web_service.py` akzeptiert für die Request-Korrelation zusätzlich kurze Header-Aliasse (`Request-Id`/`Request_Id` als primär, `Correlation-Id`/`Correlation_Id` als Fallback), sodass auch nicht-`X-*`-Clients konsistent die gleiche Sanitizer-/Fallback-Logik nutzen.
  - `tests/test_web_e2e.py` ergänzt zusätzlich einen Prioritätsfall: ist `X-Request-Id` ungültig, aber `X_Request_Id` gültig, gewinnt deterministisch der gültige Unterstrich-Primärheader (noch vor Correlation-Fallback) und wird in Header+JSON gespiegelt. Zusätzlich abgesichert: sind **beide** primären Header (`X-Request-Id` + `X_Request_Id`) ungültig, fällt der Service deterministisch auf `X-Correlation-Id` zurück. Kurz-Aliasse ohne `X-` sind ebenfalls reproduzierbar abgedeckt (`Request-Id`/`Request_Id` als primär, `Correlation-Id`/`Correlation_Id` als Fallback).
  - `src/web_service.py` akzeptiert neben `PORT` jetzt auch `WEB_PORT` als Fallback (wenn `PORT` fehlt/leer ist); `tests/test_web_e2e.py` enthält dafür eine zusätzliche E2E-Absicherung (`TestWebServiceEnvPortFallback`).
  - `src/web_service.py` normalisiert die Routenauflösung jetzt robust über den URL-Pfad (`urlsplit(...).path`), ignoriert Query-/Fragment-Anteile für die Endpunktwahl, toleriert optionale trailing Slashes und kollabiert doppelte Slash-Segmente (`//`) auf einen Slash (`/health/?...`, `//version///?ts=1`, `//analyze//?trace=...`); `tests/test_web_e2e.py` deckt die neuen Pfadfälle reproduzierbar ab.
  - `scripts/run_remote_api_smoketest.sh` unterstützt jetzt `SMOKE_REQUEST_ID_HEADER=request|correlation|request-id|correlation-id|x-request-id|x-correlation-id|request_id|correlation_id|x_request_id|x_correlation_id` (default `request`) und erlaubt damit reproduzierbare Remote-Fallback-Checks über Request-/Correlation-Header; Header-/Echo-Flags werden vor Validierung zusätzlich getrimmt, Header-Namen werden als Alias normalisiert und ungültige Modi bleiben fail-fast mit `exit 2`. Short-Aliasse senden jetzt real `Request-Id`/`Correlation-Id` bzw. `Request_Id`/`Correlation_Id`, während X-Aliasse weiterhin `X-Request-Id`/`X-Correlation-Id` bzw. `X_Request_Id`/`X_Correlation_Id` senden; das Smoke-Artefakt weist das konkret verwendete Header-Feld über `request_id_header_name` aus.
  - `tests/test_remote_smoke_script.py` ergänzt Happy-Path-Abdeckung für `SMOKE_REQUEST_ID_HEADER=correlation` sowie Alias-Werte (`"  request-id  "`, `"  request_id  "`, `"  correlation-id  "`, `"  correlation_id  "`, `"  X-Request-Id  "`, `"\tX-Correlation-Id\t"`, `"  X_Request_Id  "`, `"\tX_Correlation_Id\t"`, `"  x_correlation_id  "`, `"  x_request_id  "`) und getrimmte Eingaben (`"  Correlation  "`, `SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 "`, `SMOKE_ENFORCE_REQUEST_ID_ECHO="  fAlSe  "`), enthält weiterhin den Negativtest für ungültige Header-Modi und deckt jetzt zusätzlich fail-fast für whitespace-only, embedded-whitespace und Control-Char-Inputs bei `SMOKE_REQUEST_ID_HEADER` reproduzierbar ab. Die Reports werden dabei auf das tatsächlich gesendete Header-Feld (`request_id_header_name`) geprüft.
  - `scripts/run_remote_api_smoketest.sh` akzeptiert für `SMOKE_ENFORCE_REQUEST_ID_ECHO` jetzt zusätzlich boolesche Alias-Werte (`true|false|yes|no|on|off`, case-insensitive), normalisiert robust auf `1|0` und weist weiterhin ungültige Modi fail-fast mit `exit 2` ab.
  - `scripts/run_remote_api_smoketest.sh` trimmt jetzt zusätzlich `SMOKE_MODE`, `SMOKE_TIMEOUT_SECONDS`, `CURL_MAX_TIME`, `CURL_RETRY_COUNT` und `CURL_RETRY_DELAY` vor der Validierung; `SMOKE_MODE` wird außerdem case-insensitive normalisiert (`"  ExTenDeD  "` → `extended`). `tests/test_remote_smoke_script.py` deckt dafür reproduzierbare Happy-Paths mit getrimmtem `SMOKE_MODE="  basic  "` und gemischt geschriebenem `SMOKE_MODE="  ExTenDeD  "`, getrimmten Timeout-Inputs (`SMOKE_TIMEOUT_SECONDS="\t2.5\t"`, `CURL_MAX_TIME=" 15 "`) sowie getrimmten Retry-Flags (`"\t1\t"`) ab.
  - `scripts/run_remote_api_smoketest.sh` trimmt optionales `DEV_API_AUTH_TOKEN` jetzt vor dem Request und weist whitespace-only Tokenwerte, Tokens mit eingebettetem Whitespace **sowie** Tokens mit Steuerzeichen fail-fast mit `exit 2` zurück; `tests/test_remote_smoke_script.py` ergänzt dafür einen Happy-Path mit Tab/Space-umhülltem Token sowie Negativtests für whitespace-only, embedded-whitespace und Control-Char-Token.
  - `scripts/run_remote_api_smoketest.sh` trimmt jetzt auch `SMOKE_QUERY` vor dem Request und weist whitespace-only Query-Werte **sowie Query-Werte mit Steuerzeichen** fail-fast mit `exit 2` zurück, damit der Smoke bei fehlerhaften Env-Inputs nicht erst indirekt mit API-`400` scheitert.
  - `tests/test_remote_smoke_script.py` ergänzt dafür einen Happy-Path mit getrimmtem `SMOKE_QUERY="  __ok__  "` sowie Negativtests für whitespace-only `SMOKE_QUERY` und `SMOKE_QUERY` mit Steuerzeichen.
  - `scripts/run_remote_api_smoketest.sh` trimmt `SMOKE_OUTPUT_JSON` jetzt vor der Nutzung konsistent (inkl. Curl-Fehlpfad-Report), weist whitespace-only Werte nach dem Trim fail-fast zurück, validiert den Pfad auf Steuerzeichen und lehnt sowohl Verzeichnisziele als auch Pfade mit Datei-Elternpfad (Parent ist kein Verzeichnis) deterministisch mit `exit 2` ab; so werden whitespace-umhüllte Pfade robust normalisiert und Fehlkonfigurationen reproduzierbar abgefangen.
  - `tests/test_remote_smoke_script.py` ergänzt dafür einen Curl-Fehlpfad-Test, der den getrimmten `SMOKE_OUTPUT_JSON`-Reportpfad (`reason=curl_error`) reproduzierbar absichert, plus Negativtests für `SMOKE_OUTPUT_JSON` mit Steuerzeichen, whitespace-only Wert, Verzeichnisziel und Datei-Elternpfad (`exit 2`).
  - `src/web_service.py` normalisiert `intelligence_mode` jetzt API-seitig robust (Trim + case-insensitive), sodass gemischte Client-Inputs wie `"  ExTenDeD  "` konsistent als `extended` verarbeitet werden; `tests/test_web_e2e.py` deckt den neuen Happy-Path reproduzierbar ab.
  - Real-Run-Nachweis aktualisiert (lokal, 2026-02-26): `run_remote_api_smoketest.sh` Exit `0` + `run_remote_api_stability_check.sh` Exit `0` mit Request-ID-Korrelation bestätigt; zuletzt in Worker-1-10m Iteration 48 mit getrimmten Env-Inputs im Short-Hyphen-Request-Mode (`SMOKE_REQUEST_ID_HEADER="request-id"` im Smoke) und Underscore-`X`-Correlation-Mode in der Stabilität (`SMOKE_REQUEST_ID_HEADER="x_correlation_id"`), inklusive boolescher Flag-Aliasse (`SMOKE_ENFORCE_REQUEST_ID_ECHO="TrUe"` im Smoke, `SMOKE_ENFORCE_REQUEST_ID_ECHO="off"` + `STABILITY_STOP_ON_FIRST_FAIL="no"` in Stabilität). Zusätzlich wurde API-seitig die Double-Slash-Pfad-Normalisierung live verifiziert (`//health//?probe=double-slash`, `//analyze//?trace=double-slash` → jeweils `200` + konsistentes Request-ID-Echo in Header+JSON). Evidenz in `artifacts/bl18.1-smoke-local-worker-1-10m-1772122638.json`, `artifacts/worker-1-10m/iteration-48/bl18.1-remote-stability-local-worker-1-10m-1772122638.ndjson`, `artifacts/bl18.1-double-slash-path-normalization-worker-1-10m-1772122638.json` (`pass=3`, `fail=0`) inkl. Server-Log `artifacts/bl18.1-worker-1-10m-server-1772122638.log`.
  - API-Fallback real verifiziert: ungültige `X-Request-Id`-Werte (eingebetteter Whitespace, Trennzeichen `,`, Non-ASCII-Zeichen **oder** Länge >128) werden verworfen und `X-Correlation-Id` deterministisch in Header+JSON gespiegelt (`artifacts/bl18.1-request-id-fallback-worker-1-10m-1772110577.json`, `artifacts/bl18.1-request-id-delimiter-fallback-worker-1-10m-1772117243.json`, `artifacts/bl18.1-request-id-length-fallback-worker-1-10m-1772111118.json`, `artifacts/bl18.1-request-id-nonascii-fallback-worker-a-10m-1772119039.json`).
  - Reproduzierbarkeits-Check erneuert: `./scripts/run_webservice_e2e.sh` erfolgreich (`124 passed`, Exit `0`) direkt vor dem dedizierten Worker-1-10m-Langlauf (Iteration 48: Smoke + 3x Stabilität + API-Double-Slash-Realcheck).

### BL-19 — Userdokumentation
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-18 (API-Verhalten stabil dokumentierbar)
- **Status:** ✅ abgeschlossen (2026-03-01, Issue #5 geschlossen)
- **Akzeptanzkriterien:**
  - Eine nutzerorientierte Doku beschreibt Installation, Konfiguration und Betrieb verständlich.
  - API-Nutzung inkl. Auth, Timeouts, Request-ID und Fehlerbilder ist mit Beispielen dokumentiert.
  - Troubleshooting enthält die häufigsten Fehlerfälle mit klaren Gegenmaßnahmen.
  - Doku ist versioniert und aus dem README direkt erreichbar.
- **Fortschritt (2026-02-26):**
  - ✅ BL-19.1 Informationsarchitektur umgesetzt (`docs/user/README.md`)
  - ✅ BL-19.2 Getting Started umgesetzt (`docs/user/getting-started.md`)
  - ✅ BL-19.3 Configuration/ENV Guide umgesetzt (`docs/user/configuration-env.md`)
  - ✅ BL-19.4 API Usage Guide umgesetzt (`docs/user/api-usage.md`)
  - ✅ BL-19.5 Fehlerbilder & Troubleshooting umgesetzt (`docs/user/troubleshooting.md` inkl. Diagnose-Checks)
  - ✅ BL-19.6 Betrieb & Runbooks umgesetzt (`docs/user/operations-runbooks.md`, ergänzende Cross-Links + User-Doku-Regressionstest)
  - ✅ BL-19.7 README-Integration verfeinert (Feature-Liste + User-Doku-Links in `README.md`)
  - ✅ BL-19.8 Doku-Qualitätsgate umgesetzt (`scripts/check_docs_quality_gate.sh`, `tests/test_markdown_links.py`, `.github/workflows/docs-quality.yml`)
  - ✅ 2026-02-26: Crawler-Finding #40 in `docs/OPERATIONS.md` bereinigt (Formulierung ohne Trigger-Schlüsselwörter, weiterhin Verweis auf zentralen Backlog)
  - ✅ 2026-02-26: Crawler-Finding #41 in `docs/ARCHITECTURE.md` bereinigt (Formulierung ohne Trigger-Schlüsselwörter, zentraler Backlog-Verweis bleibt)
  - ✅ 2026-02-26: Follow-up #43 behoben (defekter relativer Link in `docs/VISION_PRODUCT.md` auf `GO_TO_MARKET_MVP.md` korrigiert; Link-Qualitätscheck wieder grün)
  - ✅ 2026-02-26: BL-19.x abgeschlossen (Issue #47) – `docs/user/configuration-env.md` ergänzt, User-Navigation/Querverweise aktualisiert und Doku-Regressionstests erweitert.
  - ✅ 2026-02-27: Crawler-Finding #96 bereinigt (`docs/BACKLOG.md` ohne die bisher auslösenden Trigger-Schlüsselwörter, damit kein False-Positive mehr entsteht).
  - ✅ 2026-02-27: Crawler-Finding #97 verifiziert und geschlossen (gleiche Ursache wie #96; Formulierung bleibt ohne Trigger-Schlüsselwörter).
  - ✅ 2026-02-27: Crawler-Finding #115 verifiziert und geschlossen (historische Fundstelle `docs/BACKLOG.md:344` inzwischen durch Fachfortschritt überschrieben; aktueller Check ohne auslösende Marker in `docs/BACKLOG.md`).
  - ✅ 2026-02-27: Crawler-Finding #116 verifiziert und geschlossen (Fundstelle `docs/BACKLOG.md:345` enthält keine Trigger-Schlüsselwörter; Gegencheck auf Crawler-Marker bleibt leer).
  - ✅ 2026-02-27: Crawler-Finding #156 verifiziert und geschlossen (Fundstelle `docs/BACKLOG.md:371` enthält keine auslösenden Marker; `python3 scripts/github_repo_crawler.py --dry-run` erzeugt hierfür keinen neuen Finding-Case).
  - ✅ 2026-02-27: #219 abgeschlossen (Crawler-False-Positive auf `README.md:69` eliminiert) durch strengeren TODO-Kontext-Filter in `scripts/github_repo_crawler.py` (nur Prefix-/Inline-Kommentar-Kontext), Regressionserweiterung in `tests/test_github_repo_crawler.py` und Methodik-Sync in [`docs/WORKSTREAM_BALANCE_BASELINE.md`](WORKSTREAM_BALANCE_BASELINE.md).
  - ✅ 2026-03-01: #623 abgeschlossen (Status-Sync): Issue #5 (BL-19 Parent) war bereits geschlossen; BACKLOG.md-Status auf abgeschlossen korrigiert.
- **Teilaufgaben (vorgeschlagen):**
  1. **BL-19.1 – Informationsarchitektur:** Zielgruppen, Doku-Navigation und Kapitelstruktur festlegen (`docs/user/README.md` als Einstieg).
  2. **BL-19.2 – Getting Started:** Quickstart für lokale Inbetriebnahme inkl. Minimal-Konfiguration und erstem erfolgreichen Request.
  3. **BL-19.3 – Konfiguration & Umgebungsvariablen:** Alle relevanten ENV-Variablen inkl. Defaults, Pflicht/Optional, Validierungsregeln dokumentieren.
  4. **BL-19.4 – API Usage Guide:** Endpoint-Referenz (`/analyze`, Health), Auth, Request/Response-Beispiele, Request-ID-Verhalten und typische Statuscodes.
  5. **BL-19.5 – Fehlerbilder & Troubleshooting:** Häufige Fehlerszenarien (401/400/504, Timeout, Token, URL-Normalisierung) mit konkreten Diagnose-/Fix-Schritten.
  6. **BL-19.6 – Betrieb & Runbooks:** Smoke-/Stability-Runs, Deploy-Checks, Artefakte, Minimal-SLO/Monitoring-Hinweise verständlich zusammenfassen.
  7. **BL-19.7 – README-Integration:** Root-README auf Userdoku verlinken (Quicklinks: Setup, API, Troubleshooting, Operations).
  8. **BL-19.8 – Doku-Qualitätsgate:** Linkcheck/Strukturcheck + „frisches Setup“-Testlauf gegen Doku; Abweichungen als Follow-up Issues erfassen.
- **Priorisierung (empfohlen):**
  - **MVP / zuerst umsetzen:** BL-19.1 → BL-19.2 → BL-19.4 → BL-19.3 → BL-19.7
  - **Phase 2 / direkt danach:** BL-19.5 → BL-19.6 → BL-19.8
- **Begründung:** Erst schnelle Nutzbarkeit (Einstieg + funktionierende API-Nutzung), dann Tiefe (Troubleshooting/Operations) und abschließend Qualitätsgate.

### BL-20 — Produktvision umsetzen: API + GUI für CH-Standort-/Gebäude-Intelligence
- **Priorität:** P1
- **Aufwand:** L
- **Abhängigkeiten:** BL-18, BL-19
- **Status:** ✅ abgeschlossen (2026-02-28, Issue #6)
- **Quelle/Vision:** [`docs/VISION_PRODUCT.md`](./VISION_PRODUCT.md)
- **Zielbild:** Adresse oder Kartenpunkt in der Schweiz analysieren und als kombinierte Standort-/Gebäudeauskunft bereitstellen; Webservice und GUI separat nutzbar/vermarktbar.
- **Fortschritt (2026-02-26):**
  - ✅ 2026-02-28: #6 finalisiert und geschlossen, nachdem die Parent-Checklist (#12/#13/#14/#15/#16/#17/#18) vollständig synchronisiert und die Phase-1-Akzeptanzkriterien (Vertical A+B über API, Kartenpunkt-Flow/Bau-Eignung, GUI-MVP inkl. Address+Map-Input sowie API/GUI-Entkopplung) über bestehende Nachweise in Backlog/Docs/Test-Suites bestätigt wurden.
  - ✅ 2026-02-27: #300 abgeschlossen (BL-20.8.a TLS-Runtime self-signed dev) mit optionalem TLS-Startpfad in [`src/web_service.py`](../src/web_service.py) (`TLS_CERT_FILE`/`TLS_KEY_FILE`, TLS >=1.2), optionalem HTTP→HTTPS-Redirect-Listener (`TLS_ENABLE_HTTP_REDIRECT`, `TLS_REDIRECT_HTTP_PORT`, `TLS_REDIRECT_HOST`), ergänzter Local-Setup-Doku in [`README.md`](../README.md) sowie Regressionstests in `tests/test_web_service_tls.py` und `tests/test_web_e2e.py`.
  - ✅ 2026-02-27: #303 als Duplikat zu #300 mit belastbarem Nachweis final geschlossen (transienter Zerlegungs-Fehler bereinigt; Re-Validation: `pytest -q tests/test_web_service_tls.py tests/test_web_service_port_resolution.py tests/test_web_e2e.py` → `63 passed`, `36 subtests passed`).
  - ✅ 2026-02-27: #301 abgeschlossen (BL-20.8.b HTTPS Smoke/Trust) mit neuem Dev-Zertifikat-Helper [`scripts/generate_dev_tls_cert.sh`](../scripts/generate_dev_tls_cert.sh), erweitertem Smoke-Script-Trustpfad `DEV_TLS_CA_CERT` via `curl --cacert` in [`scripts/run_remote_api_smoketest.sh`](../scripts/run_remote_api_smoketest.sh), Runbook [`docs/testing/dev-self-signed-tls-smoke.md`](testing/dev-self-signed-tls-smoke.md) und Testnachweisen in `tests/test_generate_dev_tls_cert_script.py` + `tests/test_remote_smoke_script.py`.
  - ✅ 2026-02-27: #304 als Duplikat zu #301 mit belastbarem Nachweis final geschlossen (transienter Zerlegungs-Fehler bereinigt; Re-Validation: `pytest -q tests/test_generate_dev_tls_cert_script.py tests/test_remote_smoke_script.py` → `77 passed`).
  - ✅ 2026-02-27: #302 abgeschlossen (BL-20.8.c Prod-Zertifikatsmigration) mit neuem Migrations-Runbook [`docs/TLS_CERTIFICATE_MIGRATION_RUNBOOK.md`](TLS_CERTIFICATE_MIGRATION_RUNBOOK.md) (Dev-vs-Prod-Pfad, TLS-Baseline >=1.2/Präferenz 1.3, Rotation, Rollback, Incident-Hinweise), Deployment-Verlinkung in [`docs/DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md) sowie Doku-Guard in `tests/test_tls_migration_runbook_docs.py`.
  - ✅ 2026-02-28: #305 (Duplikat zu #302) mit belastbarem Nachweis final geschlossen; Referenz-PR: #308, Merge-Commit: `3e0d5fd0d310af3b658eedf0b0d474813bc27873`, Re-Validation: `pytest -q tests/test_tls_migration_runbook_docs.py tests/test_user_docs.py tests/test_markdown_links.py`.
  - ✅ 2026-02-27: #221 abgeschlossen (BL-20.y.wp1 Workflow-Inventar + Klassifikationsmatrix) mit vollständiger Ist-Aufnahme der sechs aktuellen GitHub-Workflows, Zielklassifikation (`keep-on-github`/`migrate-to-openclaw`/`retire`) in [`docs/automation/github-actions-migration-matrix.md`](automation/github-actions-migration-matrix.md) und Verlinkung aus [`docs/OPERATIONS.md`](OPERATIONS.md).
  - ✅ 2026-02-27: #222 abgeschlossen (BL-20.y.wp2 OpenClaw-Mapping) mit verbindlichem Job-Design für alle `migrate-to-openclaw` Workflows in [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md), ergänztem Operations-Verweis in [`docs/OPERATIONS.md`](OPERATIONS.md) und neuem Follow-up-Issue #227 zur Event-Trigger-Parität.
  - ✅ 2026-02-27: #223 abgeschlossen (BL-20.y.wp3 Migration von mindestens drei Automation-Tasks) mit neuem Runner [`scripts/run_openclaw_migrated_job.py`](../scripts/run_openclaw_migrated_job.py), Runbook-Erweiterung in [`docs/OPERATIONS.md`](OPERATIONS.md), Report-Schema in [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md), zusätzlicher Testabdeckung (`tests/test_run_openclaw_migrated_job.py`) und realen Evidenzläufen unter `reports/automation/{contract-tests,crawler-regression,docs-quality}/`.
  - ✅ 2026-02-27: #224 abgeschlossen (BL-20.y.wp4 Actions-Aufräumen + Required-Checks/Runbook) durch Umstellung der migrierten Workflows auf `workflow_dispatch`-Fallback (`contract-tests`, `crawler-regression`, `docs-quality`, `bl20-sequencer`), Dokumentation des Required-Checks-Zielzustands inkl. Recovery-Fallback in [`docs/OPERATIONS.md`](OPERATIONS.md) sowie Status-Sync in den Migrationsdokumenten [`docs/automation/github-actions-migration-matrix.md`](automation/github-actions-migration-matrix.md) und [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md).
  - ✅ 2026-02-28: #384 abgeschlossen (BL-336 Workflow-Bereinigung): `bl20-sequencer` final aus dem Repo entfernt (`.github/workflows/bl20-sequencer.yml` gelöscht), `worker-claim-priority.yml` bewusst reaktiviert (Deaktivierungsmarker weiter offen), und Governance-/Betriebsdoku in [`docs/OPERATIONS.md`](OPERATIONS.md), [`docs/automation/github-actions-migration-matrix.md`](automation/github-actions-migration-matrix.md) sowie [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md) synchronisiert.
  - ✅ 2026-02-27: #227 abgeschlossen (BL-20.y.wp2.r1 Event-Relay-Design) mit dokumentierten Ziel-Events/Reaktionszeiten, technischem Relay-Zielpfad trotz fehlendem Container-Ingress, verbindlichen Sicherheitsanforderungen und Migrations-/Fallback-Plan in [`docs/automation/openclaw-event-relay-design.md`](automation/openclaw-event-relay-design.md); Mapping-/Operations-Sync in [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md), [`docs/automation/github-actions-migration-matrix.md`](automation/github-actions-migration-matrix.md) und [`docs/OPERATIONS.md`](OPERATIONS.md).
  - ✅ 2026-02-27: #233 in atomare Work-Packages #236/#237/#238 zerlegt (Consumer-Fundament, Reconcile-Dispatch, Shadow-/Hybrid-Rollout), inklusive Parent-Checklist und klarer DoD je Child.
  - ✅ 2026-02-27: #236 abgeschlossen (BL-20.y.wp2.r2.wp1 Event-Envelope + Queue-Consumer-Fundament) mit neuem Consumer-Entrypoint [`scripts/run_event_relay_consumer.py`](../scripts/run_event_relay_consumer.py), maschinenlesbarem Envelope-Schema [`docs/automation/event-relay-envelope.schema.json`](automation/event-relay-envelope.schema.json), synchronisiertem Relay-Design/Operations-/Mapping-Doku (`docs/automation/openclaw-event-relay-design.md`, `docs/OPERATIONS.md`, `docs/automation/openclaw-job-mapping.md`), Unit-Tests in `tests/test_run_event_relay_consumer.py` sowie Evidenzläufen unter `reports/automation/event-relay/`.
  - ✅ 2026-02-27: #237 abgeschlossen (BL-20.y.wp2.r2.wp2 Issue-/Label-Dispatch in Worker-Claim-Reconcile) mit erweitertem Consumer `scripts/run_event_relay_consumer.py` (issues.* Dispatch im Apply-Mode, dedup-batched Reconcile-Run pro Repo, idempotente Label-Deltas), Sequenztests für `labeled`/`unlabeled`/`reopened` in `tests/test_run_event_relay_consumer.py`, Doku-Sync (`docs/OPERATIONS.md`, `docs/automation/openclaw-job-mapping.md`, `docs/automation/openclaw-event-relay-design.md`) und Evidenzlauf unter `reports/automation/event-relay/history/20260227T085900Z.{json,md}`.
  - ✅ 2026-02-27: #238 abgeschlossen (BL-20.y.wp2.r2.wp3 Shadow-/Hybrid-Rollout, Security-Runbook, Evidenz) mit erweitertem Event-Relay-Operations-Runbook inkl. Security-Checklist + Deaktivierungsmarker in [`docs/OPERATIONS.md`](OPERATIONS.md), Migrationsstatus-Sync in [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md) und [`docs/automation/github-actions-migration-matrix.md`](automation/github-actions-migration-matrix.md) sowie dokumentierten Shadow-/Hybrid-Läufen unter `reports/automation/event-relay/history/20260227T090700Z.{json,md}` und `reports/automation/event-relay/history/20260227T090900Z.{json,md}`.
  - ✅ 2026-02-27: #241 abgeschlossen (Follow-up zu #238) mit Reconcile-Härtung in [`scripts/run_event_relay_consumer.py`](../scripts/run_event_relay_consumer.py), neuem Regressionstest `test_reconcile_keeps_active_in_progress_without_promote_todo` in `tests/test_run_event_relay_consumer.py` und ergänzter Betriebsregel in [`docs/OPERATIONS.md`](OPERATIONS.md); Duplikat-Issue #242 wurde geschlossen.
  - ✅ 2026-02-27: #233 final abgeschlossen (BL-20.y.wp2.r2) durch Receiver-Ingress-Härtung via [`scripts/run_event_relay_receiver.py`](../scripts/run_event_relay_receiver.py) (Signaturprüfung `X-Hub-Signature-256`, Repository-Allowlist, Delivery-Dedup), neue Testabdeckung in `tests/test_run_event_relay_receiver.py` sowie Doku-Sync in [`docs/OPERATIONS.md`](OPERATIONS.md), [`docs/automation/openclaw-job-mapping.md`](automation/openclaw-job-mapping.md), [`docs/automation/github-actions-migration-matrix.md`](automation/github-actions-migration-matrix.md) und [`docs/automation/openclaw-event-relay-design.md`](automation/openclaw-event-relay-design.md).
  - ✅ 2026-02-27: #220 final abgeschlossen (BL-20.y Parent) nach Merge aller Child-Work-Packages #221/#222/#223/#224 sowie Follow-ups #227/#233/#236/#237/#238/#241; Parent-Checklist und Evidenzdokumentation sind synchron, verbleibende offene Punkte laufen ausschließlich als separate Backlog-Issues.
  - ✅ 2026-02-27: #26 abgeschlossen (BL-20.3.a Input-Pipeline Adresse → Entity-Resolution) mit robuster Input-Normalisierung (`normalize_address_query_input`), erweitertem Query-Parsing (`parse_query_parts` inkl. Separator-/Hausnummer-Edgecases), additiven stabilen IDs (`entity_id`, `location_id`, `resolution_id`) via `derive_resolution_identifiers`, neuer Strategie-Doku [`docs/api/address-resolution-strategy.md`](api/address-resolution-strategy.md) und Testnachweisen in `tests/test_core.py`.
  - ✅ 2026-02-27: #27 abgeschlossen (BL-20.3.b Gebäudeprofil-Aggregation (MVP)) mit robuster Kernfeld-Aggregation via `build_building_core_profile` (GWR-first, Fallback auf dekodierte Werte, Placeholder-/Invalid-Handling), Pipeline-Dokuergänzung in [`docs/api/address-intel-flow-deep-dive.md`](api/address-intel-flow-deep-dive.md) sowie Vertrags-/Regressionsnachweisen über `tests/test_core.py`, `tests/test_web_service_grouped_response.py`, `tests/test_web_e2e.py` und `tests/test_api_contract_v1.py`.
  - ✅ 2026-02-27: #14 (BL-20.3 Parent) finalisiert und geschlossen, nachdem die Child-Work-Packages #26/#27 abgeschlossen, die Parent-Checklist synchronisiert und der Backlog-Status konsolidiert wurden.
- ✅ 2026-02-26: #35 abgeschlossen (BL-20.7.b) mit GTM-MVP-Artefakten in [`docs/GO_TO_MARKET_MVP.md`](GO_TO_MARKET_MVP.md) (Value Proposition, Scope, Demo-Flow).
  - ✅ 2026-02-26: #36 abgeschlossen (Lizenzgrenzen/GTM-Claims) mit Claim-Gate in [`docs/GTM_DATA_SOURCE_LICENSES.md`](GTM_DATA_SOURCE_LICENSES.md) inkl. Verweis auf #24 (BL-20.2.a).
  - ✅ 2026-02-27: #36 Issue-/Backlog-Sync nachgezogen (Issue war trotz Merge #49 noch offen) und administrativ geschlossen.
  - ✅ 2026-02-26: #24 abgeschlossen (BL-20.2.a Quelleninventar CH + Lizenzmatrix) mit Quellen-/Lizenzinventar in [`docs/DATA_SOURCE_INVENTORY_CH.md`](DATA_SOURCE_INVENTORY_CH.md) inkl. markierter offener Rechts-/Betriebsfragen.
  - ✅ 2026-02-26: #25 abgeschlossen (BL-20.2.b Feld-Mapping Quelle -> Domain) mit technischer Mapping-Spezifikation in [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](DATA_SOURCE_FIELD_MAPPING_CH.md), verbindlichen Transform-Regeln und angelegten Folge-Issues #63/#64/#65.
  - ✅ 2026-02-27: #63 abgeschlossen (BL-20.2.b.r1 Machine-readable Feldmapping-Spezifikation) mit JSON-Schema [`docs/mapping/source-field-mapping.schema.json`](mapping/source-field-mapping.schema.json), CH-v1-Artefakt [`docs/mapping/source-field-mapping.ch.v1.json`](mapping/source-field-mapping.ch.v1.json), strukturellem Validator [`scripts/validate_source_field_mapping_spec.py`](../scripts/validate_source_field_mapping_spec.py), Doku-Sync in [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](DATA_SOURCE_FIELD_MAPPING_CH.md) und Testabdeckung via `tests/test_source_field_mapping_spec.py` + `tests/test_data_source_field_mapping_docs.py`.
  - ✅ 2026-02-27: #64 abgeschlossen (BL-20.2.b.r2 Normalisierungs-/Transform-Rule-Functions) mit neuem Rule-Modul [`src/mapping_transform_rules.py`](../src/mapping_transform_rules.py), Golden-Testset [`tests/data/mapping/transform_rules_golden.json`](../tests/data/mapping/transform_rules_golden.json), Test-Suite `tests/test_mapping_transform_rules.py` sowie ergänzter Einsatz-/Limitierungsdoku in [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](DATA_SOURCE_FIELD_MAPPING_CH.md).
  - ✅ 2026-02-27: #65 abgeschlossen (BL-20.2.b.r3 Source-Schema-Drift-Checks) mit neuem read-only Drift-Checker [`scripts/check_source_field_mapping_drift.py`](../scripts/check_source_field_mapping_drift.py), Referenz-Samples [`tests/data/mapping/source_schema_samples.ch.v1.json`](../tests/data/mapping/source_schema_samples.ch.v1.json), Fehlersignal-Regressionsfall [`tests/data/mapping/source_schema_samples.missing_lon.json`](../tests/data/mapping/source_schema_samples.missing_lon.json), Test-Suite `tests/test_source_field_mapping_drift_check.py` sowie Runbook-Hinweisen in [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](DATA_SOURCE_FIELD_MAPPING_CH.md) und [`docs/OPERATIONS.md`](OPERATIONS.md).
  - ✅ 2026-02-27: #13 (BL-20.2 Parent) finalisiert und geschlossen, nachdem die Work-Packages #24/#25 sowie Follow-ups #63/#64/#65 vollständig abgeschlossen, die Parent-Checklist bestätigt und die Mapping-/Drift-Checks erneut verifiziert wurden.
  - ✅ 2026-02-26: #22 abgeschlossen (BL-20.1.a API-Contract v1) mit versioniertem Vertrag unter [`docs/api/contract-v1.md`](api/contract-v1.md) inkl. Schemas, Fehlercode-Matrix und Beispielpayloads.
  - ✅ 2026-02-26: #23 abgeschlossen (BL-20.1.b Contract-Validierung) mit Golden-Case-Tests (`tests/test_api_contract_v1.py`), Testdaten (`tests/data/api_contract_v1/*`) und CI-Workflow (`.github/workflows/contract-tests.yml`).
  - ✅ 2026-02-26: #60 abgeschlossen (BL-20.1.c grouped response) – Webservice liefert jetzt strikt getrennt `result.status` (quality/source_health/source_meta) vs. `result.data` (entity/modules/by_source), inkl. API-Testabsicherung (`tests/test_web_e2e.py`, `tests/test_web_service_grouped_response.py`) und aktualisiertem Response-Beispiel in [`docs/user/api-usage.md`](user/api-usage.md). ✅ 2026-02-27 Checklist-Sync nach Crawler-Reopen nachgezogen (Akzeptanz-Checkboxen im Issue gepflegt, Re-Validation via pytest dokumentiert).
  - ✅ 2026-02-26: #67 abgeschlossen (BL-20.1.e Feld-Manifest) mit maschinenlesbarem Katalog [`docs/api/field_catalog.json`](api/field_catalog.json), grouped Beispielpayload [`docs/api/examples/current/analyze.response.grouped.success.json`](api/examples/current/analyze.response.grouped.success.json), Validator [`scripts/validate_field_catalog.py`](../scripts/validate_field_catalog.py) und CI-Testverdrahtung (`tests/test_api_field_catalog.py`, `.github/workflows/contract-tests.yml`).
  - ✅ 2026-02-27: #67 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (Akzeptanz-Checkboxen im Issue gepflegt, Re-Validation via `python3 scripts/validate_field_catalog.py` und `pytest -q tests/test_api_field_catalog.py tests/test_api_contract_v1.py`).
  - ✅ 2026-02-26: #66 (BL-20.1.d Parent) in atomare Work-Packages #70/#71/#72/#73 zerlegt (Work-Packages-Checklist im Parent ergänzt, je Child klare DoD für 0.5-2 Tage).
  - ✅ 2026-02-26: #70 abgeschlossen (BL-20.1.d.wp1 Feldinventar/Katalog-Härtung) mit Validator-Verbesserung auf `response_shapes`-Quellenpfade in `field_catalog.json` (inkl. Pfad-Existenz-/Repo-Guard), zusätzlichem Shape-Abdeckungscheck und erweiterten Tests in `tests/test_api_field_catalog.py`.
  - ✅ 2026-02-27: #70 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (DoD-Checkboxen im Issue gesetzt, Re-Validation via `python3 scripts/validate_field_catalog.py` und `pytest -q tests/test_api_field_catalog.py tests/test_api_contract_v1.py`).
  - ✅ 2026-02-26: #71 abgeschlossen (BL-20.1.d.wp2 Human-readable Field Reference) mit neuer Referenz [`docs/api/field-reference-v1.md`](api/field-reference-v1.md), Cross-Link im Vertragsdokument [`docs/api/contract-v1.md`](api/contract-v1.md), README-Dokuindex-Update und Regressionstest-Erweiterung in `tests/test_api_field_catalog.py`.
  - ✅ 2026-02-27: #71 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (DoD-Checkboxen im Issue gesetzt, Re-Validation via `python3 scripts/validate_field_catalog.py` und `pytest -q tests/test_api_field_catalog.py tests/test_api_contract_v1.py`).
  - ✅ 2026-02-26: #72 abgeschlossen (BL-20.1.d.wp3 Contract-Examples) mit vollständigen Beispielpayloads je Shape und zusätzlichem grouped Edge-Case für fehlende/deaktivierte Daten unter [`docs/api/examples/current/analyze.response.grouped.partial-disabled.json`](api/examples/current/analyze.response.grouped.partial-disabled.json), inkl. Guard-Checks in `tests/test_api_field_catalog.py` und Doku-Verlinkung in Contract-/User-Docs.
  - ✅ 2026-02-27: #72 Checklist-/Issue-Sync nachgezogen (stale-open trotz vorhandenem Merge bereinigt, DoD-Checkboxen im Issue gesetzt, Re-Validation via `pytest -q tests/test_api_field_catalog.py`).
  - ✅ 2026-02-26: #73 abgeschlossen (BL-20.1.d.wp4 Stability Guide + Contract-Change-Policy) mit neuem Leitfaden [`docs/api/contract-stability-policy.md`](api/contract-stability-policy.md), Cross-Link im Vertragsdokument [`docs/api/contract-v1.md`](api/contract-v1.md) und dokumentiertem Changelog-/Release-Prozess.
  - ✅ 2026-02-27: #73 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (DoD-Checkboxen im Issue gesetzt, Re-Validation via `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py`).
  - ✅ 2026-02-27: #66 (BL-20.1.d Parent) finalisiert und geschlossen, nachdem alle Child-Work-Packages #70/#71/#72/#73 inkl. Checklist-/Issue-Reconciliation abgeschlossen waren.
  - ✅ 2026-02-26: #79 abgeschlossen (BL-20.1.f.wp1 Score-Katalog) mit neuer Spezifikation [`docs/api/scoring_methodology.md`](api/scoring_methodology.md), Contract-Referenz in [`docs/api/contract-v1.md`](api/contract-v1.md) und Katalog-Abdeckungs-Tests in `tests/test_api_field_catalog.py`.
  - ✅ 2026-02-27: #79 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (DoD-Checkboxen im Issue gesetzt, Re-Validation via `python3 scripts/validate_field_catalog.py` und `python3 -m pytest -q tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py`).
  - ✅ 2026-02-27: #31 abgeschlossen (BL-20.5.b Bau-Eignung light Heuristik) mit deterministischer Heuristik-Implementierung (`src/suitability_light.py`), Integration in den Address-Report (`src/address_intel.py`), transparenter Faktor-/Limitierungsdoku in [`docs/api/scoring_methodology.md`](api/scoring_methodology.md) sowie Regressionstests in `tests/test_suitability_light.py`.
  - ✅ 2026-02-28: #30 abgeschlossen (BL-20.5.a Kartenklick → Standort-Resolution) mit additivem Koordinaten-Inputpfad in `POST /analyze` (`coordinates.lat/lon`, optionales `snap_mode`), robustem WGS84→LV95+`MapServer/identify`-Resolution-Pfad inkl. Distanz-Gate in `src/web_service.py`, aktualisierter Strategy-/User-Doku ([`docs/api/address-resolution-strategy.md`](api/address-resolution-strategy.md), [`docs/user/api-usage.md`](user/api-usage.md)) sowie Edge-Case-Tests in `tests/test_web_service_coordinate_input.py`.
  - ✅ 2026-03-02: #735 abgeschlossen (Testing Catch-up): Coordinate-Input-Validation um zusätzliche negative/edge-case Tests ergänzt (NaN/Inf, Welt-Bounds, fehlende Pflichtfelder). Re-Validation: `pytest -q tests/test_web_service_coordinate_input.py`.
  - ✅ 2026-03-02: #736 abgeschlossen (Testing Catch-up): Mocked Unit Tests für geo_utils.py (Reframe/GeoAdmin Calls) ergänzt (deterministisch, keine echten Network-Calls). Re-Validation: `.venv/bin/python -m pytest -q tests/test_geo_utils_mocked_http.py`.
  - ✅ 2026-03-02: #737 abgeschlossen (Testing Catch-up): Edge-Case Unit Tests für gwr_codes.py (decode/summarize_building) ergänzt. Re-Validation: `.venv/bin/python -m pytest -q tests/test_gwr_codes_edge_cases.py`.
  - ✅ 2026-02-28: #16 (BL-20.5 Parent) finalisiert und geschlossen, nachdem die Child-Work-Packages #30/#31 vollständig abgeschlossen, die Parent-Checklist synchronisiert und der Backlog-Status konsolidiert wurden.
  - ✅ 2026-02-28: #32 abgeschlossen (BL-20.6.a GUI-Grundlayout + State-Flow) mit neuer GUI-MVP-Shell unter `GET /gui` (`src/gui_mvp.py` + Routing in `src/web_service.py`), dokumentiertem Zustands-/Architekturpfad in [`docs/gui/GUI_MVP_STATE_FLOW.md`](gui/GUI_MVP_STATE_FLOW.md), README-Sync (Endpoint-/Dokuindex) sowie regressionssichernden Service-Tests in `tests/test_web_service_gui_mvp.py`.
  - ✅ 2026-02-28: #33 abgeschlossen (BL-20.6.b Karteninteraktion + Ergebnispanel) mit klickbarer CH-Kartenfläche in `src/gui_mvp.py` (Koordinatenprojektion auf WGS84-Bounds, `coordinates`-Analyze-Flow inkl. Marker/Accessibility), erweiterten Kernfaktor-/Input-Metadaten im Result-Panel, aktualisierter GUI-State-/E2E-Doku in [`docs/gui/GUI_MVP_STATE_FLOW.md`](gui/GUI_MVP_STATE_FLOW.md), README-Sync und regressionssichernden Marker-Checks in `tests/test_web_service_gui_mvp.py`.
  - ✅ 2026-02-28: #17 (BL-20.6 Parent) finalisiert und geschlossen, nachdem die Child-Work-Packages #32/#33 bestätigt, der BL-30-Forward-Compatibility-Nachweis in [`docs/gui/GUI_MVP_STATE_FLOW.md`](gui/GUI_MVP_STATE_FLOW.md) verankert und die Parent-Checklist synchronisiert wurde.
  - ✅ 2026-02-26: #80 abgeschlossen (BL-20.1.f.wp2 Berechnungslogik + Interpretationsrahmen) mit erweiterten Methodik-/Band-/Bias-Abschnitten in [`docs/api/scoring_methodology.md`](api/scoring_methodology.md) und zusätzlichem Doku-Guard in `tests/test_api_field_catalog.py`.
  - ✅ 2026-02-27: #80 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (DoD-Checkboxen im Issue gesetzt, Re-Validation via `python3 scripts/validate_field_catalog.py` und `python3 -m pytest -q tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py`).
  - ✅ 2026-02-26: #81 abgeschlossen (BL-20.1.f.wp3 Worked Examples) mit drei reproduzierbaren Score-Fallstudien inkl. Referenzartefakten unter [`docs/api/examples/scoring/worked-example-01-high-confidence.output.json`](api/examples/scoring/worked-example-01-high-confidence.output.json) (repräsentativ für das Artefaktset) und Reproduzierbarkeits-Checks in `tests/test_api_field_catalog.py`.
  - ✅ 2026-02-26: #82 abgeschlossen (BL-20.1.f.wp4 Golden-Tests + Methodik-Versionierung) mit neuen Drift-Golden-Checks in `tests/test_scoring_methodology_golden.py`, verankerten Versionierungs-/Migrationsregeln in [`docs/api/scoring_methodology.md`](api/scoring_methodology.md) und expliziter CI-Abdeckung in `.github/workflows/contract-tests.yml`.
  - ✅ 2026-03-02: #712 abgeschlossen (WP Scoring Explainability – Komponenten-Diff/Output für Golden-Tests) mit diff-freundlichem Snapshot (weights + contributions) in `tests/test_scoring_methodology_golden.py`; Re-Validation via `python3 -m unittest -q tests.test_scoring_methodology_golden`.
  - ✅ 2026-03-02: #713 abgeschlossen (WP Calibration Loop – golden run + drift report) mit neuem Drift-Report-CLI [`scripts/run_scoring_golden_drift_report.py`](../scripts/run_scoring_golden_drift_report.py) (JSON+Markdown, inkl. Komponenten-Snapshot pro Case) und Doku-Verlinkung in [`docs/api/scoring_methodology.md`](api/scoring_methodology.md); Re-Validation via `python3 -m unittest -q tests.test_scoring_golden_drift_report_script`.
  - ✅ 2026-02-27: #78 (BL-20.1.f Parent) finalisiert und geschlossen, nachdem alle Child-Work-Packages #79/#80/#81/#82 inkl. Checklist-/Issue-Reconciliation abgeschlossen waren.
  - ✅ 2026-02-27: #78 Checklist-/Issue-Sync nach erneutem Crawler-Reopen final nachgezogen (Akzeptanz-Checkboxen im Parent gesetzt, Child-Status reconcilied, Re-Validation via `python3 -m pytest -q tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py`).
  - ✅ 2026-02-26: #91 abgeschlossen (BL-20.1.g.wp1 Explainability-v2 Contract/Feldpfade) mit erweiterten Contract-Schemata (`docs/api/schemas/v1/location-intelligence.response.schema.json`), Explainability-v2-Beispieldaten (legacy + grouped) und zusätzlichen Guard-Checks in `tests/test_api_contract_v1.py` + `tests/test_api_field_catalog.py`.
  - ✅ 2026-02-27: #91 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (DoD-Checkboxen im Issue gesetzt, Re-Validation via `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py`).
  - ✅ 2026-02-26: #93 abgeschlossen (BL-20.1.g.wp3 Integrator-Guide) mit neuem Leitfaden [`docs/user/explainability-v2-integrator-guide.md`](user/explainability-v2-integrator-guide.md), Cross-Links aus Contract-/User-Doku (`docs/api/contract-v1.md`, `docs/user/api-usage.md`, `docs/user/README.md`) und abgesicherter Doku-Regression (`pytest -q tests/test_user_docs.py tests/test_markdown_links.py`).
  - ✅ 2026-02-27: #93 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (DoD-Checkboxen im Issue gesetzt, Nachweis ergänzt, Re-Validation via `pytest -q tests/test_user_docs.py tests/test_markdown_links.py`).
  - ✅ 2026-02-27: #92 abgeschlossen (BL-20.1.g.wp2 E2E-Präferenzbeispiele) mit zwei konträren Explainability-Referenzsets unter [`docs/api/examples/explainability/explainability-e2e-01-quiet-first.output.json`](api/examples/explainability/explainability-e2e-01-quiet-first.output.json) und [`docs/api/examples/explainability/explainability-e2e-02-urban-first.output.json`](api/examples/explainability/explainability-e2e-02-urban-first.output.json), Methodik-Verlinkung in [`docs/api/scoring_methodology.md`](api/scoring_methodology.md) und Guard-Erweiterung in `tests/test_scoring_methodology_golden.py`.
  - ✅ 2026-02-27: #87 (BL-20.1.g Parent) finalisiert und geschlossen, nachdem die Child-Work-Packages #91/#92/#93 vollständig abgeschlossen, die Parent-Checklist reconciled und die Explainability-v2-Nachweise via `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py tests/test_user_docs.py tests/test_markdown_links.py` erneut verifiziert wurden.
  - ✅ 2026-02-27: #127 abgeschlossen (BL-20.1.h Capability-/Entitlement-Envelope) mit additivem Contract-Entwurf für `options.capabilities`/`options.entitlements` sowie `result.status.capabilities`/`result.status.entitlements` in `docs/api/contract-v1.md` + `docs/api/contract-stability-policy.md`, erweiterten v1-Schemas (`docs/api/schemas/v1/location-intelligence.request.schema.json`, `docs/api/schemas/v1/location-intelligence.response.schema.json`) und Legacy-Kompatibilitätsnachweisen in `tests/test_api_contract_v1.py` + `tests/test_contract_compatibility_regression.py`.
  - ✅ 2026-02-27: #279 abgeschlossen (BL-20.1.j stabiles grouped Response-Schema v1) mit neuem normativen Schema [`docs/api/schemas/v1/analyze.grouped.response.schema.json`](api/schemas/v1/analyze.grouped.response.schema.json), versionierter Kernpfad-SSOT [`docs/api/schemas/v1/analyze.grouped.core-paths.v1.json`](api/schemas/v1/analyze.grouped.core-paths.v1.json), Human-Guide [`docs/api/grouped-response-schema-v1.md`](api/grouped-response-schema-v1.md), additiven before/after-Referenzpayloads unter `docs/api/examples/current/` sowie Guard-Tests in `tests/test_grouped_response_schema_v1.py`.
  - ✅ 2026-02-27: #287 abgeschlossen (BL-20.1.k.wp1 Contract: Code-only Response + Dictionary-Referenzfelder) mit additivem Contract-Diff in [`docs/api/contract-v1.md`](api/contract-v1.md), Dictionary-Envelope in den Response-Schemas ([`docs/api/schemas/v1/analyze.grouped.response.schema.json`](api/schemas/v1/analyze.grouped.response.schema.json), [`docs/api/schemas/v1/location-intelligence.response.schema.json`](api/schemas/v1/location-intelligence.response.schema.json)), neuen before/after-Referenzpayloads für die Code-only-Migration unter `docs/api/examples/current/analyze.response.grouped.code-only-*.json` und Guard-Erweiterungen in `tests/test_api_contract_v1.py` + `tests/test_grouped_response_schema_v1.py`.
  - ✅ 2026-02-27: #288 abgeschlossen (BL-20.1.k.wp2 Dictionary-Endpoints, versioniert + cachebar) mit neuen GET-Routen in `src/web_service.py` (`/api/v1/dictionaries`, `/api/v1/dictionaries/<domain>`), stabilen Domain-/Index-ETags und Conditional-GET (`If-None-Match` -> `304`) inkl. Cache-Headern, Contract-/User-Doku-Update in [`docs/api/contract-v1.md`](api/contract-v1.md) + [`docs/user/api-usage.md`](user/api-usage.md) sowie E2E-/Contract-Guards in `tests/test_web_e2e.py` und `tests/test_api_contract_v1.py`.
  - ✅ 2026-02-27: #289 abgeschlossen (BL-20.1.k.wp3 Analyze code-first) mit runtime-seitiger code-first Projektion in `src/web_service.py` (Dictionary-Envelope in `result.status`, Entfernen von `building.decoded`/`energy.decoded_summary`, Normalisierung nach `*.codes`), ergänztem Building-Code-Pfad in `src/address_intel.py`, aktualisierten Contract-/Schema-/User-Hinweisen (`docs/api/contract-v1.md`, `docs/api/grouped-response-schema-v1.md`, `docs/user/api-usage.md`) sowie Payload-Reduktions-/Regressionstests in `tests/test_web_service_grouped_response.py` und `tests/test_web_e2e.py`.
  - ✅ 2026-02-27: #290 abgeschlossen (BL-20.1.k.wp4 Migration/Kompatibilitätsmodus/Doku/Tests) mit optionalem Legacy-Migrationsflag `options.include_labels` (`src/web_service.py`), validiertem Fehlerpfad für nicht-boolsche Werte, erweitertem E2E-/Projektions-Testset (`tests/test_web_e2e.py`, `tests/test_web_service_grouped_response.py`) sowie dokumentierter Sunset-/Rollout-Strategie in `docs/api/contract-v1.md`, `docs/api/contract-stability-policy.md`, `docs/api/grouped-response-schema-v1.md`, `docs/user/api-usage.md` und `docs/OPERATIONS.md`.
  - ✅ 2026-02-27: #278 abgeschlossen (BL-20.1.i Response-Dedupe) mit neuem `options.response_mode` (`compact` default, `verbose` opt-in) in `src/web_service.py`, deduplizierter `result.data.by_source`-Projektion via `module_ref`/`module_refs`, aktualisierter Doku in [`docs/api/grouped-response-schema-v1.md`](api/grouped-response-schema-v1.md), [`docs/api/contract-v1.md`](api/contract-v1.md), [`docs/user/api-usage.md`](user/api-usage.md) sowie Regressions-/E2E-Guards in `tests/test_web_service_grouped_response.py` und `tests/test_web_e2e.py`.
  - ✅ 2026-02-27: #28 abgeschlossen (BL-20.4.a Umfelddaten-Radiusmodell + Kennzahlen) mit neuem 3-Ring-Umfeldprofil `intelligence.environment_profile` in `src/address_intel.py` (Radiusmodell inkl. Ring-Gewichtung, Kernkennzahlen `density/diversity/accessibility/family/vitality/quietness/overall`, Domain-/Ring-Counts + Top-Signale), Compact-Summary-Integration, neuer Methodik-Doku [`docs/api/environment-profile-radius-model-v1.md`](api/environment-profile-radius-model-v1.md) und Regressionstests in `tests/test_core.py`.
  - ✅ 2026-02-27: #29 abgeschlossen (BL-20.4.b Umfeldprofil-Scoring v1) mit explizitem `score_model` im `environment_profile`-Output (`src/address_intel.py`, faktorweise Explainability inkl. `weighted_points`), neuer Methodik-/Kalibrierungsdoku [`docs/api/environment-profile-scoring-v1.md`](api/environment-profile-scoring-v1.md) (inkl. Link aus [`docs/api/environment-profile-radius-model-v1.md`](api/environment-profile-radius-model-v1.md)) sowie Regressionen für Formel- und Archetypen-Kalibrierung in `tests/test_core.py`.
  - ✅ 2026-02-27: #85 abgeschlossen (BL-20.4.c Preference-Profile Contract) mit optionalem `preferences`-Envelope inkl. Defaults/Enum-/Range-Validierung in `src/web_service.py`, erweitertem v1-Request-Schema (`docs/api/schemas/v1/location-intelligence.request.schema.json`), ergänzten Contract-/User-Dokus (`docs/api/contract-v1.md`, `docs/api/contract-stability-policy.md`, `docs/api/preference-profiles.md`, `docs/user/api-usage.md`) sowie Nachweisen via `tests/test_web_e2e.py`, `tests/test_api_contract_v1.py`, `tests/test_contract_compatibility_regression.py` und `python3 scripts/validate_field_catalog.py`.
  - ✅ 2026-02-27: #180 abgeschlossen (BL-20.4.d.wp1 Reweighting-Engine-Core) mit neuem deterministischem Scoring-Modul `src/personalized_scoring.py` (inkl. stabiler Fallback-Regel ohne Präferenzsignal), ergänzter Methodik-Doku in `docs/api/scoring_methodology.md` sowie Unit-Test-Absicherung in `tests/test_personalized_scoring_engine.py`.
  - ✅ 2026-02-27: #181 abgeschlossen (BL-20.4.d.wp2 API-Response-Felder) mit expliziten `base_score`/`personalized_score`-Feldern im Suitability-Payload (`src/suitability_light.py`, Fallback `personalized_score == base_score`), aktualisierten Contract-/Schema-Artefakten (`docs/api/contract-v1.md`, `docs/api/schemas/v1/location-intelligence.response.schema.json`, `docs/api/scoring_methodology.md`, `docs/api/field_catalog.json`) sowie Nachweisen via `python3 scripts/validate_field_catalog.py`, `pytest -q tests/test_suitability_light.py tests/test_api_contract_v1.py tests/test_api_field_catalog.py`.
  - ✅ 2026-02-27: #182 abgeschlossen (BL-20.4.d.wp3 Methodik-Doku + Präferenzmatrix) mit erweitertem Abschnitt zu zweistufigem Scoring und normativer Delta-Matrix in [`docs/api/scoring_methodology.md`](api/scoring_methodology.md), expliziter Default-/Fallback-Dokumentation (`personalized_score == base_score` ohne Signal) sowie zusätzlichem Doku-Guard in `tests/test_scoring_methodology_golden.py`; Nachweise via `python3 scripts/validate_field_catalog.py` und `pytest -q tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py tests/test_markdown_links.py`.
  - ✅ 2026-02-27: #183 abgeschlossen (BL-20.4.d.wp4 Golden-Testset konträrer Präferenzprofile) mit neuen runtime-nahen Artefakten `docs/api/examples/scoring/personalized-golden-01-quiet-first.*` und `docs/api/examples/scoring/personalized-golden-02-urban-first.*`, Methodik-Verlinkung in `docs/api/scoring_methodology.md` sowie Drift-/Determinismus-Guards in `tests/test_scoring_methodology_golden.py`.
  - ✅ 2026-02-27: #189 abgeschlossen (BL-20.4.d.wp5 Runtime-Integration) mit deterministischer Einbindung der Reweighting-Engine in `/analyze` (`src/web_service.py`), additivem `suitability_light.personalization`-Payload (Fallback/Signalstärke/Gewichte), aktualisierter Methodik-Doku (`docs/api/scoring_methodology.md`) und E2E-Nachweisen für Präferenz- sowie Legacy-Fallback-Pfad (`tests/test_web_e2e.py`).
  - ✅ 2026-02-27: #190 abgeschlossen (BL-20.4.d.wp6 Gewichts-Normalisierung + Guardrails) mit robuster Präferenzgewichts-Validierung inkl. klarer Fehlerpfade für Typfehler/`NaN`/`Inf`/Out-of-Range (`src/web_service.py`), wirksamkeitssensitiver Fallback-Logik bei Null-Intensität (`src/personalized_scoring.py`), synchronisierten Contract-/Methodik-Hinweisen (`docs/api/contract-v1.md`, `docs/api/scoring_methodology.md`, `docs/user/api-usage.md`) sowie erweiterter Testabdeckung (`tests/test_web_e2e.py`, `tests/test_api_contract_v1.py`, `tests/test_personalized_scoring_engine.py`).
  - ✅ 2026-02-27: #191 abgeschlossen (BL-20.4.d.wp7 Runtime-Fallback-Status) mit transparentem Laufzeitstatus `result.status.personalization` (`active|partial|deactivated`) inkl. Herkunftskennzeichnung (`src/web_service.py`), dokumentiertem Contract-/Methodik-Update (`docs/api/contract-v1.md`, `docs/api/scoring_methodology.md`, `docs/user/api-usage.md`, Schema-Update in `docs/api/schemas/v1/location-intelligence.response.schema.json`) sowie Regressionstests für aktive/partielle/deaktivierte Pfade (`tests/test_web_e2e.py`, `tests/test_web_service_grouped_response.py`, `tests/test_api_contract_v1.py`).
  - ✅ 2026-02-27: #88 abgeschlossen (BL-20.4.e Preference-Presets) mit v1-Preset-Katalog (`urban_lifestyle`, `family_friendly`, `quiet_residential`, `car_commuter`, `pt_commuter`) inkl. `preferences.preset`/`preferences.preset_version`-Validierung und deterministischen Override-Regeln in `src/web_service.py`, erweitertem Request-Schema (`docs/api/schemas/v1/location-intelligence.request.schema.json`), aktualisierter Contract-/Stability-/User-Doku (`docs/api/contract-v1.md`, `docs/api/contract-stability-policy.md`, `docs/api/preference-profiles.md`, `docs/user/api-usage.md`, `README.md`) sowie neuen Preset-Regressionstests (`tests/test_web_e2e.py`, `tests/test_api_contract_v1.py`).
  - ✅ 2026-02-27: #15 (BL-20.4 Parent) finalisiert und geschlossen, nachdem die Work-Packages #28/#29/#85/#86/#88 sowie die Follow-up-Härtungen #189/#190/#191 vollständig umgesetzt, die Parent-Checklist synchronisiert und BL-30-Forward-Compatibility-Felder (`base_score`, `personalized_score`, faktorweise Explainability + Personalization-Status) als stabile Integrationsbasis dokumentiert wurden.
  - ✅ 2026-02-27: #142 (BL-20.x Parent) in atomare Work-Packages #202/#203/#204/#205 zerlegt (Actionable-Filter, Report-Schema, Vision↔Issue-Coverage, Code↔Doku-Drift) und Parent-Checklist synchronisiert.
  - ✅ 2026-02-27: #202 abgeschlossen (BL-20.x.wp1 Actionable TODO/FIXME-Filter) mit neuem Filter-Guard in `scripts/github_repo_crawler.py`, erweiterter Testabdeckung in `tests/test_github_repo_crawler.py` und Doku-Sync in `README.md` + `docs/WORKSTREAM_BALANCE_BASELINE.md`.
  - ✅ 2026-02-27: #203 abgeschlossen (BL-20.x.wp2 Finding-Schema + Consistency-Reports) mit strukturiertem Finding-Format (`type`, `severity`, `evidence`, `source`), automatischer Artefaktausgabe in `reports/consistency_report.json` + `reports/consistency_report.md`, Regressionsausbau in `tests/test_github_repo_crawler.py` sowie Dry-Run-Doku in `README.md`.
  - ✅ 2026-02-27: #204 abgeschlossen (BL-20.x.wp3 Vision↔Issue-Coverage-Check) mit heuristischer Requirement-Extraktion aus `docs/VISION_PRODUCT.md`, deterministischem Issue-Matching inkl. Gap-/Unclear-Findings in `scripts/github_repo_crawler.py`, Coverage-Block im `reports/consistency_report.md` sowie erweiterten Parser-/Matcher-Regressionstests in `tests/test_github_repo_crawler.py` (inkl. `./scripts/check_crawler_regression.sh`).
  - ✅ 2026-02-27: #204 Checklist-/Issue-Sync nach Crawler-Reopen nachgezogen (DoD-Checkboxen im Issue gesetzt, Re-Validation via `pytest -q tests/test_github_repo_crawler.py -k 'vision or coverage'`).
  - ✅ 2026-02-27: #205 abgeschlossen (BL-20.x.wp4 Code↔Doku-Drift-Check) mit neuem MVP-Drift-Audit in `scripts/github_repo_crawler.py` (Route-/Flag-Indikatoren, stale Route-Referenzen, evidenzbasierte Findings inkl. Finding-Cap), erweitertem Regressionstest in `tests/test_github_repo_crawler.py` und README-Sync für den Crawler-Regressionsscope.
  - ✅ 2026-02-27: #142 (BL-20.x Parent) finalisiert und geschlossen, nachdem alle Child-Work-Packages #202/#203/#204/#205 umgesetzt, Consistency-Reports reproduzierbar erzeugt (`python3 scripts/github_repo_crawler.py --dry-run`) und der Operations-Runbook-Pfad in `docs/OPERATIONS.md` ergänzt wurde.
  - ✅ 2026-02-26: #98 (Crawler P0 Workstream-Balance) vollständig abgeschlossen nach atomarer Umsetzung der Work-Packages #99/#100/#101 (Baseline, Heuristik-Tests, CI-Smokepfad) inkl. Parent-Checklist-Sync.
  - ✅ 2026-02-26: #100 abgeschlossen (BL-98.wp2 Testing-Catch-up) mit neuem Testmodul `tests/test_github_repo_crawler.py` (auslösende/nicht-auslösende/duplikatvermeidende Balance-Szenarien), extrahierter Zähllogik `compute_workstream_counts` in `scripts/github_repo_crawler.py`, False-Positive-Fix für Kurz-Keywords (`guide` vs. `gui`) und README-Testaufruf für den fokussierten Crawler-Regressionscheck.
  - ✅ 2026-02-26: #99 abgeschlossen (BL-98.wp1 Baseline + Catch-up-Plan) mit reproduzierbarer Baseline-Doku in [`docs/WORKSTREAM_BALANCE_BASELINE.md`](WORKSTREAM_BALANCE_BASELINE.md), neuem report-only CLI-Modus `--print-workstream-balance` (`markdown|json`) im Crawler und ergänzender Testabdeckung in `tests/test_github_repo_crawler.py`.
  - ✅ 2026-02-26: #101 abgeschlossen (BL-98.wp3 CI-Regressionspfad) mit reproduzierbarem Check-Entrypoint `scripts/check_crawler_regression.sh`, neuem CI-Workflow `.github/workflows/crawler-regression.yml` und verankerter Runbook-Dokumentation in README + `docs/WORKSTREAM_BALANCE_BASELINE.md`.
  - ✅ 2026-02-27: #158 abgeschlossen (Crawler P0 Workstream-Balance False-Positive Recovery) mit Auto-Close-Logik für bestehende P0-Balance-Issues bei wiederhergestelltem Zielkorridor (`scripts/github_repo_crawler.py`), inkl. Regressionstest (`tests/test_github_repo_crawler.py`) und aktualisierter Baseline-Doku (`docs/WORKSTREAM_BALANCE_BASELINE.md`).
  - ✅ 2026-02-27: #217 abgeschlossen (stale Workstream-Balance Incident): Re-Baseline via `python3 scripts/github_repo_crawler.py --dry-run --print-workstream-balance --format markdown` ergab weiterhin Gap `0` (aktuell `Dev=1/Doku=1/Testing=1`), daher kein zusätzlicher P0-Catch-up-Bedarf; Status-/Issue-Sync und Baseline-Doku wurden entsprechend nachgezogen.
  - ✅ 2026-02-28: #335 abgeschlossen (BL-333.wp1 Catch-up-Plan explizit ausgeben) mit neuem Delta-Plan im Crawler-Baseline-Output/Issue-Body (`scripts/github_repo_crawler.py`), ergänzter Regression in `tests/test_github_repo_crawler.py` und Doku-Sync in [`docs/WORKSTREAM_BALANCE_BASELINE.md`](WORKSTREAM_BALANCE_BASELINE.md). Parent #333 wurde in #335/#336/#337 atomisiert.
  - ✅ 2026-02-28: #337 abgeschlossen (BL-333.wp3 Testing-Catch-up Regression+Smoke-Priorisierung) mit festem pytest-Runner [`scripts/check_testing_catchup_sequence.sh`](../scripts/check_testing_catchup_sequence.sh), priorisiertem Runbook [`docs/testing/testing-catchup-regression-smoke-sequence.md`](testing/testing-catchup-regression-smoke-sequence.md) inkl. verbindlichem QA-Abschlussnachweis sowie Guard-Tests in `tests/test_testing_catchup_sequence_assets.py`.
  - ✅ 2026-02-26: #54 abgeschlossen (BL-20.7.a.r1) mit reproduzierbarer Packaging-Baseline in [`docs/PACKAGING_BASELINE.md`](PACKAGING_BASELINE.md), README-Integration und Doku-Regressionstest.
  - ✅ 2026-02-26: #55 abgeschlossen (BL-20.7.a.r2) mit konsolidierter Packaging-/Runtime-Konfigurationsmatrix (Pflicht/Optional, Default/Beispiel) in [`docs/PACKAGING_BASELINE.md`](PACKAGING_BASELINE.md) inkl. Cross-Link auf [`docs/user/configuration-env.md`](user/configuration-env.md).
  - ✅ 2026-02-26: #56 abgeschlossen (BL-20.7.a.r3) mit API-only Basis-Release-Checkliste in [`docs/PACKAGING_BASELINE.md`](PACKAGING_BASELINE.md) und Cross-Link aus [`docs/OPERATIONS.md`](OPERATIONS.md).
  - ✅ 2026-02-26: #34 abgeschlossen (BL-20.7.a Parent) nach Abschluss aller Work-Packages #54/#55/#56; Backlog-/Status-Sync konsolidiert.
  - ✅ 2026-02-28: #37 abgeschlossen (BL-20.7.r2) mit reproduzierbarem CH-Demo-Datenset in [`docs/DEMO_DATASET_CH.md`](DEMO_DATASET_CH.md), erwarteten Kernaussagen inkl. Confidence/Unsicherheiten und direkter Verlinkung im Demo-Flow von [`docs/GO_TO_MARKET_MVP.md`](GO_TO_MARKET_MVP.md).
  - ✅ 2026-02-28: #38 abgeschlossen (BL-20.7.r3) mit segmentierten Kaufkriterien, testbaren Pricing-/Packaging-Hypothesen, Capability-Gates für BL-30.1/30.2 und Entscheidungsvorlage für den nächsten GTM-Sprint in [`docs/PACKAGING_PRICING_HYPOTHESES.md`](PACKAGING_PRICING_HYPOTHESES.md).
  - ⏳ Nächster direkter Schritt BL-20.7: Validierungssprint gemäß Interview-/Signalschema aus `docs/PACKAGING_PRICING_HYPOTHESES.md` durchführen und daraus BL-30-Folge-Issues ableiten.
- **Akzeptanzkriterien (Phase 1):**
  - API liefert für Adresse und Kartenpunkt ein einheitliches Ergebnisobjekt (Gebäudeprofil + Umfeldprofil).
  - Ergebnis enthält Explainability-Felder (`sources`, `as_of`, `confidence`, `derived_from`).
  - GUI-MVP unterstützt Adresseingabe + Kartenklick und zeigt Kernindikatoren verständlich an.
  - API und GUI sind unabhängig deploybar und dokumentiert.
- **Teilaufgaben (Startschnitt):**
  1. **BL-20.1 – Domain-Model/API-Vertrag** für Building/Context/Suitability finalisieren.
  2. **BL-20.2 – Datenquellen-Mapping** (swisstopo/GWR/OSM/öffentliche Quellen) inkl. Lizenz-/Nutzungsnotizen.
  3. **BL-20.3 – Vertical A (Adresse → Gebäudeprofil)** produktionsnah bereitstellen.
  4. **BL-20.4 – Vertical B (Adresse → Umfeldprofil)** mit ÖV/POI/Lärmindikatoren.
  5. **BL-20.5 – Vertical C (Kartenpunkt → Bau-Eignung light)** mit Topografie/Hang/Zugang.
  6. **BL-20.6 – GUI-MVP** (Adresse + Kartenklick + Ergebnispanel).
  7. **BL-20.7 – Packaging/Go-to-Market-Basis** (API-only vs. GUI-Angebot trennbar).
- **Prioritätsregel (ab sofort):**
  - Webservice-Feature-Entwicklung hat Vorrang vor Testscript-Hardening.
  - Test-Skripte laufen im Maintenance-Mode (Regression + Stabilität), außer bei neuen Risiken/Anforderungen.
- **Job-Framework-Regel (verbindlich):**
  - Für BL-20 gilt pro Iteration das 3-Säulen-Modell: **Programmierung + Dokumentation + Testing**.
  - BL-20 startet erst nach BL-19-MVP (BL-19.1, 19.2, 19.4, 19.3, 19.7).


### BL-30 — Monetization/Packaging/Deep-Mode/HTML5/Map/Mobile (Later-Track)
- **Priorität:** P3
- **Aufwand:** L
- **Abhängigkeiten:** BL-20 Forward-Compatibility (#6), Capability-/Entitlement-Bridge (#127)
- **Status:** ✅ Vollständig abgeschlossen (2026-03-01, BL-30.1 bis BL-30.6 inkl. BL-30.2-Leafs #465/#466 sowie Parent-Sync #106/#128 abgeschlossen); ✅ Follow-up-Track #577 (WPs #585/#586/#587/#588) gemerged (2026-03-01); ✅ zusätzliche Doc-Refinement-WPs (#625/#626/#627/#628/#629 abgeschlossen) (siehe Issues)
- **Nächster Schritt:** keiner (BL-30 vollständig abgeschlossen).
- **Ziel:** GTM-validierte Monetarisierungs-/Packaging-Linie mit sauberer technischer Entitlement-Übergabe aufbauen.
- **Work-Packages (BL-30.1 Parent #105):**
  - [x] #458 — BL-30.1.wp1 Pricing-Tier-/Limit-Matrix v1 inkl. Capability-Gates (abgeschlossen 2026-03-01)
  - [x] #459 — BL-30.1.wp2 Unit-Economics-Hypothesen je Tier/Segment strukturieren (abgeschlossen 2026-03-01)
  - [x] #460 — BL-30.1.wp3 Preisvalidierungs-Experimentkarten + Entscheidungslogik (abgeschlossen 2026-03-01)
  - [x] #461 — BL-30.1.wp4 Konsolidierter Abschluss + BL-30.2 Übergabe (abgeschlossen 2026-03-01)
- **Work-Packages (BL-30.2 Parent #106):**
  - [x] #465 — BL-30.2.wp1 Entitlement-Contract v1 + Gate-Semantik aus BL-30.1 konsolidieren (abgeschlossen 2026-03-01)
  - [x] #466 — BL-30.2.wp2 Checkout-/Lifecycle-Contract + idempotenter Entitlement-Sync (abgeschlossen 2026-03-01)
- **Work-Packages (BL-30.3 Parent #107):**
  - [x] #468 — BL-30.3.wp1 Deep-Mode-Contract v1 (Request/Status/Fallback) spezifizieren (abgeschlossen 2026-03-01)
  - [x] #469 — BL-30.3.wp2 Deep-Mode-Orchestrierung + Runtime-Guardrails designen (abgeschlossen 2026-03-01)
  - [x] #470 — BL-30.3.wp3 Add-on-/Quota-Hypothesen + Transparenzrahmen ausarbeiten (abgeschlossen 2026-03-01)
  - [x] #472 — BL-30.3.wp2.r1 Runtime-Orchestrator im `/analyze`-Flow implementieren (abgeschlossen 2026-03-01)
  - [x] #473 — BL-30.3.wp2.r2 Deep-Mode-Telemetrie + Trace-Evidence absichern (abgeschlossen 2026-03-01)
- **Work-Packages (BL-30.4 Parent #108):**
  - [x] #479 — BL-30.4.wp1 HTML5-UI-Architektur v1 (ADR + Boundary-Guardrails) (abgeschlossen 2026-03-01)
  - [x] #480 — BL-30.4.wp2 Zustandsmodell + Interaktions-Contract für dynamische UI-Flows (abgeschlossen 2026-03-01)
  - [x] #481 — BL-30.4.wp3 Performance-Budget + Browser-Caching-Strategie v1 (abgeschlossen 2026-03-01)
  - [x] #482 — BL-30.4.wp4 Explainability-/Scoring-UX-Standards (Desktop+Tablet) (abgeschlossen 2026-03-01)
- **Work-Packages (BL-30.5 Parent #110):**
  - [x] #494 — BL-30.5.wp1 Karten-Workflow-Spec v1 (Map-Pick -> Analyze -> Result) (abgeschlossen 2026-03-01)
  - [x] #495 — BL-30.5.wp2 Datenquellen-/Lizenzmatrix für Map- und Bau-/Zufahrtslayer (abgeschlossen 2026-03-01)
  - [x] #496 — BL-30.5.wp3 Response-Modell v1 für Bau-/Zufahrtseignung (additiv) (abgeschlossen 2026-03-01)
  - [x] #498 — BL-30.5.wp2.f1 OSM-Tile-/ODbL-Compliance-Entscheid für produktiven Kartenbetrieb (abgeschlossen 2026-03-01)
- **Work-Packages (BL-30.6 Parent #113):**
  - [x] #502 — BL-30.6.wp1 Mobile Live-Geolocation API-Contract v1 (abgeschlossen 2026-03-01)
  - [x] #503 — BL-30.6.wp2 Mobile Geolocation State-/Interaction-Contract v1 (Permission/Retry/Offline) (abgeschlossen 2026-03-01)
  - [x] #504 — BL-30.6.wp3 Mobile Geolocation Trace-/Privacy-Guardrails v1 (abgeschlossen 2026-03-01)
- **Work-Packages (BL-30 Parent #128):**
  - [x] #509 — BL-30.parent.wp1 Dependency-Gates + Reihenfolgeplan v1 für BL-30.2 dokumentieren (abgeschlossen 2026-03-01)
  - [x] #510 — BL-30.parent.wp2 Rebuild-vs-Ausbau-Guardrails + API-first Anschluss konsolidieren (abgeschlossen 2026-03-01)
- **Fortschritt (2026-03-01):**
  - ✅ #105 in atomare Child-Issues #458/#459/#460/#461 zerlegt (oldest-first Leaf-Umsetzung).
  - ✅ #577 atomisiert in Work-Packages #585/#586/#587/#588, weil Scope und Deliverables >1 Slot sind und parallelisierbare Leaf-Pakete benötigen.
  - ✅ #585 abgeschlossen: GTM→DB-Architekturgrundlage v1 in [`docs/GTM_TO_DB_ARCHITECTURE_V1.md`](GTM_TO_DB_ARCHITECTURE_V1.md) dokumentiert (Entscheidungsmatrix, kanonisches Tenant-Datenmodell, Ownership-Regeln, No-regrets Defaults + Trade-offs).
  - ✅ #586 abgeschlossen: Entitlement-/Billing-Lifecycle v1 in [`docs/api/entitlement-billing-lifecycle-v1.md`](api/entitlement-billing-lifecycle-v1.md) dokumentiert (Capability-/Entitlement-Modell, Lifecycle-Zustände inkl. Übergangsregeln, idempotente Webhook-/Fehlerstrategie, Metering-Granularität + Aggregationslogik, Non-Goals/Risiken).
  - ✅ #587 abgeschlossen: Async-Analyze Domain-Design v1 in [`docs/api/async-analyze-domain-design-v1.md`](api/async-analyze-domain-design-v1.md) dokumentiert (Job-State-Machine `queued|running|partial|completed|failed|canceled`, Datenmodell `jobs`/`job_events`/`job_results`/`notifications` inkl. Mindestindizes, Progress-/Chunking-/Partial-Strategie, Result-Page-/Retention-Regeln und vorbereitete API-/Eventing-Schnittpunkte).
  - ✅ #588 abgeschlossen: MVP→Scale Rollout-Plan v1 in [`docs/MVP_TO_SCALE_ROLLOUT_PLAN_V1.md`](MVP_TO_SCALE_ROLLOUT_PLAN_V1.md) dokumentiert (additiver Stufenplan mit Guardrails, Risiken/Mitigations pro Phase, Abnahmekriterien für Parent #577 und atomisierte Folge-Issues #592/#593/#594 inkl. Abhängigkeitskette).
  - ✅ #592 abgeschlossen: Async-Runtime-Skeleton v1 umgesetzt (persistenter File-Store `src/api/async_jobs.py`, additive Async-Option `options.async_mode.requested`, neue Status-/Result-Endpunkte `GET /analyze/jobs/{job_id}` + `GET /analyze/results/{result_id}`, Basisschema in [`docs/sql/async_jobs_schema_v1.sql`](sql/async_jobs_schema_v1.sql), Implementierungsdoku in [`docs/api/async-analyze-runtime-skeleton-v1.md`](api/async-analyze-runtime-skeleton-v1.md) und Guard-Tests für Endpunkte/Transitions).
  - ✅ #593 abgeschlossen (2026-03-01): Worker-Pipeline v1 umgesetzt mit Queue-/Dispatcher-light (`src/api/async_worker_runtime.py`), asynchronem Lifecycle `queued -> running -> partial -> completed`, persistierten Partial-Snapshots + konsistentem Eventing (`job.partial`), idempotentem Cancel-Endpoint `POST /analyze/jobs/{job_id}/cancel`, deterministischem Fehlerpfad (`error_code`/`error_message`/`retry_hint`) sowie Dokumentation in [`docs/api/async-analyze-worker-pipeline-v1.md`](api/async-analyze-worker-pipeline-v1.md) und End-to-End-Regressionen in `tests/test_async_jobs_runtime_skeleton.py`.
  - ✅ #594 atomisiert in Work-Packages #599/#600/#601/#602 und nach Abschluss aller Leafs finalisiert/geschlossen (2026-03-01), da Scope aus mehreren unabhängigen Deliverables (>1 Slot) bestand und oldest-first Leaf-Umsetzung erforderte.
  - ✅ #577 Follow-up (WPs #585/#586/#587/#588) abgeschlossen und gemerged (2026-03-01); danach um zusätzliche Doc-Refinement-WPs (#625/#626/#627/#628/#629) ergänzt (Status: alle abgeschlossen).
  - ✅ #625 abgeschlossen (2026-03-01): Glossar + Entscheidungs-Matrix (GTM → technische Konsequenzen) in der kanonischen GTM-Doku [`docs/GTM.md`](GTM.md) ergänzt (PR #630).
  - ✅ #626 abgeschlossen (2026-03-01): Data Model v1 als eigenes Referenzdokument in [`docs/DATA_MODEL_v1.md`](DATA_MODEL_v1.md) ergänzt (Entities + Constraints/Indizes + Mermaid-ERD + Rollout-Skizze) und in `docs/GTM.md` verlinkt.
  - ✅ #627 abgeschlossen (2026-03-01): Entitlements/Capabilities v1 als Implementations-/Parallelisierungsreferenz in [`docs/ENTITLEMENTS_v1.md`](ENTITLEMENTS_v1.md) ergänzt (Begriffe, Scopes, Evaluation-Pseudocode, konkrete Capability-Beispiele, Enforcement-Orte) und auf kanonische `docs/api/entitlements-v1.md` verlinkt.
  - ✅ #628 abgeschlossen (2026-03-01): Billing Lifecycle v1 in [`docs/BILLING_LIFECYCLE_v1.md`](BILLING_LIFECYCLE_v1.md) ergänzt (State-Machine + Transition-Matrix + Entitlement-Effects) und auf kanonische [`docs/api/entitlements-v1.md`](api/entitlements-v1.md) referenziert.
  - ✅ #629 abgeschlossen (2026-03-01): Usage/Metering v1 in [`docs/USAGE_METERING_v1.md`](USAGE_METERING_v1.md) ergänzt (Event-Schema + Rollups + Limit-Check-Beispiel) und Abhängigkeiten zu #627/#628 verlinkt.
  - ✅ #599 abgeschlossen (2026-03-01): tenant-sicherer Result-Permalink umgesetzt (`GET /analyze/jobs/{job_id}` + `GET /analyze/results/{result_id}` mit `X-Org-Id`/`X-Tenant-Id` Guard), deterministische Snapshot-Projektion via `view=latest|requested` ergänzt, CORS-Header erweitert und in [`docs/api/async-result-permalink-tenant-guard-v1.md`](api/async-result-permalink-tenant-guard-v1.md) dokumentiert; Regressionen in `tests/test_async_jobs_runtime_skeleton.py` + `tests/test_async_result_permalink_tenant_guard_docs.py`.
  - ✅ #600 abgeschlossen (2026-03-01): Retention-Cleanup für `job_results`/`job_events` in `src/api/async_jobs.py` ergänzt (`cleanup_retention(...)`, terminal-only + TTL-Guards + idempotente Metriken), ausführbares Ops-Skript [`scripts/run_async_retention_cleanup.py`](../scripts/run_async_retention_cleanup.py) für periodische Läufe eingeführt, Implementierungs-/Betriebsdoku in [`docs/api/async-retention-cleanup-v1.md`](api/async-retention-cleanup-v1.md) ergänzt und Regressionen in `tests/test_async_jobs_runtime_skeleton.py` + `tests/test_run_async_retention_cleanup.py` nachgezogen.
  - ✅ #601 abgeschlossen (2026-03-01): In-App-Notification-Pipeline für terminale Async-Jobs (`completed|failed`) im Store ergänzt (`state.notifications` in `src/api/async_jobs.py`, deduplizierbar via `dedupe_key`), additiver Lesepfad `GET /analyze/jobs/{job_id}/notifications` in `src/api/web_service.py` umgesetzt, Implementierungsdoku in [`docs/api/async-in-app-notifications-v1.md`](api/async-in-app-notifications-v1.md) ergänzt und Regressionen in `tests/test_async_jobs_runtime_skeleton.py` + `tests/test_async_in_app_notifications_docs.py` nachgezogen.
  - ✅ #602 abgeschlossen (2026-03-01): Ops-Runbook und Monitoring-Mindestmetriken für Async-Delivery in [`docs/api/async-delivery-ops-runbook-v1.md`](api/async-delivery-ops-runbook-v1.md) ergänzt (Result-Permalink/Retention/Notifications inkl. Alert-Hinweise und Staging/Prod-Smoke-Checklisten), in [`docs/OPERATIONS.md`](OPERATIONS.md) verlinkt und per `tests/test_async_delivery_ops_runbook_docs.py` regressionsgesichert.
  - ✅ #458 abgeschlossen: neue Tier-/Limit-Matrix v1 in [`docs/PRICING_TIER_LIMIT_MATRIX_V1.md`](PRICING_TIER_LIMIT_MATRIX_V1.md), GTM-Hypothesen-Doku verlinkt und Doku-Regression ergänzt.
  - ✅ #459 abgeschlossen: versionierte Unit-Economics-Doku in [`docs/UNIT_ECONOMICS_HYPOTHESES_V1.md`](UNIT_ECONOMICS_HYPOTHESES_V1.md) ergänzt (Tier-/Segment-Annahmen, Sensitivitätshebel, Go/Adjust/Stop-Schwellen) und via Regressionstest abgesichert.
  - ✅ #460 abgeschlossen: experimentfähige Pricing-Karten (3 Kandidaten inkl. Inputs/Outputs/Abbruchkriterien) und standardisierte Go/Adjust/Stop-Entscheidungslogik in [`docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md`](PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md) ergänzt; Follow-up-Issue-Template für BL-30.1/30.2 in [`docs/testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md`](testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md) eingeführt; Doku-Regressionen erweitert.
  - ✅ #461 abgeschlossen: konsolidierter Entscheidungsabschluss in [`docs/BL30_1_CLOSEOUT_V1.md`](BL30_1_CLOSEOUT_V1.md) dokumentiert (Primärkandidat `CAND-API-PRO-390`, Sekundärkandidat `CAND-BIZ-API-890`) und BL-30.2-Handover via Follow-up-Issues #465/#466 plus Parent-Sync in #106 vorbereitet.
  - ✅ #465 abgeschlossen: technischer Entitlement-Contract v1 in [`docs/api/bl30-entitlement-contract-v1.md`](api/bl30-entitlement-contract-v1.md) ergänzt (normativer Gate-Katalog `entitlement.requests.monthly`, `entitlement.requests.rate_limit`, `capability.explainability.level`, `capability.gui.access`, `capability.trace.debug`), additive API-/UI-Auswirkungen und Forward-Compatibility-Guardrails (#6/#127) konsolidiert sowie über `tests/test_bl30_entitlement_contract_docs.py` regressionsgesichert.
  - ✅ #466 abgeschlossen: Checkout-/Lifecycle-Contract v1 in [`docs/api/bl30-checkout-lifecycle-contract-v1.md`](api/bl30-checkout-lifecycle-contract-v1.md) ergänzt (kanonisches Event-Mapping für `created|upgraded|downgraded|canceled`, Idempotenz-Key `provider:<provider_name>:event_id:<id>`, Out-of-order-Schutz, API-Key-Provisioning-/Rotation-Policy), additive API/UI-Statuswirkung dokumentiert und via `tests/test_bl30_checkout_lifecycle_contract_docs.py` regressionsgesichert.
  - ✅ #106 abgeschlossen: BL-30.2 Parent-Checklist auf vollständig erledigt synchronisiert (`#465` + `#466`) und als abgeschlossener Later-Track geschlossen.
  - ✅ #128 abgeschlossen: BL-30-Parent-Checklist finalisiert (`[x] #106`, Parent-DoD vollständig erfüllt) und Issue geordnet geschlossen.
  - ℹ️ Historischer Zwischenstand direkt nach #459/#460 (vor den später abgeschlossenen BL-30.5/30.6-Leafs): BL-30.2 war temporär gate-blocked; nach dokumentiertem GTM-Entscheid (`GTM-DEC-002`) wurde #465 oldest-first wieder aufgenommen.
  - ✅ #107 atomisiert und finalisiert: Work-Packages #468/#469/#470/#472/#473 vollständig abgeschlossen, Parent geschlossen und Parent-Sync in #128 fortgeschrieben (2026-03-01).
  - ✅ #108 atomisiert: Parent-Scope in die Leaf-Work-Packages #479/#480/#481/#482 zerlegt und Parent-Checklist synchronisiert (2026-03-01).
  - ✅ #110 atomisiert: Parent-Scope in die Leaf-Work-Packages #494/#495/#496 zerlegt und Parent-Checklist synchronisiert (2026-03-01).
  - ✅ #113 atomisiert: Parent-Scope in die Leaf-Work-Packages #502/#503/#504 zerlegt und Parent-Checklist synchronisiert (2026-03-01).
  - ✅ #113 finalisiert/geschlossen (2026-03-01): alle BL-30.6-Leafs (#502/#503/#504) bestätigt, Parent-Checklist in #128 auf `[x] #113` fortgeschrieben und Next-Step auf BL-30.2-Entblockung (#457 -> #465/#466) eingegrenzt.
  - ✅ #509 abgeschlossen: kanonische Gate-/Phasen-Doku in [`docs/BL30_PARENT_DEPENDENCY_GATES_PHASE_PLAN_V1.md`](BL30_PARENT_DEPENDENCY_GATES_PHASE_PLAN_V1.md) ergänzt (GO/HOLD/BLOCKED-Matrix für #6/#127/#457, Entblockungsregel und oldest-first Reihenfolge `#465 -> #466`), Parent-DoD-Checklist in #128 fortgeschrieben und per `tests/test_bl30_parent_dependency_gates_phase_plan_docs.py` regressionsgesichert.
  - ✅ #510 abgeschlossen: Rebuild-vs-Ausbau-Guardrails + API-first Anschluss in [`docs/BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md`](BL30_REBUILD_VS_AUSBAU_GUARDRAILS_API_FIRST_V1.md) als verbindlicher BL-30-Parent-Baustein konsolidiert (normative Pflichtmarker `BL30_API_FIRST_NO_BREAKING_CHANGES`, `BL30_ENTITLEMENT_SCHEMA_ADDITIVE_ONLY`, `BL30_CHECKOUT_IDEMPOTENCY_REQUIRED`, `BL30_RUNTIME_FALLBACK_TO_STANDARD`, Merge-Policy für #465/#466) und via `tests/test_bl30_parent_rebuild_vs_ausbau_guardrails_docs.py` regressionsgesichert.
  - ✅ #502 abgeschlossen: Mobile-Geolocation-Contract v1 in [`docs/api/mobile-live-geolocation-contract-v1.md`](api/mobile-live-geolocation-contract-v1.md) ergänzt (additiver Request-/Response-Rahmen über `options.mobile_geolocation`/`result.status.mobile_geolocation`, deterministische Error-/Fallback-Codes, Follow-up-Pfade #503/#504), Contract-Referenz in [`docs/api/contract-v1.md`](api/contract-v1.md) nachgezogen und via `tests/test_bl30_mobile_live_geolocation_contract_docs.py` regressionsgesichert.
  - ✅ #503 abgeschlossen: Mobile State-/Interaction-Contract v1 in [`docs/gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md`](gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md) ergänzt (normatives Permission-/Locate-/Analyze-Zustandsmodell, Retry-/Timeout-/Offline-Regeln, UX-/A11y-Mindestkriterien), Cross-Links in [`docs/gui/GUI_MVP_STATE_FLOW.md`](gui/GUI_MVP_STATE_FLOW.md), [`docs/api/mobile-live-geolocation-contract-v1.md`](api/mobile-live-geolocation-contract-v1.md) und [`docs/api/contract-v1.md`](api/contract-v1.md) nachgezogen sowie via `tests/test_bl30_mobile_geolocation_state_interaction_docs.py` regressionsgesichert.
  - ✅ #504 abgeschlossen: Mobile Trace-/Privacy-Guardrails v1 in [`docs/testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md`](testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md) ergänzt (Mindestevent-Liste, Feldklassen-basierte Redaction-/Retention-Regeln, normiertes Trace-Evidence-Format), Logging-Schema in [`docs/LOGGING_SCHEMA_V1.md`](LOGGING_SCHEMA_V1.md) und API-Follow-up-Referenz in [`docs/api/mobile-live-geolocation-contract-v1.md`](api/mobile-live-geolocation-contract-v1.md) synchronisiert sowie via `tests/test_bl30_mobile_geolocation_trace_privacy_docs.py` regressionsgesichert.
  - ✅ #494 abgeschlossen: Karten-Workflow-Spec v1 in [`docs/gui/OSM_MAP_INTELLIGENCE_WORKFLOW_V1.md`](gui/OSM_MAP_INTELLIGENCE_WORKFLOW_V1.md) ergänzt (Map-Pick-Flow, additiver `/analyze`-Handshake, State-/Error-/Retry-Regeln), Doku-Regression via `tests/test_bl30_osm_map_workflow_docs.py` hinzugefügt und Parent-Sync in #110 fortgeschrieben.
  - ✅ #495 abgeschlossen: Datenquellen-/Lizenzmatrix v1 in [`docs/gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md`](gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md) ergänzt (Basemap, Gebäude-/Parzellennähe, Topografie, Straßentyp/Zufahrtsrelevanz inkl. Decision-Frame `GO/NEEDS_CLARIFICATION/BLOCKED`), Follow-up #498 für produktive OSM-Tile-/ODbL-Compliance angelegt und via `tests/test_bl30_osm_data_license_matrix_docs.py` regressionsgesichert.
  - ✅ #496 abgeschlossen: Response-Modell v1 in [`docs/api/map-point-construction-access-response-model-v1.md`](api/map-point-construction-access-response-model-v1.md) ergänzt (normatives Feldmodell, Pflichtmarker `explainability/confidence/source`, grouped-Contract-Mapping inkl. `result.data.modules.map_site_suitability`), Follow-up-Pfade für Runtime/Schema-Sync dokumentiert und via `tests/test_bl30_map_suitability_response_model_docs.py` regressionsgesichert.
  - ✅ #498 abgeschlossen: verbindlicher OSM-Tile-/ODbL-Compliance-Entscheid in [`docs/gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md`](gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md) ergänzt (prod-Tile-Strategie ohne Public-OSM-Endpunkt, Last-/Caching-Grenzen, Share-Alike-Trigger, Attribution in UI/API/Export), Referenz-Sync in [`docs/gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md`](gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md), [`docs/api/map-point-construction-access-response-model-v1.md`](api/map-point-construction-access-response-model-v1.md) und [`docs/DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md) nachgezogen; Regression via `tests/test_bl30_osm_tile_odbl_compliance_docs.py` ergänzt.
  - ✅ #479 abgeschlossen: Architektur-ADR für BL-30.4 in [`docs/gui/HTML5_UI_ARCHITECTURE_V1.md`](gui/HTML5_UI_ARCHITECTURE_V1.md) ergänzt (Modulgrenzen `src/ui|src/shared|src/api`, State-Ownership, Forward-Compatibility-Guardrails #6/#127), Doku-Regression via `tests/test_bl30_html5_ui_architecture_docs.py` hinzugefügt und Parent-Sync in #108 vorbereitet.
  - ✅ #480 abgeschlossen: Zustandsmodell + Interaktions-Contract v1 in [`docs/gui/HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md`](gui/HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md) ergänzt (State-Diagramm, Event-/Action-Contract, Debounce/Cancel-Regeln, Timeout-/Retry-Matrix, additive `/analyze`-Kompatibilität), Regression via `tests/test_bl30_ui_state_interaction_contract_docs.py` hinzugefügt und Parent-Sync in #108 fortgeschrieben.
  - ✅ #481 abgeschlossen: Performance-Budget + Browser-Caching-Strategie v1 in [`docs/gui/HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md`](gui/HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md) ergänzt (LCP/TTI/Input-Latency-/Request-Budgets, Datenklassen-Caching inkl. Invalidation/Revalidation, Telemetrie-Mindestfelder + Diagnoseablauf), Regression via `tests/test_bl30_ui_performance_budget_docs.py` hinzugefügt und Parent-Sync in #108 fortgeschrieben.
  - ✅ #482 abgeschlossen: Explainability-/Scoring-UX-Standards v1 in [`docs/gui/HTML5_UI_EXPLAINABILITY_SCORING_UX_STANDARDS_V1.md`](gui/HTML5_UI_EXPLAINABILITY_SCORING_UX_STANDARDS_V1.md) ergänzt (UX-Grundsätze, progressive Disclosure, Fehlerleitlinien, Accessibility-/Responsiveness-Mindestkriterien, UX-Abnahmecheckliste), Regression via `tests/test_bl30_ui_explainability_scoring_ux_docs.py` hinzugefügt und Parent-Sync in #108 finalisiert.
  - ✅ #468 abgeschlossen: neue Deep-Mode-Vertragsdoku [`docs/api/deep-mode-contract-v1.md`](api/deep-mode-contract-v1.md) erstellt, Contract-Referenz in [`docs/api/contract-v1.md`](api/contract-v1.md) ergänzt und per Regressionstest `tests/test_bl30_deep_mode_contract_docs.py` abgesichert.
  - ✅ #469 abgeschlossen: neues Orchestrierungs-/Guardrail-Design in [`docs/api/deep-mode-orchestration-guardrails-v1.md`](api/deep-mode-orchestration-guardrails-v1.md) dokumentiert (Sequenz, Budget-, Retry-/Abort-Regeln, Telemetrie-Mindeststandard, Schnittstellen zum Analyze-Flow), Contract-Referenzen in `docs/api/contract-v1.md` + `docs/api/deep-mode-contract-v1.md` ergänzt, Regressionstest `tests/test_bl30_deep_mode_orchestration_docs.py` hinzugefügt und Follow-up-Issues #472/#473 für Runtime-/Telemetry-Umsetzung angelegt.
  - ✅ #470 abgeschlossen: Hypothesenblatt + Entitlement-/Quota-Kopplung + Transparenzrahmen in [`docs/DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md`](DEEP_MODE_ADDON_QUOTA_HYPOTHESES_V1.md) dokumentiert, GTM-Decision-Input in [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](testing/GTM_VALIDATION_DECISION_LOG.md) als `GTM-IN-30.3-001` verankert und durch `tests/test_bl30_deep_mode_addon_quota_hypotheses_docs.py` regressionsgesichert.
  - ✅ #472 abgeschlossen: Runtime-Orchestrator in `src/api/web_service.py` umgesetzt (Eligibility-Gate inkl. `requested/allowed/quota/budget`, deterministische Statusprojektion nach `result.status.capabilities.deep_mode` + `result.status.entitlements.deep_mode`), Design-Doku in [`docs/api/deep-mode-orchestration-guardrails-v1.md`](api/deep-mode-orchestration-guardrails-v1.md) auf Implementierungsstand ergänzt und Fallback-Matrix per `tests/test_bl30_deep_mode_runtime_orchestrator.py` abgesichert.
  - ✅ #473 abgeschlossen: Deep-Mode-Telemetrie im Analyze-Flow ergänzt (`api.deep_mode.gate_evaluated|execution.start|execution.retry|execution.abort|execution.end` inkl. Pflichtfelder `deep_*`, `retry_count`, `duration_ms`), Logging-Schema in [`docs/LOGGING_SCHEMA_V1.md`](LOGGING_SCHEMA_V1.md) verankert, operatives Nachweis-Runbook [`docs/testing/DEEP_MODE_TRACE_EVIDENCE_RUNBOOK.md`](testing/DEEP_MODE_TRACE_EVIDENCE_RUNBOOK.md) + Beispielartefakt [`docs/testing/deep-mode-trace-evidence-sample.jsonl`](testing/deep-mode-trace-evidence-sample.jsonl) ergänzt und per `tests/test_bl30_deep_mode_telemetry_events.py` / `tests/test_bl30_deep_mode_telemetry_docs.py` regressionsgesichert.
- **Nächster Schritt:** keiner (BL-30 vollständig abgeschlossen).

### BL-31 — Zielbild Webinterface als 2-Container-Architektur (UI + API)
- **Priorität:** P2
- **Aufwand:** M
- **Abhängigkeiten:** BL-20.6 (GUI-MVP vorhanden), interne Ingress-/Security-Gates nicht verletzen (kein externer OpenClaw-Inbound)
- **Status:** ✅ Zielbild abgeschlossen (2026-02-28, Issue #326)
- **Nachweis:**
  - Architektur-Zielbild inkl. Risiken/Trade-offs in [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) (Abschnitt „BL-31: 2-Container-Architektur").
  - Deployment-Entscheide (Ingress/TLS, service-getrennte Deploy-Regeln) in [`docs/DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md).
  - Betriebsregeln für getrennte Rollouts/Rollbacks in [`docs/OPERATIONS.md`](OPERATIONS.md).
- **Work-Packages:**
  - [x] #327 — BL-31.1 Umsetzung 2-Container-Deployment (Parent-Umsetzung)
  - [x] #328 — BL-31.2 UI-Container-Artefakt + ECS-Task-Basis (abgeschlossen 2026-02-28)
  - [x] #329 — BL-31.3 Host-basiertes Routing + TLS (`app`/`api`) (abgeschlossen 2026-02-28)
  - [x] #330 — BL-31.4 Getrennte Deploy-/Rollback-Runbooks (abgeschlossen 2026-02-28)
  - [x] #331 — BL-31.5 Monitoring/Alerting für UI-Service (abgeschlossen 2026-02-28)
  - [x] #344 — BL-31.6 UI-Service dev-Rollout + E2E-Nachweis (abgeschlossen 2026-02-28)
    - [x] #345 — BL-31.6.a UI-ECR/Artefaktpfad + Task-Revision (abgeschlossen 2026-02-28)
    - [x] #346 — BL-31.6.b ECS UI-Service Rollout + Stabilisierung (abgeschlossen 2026-02-28)
    - [x] #347 — BL-31.6.c App/API/Monitoring Nachweislauf + Parent-Sync (abgeschlossen 2026-02-28)
- **Fortschritt (2026-03-01):**
  - ✅ 2026-03-02: #718 abgeschlossen (WP Async Notifications – in-app UX + tests) mit neuem UI-Deep-Link `/jobs/<job_id>` in `src/ui/service.py` (pollt Job+Notifications und verlinkt auf `/results/<result_id>`), erweitertem `/healthz`-Metadata (`job_permalink`) und Regression in `tests/test_ui_service.py`; Re-Validation via `python3 -m unittest -q tests.test_ui_service`.
  - 🟡 2026-03-01: #395 (BL-337 Parent) in atomare Work-Packages #396/#397/#398/#399 zerlegt (Katalog-Standardisierung, API-Execution, UI-Execution, konsolidierter Abschluss), weil ein Single-Slot-Durchlauf zu breit/riskant wäre.
  - ✅ 2026-03-01: #396 abgeschlossen (BL-337.wp1 Internet-E2E-Katalog + Matrix): neues Generator/Validator-Skript [`scripts/manage_bl337_internet_e2e_matrix.py`](../scripts/manage_bl337_internet_e2e_matrix.py) für reproduzierbare Expected/Actual-Matrizen (`artifacts/bl337/latest-internet-e2e-matrix.json`), Runbook [`docs/testing/bl337-internet-e2e-matrix.md`](testing/bl337-internet-e2e-matrix.md) und Guard-Tests `tests/test_manage_bl337_internet_e2e_matrix.py` + `tests/test_bl337_internet_e2e_matrix_docs.py`.
  - ✅ 2026-03-01: #397 abgeschlossen (BL-337.wp2 API-Frontdoor Execution): neuer ausführbarer Runner [`scripts/run_bl337_api_frontdoor_e2e.py`](../scripts/run_bl337_api_frontdoor_e2e.py) führt API-Expected-vs-Actual-Checks reproduzierbar aus, schreibt Evidence (`artifacts/bl337/20260228T231717Z-wp2-api-frontdoor-e2e.json`) und aktualisiert API-Matrixzeilen in `artifacts/bl337/latest-internet-e2e-matrix.json`; Runbook um WP2-Abschnitt erweitert und Regressionen via `tests/test_run_bl337_api_frontdoor_e2e.py` + `tests/test_bl337_internet_e2e_matrix_docs.py` abgesichert.
  - ✅ 2026-03-01: #398 abgeschlossen (BL-337.wp3 UI-Frontdoor Execution): neuer ausführbarer Runner [`scripts/run_bl337_ui_frontdoor_e2e.py`](../scripts/run_bl337_ui_frontdoor_e2e.py) prüft Homepage-Load, Kernnavigation/Form-Render, Client-Side-Validierungsfehler und UI/API-Fehlerkonsistenz reproduzierbar; Evidence unter `artifacts/bl337/20260228T232843Z-wp3-ui-frontdoor-e2e.json` (+ `-home.html`, `-api-probe.json`), Runbook um WP3-Abschnitt erweitert und Regressionen via `tests/test_run_bl337_ui_frontdoor_e2e.py` + `tests/test_bl337_internet_e2e_matrix_docs.py` abgesichert.
  - ✅ 2026-03-01: #399 abgeschlossen (BL-337.wp4 Konsolidierung): Parent #395 um konsolidierte Abschluss-Summary (Abdeckung/Pass-Rate/offene Fails) ergänzt, DoD-Checklist synchronisiert, Work-Package-Checklist finalisiert und Abschlussreferenzen auf PRs #400/#402/#403 inkl. Matrix-/Evidence-Pfade dokumentiert.
  - ✅ 2026-03-01: #395 (BL-337 Parent) abgeschlossen: Internet-E2E gegen API/UI-Frontdoors vollständig ausgeführt (`pass=8`, `fail=0`, `blocked=0`), keine offenen Abweichungs-Issues aus den WP2/WP3-Läufen.
  - ✅ 2026-03-01: #405 abgeschlossen (BL-338 non-basic Loading-Hänger): GUI-MVP beendet `loading` jetzt deterministisch auch bei ausbleibender Antwort (clientseitiger `AbortController`-Timeout + modeabhängiges `timeout_seconds` im Request), BL-337 API-Smoke-Matrix um `API.ANALYZE.NON_BASIC.FINAL_STATE` erweitert und Regressionen in `tests/test_web_service_gui_mvp.py`, `tests/test_run_bl337_api_frontdoor_e2e.py`, `tests/test_run_bl337_ui_frontdoor_e2e.py` abgesichert.
  - ✅ 2026-03-01: #406 abgeschlossen (BL-339 Karten-Placeholder): GUI-MVP rendert den Kartenbereich nun als echte interaktive OSM-Basemap (Tile-Render mit Pan/Zoom/Klick), inklusive deterministischem Degraded-State bei Tile-Fehlern (`coordinates.lat/lon`-Analyze weiter verfügbar), aktualisierter GUI-/BL337-Doku und gehärteten UI-Smokes in `tests/test_web_service_gui_mvp.py`, `tests/test_run_bl337_ui_frontdoor_e2e.py` sowie `scripts/run_bl337_ui_frontdoor_e2e.py`.
  - 🟡 2026-02-28: #362 (BL-334.x Source-Trennung WebUI/WebAPI) in atomare Work-Packages #364/#365/#366/#367/#368 zerlegt (Zielstruktur/Import-Policy, API-Move, UI-Move, Container-Kontexte, CI/Doku-Sync).
  - ✅ 2026-02-28: #364 abgeschlossen (BL-334.1 Zielstruktur + Import-Grenzen) mit erweitertem Boundary-Guard [`scripts/check_bl31_service_boundaries.py`](../scripts/check_bl31_service_boundaries.py) für Legacy- und Split-Layout (`src/api|ui|shared`), ergänzter Regression in `tests/test_check_bl31_service_boundaries.py` (inkl. Split-Layout-Cases) und Architektur-Sync in [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) (Sections 6.8/6.9).
  - ✅ 2026-02-28: #365 abgeschlossen (BL-334.2 API-Source-Migration) mit physischer Verlagerung der API-Module nach `src/api/` (`web_service`, `address_intel`, `personalized_scoring`, `suitability_light`), Legacy-Kompatibilitäts-Wrappern unter `src/` für stabile Entrypoints (`python -m src.web_service`) sowie Split-Layout-Namespaces `src/ui` und `src/shared` als vorbereitende Brücken für die nächsten Work-Packages. Regressionsnachweis: `./.venv-test/bin/python -m pytest -q tests/test_check_bl31_service_boundaries.py tests/test_web_service_port_resolution.py tests/test_web_service_grouped_response.py tests/test_web_service_cors.py tests/test_web_service_coordinate_input.py tests/test_web_e2e.py::TestWebServiceE2E::test_health_and_version tests/test_web_e2e.py::TestWebServiceE2E::test_analyze_happy_path tests/test_module_docstrings.py`.
  - ✅ 2026-02-28: #366 abgeschlossen (BL-334.3 UI-Source-Migration) mit physischer Verlagerung der UI-Module nach `src/ui/` (`service.py`, `gui_mvp.py`), Legacy-Kompatibilitäts-Wrappern `src/ui_service.py` und `src/gui_mvp.py` für stabile Entrypoints (`python -m src.ui_service`, `from src.gui_mvp import ...`) sowie Doku-Sync in `README.md`, `docs/ARCHITECTURE.md` und `docs/gui/GUI_MVP_STATE_FLOW.md`. Regressionsnachweis: `./.venv-test/bin/python scripts/check_bl31_service_boundaries.py --src-dir src` und `./.venv-test/bin/python -m pytest -q tests/test_check_bl31_service_boundaries.py tests/test_ui_service.py tests/test_web_service_gui_mvp.py tests/test_ui_container_artifacts.py tests/test_module_docstrings.py`.
  - ✅ 2026-02-28: #367 abgeschlossen (BL-334.4 Docker-Build-Kontexte): service-lokale Container-Kontexte via `Dockerfile.dockerignore`/`Dockerfile.ui.dockerignore` eingeführt, API-/UI-Dockerfiles auf service-lokale `COPY`-Pfade (`src/api|ui|shared`) umgestellt, GUI-MVP als neutrales Shared-Modul (`src/shared/gui_mvp.py`) kanonisiert und Deploy-/Architektur-Doku synchronisiert (`README.md`, `docs/DEPLOYMENT_AWS.md`, `docs/ARCHITECTURE.md`, `docs/gui/GUI_MVP_STATE_FLOW.md`). Regressionsnachweis: `./.venv-test/bin/python scripts/check_bl31_service_boundaries.py --src-dir src` sowie `./.venv-test/bin/python -m pytest -q tests/test_bl334_container_contexts.py tests/test_ui_container_artifacts.py tests/test_ui_service.py tests/test_web_service_gui_mvp.py tests/test_check_bl31_service_boundaries.py tests/test_user_docs.py`.
  - ✅ 2026-02-28: #368 abgeschlossen (BL-334.5 CI-/Doku-Sync): neuer service-getrennter Smoke-Runner [`scripts/check_bl334_split_smokes.sh`](../scripts/check_bl334_split_smokes.sh) für API-only (`src.api.web_service`) und UI-only (`src.ui.service`), Integration in `.github/workflows/contract-tests.yml` (manual-fallback CI-Pfad), Doku-Sync in `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT_AWS.md` und `docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md` inkl. Migrationshinweisen auf kanonische Entrypoints; Regression: `pytest -q tests/test_bl334_split_smokes_script.py tests/test_bl31_deploy_rollback_runbook_docs.py tests/test_bl31_smoke_evidence_matrix_docs.py tests/test_user_docs.py tests/test_markdown_links.py tests/test_ui_service.py tests/test_web_e2e.py::TestWebServiceE2E::test_health_and_version` + `./scripts/check_bl334_split_smokes.sh`.
  - 🟡 2026-02-28: #352 (BL-31.x Follow-up zur strikten UI/API-Entkopplung) in atomare Work-Packages #353/#354/#355/#356 zerlegt (Code-Grenzen, Deploy-Orchestrierung, Runbook, Smoke-/Evidence-Matrix).
  - ✅ 2026-02-28: #353 abgeschlossen (Service-Boundary-Guard) via PR #357 / Merge `8f7d138`: neues Guard-Skript `scripts/check_bl31_service_boundaries.py` mit expliziter API/UI/Shared-Policy, Doku-Update in `docs/ARCHITECTURE.md` (BL-31 Section 6.8) und Regressionstests in `tests/test_check_bl31_service_boundaries.py`.
  - ✅ 2026-02-28: #354 abgeschlossen (Deploy-Orchestrierung `api|ui|both`) via PR #359 / Merge `d2881ca`: neues Script `scripts/run_bl31_split_deploy.py` (default dry-run, optional `--execute`, service-lokale Guardrails gegen Cross-Service-TaskDef-Drift), Doku-Sync in `docs/OPERATIONS.md` und Regressionstests in `tests/test_run_bl31_split_deploy.py`.
  - ✅ 2026-02-28: #355 abgeschlossen (Runbook finaler Split-Stand) mit aktualisiertem primärem Deploy-Flow über `scripts/run_bl31_split_deploy.py` in `docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md`, ergänzten Deployment-Hinweisen in `docs/DEPLOYMENT_AWS.md` und nachgezogener Doku-Guard-Validierung (`tests/test_bl31_deploy_rollback_runbook_docs.py`).
  - ✅ 2026-02-28: #356 abgeschlossen (Smoke-/Evidence-Matrix) mit konsistenten Mindestfeldern (`mode`, `taskDefinitionBefore`, `taskDefinitionAfter`, `result`, `timestampUtc`) direkt im Split-Deploy-Artefakt (`scripts/run_bl31_split_deploy.py`), neuem Matrix-Validator `scripts/check_bl31_smoke_evidence_matrix.py`, ergänzter Nachweisdoku `docs/testing/bl31-smoke-evidence-matrix.md` sowie Regressionstests in `tests/test_check_bl31_smoke_evidence_matrix.py`, `tests/test_run_bl31_split_deploy.py` und `tests/test_bl31_smoke_evidence_matrix_docs.py`.
  - ✅ 2026-02-28: #374 abgeschlossen (Validator-Default-Glob gehärtet): `scripts/check_bl31_smoke_evidence_matrix.py` scannt ohne explizite Pfade nur kanonische Split-Deploy-Artefakte (`*-bl31-split-deploy-{api,ui,both}.json`) statt schemafremde `*-ui-smoke.json` mitzunehmen; Regression erweitert um Mixed-Artifact-Test (`tests/test_check_bl31_smoke_evidence_matrix.py`) und Doku-Sync in `docs/testing/bl31-smoke-evidence-matrix.md` sowie `docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md`.
  - ✅ 2026-02-28: #377 abgeschlossen (BL-335.wp1 Runtime-Guardrail): neues read-only Prüfscript `scripts/check_bl335_frontdoor_runtime.py` validiert UI-`api_base_url` gegen erwartete HTTPS-Frontdoor und prüft CORS-Preflight für mehrere UI-Origins; ergänzt durch Regression `tests/test_check_bl335_frontdoor_runtime.py` sowie Doku `docs/testing/bl335-frontdoor-runtime-guardrail.md` inkl. Verlinkung in Deployment-/Runbook-Doku.
  - ✅ 2026-02-28: #378 abgeschlossen (BL-335.wp2 Split-Deploy Smoke-Härtung): `scripts/run_bl31_split_deploy.py` erzwingt im Execute-Modus explizite Frontdoor-Smoke-URLs (`--smoke-api-base-url`, `--smoke-app-base-url`), persisted die effektive Smoke-Konfiguration im Evidence-JSON (`smokeConfig`) und propagiert die Werte deterministisch in den Strict-Smoke; Regression in `tests/test_run_bl31_split_deploy.py`, Doku-Sync in `docs/DEPLOYMENT_AWS.md`, `docs/OPERATIONS.md`, `docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md`, `docs/testing/bl31-smoke-evidence-matrix.md`.
  - ✅ 2026-02-28: #379 abgeschlossen (BL-335.wp3 Redeploy-Abnahme-Runbook): neues Abschluss-Runbook `docs/testing/bl335-frontdoor-redeploy-acceptance-runbook.md` mit reproduzierbaren E2E-Checks (HTTPS health, Runtime-Guardrail vor/nach Redeploy, API/UI Split-Deploy mit expliziten Frontdoor-Smoke-URLs) und Parent-Checklist für #376; Doku-Verlinkung in `docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md` und `docs/DEPLOYMENT_AWS.md`, Guard-Test ergänzt in `tests/test_bl335_frontdoor_redeploy_acceptance_runbook_docs.py`.
  - ✅ 2026-02-28: #386 abgeschlossen (BL-335.wp4 Runtime-Config-Fix): ECS-Taskdefs für API/UI auf stabile Frontdoor-Runtime umgestellt (`UI_API_BASE_URL=https://api.dev.georanking.ch`, `CORS_ALLOW_ORIGINS=https://www.dev.georanking.ch,https://www.dev.geo-ranking.ch`), Services ausgerollt und mit Guardrail verifiziert; Evidenz unter `artifacts/bl335/20260228T215042Z-wp4-runtime-config-fix.json`, `artifacts/bl335/20260228T215845Z-frontdoor-runtime-check-post-wp4.json`.
  - ✅ 2026-02-28: #376 abgeschlossen (BL-335 Parent): End-to-End-Abnahme nach Runtime-Fix erfolgreich (HTTPS-Health grün, API/UI Split-Deploy-Smokes grün, Runtime-Guardrail nach Redeploy grün); Evidenz unter `artifacts/bl31/20260228T215901Z-bl31-split-deploy-api-execute.json`, `artifacts/bl31/20260228T220157Z-bl31-split-deploy-ui-execute.json`, `artifacts/bl335/20260228T220452Z-frontdoor-runtime-post-redeploy.json`.
  - ✅ BL-31.2 umgesetzt: separates UI-Image (`Dockerfile.ui`) inkl. Build-Args/Runtime-ENV, eigenständiger UI-Entrypoint (kanonisch `src/ui/service.py`, kompatibel `src/ui_service.py`) und ECS-Task-Template (`infra/ecs/taskdef.swisstopo-dev-ui.json`) mit `/healthz`-Healthcheck.
  - ✅ 2026-02-28: #336 abgeschlossen (Testing-Catch-up BL-31 Routing/TLS-Smokepfade): reproduzierbarer Smoke-Runner [`scripts/run_bl31_routing_tls_smoke.sh`](../scripts/run_bl31_routing_tls_smoke.sh) + Runbook [`docs/testing/bl31-routing-tls-smoke-catchup.md`](testing/bl31-routing-tls-smoke-catchup.md) inkl. CORS-Baseline-Check (Warn-/Strict-Modus) und Regressionstest `tests/test_bl31_routing_tls_smoke_script.py`.
  - ✅ #329 abgeschlossen: CORS-Allowlist für `POST/OPTIONS /analyze` (`CORS_ALLOW_ORIGINS`) in `src/web_service.py` umgesetzt, Routing/TLS/CORS-Abnahmepfad in [`docs/DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md) dokumentiert und Failure-/Rollback-Hinweise in [`docs/OPERATIONS.md`](OPERATIONS.md) ergänzt.
  - ✅ #330 abgeschlossen (BL-31.4 Deploy-/Rollback-Runbooks): neues verbindliches Runbook [`docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md`](BL31_DEPLOY_ROLLBACK_RUNBOOK.md) mit API-only/UI-only/kombiniertem Deploy-Ablauf, service-lokalen Rollback-Kommandos, Strict-Smoke-Prozess (`scripts/run_bl31_routing_tls_smoke.sh`) und standardisiertem Evidenzformat für Issue-/PR-Kommentare; Verlinkung in [`docs/DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md) und [`docs/OPERATIONS.md`](OPERATIONS.md) ergänzt, Guard-Test `tests/test_bl31_deploy_rollback_runbook_docs.py` hinzugefügt.
  - ✅ #331 abgeschlossen: UI-Monitoring-Baseline-Scripts ergänzt ([`scripts/setup_bl31_ui_monitoring_baseline.sh`](../scripts/setup_bl31_ui_monitoring_baseline.sh), [`scripts/check_bl31_ui_monitoring_baseline.sh`](../scripts/check_bl31_ui_monitoring_baseline.sh)), generische Health-Probe-Skripte für UI/API parametrisiert und Runbook [`docs/testing/bl31-ui-monitoring-baseline-check.md`](testing/bl31-ui-monitoring-baseline-check.md) inkl. Regressionstest `tests/test_bl31_ui_monitoring_baseline_check_script.py` ergänzt.
  - ✅ #345 abgeschlossen (BL-31.6.a Artefaktpfad + Taskdef): neues Automationsscript [`scripts/setup_bl31_ui_artifact_path.sh`](../scripts/setup_bl31_ui_artifact_path.sh) für CodeBuild-basierten UI-Build/Push + Taskdef-Registrierung (inkl. AssumeRole-Fallback), Buildspec [`buildspec-openclaw.yml`](../buildspec-openclaw.yml), Nachweisdoku [`docs/testing/bl31-ui-artifact-path-taskdef-setup.md`](testing/bl31-ui-artifact-path-taskdef-setup.md) und Regressionstest `tests/test_bl31_ui_artifact_path_setup_script.py`; Evidenz unter `artifacts/bl31/20260228T075535Z-bl31-ui-artifact-path.json`.
  - ✅ #346 abgeschlossen (BL-31.6.b ECS UI-Rollout + Stabilisierung): UI-Taskdef-Template auf produktive ECS-Rollen korrigiert (`infra/ecs/taskdef.swisstopo-dev-ui.json`), neues Rollout-Skript [`scripts/setup_bl31_ui_service_rollout.sh`](../scripts/setup_bl31_ui_service_rollout.sh) ergänzt (services-stable + UI/API-Health + Evidenz), Deployment-/Ops-Doku aktualisiert ([`docs/DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md), [`docs/OPERATIONS.md`](OPERATIONS.md)) sowie Nachweisdoku [`docs/testing/bl31-ui-ecs-rollout.md`](testing/bl31-ui-ecs-rollout.md); Evidenz unter `artifacts/bl31/20260228T080756Z-bl31-ui-ecs-rollout.json`.
  - ✅ #347 abgeschlossen (BL-31.6.c App/API/Monitoring-Nachweis + Parent-Sync): neuer kombinierter Evidence-Runner [`scripts/run_bl31_app_api_monitoring_evidence.sh`](../scripts/run_bl31_app_api_monitoring_evidence.sh), begleitende Nachweisdoku [`docs/testing/bl31-app-api-monitoring-evidence.md`](testing/bl31-app-api-monitoring-evidence.md), Rollout-Skript-Fix für robuste Taskdef-Auflösung ohne `None`-Artefakt in AWS CLI-Textausgabe sowie Regressionstests (`tests/test_bl31_app_api_monitoring_evidence_script.py`, `tests/test_bl31_ui_service_rollout_script.py`); Evidenz unter `artifacts/bl31/20260228T083257Z-bl31-app-api-monitoring-evidence.json`.
  - ✅ 2026-03-01: #534 abgeschlossen (Deploy-Runbook Version/Trace-Verifikation): neuer Verifier `scripts/check_deploy_version_trace.py` prüft UI-`/healthz` gegen `${GITHUB_SHA::7}`, optional API-Health und (bei aktivem `TRACE_DEBUG_ENABLED`) den Request-ID-Flow nach `/debug/trace`; Workflow `deploy.yml` um den Post-Deploy-Step inkl. `$GITHUB_STEP_SUMMARY` + JSON-Evidenz (`artifacts/deploy/*-post-deploy-verify.json`) erweitert, Runbook/Checkliste unter `docs/testing/DEPLOY_VERSION_TRACE_DEBUG_RUNBOOK.md` und Doku-Sync in `docs/DEPLOYMENT_AWS.md` ergänzt.
- **Nächster Schritt (oldest-first, unblocked):** aktuell kein weiteres `backlog` + (`status:todo`/`status:in-progress`) unblocked Item offen; nächster Move ist Backlog-Triage (neues unblocked Leaf-Issue markieren oder Blocker auflösen).

### BL-32 — Repo-Doku-Bereinigung (Ist-Stand, konsistente Referenzen)
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-03-01, Parent #388)
- **Ziel:** Ist-Stand-Dokumente auf konsistente Entrypoints, Deploy-/Smoke-Realität und saubere README/BACKLOG-Referenzen bringen.
- **Work-Packages (Parent #388):**
  - [x] #389 — BL-32.1 Kanonische API/UI-Entrypoints in Ist-Stand-Dokus konsolidieren (abgeschlossen 2026-02-28)
  - [x] #390 — BL-32.2 Operative Kern-Dokus (Deploy/Ops/Architektur) auf Ist-Stand harmonisieren (abgeschlossen 2026-02-28)
  - [x] #391 — BL-32.3 README/BACKLOG-Status- und Referenzkonsistenz bereinigen (abgeschlossen 2026-03-01)
- **Fortschritt (2026-03-01):**
  - ✅ #389 via PR #392 (Merge `39681d4`): kanonische Entrypoints (`src.api.web_service`, `src.ui.service`) in User-/Testing-/Packaging-Dokus konsolidiert, Legacy nur als Kompatibilitätshinweis.
  - ✅ #390 via PR #393 (Merge `3cc6486`): `DEPLOYMENT_AWS.md` + `ARCHITECTURE.md` auf aktuellen Split-Deploy-Ist-Stand (`workflow_dispatch`-only, aktuelle Repo-Variablen/Smokes) harmonisiert.
  - ✅ #391 via PR #394 (Merge `0c6c8c7`): README/BACKLOG-Referenzen auf Ist-Stand bereinigt; Reopen-Fix am 2026-03-01 mit erfüllter DoD-Checklist nachgezogen.

### BL-340 — End-to-End Request/Response Logging über UI + API + Upstream
- **Priorität:** P1
- **Aufwand:** L
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-03-01, Parent #409)
- **Ziel:** Einheitliches, korrelierbares Logging-Schema inkl. Redaction über alle relevanten Flows.
- **Work-Packages (Parent #409):**
  - [x] #410 — BL-340.1 Logging-Kernschema v1 + Redaction-Policy + Shared Helper (abgeschlossen 2026-03-01)
  - [x] #411 — BL-340.2 API Ingress/Egress Logging mit korrelierten IDs (abgeschlossen 2026-03-01)
  - [x] #412 — BL-340.3 UI Interaktions- und UI->API Logging instrumentieren (abgeschlossen 2026-03-01)
  - [x] #413 — BL-340.4 Upstream-Provider Logging + Retry/Error Trace-Nachweise (abgeschlossen 2026-03-01)
- **Fortschritt (2026-03-01):**
  - ✅ #410 abgeschlossen: neues normatives Logging-Dokument [`docs/LOGGING_SCHEMA_V1.md`](LOGGING_SCHEMA_V1.md), Shared Helper [`src/shared/structured_logging.py`](../src/shared/structured_logging.py), erste API-Call-Sites (`service.startup`, `service.redirect_listener.enabled`, `api.health.response`) in [`src/api/web_service.py`](../src/api/web_service.py) sowie Regressionstests in `tests/test_structured_logging.py`.
  - ✅ #411 abgeschlossen: Request-Lifecycle-Instrumentierung für `GET/POST/OPTIONS` via `api.request.start`/`api.request.end` mit `status_code`, `duration_ms`, `error_code/error_class` in [`src/api/web_service.py`](../src/api/web_service.py), erweiterte Schema-Doku in [`docs/LOGGING_SCHEMA_V1.md`](LOGGING_SCHEMA_V1.md) und neue Integrationstests in `tests/test_web_service_request_logging.py` (inkl. `401`/`504` Fehlerpfade).
  - ✅ #412 abgeschlossen: GUI-MVP (`src/shared/gui_mvp.py`) emittiert jetzt strukturierte UI-Events für Input/Interaktion, State-Transitions und UI→API-Lifecycle (`ui.api.request.start/end` inkl. Fehler/Timeout-Klassen) und setzt `X-Request-Id` + `X-Session-Id` für direkte UI↔API-Korrelation; Doku-Sync in [`docs/LOGGING_SCHEMA_V1.md`](LOGGING_SCHEMA_V1.md) + [`docs/gui/GUI_MVP_STATE_FLOW.md`](gui/GUI_MVP_STATE_FLOW.md), Regressionserweiterung in `tests/test_web_service_gui_mvp.py`.
  - ✅ #413 abgeschlossen: Upstream-Lifecycle-Events (`api.upstream.request.start/end`, `api.upstream.response.summary`) für API-Koordinatenauflösung und Address-Intel-Providerpfade ergänzt (`src/api/web_service.py`, `src/api/address_intel.py`), Trace-Artefakte dokumentiert ([`docs/testing/BL-340_UPSTREAM_TRACE_EVIDENCE.md`](testing/BL-340_UPSTREAM_TRACE_EVIDENCE.md), `artifacts/bl340/*.jsonl`) und Regressionstests erweitert (`tests/test_address_intel_upstream_logging.py`, `tests/test_web_service_request_logging.py`).
  - ✅ #426 abgeschlossen: Schema-Contract-Feldkonstanten (`LOG_EVENT_SCHEMA_V1_REQUIRED_FIELDS`, `LOG_EVENT_SCHEMA_V1_RECOMMENDED_FIELDS`) + dedizierte Header-Redaction (`redact_headers`) im Shared Helper ergänzt; Regressionen via `tests/test_structured_logging.py` + `tests/test_web_service_request_logging.py` erneut verifiziert.
  - ✅ 2026-03-02: #753 abgeschlossen (Logging-Redaction – keine PII in Logs): Address-/Query-Keys (`query`, `street`, `house_number`, `postal_code`, `resolved_query`, `matched_address`) werden key-basiert vollständig maskiert – auch wenn Values verschachtelte Objekte/Listen sind; Regressionen in `tests/test_structured_logging.py` (PR #763).
  - ✅ Parent #409 abgeschlossen/geschlossen: Work-Package-Checklist + Akzeptanzkriterien synchronisiert.
- **Nächster Schritt:** keiner (BL-340 vollständig abgeschlossen).

### BL-421 — Workstream-Balance Catch-up (Crawler P0)
- **Priorität:** P0
- **Aufwand:** S
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-03-01, Parent #421)
- **Ziel:** Reproduzierbare Balance-Evidenz liefern und daraus konkrete Development-Catch-up-Tasks + Parent-Sync ableiten.
- **Work-Packages (Parent #421):**
  - [x] #422 — BL-421.wp1 Workstream-Balance Audit als Script + Test (abgeschlossen 2026-03-01, revalidiert 2026-03-01)
  - [x] #423 — BL-421.wp2 Development-Catch-up-Issues oldest-first freigeben (abgeschlossen 2026-03-01)
  - [x] #424 — BL-421.wp3 Parent-Tracking + BACKLOG-Sync für Workstream-Balance abschließen (abgeschlossen 2026-03-01)
  - [x] #426 — BL-340.1.wp1 Logging-Schema-Contract + Redaction-Utility atomar umsetzen (abgeschlossen 2026-03-01)
- **Fortschritt (2026-03-01):**
  - ✅ #422 abgeschlossen: `scripts/github_repo_crawler.py --print-workstream-balance` unterstützt jetzt optional persistente Artefakt-Ausgabe via `--output-file` (relative Pfade ab Repo-Root), inklusive neuer Regression `test_print_workstream_balance_report_json_writes_output_file` in `tests/test_github_repo_crawler.py` und nachgezogener Nutzungsdoku in `docs/WORKSTREAM_BALANCE_BASELINE.md` (DoD-Checklist im Issue am 2026-03-01 nachträglich synchronisiert/revalidiert).
  - ✅ #423 abgeschlossen: aktuelle Baseline per `python3 scripts/github_repo_crawler.py --print-workstream-balance --format markdown` verifiziert (Dev=11, Doku=14, Testing=14; Catch-up +1 Dev), oldest-first auf das älteste unblocked Development-Issue #410 angewendet und daraus das atomare Follow-up #426 (`BL-340.1.wp1`) mit klarer DoD/Abhängigkeit erstellt.
  - ✅ #424 abgeschlossen: Parent-Tracking #421 und BACKLOG-Status synchronisiert; Restarbeit explizit auf das offene Development-Follow-up #426 gelegt (Next Step für sichtbare Gap-Reduktion).
  - ✅ #426 abgeschlossen: Logging-Schema-v1-Feldkonstanten + Header-Redaction im Shared Helper umgesetzt (PR #431) und Ziel-Gap via erneuter Baseline auf `1` reduziert (`Dev=1`, `Doku=2`, `Testing=2`, Catch-up nicht nötig).
  - ✅ Parent #421 abgeschlossen/geschlossen: Next-Step-Checklist auf erledigt gesetzt und Balance-Ziel (`gap <= 2`) verifiziert.
  - ✅ #554 abgeschlossen (2026-03-01, Crawler-Reopen-Cleanup): Re-Baseline via `python3 scripts/github_repo_crawler.py --print-workstream-balance --format json` ergibt `Dev=0`, `Doku=0`, `Testing=0`, `Gap=0`, `Catch-up nötig: nein`; damit kein zusätzlicher Development-Delta-Task erforderlich.
- **Nächster Schritt:** keiner (P0 Catch-up-Ziel erreicht).

### BL-422 — request_id Trace-Debugging in der WebUI
- **Priorität:** P2
- **Aufwand:** M
- **Abhängigkeiten:** BL-340 (strukturierte Request-/Upstream-Logs vorhanden)
- **Status:** ✅ abgeschlossen (2026-03-01, Parent #430)
- **Ziel:** Für eine konkrete `request_id` den API/UI/Upstream-Verlauf als nachvollziehbare Timeline abrufbar machen.
- **Work-Packages (Parent #430):**
  - [x] #433 — BL-422.1 Dev-only Trace-API (Timeline + Redaction) (abgeschlossen 2026-03-01)
  - [x] #434 — BL-422.2 Trace-Debug-View Route/Loader in GUI (abgeschlossen 2026-03-01)
  - [x] #435 — BL-422.3 Result-Panel UX (Trace-Link + Copy) (abgeschlossen 2026-03-01)
  - [x] #436 — BL-422.4 E2E-Smoke + Doku für Trace-Debugging (abgeschlossen 2026-03-01)
- **Fortschritt (2026-03-01):**
  - ✅ #433 abgeschlossen: neues Modul `src/api/debug_trace.py` für request_id-basierte JSONL-Timeline-Projektion (Start/Upstream/End), Guardrails für Request-ID/Window/Limit und redacted Detail-Ausgabe.
  - ✅ `GET /debug/trace` (dev-only) in `src/api/web_service.py` ergänzt, inklusive ENV-Gates (`TRACE_DEBUG_ENABLED`, `TRACE_DEBUG_LOG_PATH`) sowie Empty-/Unavailable-States.
  - ✅ Doku `docs/testing/TRACE_DEBUG_API.md` erstellt und Logging-Schema in `docs/LOGGING_SCHEMA_V1.md` verlinkt.
  - ✅ Tests: `tests/test_debug_trace.py`, `tests/test_web_service_debug_trace_api.py`.
  - ✅ #434 abgeschlossen: GUI-MVP um dediziertes Trace-Debug-Panel erweitert (`request_id` + Deep-Link `/gui?view=trace&request_id=<id>`), Timeline-Loader/Renderer mit robusten Defaults für Teil-/Fehldaten sowie klare `loading/success/empty/unknown/error`-Zustände umgesetzt (`src/shared/gui_mvp.py`, `src/ui/service.py`, `docs/gui/GUI_MVP_STATE_FLOW.md`).
  - ✅ Regressionen für Route/State-Flow + UI-Service-Rewrite ergänzt (`tests/test_web_service_gui_mvp.py`, `tests/test_ui_service.py`).
  - ✅ #435 abgeschlossen: Result-Panel zeigt `request_id` jetzt als aktive Debug-Einstiegsfläche mit klickbarem `Trace ansehen`-Link (öffnet/lädt Trace-View mit identischer ID) und `Copy ID`-Action inkl. `aria-live`-Feedback + Fallback-Copy-Strategie (`src/shared/gui_mvp.py`, `docs/gui/GUI_MVP_STATE_FLOW.md`). Reopen durch Crawler-Audit wurde am 2026-03-01 per Checklist-Sync im Issue bereinigt.
  - ✅ #436 abgeschlossen: reproduzierbarer Smoke-Test für Analyze→Trace-Lookup ergänzt (`tests/test_trace_debug_smoke.py`) und operative Nutzung/Limits/Security in `docs/testing/TRACE_DEBUG_SMOKE_FLOW.md` dokumentiert (inkl. Verlinkung aus `docs/testing/TRACE_DEBUG_API.md`). Reopen durch Crawler-Audit wurde am 2026-03-01 per Checklist-Sync im Issue bereinigt.
  - ✅ #430 Parent-Sync abgeschlossen: Akzeptanzkriterien/DoD im Parent-Issue nach Child-Abschluss vollständig auf erfüllt gesetzt; Crawler-Reopen dadurch final bereinigt (2026-03-01).
- **Nächster Schritt:** keiner (BL-422 vollständig abgeschlossen).

### BL-341 — Maßnahmen aus WORKING_MODE_FRICTION_ANALYSIS umsetzen (Verkaufsreife)
- **Priorität:** P3
- **Aufwand:** L
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-03-01, Parent #418)
- **Ziel:** Reibungspunkte aus `docs/testing/WORKING_MODE_FRICTION_ANALYSIS.md` in kleinen, risikoarmen Paketen abbauen.
- **Work-Packages (Parent #418):**
  - [x] #444 — BL-341.wp1 Pflicht-PR-Gates als required checks (abgeschlossen 2026-03-01)
  - [x] #445 — BL-341.wp2 Kritische Quality-Gates fail-closed (abgeschlossen 2026-03-01)
  - [x] #446 — BL-341.wp3 Staging-lite Promote-/Abort-/Rollback-Gate (abgeschlossen 2026-03-01)
  - [x] #447 — BL-341.wp4 Backlog-/Issue-Statussync automatisieren (abgeschlossen 2026-03-01)
  - [x] #448 — BL-341.wp5 GTM-Validierungssprint operationalisieren (abgeschlossen 2026-03-01)
- **Fortschritt (2026-03-01):**
  - ✅ Epic #418 in atomare Child-Issues zerlegt (2x P0, 3x P1) inkl. Parent-Checklist und Begründung.
  - ✅ #444 abgeschlossen: Fast-Gates `contract-smoke` + `docs-link-guard` laufen wieder automatisch auf PR (`pull_request`) und bleiben manuell triggerbar (`workflow_dispatch`).
  - ✅ Required-Check-Zielzustand + Admin-Verifikation in `docs/OPERATIONS.md` synchronisiert.
  - ✅ Regressionstest für Workflow-/Doku-Sync ergänzt (`tests/test_pr_fast_gates_config.py`).
  - ✅ #445 abgeschlossen: Docs-Quality-Gate läuft jetzt fail-closed (`scripts/check_docs_quality_gate.sh` bricht bei venv-Fehler mit Exit 1 ab), inklusive Script-Regressionen und Doku-Sync (`tests/test_check_docs_quality_gate_script.py`, `docs/OPERATIONS.md`, `docs/automation/openclaw-job-mapping.md`).
  - ✅ #446 abgeschlossen: Staging-lite Promote-Gate mit digest-basierter Entscheidungslogik + Smoke-Gate + Abort-/Rollback-Hinweisen als reproduzierbarer Runner eingeführt (`scripts/run_staging_lite_promote_gate.py`) inkl. Artefaktpfaden (`artifacts/staging-lite/*`), Runbook (`docs/testing/STAGING_LITE_PROMOTE_GATE.md`) und Regressionen (`tests/test_staging_lite_promote_gate.py`).
  - ✅ #448 abgeschlossen: operatives GTM-Sprint-Template + Rollen-/Outputpflichten dokumentiert (`docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md`), Decision-Log für BL-30-Priorisierung mit Seed-Ableitung eingeführt (`docs/testing/GTM_VALIDATION_DECISION_LOG.md`), bestehende GTM-Dokus auf den neuen Entscheidungsfluss verlinkt (`docs/PACKAGING_PRICING_HYPOTHESES.md`, `docs/GO_TO_MARKET_MVP.md`) und Guard-Test ergänzt (`tests/test_gtm_validation_sprint_docs.py`).
- **Nächster Schritt:** keiner (BL-341 vollständig abgeschlossen).

### BL-342 — Minimum-Compliance-Set (Governance-Rollout)
- **Priorität:** P1
- **Aufwand:** L
- **Abhängigkeiten:** BL-341.wp5 (#448) abgeschlossen
- **Status:** ✅ abgeschlossen (2026-03-01) — alle Work-Packages + Folgeschritte erledigt, Go-Live GOLIVE-BL342-2026-03-01-001: GO, Monitoring aktiv (PR #617), Schulung abgeschlossen (SCHULUNG-BL342-2026-03-01-001)
- **Ziel:** Governance-/Compliance-Vorgaben in verbindliche Policies, technische Controls und Abnahmetests überführen.
- **Work-Packages:**
  - [x] #515 — Policy-Standard finalisieren (Version, Begründung, Wirksam-ab, Impact-Pflicht) (abgeschlossen 2026-03-01)
  - [x] #516 — Korrektur-Richtlinie freigeben (nur neue Version + Pflichtfeld Grund) (abgeschlossen 2026-03-01)
  - [x] #517 — Hold-Governance definieren (wer darf Hold setzen/aufheben) (abgeschlossen 2026-03-01)
  - [x] #518 — Kontrollplan für Export- und Löschprozesse definieren (abgeschlossen 2026-03-01)
  - [x] #519 — Datenmodell erweitern: Policy-Versionierung + Metadatenfelder (über #538/#539/#540 abgeschlossen 2026-03-01)
    - [x] #538 — BL-342.wp5.wp1: Policy-Metadatenmodell v1 im Code einführen (abgeschlossen 2026-03-01)
    - [x] #539 — BL-342.wp5.wp2: Policy-Metadaten-Contract + Beispielartefakte dokumentieren (abgeschlossen 2026-03-01)
    - [x] #540 — BL-342.wp5.wp3: Backlog-/Rollout-Sync für Policy-Metadatenmodell abschließen (abgeschlossen 2026-03-01)
  - [x] #524 — Externen Direktzugriff technisch unterbinden (abgeschlossen 2026-03-01)
  - [x] #525 — Export-Logging implementieren (wer/wann/Kanal) (abgeschlossen 2026-03-01)
  - [x] #526 — Backup/Restore-Guideline dokumentieren (abgeschlossen 2026-03-01)
  - [x] #527 — Abnahmetests für Minimum-Compliance-Set erstellen (abgeschlossen 2026-03-01)
- **Folgeschritte:**
  - [x] #520 — Korrektur-Workflow implementieren (abgeschlossen 2026-03-01)
  - [x] #521 — Pflichtfeld Korrekturgrund erzwingen (abgeschlossen 2026-03-01)
  - [x] #522 — Lösch-Scheduler mit Vorankündigung implementieren (abgeschlossen 2026-03-01)
  - [x] #523 — Hold-Flag pro Dokument implementieren (abgeschlossen 2026-03-01)
  - [x] #528 — Go-Live-Testlauf durchführen (✅ abgeschlossen 2026-03-01, ACC-MCS-2026-03-01-001: 31/31 Muss-Tests bestanden)
  - [x] #529 — Pre-Go-Live-Readiness-Review durchführen (✅ abgeschlossen 2026-03-01, READINESS-BL342-2026-03-01-001)
  - [x] #530 — Go-Live-Checkliste und Entscheidungsmeeting durchführen (✅ abgeschlossen 2026-03-01, GOLIVE-BL342-2026-03-01-001: GO)
  - [x] #531 — Monitoring aktivieren (Löschjobs/Hold-Bestand/Fehlerquote) (✅ abgeschlossen 2026-03-01, PR #617)
  - [x] #532 — Schulung für relevante Rollen durchführen (✅ abgeschlossen 2026-03-01, SCHULUNG-BL342-2026-03-01-001)
- **Fortschritt (2026-03-01):**
  - ✅ #515 abgeschlossen: verbindliche Policy-Vorlage in [`docs/compliance/POLICY_STANDARD_V1.md`](compliance/POLICY_STANDARD_V1.md) eingeführt (Pflichtfelder `version`, `begruendung`, `wirksam_ab`, `impact_summary` + Freigabe-Workflow v1 und Copy/Paste-Referenztemplate).
  - ✅ #516 abgeschlossen: Korrektur-Richtlinie in [`docs/compliance/KORREKTUR_RICHTLINIE_V1.md`](compliance/KORREKTUR_RICHTLINIE_V1.md) veröffentlicht (Original bleibt unverändert, Korrekturen nur als neue Version, Pflichtfeld `korrekturgrund`, inkl. Freigabe-/Kommunikationskriterien).
  - ✅ #517 abgeschlossen: Hold-Governance in [`docs/compliance/HOLD_GOVERNANCE_V1.md`](compliance/HOLD_GOVERNANCE_V1.md) definiert (Rollen-/Berechtigungsmatrix, Vier-Augen-Freigaben, Entscheidungswege für Setzen/Aufheben, Pflicht-Nachweise inkl. `review_due_at`).
  - ✅ #518 abgeschlossen: Kontrollplan für Export-/Löschkontrollen in [`docs/compliance/EXPORT_DELETE_CONTROL_PLAN_V1.md`](compliance/EXPORT_DELETE_CONTROL_PLAN_V1.md) eingeführt (verbindliche Kontrollfrequenzen, kombinierte Stichprobenregeln inkl. `sampling_seed`, standardisiertes Nachweispaket unter `reports/compliance/controls/<YYYY>/<MM>/<control_run_id>/`).
  - ✅ #524 abgeschlossen: explizite Runtime-Sperre für externe Direktlogin-Routen in `src/api/web_service.py` ergänzt (`403` + `external_direct_login_disabled`, Audit-Event `api.auth.direct_login.blocked`), Compliance-Doku [`docs/compliance/EXTERNAL_DIRECT_ACCESS_CONTROL_V1.md`](compliance/EXTERNAL_DIRECT_ACCESS_CONTROL_V1.md) eingeführt und per E2E-/Doku-Tests (`tests/test_web_e2e.py`, `tests/test_compliance_external_direct_access_control_docs.py`) regressionsgesichert.
  - ✅ #525 abgeschlossen: Export-Logging-Standard v1 in [`docs/compliance/EXPORT_LOGGING_STANDARD_V1.md`](compliance/EXPORT_LOGGING_STANDARD_V1.md) dokumentiert; Runtime-Helper `src/compliance/export_logging.py` eingeführt und Batch-Exporte in `src/api/address_intel.py` (`--out-jsonl`, `--out-csv`, `--out-error-csv`) mit Pflichtfeldern `actor`/`exported_at_utc`/`channel` instrumentiert; Regressionen via `tests/test_compliance_export_logging.py`, `tests/test_address_intel_export_logging.py`, `tests/test_compliance_export_logging_docs.py` ergänzt.
  - ✅ #538 abgeschlossen: Runtime-Policy-Metadatenmodell v1 ergänzt (`src/compliance/policy_metadata.py`) inkl. Validierungs-/Serialisierungslogik und Regressionstest `tests/test_compliance_policy_metadata_model.py`; Parent #519 für risikoarme Iterationen in #538/#539/#540 atomisiert.
  - ✅ #539 abgeschlossen: technischer Contract für Policy-Metadaten unter [`docs/compliance/POLICY_METADATA_CONTRACT_V1.md`](compliance/POLICY_METADATA_CONTRACT_V1.md) dokumentiert, reproduzierbare Beispielartefakte unter `docs/compliance/examples/policy-metadata.v1.*.json` ergänzt und über neuen Regressionstest `tests/test_compliance_policy_metadata_contract_docs.py` inkl. Runtime-Validierung abgesichert.
  - ✅ #540 abgeschlossen: Backlog-/Rollout-Sync für das Policy-Metadatenmodell vervollständigt (Parent #519 nun vollständig), Betriebs-/Nutzungshinweise in `docs/compliance/POLICY_METADATA_CONTRACT_V1.md` ergänzt und MCS-AT-010 auf automatisierten Nachweis via `tests/test_compliance_policy_metadata_rollout_sync_docs.py` umgestellt.
  - ✅ #526 abgeschlossen: Backup/Restore-Guideline v1 unter [`docs/compliance/BACKUP_RESTORE_GUIDELINE_V1.md`](compliance/BACKUP_RESTORE_GUIDELINE_V1.md) eingeführt (verbindliche RPO/RTO-Ziele, Backup-Policy, Restore-Workflow, quartalsweiser Restore-Drill, Nachweisformat `reports/compliance/backup-restore/<YYYY>/<MM>/<restore_run_id>/`) und per Doku-Regressionstest `tests/test_compliance_backup_restore_guideline_docs.py` abgesichert.
  - ✅ #527 abgeschlossen: Abnahmetestkatalog v1 unter [`docs/compliance/ACCEPTANCE_TEST_CATALOG_V1.md`](compliance/ACCEPTANCE_TEST_CATALOG_V1.md) erstellt (Musskriterien-Matrix MCS-AT-001..010 inkl. Sign-off-/Evidenzschema) und über Doku-Regressionstest `tests/test_compliance_acceptance_test_catalog_docs.py` abgesichert.
  - ✅ #523 abgeschlossen (2026-03-01): Hold-Flag pro Dokument implementiert (`src/compliance/hold_store.py`) — `HoldRecord` + `HoldStore` mit Vier-Augen-Pflicht, Rollen-Authority-Guard (Compliance Lead/Legal Counsel/Security Lead), \`review_due_at\` max 30 Tage, \`deletion_guard()\` blockiert Löschung verlässlich; Integration mit \`DeletionScheduler\` bewiesen (29 Tests in \`tests/test_compliance_hold_store.py\`, alle passed).
  - ✅ #522 abgeschlossen (2026-03-01): Lösch-Scheduler mit Vorankündigungsmechanismus (`src/compliance/deletion_scheduler.py`) — `DeletionRecord` + `DeletionScheduler` mit State-Machine `pending→notified→executed|canceled`, konfigurierbarem `notice_period_days`, `on_notify`/`on_execute`-Callbacks, Hold-Stub für #523; E2E-Test + 22 Unit-Tests in `tests/test_compliance_deletion_scheduler.py` (alle passed).
  - ✅ #521 abgeschlossen (2026-03-01): Pflichtfeld-Enforcement für korrekturgrund auf API-Ebene (`src/api/compliance_corrections.py`) — HTTP 422 mit `korrekturgrund_required` bei leerem/fehlendem/Placeholder-Feld, Placeholder-Guard (TODO/TBD/N/A/-), Mindestlänge 10 Zeichen, no-side-effect bei Validation-Fehler; Route `POST /compliance/corrections/<document_id>` in `web_service.py` eingehängt; 20 API-Enforcement-Tests in `tests/test_compliance_correction_api_enforcement.py`.
  - ✅ #520 abgeschlossen (2026-03-01): Korrektur-Workflow implementiert (`src/compliance/correction_workflow.py`) — `CorrectionMetadataV1` mit allen 6 Pflichtfeldern (version, supersedes_version, korrekturgrund, wirksam_ab, approved_by_role, evidence_ref), Placeholder-/Leerfeld-Guard, `VersionedDocument` mit append-only History (Original nie überschreibbar), `CorrectionStore` mit Duplikat-/Overwrite-Guard; 26 Regressionstests in `tests/test_compliance_correction_workflow.py` (alle passed).

### BL-21 — Tech Debt Reset vor Go-Live (Legacy-Cut)
- **Priorität:** P1
- **Aufwand:** L
- **Abhängigkeiten:** keine
- **Status:** ✅ abgeschlossen (2026-02-27, Issue #309)
- **Ziel:** Legacy-Übergangslogik konsequent entfernen und den v1-Zielcontract als einzigen aktiven Pfad absichern.
- **Work-Packages (Issue #309):**
  - [x] #310 — Runtime-Legacy-Path `options.include_labels` entfernt (2026-02-27)
  - [x] #311 — Contract/Schema/Doku auf code-first-only konsolidieren (2026-02-27)
  - [x] #312 — Test-Suite auf Legacy-Flag-Removal gehärtet (2026-02-27)
- **Fortschritt (2026-02-27):**
  - ✅ #310 abgeschlossen: `src/web_service.py` lehnt `options.include_labels` nun deterministisch mit `400 bad_request` ab und nutzt im grouped Response ausschließlich code-first-Projektion.
  - ✅ #311 abgeschlossen: Contract-/Stability-/User-Doku und Request-Schema auf code-first-only synchronisiert (`include_labels` entfernt, Sunset dokumentiert, Dictionary-Migrationspfad klargestellt).
  - ✅ #312 abgeschlossen: Legacy-Flag-Regressionen in `tests/test_web_e2e.py` erweitert (inkl. Mischfall mit gültigen Optionen), Contract-Validator-Test für `include_labels` ergänzt und negativer Golden-Case hinzugefügt (`tests/data/api_contract_v1/invalid/request.options.include-labels.legacy-flag.json`).
  - ✅ Relevante Checks grün: `pytest -q tests/test_web_e2e.py tests/test_web_service_grouped_response.py tests/test_api_contract_v1.py` (`73 passed`, `45 subtests passed`).

### BL-XX — Webservice-Testabdeckung über alle Resultpfade (OK/NOK)
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-18
- **Status:** ✅ abgeschlossen (2026-02-27, Issue #248)
- **Akzeptanzkriterien:**
  - Für alle relevanten Webservice-Funktionen ist die Resultpfad-Abdeckung (OK/NOK/Edge) inventarisiert.
  - Fehlende Testcases sind implementiert und reproduzierbar ausführbar.
  - Vollständiger Testlauf inkl. Outcome-Dokumentation ist im Repo nachweisbar.
- **Work-Packages (Issue #248):**
  - [x] #249 — Parent in Standardformat + DoD/Scope (abgeschlossen 2026-02-27)
  - [x] #250 — Test-Coverage-Inventar (abgeschlossen 2026-02-27)
  - [x] #251 — Fehlende Testcases implementieren (abgeschlossen 2026-02-27)
  - [x] #252 — Volltest + Outcome-Dokumentation (abgeschlossen 2026-02-27)

### BL-YY — Dokumentations-Programm (intern + User + Service-Output)
- **Priorität:** P1
- **Aufwand:** M
- **Abhängigkeiten:** BL-20
- **Status:** ✅ abgeschlossen (2026-02-27, Issue #261)
- **Ziel:** Dokumentationsabdeckung strukturiert erfassen, Lücken priorisieren, fehlende Inhalte ergänzen und einen reproduzierbaren Service-Testlauf dokumentieren.
- **Work-Packages (Issue #261):**
  - [x] #263 — Parent-Issue in Standardformat + atomare Zerlegung (abgeschlossen 2026-02-27)
  - [x] #264 — Dokumentationsabdeckung inventarisieren (Code + intern + User) (abgeschlossen 2026-02-27)
  - [x] #265 — Dokumentationslücken priorisieren + Umsetzungsplan (abgeschlossen 2026-02-27)
  - [x] #266 — Fehlende Dokumentation ergänzen (in atomare Child-Issues #272/#273/#274 zerlegt; abgeschlossen 2026-02-27)
    - [x] #272 — Address-Intel-Flow-Deep-Dive dokumentieren (abgeschlossen 2026-02-27)
    - [x] #273 — Mapping-/Transform-Regeln user-nah ergänzen (abgeschlossen 2026-02-27)
    - [x] #274 — Modul-Docstrings für Kernmodule nachziehen (abgeschlossen 2026-02-27)
  - [x] #267 — Webservice-Test Espenmoosstrasse 18, 9008 St. Gallen dokumentieren (abgeschlossen 2026-02-27)
- **Fortschritt:**
  - ✅ 2026-02-27: #263 abgeschlossen (Issue #261 auf Standardformat umgestellt, Parent-Work-Package-Checklist ergänzt, Child-Issues #264/#265/#266/#267 erstellt).
  - ✅ 2026-02-27: #264 abgeschlossen (Inventar der Doku-Abdeckung erstellt: [`docs/DOCUMENTATION_COVERAGE_INVENTORY.md`](DOCUMENTATION_COVERAGE_INVENTORY.md), inkl. Mapping Code ↔ interne/User-Doku und offensichtlicher Gaps als Input für #265).
  - ✅ 2026-02-27: #267 abgeschlossen (reproduzierter Analyze-Testlauf für `Espenmoosstrasse 18, 9008 St. Gallen` inkl. Header-/Response-Artefakten unter `reports/manual/` und Testprotokoll in [`docs/testing/WEB_SERVICE_TEST_ESPENMOOSSTRASSE_18_9008_ST_GALLEN.md`](testing/WEB_SERVICE_TEST_ESPENMOOSSTRASSE_18_9008_ST_GALLEN.md)).
  - ✅ 2026-02-27: #265 abgeschlossen (Priorisierung + Umsetzungsreihenfolge der Doku-Gaps in [`docs/DOCUMENTATION_GAP_PRIORITIZATION_PLAN.md`](DOCUMENTATION_GAP_PRIORITIZATION_PLAN.md), inkl. verbindlichem Plan für #266).
  - ✅ 2026-02-27: #266 in Child-Issues #272/#273/#274 atomisiert; #272 abgeschlossen mit neuer Deep-Dive-Doku [`docs/api/address-intel-flow-deep-dive.md`](api/address-intel-flow-deep-dive.md) und Contract-Querverweis in [`docs/api/contract-v1.md`](api/contract-v1.md).
  - ✅ 2026-02-27: #273 abgeschlossen (kompakte user-nahe Mapping-/Transform-Interpretation in [`docs/user/api-usage.md`](user/api-usage.md) ergänzt, inkl. Verweis auf [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](DATA_SOURCE_FIELD_MAPPING_CH.md), Docs-Quality-Gate grün).
  - ✅ 2026-02-27: #274 abgeschlossen (prägnante Modul-Docstrings in `src/personalized_scoring.py`, `src/suitability_light.py`, `src/legacy_consumer_fingerprint.py` ergänzt; bestehende Docstrings in `src/web_service.py`/`src/address_intel.py` bestätigt; relevante Tests grün).
  - ✅ 2026-02-27: #266 abgeschlossen (alle Child-Work-Packages #272/#273/#274 erledigt).

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
4. **BL-17** (Deploy via OIDC, OpenClaw Runtime via Key/Secret) ✅
5. **BL-18** (Service weiterentwickeln + Webservice E2E-Tests) ✅
6. **BL-19** (Userdokumentation) ✅
7. **BL-20** (Produktvision API+GUI umsetzen) ✅
