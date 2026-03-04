# Architektur — geo-ranking-ch

> **Status:** Aktueller Ist-Stand (MVP) mit aktivem ECS/Fargate-Deploy über GitHub Actions (`dev`).

---

## 1) Systemüberblick

`geo-ranking-ch` ist als service-getrennte 2-Container-Architektur umgesetzt (API + UI) und wird in der AWS-`dev`-Umgebung betrieben.

```text
GitHub (main / manual)
        │
        ▼
GitHub Actions / OpenClaw Jobs
        │
        ├─ API-Container (Dockerfile) → ECR swisstopo-dev-api
        ├─ UI-Container  (Dockerfile.ui) → ECR swisstopo-dev-ui
        └─ CI-Smokes (API-only + UI-only)
                │
                ▼
        ECS Services (Fargate, dev)
          ├─ swisstopo-dev-api  -> src/api/web_service.py
          └─ swisstopo-dev-ui   -> src/ui/service.py
```

---

## 2) Laufzeit-Architektur (Ist)

### 2.1 Applikation

- **Runtime:** Python 3.12 (Container)
- **Kanonischer API-Entrypoint:** `python -m src.api.web_service`
- **Kanonischer UI-Entrypoint:** `python -m src.ui.service`
- **Port:** `8080` (service-lokal)
- **Container-Builds:** `Dockerfile` (API) + `Dockerfile.ui` (UI)
- **Legacy-Kompatibilität:** Wrapper `src.web_service` und `src.ui_service` bleiben für bestehende Integrationen verfügbar

**Implementierte Endpoints (service-getrennt):**

| Service | Methode | Pfad | Zweck |
|---|---|---|---|
| API | `GET` | `/health` | Health/Liveness-Check |
| API | `GET` | `/version` | Service-/Build-Metadaten (`APP_VERSION`, `GIT_SHA`) |
| API | `POST` | `/analyze` | Analyse-Endpoint (adressbezogene Auswertung) |
| UI | `GET` | `/healthz` | UI-Liveness-Check |
| UI | `GET` | `/` / `/gui` | GUI-MVP-Shell |

### 2.2 AWS-Zielumgebung (`dev`)

| Komponente | Wert |
|---|---|
| Region | `eu-central-1` |
| ECS Launch Type | Fargate |
| ECS Cluster | `swisstopo-dev` |
| ECS Service (API) | `swisstopo-dev-api` |
| ECS Service (UI) | `swisstopo-dev-ui` |
| ECR Repository (API) | `swisstopo-dev-api` |
| ECR Repository (UI) | `swisstopo-dev-ui` |

> Hinweis: AWS-Ressourcen werden intern unter dem Namen `swisstopo` geführt; das ist bewusst und konsistent mit dem bestehenden Setup.

---

## 3) CI/CD-Architektur (GitHub Actions)

Workflow-Dateien (relevant für Split-Stand):
- **`.github/workflows/deploy.yml`** (ECS Deploy-Pfad)
- **`.github/workflows/contract-tests.yml`** (CI-Fallback inkl. API/UI-Split-Smokes)

### Trigger

- `workflow_dispatch` (manueller Start)

### Pipeline-Phasen (`deploy.yml`, Ist-Stand)

1. **Build & Test**
   - Checkout
   - Python-Setup
   - `pip install -r requirements-dev.txt`
   - `pytest tests/ -v --tb=short`

2. **Build & Push (API + UI)**
   - Validierung erforderlicher Repo-Variablen
   - Validierung, dass `Dockerfile` **und** `Dockerfile.ui` existieren
   - AWS Credentials via OIDC
   - ECR Login
   - API- und UI-Image bauen/pushen (`<sha7>`-Tag)

3. **Deploy API, danach UI (service-getrennt)**
   - Aktuelle TaskDefs für API/UI lesen
   - neue API-/UI-TaskDef-Revisionen registrieren
   - API-Service updaten + `services-stable`
   - API-Smokes (`/health`, optional `/analyze`)
   - UI-Service updaten + `services-stable`
   - UI-Smoke (`/healthz`)

4. **Optionaler Strict Split-Smoke**
   - Wenn `SERVICE_API_BASE_URL` + `SERVICE_APP_BASE_URL` gesetzt sind:
     - `./scripts/run_bl31_routing_tls_smoke.sh` mit `BL31_STRICT_CORS=1`
   - sonst: sauberer Skip mit Notice

---

