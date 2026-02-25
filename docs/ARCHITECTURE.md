# Architektur — geo-ranking-ch

> **Status:** Aktueller Ist-Stand (MVP) mit aktivem ECS/Fargate-Deploy über GitHub Actions (`dev`).

---

## 1) Systemüberblick

`geo-ranking-ch` ist aktuell als containerisierter Python-Webservice umgesetzt und wird nach Build/Test automatisch in die AWS-`dev`-Umgebung ausgerollt.

```text
GitHub (main / manual)
        │
        ▼
GitHub Actions (Build, Test, Deploy)
        │
        ├─ docker build + push → Amazon ECR
        │
        └─ ECS Task Definition (neue Revision mit neuem Image)
                      │
                      ▼
                ECS Service (Fargate, dev)
                      │
                      ▼
            HTTP API (`src/web_service.py`)
            /health   /version   /analyze
```

---

## 2) Laufzeit-Architektur (Ist)

### 2.1 Applikation

- **Runtime:** Python 3.12 (Container)
- **Entrypoint:** `python -m src.web_service`
- **Port:** `8080`
- **Container-Build:** `Dockerfile` im Repo-Root vorhanden
- **HTTP-Service (MVP):** `src/web_service.py`

**Implementierte Endpoints:**

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/health` | Health/Liveness-Check |
| `GET` | `/version` | Service-/Build-Metadaten (`APP_VERSION`, `GIT_SHA`) |
| `POST` | `/analyze` | Analyse-Endpoint (adressbezogene Auswertung) |

### 2.2 AWS-Zielumgebung (`dev`)

| Komponente | Wert |
|---|---|
| Region | `eu-central-1` |
| ECS Launch Type | Fargate |
| ECS Cluster | `swisstopo-dev` |
| ECS Service | `swisstopo-dev-api` |
| ECR Repository | `swisstopo-dev-api` |

> Hinweis: AWS-Ressourcen werden intern unter dem Namen `swisstopo` geführt; das ist bewusst und konsistent mit dem bestehenden Setup.

---

## 3) CI/CD-Architektur (GitHub Actions)

Workflow-Datei: **`.github/workflows/deploy.yml`**

### Trigger

- `workflow_dispatch` (manueller Start)
- `push` auf Branch `main`

### Pipeline-Phasen

1. **Build & Test**
   - Checkout
   - Python-Setup
   - `pip install -r requirements-dev.txt`
   - `pytest tests/ -v --tb=short`

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
| `AWS_ACCESS_KEY_ID` | AWS-Zugriffsschlüssel für Deploy-User |
| `AWS_SECRET_ACCESS_KEY` | AWS-Secret für Deploy-User |
| `AWS_ACCOUNT_ID` | AWS Account-ID (für ECR Image URI) |

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

## 6) Offene Punkte / Nächste Architektur-Schritte

Die offenen Architektur-Themen werden zentral im [`docs/BACKLOG.md`](BACKLOG.md) gepflegt (insb. **BL-01**, **BL-05**, **BL-06**, **BL-07**, **BL-08**, **BL-09**), um doppelte TODO-Listen zu vermeiden.
