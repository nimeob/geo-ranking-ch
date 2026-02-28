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
- `push` auf Branch `main`

### Pipeline-Phasen

1. **Build & Test**
   - Checkout
   - Python-Setup
   - `pip install -r requirements-dev.txt`
   - `pytest tests/ -v --tb=short`

1b. **Split-Smoke-Fallback (API/UI getrennt)**
   - `./scripts/check_bl334_split_smokes.sh`
   - API-only Startpfad: `python -m src.api.web_service`
   - UI-only Startpfad: `python -m src.ui.service`

2. **Deploy to ECS (dev)**
   - Validierung erforderlicher Repo-Variablen
   - Validierung, dass `Dockerfile` existiert
   - AWS Credentials konfigurieren
   - ECR Login
   - Docker Image bauen und pushen (`<sha7>`-Tag)
   - Aktuelle ECS Task Definition laden
   - **Neue Task-Definition-Revision registrieren** (Container-Image wird ersetzt)
   - **ECS Service update** auf neue Task-Definition
   - Warten auf Stabilität via `aws ecs wait services-stable`

3. **Optionaler Smoke-Test**
   - URL aus `SERVICE_HEALTH_URL`
   - HTTP-Check gegen Health-Endpoint
   - **Wenn `SERVICE_HEALTH_URL` leer/nicht gesetzt:** Smoke-Test wird mit Notice **übersprungen** (kein Hard-Fail)

---

## 4) Konfiguration in GitHub (Secrets & Variables)

### Required Secrets

| Name | Zweck |
|---|---|
| _(keine erforderlich)_ | AWS-Authentifizierung erfolgt via GitHub OIDC Role Assume |

### OIDC-AWS-Bindung

| Name | Zweck |
|---|---|
| `role-to-assume` | `arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role` (in `aws-actions/configure-aws-credentials@v4`) |

### Required Variables

| Name | Zweck |
|---|---|
| `ECR_REPOSITORY` | Ziel-ECR-Repository (z. B. `swisstopo-dev-api`) |
| `ECS_CLUSTER` | Ziel-ECS-Cluster (z. B. `swisstopo-dev`) |
| `ECS_SERVICE` | Ziel-ECS-Service (z. B. `swisstopo-dev-api`) |
| `ECS_CONTAINER_NAME` | Containername in der Task Definition |

### Optionale Variable

| Name | Zweck |
|---|---|
| `SERVICE_HEALTH_URL` | URL für Smoke-Test nach Deploy; wenn nicht gesetzt → Schritt wird übersprungen |

---

## 5) Architektur-Entscheidungen (Stand heute)

- **Deploy-Ziel:** ECS/Fargate in `dev` ist aktiv.
- **Build/Release-Pfad:** GitHub Actions ist der führende Deploy-Pfad.
- **Artefakt:** Docker Image in ECR, Deployment über neue ECS Task-Definition-Revision.
- **Service-Form:** Lightweight MVP-Webservice mit klaren Basisendpoints (`/health`, `/version`, `/analyze`).
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

## 7) Offene Punkte / Nächste Architektur-Schritte

Die offenen Architektur-Themen werden zentral im [`docs/BACKLOG.md`](BACKLOG.md) gepflegt (inkl. BL-31 Folgepakete), um doppelte Nebenlisten zu vermeiden.