## 4) Konfiguration in GitHub (Secrets & Variables)

### Secrets

| Name | Zweck |
|---|---|
| `SERVICE_API_AUTH_TOKEN` | Optional: Bearer-Token für den API-Analyze-Smoke |
| _(keine AWS-Credentials erforderlich)_ | AWS-Authentifizierung erfolgt via GitHub OIDC Role Assume |

### OIDC-AWS-Bindung

| Name | Zweck |
|---|---|
| `role-to-assume` | `arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role` (in `aws-actions/configure-aws-credentials@v4`) |

### Required Variables

| Name | Zweck |
|---|---|
| `ECS_CLUSTER` | Ziel-ECS-Cluster (z. B. `swisstopo-dev`) |
| `ECS_API_SERVICE` | Ziel-ECS-Service API (z. B. `swisstopo-dev-api`) |
| `ECS_UI_SERVICE` | Ziel-ECS-Service UI (z. B. `swisstopo-dev-ui`) |
| `ECS_API_CONTAINER_NAME` | API-Containername in der API-TaskDef |
| `ECS_UI_CONTAINER_NAME` | UI-Containername in der UI-TaskDef |
| `ECR_API_REPOSITORY` | API-ECR-Repository |
| `ECR_UI_REPOSITORY` | UI-ECR-Repository |
| `SERVICE_API_BASE_URL` | API-Base-URL für Pflicht-Smokes |
| `SERVICE_APP_BASE_URL` | UI-Base-URL für Pflicht-Smokes |

### Optionale Variable

| Name | Zweck |
|---|---|
| `SERVICE_HEALTH_URL` | Optionales API-Health-Override-Ziel (`/health`) |

---

## 5) Architektur-Entscheidungen (Stand heute)

- **Deploy-Ziel:** ECS/Fargate in `dev` ist aktiv.
- **Build/Release-Pfad:** GitHub Actions ist der führende Deploy-Pfad.
- **Artefakte:** Getrennte Docker-Images in ECR (API + UI), Deployment über neue ECS-TaskDef-Revisionen.
- **Service-Form:** Service-getrennte Laufzeit (API: `/health` `/version` `/analyze`, UI: `/healthz` + GUI-Entry).
- **IaC-Fundament (dev):** Terraform-Startpaket unter `infra/terraform/` für ECS/ECR/CloudWatch/S3 mit Import-first-Ansatz (`manage_*` standardmässig `false`).
- **Netzwerk/Ingress-Zielbild:** Dokumentiert in `docs/NETWORK_INGRESS_DECISIONS.md` (ALB-direkt als Ziel, API Gateway aktuell nicht erforderlich, Route53-Pflichten für `staging`/`prod`).
- **Datenhaltung + API-Sicherheit:** Entscheidungen dokumentiert in `docs/DATA_AND_API_SECURITY.md` (stateless in `dev`, DynamoDB-first bei Persistenzbedarf, AuthN/Rate-Limit/Secret-Standards für `/analyze`).
- **Umgebungs-Promotion (`dev`→`staging`→`prod`):** Zielbild, Gates und Rollback-Prozess dokumentiert in `docs/ENV_PROMOTION_STRATEGY.md`.

---

## 6) Zielbild BL-31: 2-Container-Architektur (UI + API)

> **Status:** Zielbild festgelegt (2026-02-28), Umsetzung über Folge-Issues.

### 6.1 Laufzeit-Topologie (Soll)

| Baustein | Zielzustand |
|---|---|
| ECS Cluster | `swisstopo-dev` (bestehend, gemeinsam genutzt) |
| API Service | `swisstopo-dev-api` (bestehender Service, separat deploybar) |
| UI Service | `swisstopo-dev-ui` (neu, eigener Task/Service) |
| ECR Repositories | `swisstopo-dev-api` (bestehend), `swisstopo-dev-ui` (neu) |
| Scaling | API und UI mit eigener DesiredCount-/CPU-/Memory-Strategie |
| Healthchecks | API: `/health`, UI: `/healthz` (leichtgewichtiger HTTP-Check) |

### 6.2 Ingress/Routing/TLS (Soll)

- Primärpfad: **Host-basiertes Routing über einen gemeinsamen ALB**
  - `api.<domain>` → API Target Group
  - `app.<domain>` → UI Target Group
- TLS-Termination am ALB mit ACM-Zertifikat (SAN/Wildcard für `api.*` + `app.*`).
- HTTP→HTTPS Redirect als Standardregel.
- Fallback (nur falls ALB kurzfristig nicht verfügbar): temporär getrennte Endpunkte, aber kein langfristiger Zielzustand.

### 6.3 API↔UI-Kommunikation

- UI ruft API über öffentliches `api.<domain>` mit versioniertem `/api/v1`-Pfad auf.
- CORS-Allowlist strikt auf UI-Origin(s), keine pauschale `*`-Freigabe.
- Optionaler BFF/Proxy-Pfad bleibt als späterer Optimierungshebel offen, ist aber **nicht** Teil von BL-31-Baseline.

### 6.4 AuthN/AuthZ/Entitlements (BL-30-ready)

- Eintrittspunkt für künftige Entitlements liegt API-zentriert (Token-/Plan-Prüfung serverseitig).
- UI enthält keine abrechnungsrelevante Autorisierungslogik; UI steuert nur UX.
- Header-/Token-Konventionen bleiben mit bestehender API-Doku kompatibel (`docs/user/api-usage.md`).

### 6.5 Deploy-/Rollback-Strategie getrennt für UI/API

- Separate Build-/Deploy-Pipelines pro Service (UI und API unabhängig ausrollbar).
- Default-Reihenfolge bei kombinierten Changes: **API zuerst**, dann UI.
- Rollback service-lokal (nur betroffener Service auf letzte stabile Task-Revision).
- Smoke-Gates pro Service (API-Health separat, UI-Erreichbarkeit separat).

### 6.6 Monitoring/Health getrennt

- API-Alarmierung bleibt aktiv (RunningTaskCount, 5xx, HealthProbe).
- UI erhält eigene Basis-Metriken: RunningTaskCount, HTTP 5xx (falls ALB-Logs/Metrikpfad aktiv), Reachability-Check.
- Alert-Routing bleibt zentral über bestehendes SNS→Telegram-Setup.

### 6.7 Risiken & Trade-offs

| Thema | Vorteil | Risiko/Kosten | Entscheidung |
|---|---|---|---|
| 2 Services statt 1 | Unabhängige Deployments, klarere Ownership | Mehr Ops-Aufwand (zweite TaskDef/Service) | akzeptiert |
| Gemeinsamer ALB | Einheitliches TLS/Routing, weniger DNS-/Ops-Overhead | Gemeinsamer Ingress als potenzieller Bottleneck | akzeptiert mit Monitoring |
| API-zentrierte Entitlements | Sicherheit und Konsistenz | UI-spezifische UX braucht zusätzliche API-Fehlerbehandlung | akzeptiert |
| Service-lokaler Rollback | Geringerer Blast Radius | Versionsdrift UI↔API möglich | mitigiert über Smoke/Kompatibilitätschecks |

### 6.8 Service-Boundary-Guard (BL-31.x.wp1, erweitert für BL-334)

Für die laufende Entkopplung gilt ein expliziter Boundary-Guard in [`scripts/check_bl31_service_boundaries.py`](../scripts/check_bl31_service_boundaries.py).

Aktueller Stand (2026-02-28, nach BL-334.4):
- **API-Quellbereich (kanonisch):** `src/api/*`
  - `web_service.py`, `address_intel.py`, `personalized_scoring.py`, `suitability_light.py`
- **UI-Quellbereich (kanonisch):** `src/ui/*`
  - `service.py`
- **Shared-Bereich (kanonisch):** `src/shared/*`
  - `gui_mvp.py` (von API + UI genutzt)
  - plus bestehende neutrale Module `geo_utils`, `gwr_codes`, `mapping_transform_rules`
- **Legacy-Importpfade (Kompatibilität):**
  - API: `src/web_service.py`, `src/address_intel.py`, `src/personalized_scoring.py`, `src/suitability_light.py` als Wrapper auf `src/api/*`
  - UI: `src/ui_service.py`, `src/gui_mvp.py` als Wrapper auf `src/ui.service` bzw. `src/shared.gui_mvp`

Guard-Regeln (Legacy + Split):
- API darf UI nicht importieren.
- UI darf API nicht importieren.
- Shared bleibt neutral (keine Imports von API- oder UI-Modulen).

Aufruf (lokal/CI):

```bash
python3 scripts/check_bl31_service_boundaries.py --src-dir src
```

### 6.9 BL-334 Zielstruktur für Source-Trennung (Rollout-Stand)

Zielstruktur bleibt unverändert und ist mit den Work-Packages #365–#368 vollständig umgesetzt:

```text
src/
  api/        # API-Laufzeit, HTTP-Entrypoints, Domain-Aggregation
  ui/         # UI-Laufzeit, View/Interaction-Logik
  shared/     # neutrale, service-übergreifende Hilfsmodule
```

Verbindliche Import-Richtungen:
- `api -> shared` ✅ erlaubt
- `ui -> shared` ✅ erlaubt
- `shared -> api/ui` ❌ verboten
- `api <-> ui` ❌ verboten

Migrationshinweis:
- BL-334.2 hat den API-Code physisch nach `src/api/` verschoben und Legacy-Wrapper für stabile Entrypoints ergänzt.
- BL-334.3 hat den UI-Code physisch nach `src/ui/` verschoben und Legacy-Wrapper für stabile Entrypoints ergänzt.
- BL-334.4 hat die GUI-MVP als neutrales Shared-Modul (`src/shared/gui_mvp.py`) kanonisiert und service-lokale Containerkontexte via `Dockerfile*.dockerignore` eingeführt.
- BL-334.5 hat die CI-/Smoke-Pfade auf kanonische Entrypoints synchronisiert (`scripts/check_bl334_split_smokes.sh`, API: `src.api.web_service`, UI: `src.ui.service`) und die Kern-Dokumente auf den Split-Stand aktualisiert.

## 7) API/UI Boundary Contract (v1)

> **Boundary-Version:** `api-ui-boundary/v1`  
> **Gültig ab:** 2026-03-04  
> **Änderungsregel:** Jede Boundary-Änderung muss in diesem Abschnitt dokumentiert und im PR-Template explizit geprüft werden.

### 7.1 Ziel und Nicht-Ziel

- **Ziel:** klare Ownership zwischen API- und UI-Service, damit Deployments, Tests und Fehlerbilder pro Schicht eindeutig bleiben.
- **Nicht-Ziel:** bestehende Legacy-Kompatibilität sofort entfernen; Legacy bleibt nur als Migrationspfad erlaubt.

### 7.2 Verbindliche Ownership-Regeln

1. **API (`src/api/*`)**
   - liefert datenorientierte, maschinenlesbare HTTP-Schnittstellen (JSON/Status-Endpunkte).
   - enthält **keine neue front-facing View-/Seitenlogik**.
   - darf keine UI-Module importieren.

2. **UI (`src/ui/*`)**
   - enthält front-facing Flows, HTML/GUI-Darstellung und UX-orientierte Interaktion.
   - darf keine API-Module importieren.

3. **Shared (`src/shared/*`)**
   - enthält nur neutrale Hilfslogik ohne API/UI-Ownership.
   - darf keine Imports aus `src/api/*` oder `src/ui/*` enthalten.

### 7.3 Route- und Modulkonventionen (v1)

| Ownership | Kanonischer Modulpfad | Route-Konvention |
|---|---|---|
| API | `src/api/*` | Daten- und Service-Endpunkte (z. B. `/api/v1/*`, `/analyze*`, `/health`, `/version`) |
| UI | `src/ui/*` | Front-Facing-Routen und UX-Flows (z. B. `/`, `/gui`, `/history`, `/results/*`, `/jobs/*`, `/auth/*`) |
| Shared | `src/shared/*` | Keine eigenen HTTP-Routen; nur neutrale Wiederverwendung |

Konsequenz für neue Arbeit:
- neue HTTP-Funktionalität muss **vor Implementierung** einem Owner (`api` oder `ui`) zugeordnet werden.
- Cross-Layer-Logik wird über klar definierte Datenverträge und nicht über direkte Layer-Imports verbunden.

### 7.4 Enforcement (CI + Review)

- Automatischer Import-Gate bleibt `scripts/check_bl31_service_boundaries.py` (lokal + CI).
- PRs müssen den Boundary-Check im Template aktiv beantworten (siehe `.github/pull_request_template.md`).
- Ausnahmen sind nur als expliziter Follow-up-Migrationspfad zulässig (Issue-Referenz + Sunset-Plan).

## 8) Offene Punkte / Nächste Architektur-Schritte

Die offenen Architektur-Themen werden zentral im [`docs/BACKLOG.md`](BACKLOG.md) gepflegt (inkl. BL-31 Folgepakete), um doppelte Nebenlisten zu vermeiden.
