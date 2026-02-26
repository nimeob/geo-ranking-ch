# geo-ranking-ch

> Geographisches Ranking-System für Schweizer Geodaten.

[![License](https://img.shields.io/badge/license-propriet%C3%A4r-lightgrey.svg)]()
[![Status](https://img.shields.io/badge/status-in%20development-yellow.svg)]()
[![CI/CD](https://img.shields.io/badge/CI%2FCD-ECS%20dev%20(main%20%2B%20manual)-orange.svg)](.github/workflows/deploy.yml)

---

## Überblick

`geo-ranking-ch` ist ein Projekt zur Analyse und zum Ranking von geographischen Einheiten (Gemeinden, Kantone, Regionen) in der Schweiz, basierend auf konfigurierbaren Kriterien und Datensätzen.

> **Hinweis:** Das Projekt befindet sich in einem frühen Entwicklungsstadium. Kernfunktionalität und Infrastruktur werden aktiv aufgebaut.

> **AWS-Naming:** AWS-Ressourcen werden intern unter dem Namen **`swisstopo`** geführt (z. B. ECS Cluster `swisstopo-dev`, S3 `swisstopo-dev-*`). Das ist so gewollt und konsistent — der Repo-Name `geo-ranking-ch` und das interne AWS-Naming `swisstopo` koexistieren. Eine Umbenennung der AWS-Ressourcen ist nicht vorgesehen.

> **Umgebungen:** Aktuell existiert ausschließlich eine **`dev`-Umgebung**. `staging` und `prod` sind noch nicht aufgebaut.

## Schnellstart

### Voraussetzungen

- Python **3.12** (verbindliche Dev-/CI-Baseline; lokal idealerweise via `python3.12`)
- AWS CLI ≥ 2.x (für Deployment-Operationen)
- Zugriff auf AWS Account `523234426229` (Region: `eu-central-1`)

### Lokale Entwicklung

```bash
# Repo klonen
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

# Virtuelle Umgebung mit Python 3.12 erstellen
python3.12 -m venv .venv
source .venv/bin/activate

# Dev-Abhängigkeiten installieren (pytest + pre-commit)
pip install -r requirements-dev.txt

# Optional: Git-Hooks für Format/Lint aktivieren
pre-commit install

# Checks ausführen
pytest tests/ -v
pre-commit run --all-files

# Minimalen Webservice starten (für ECS vorbereitet)
python -m src.web_service
# Healthcheck: http://localhost:8080/health
```

### Docker (wie in ECS)

```bash
docker build -t geo-ranking-ch:dev .
docker run --rm -p 8080:8080 geo-ranking-ch:dev
# Healthcheck
curl http://localhost:8080/health
```

### Webservice-Endpoints (MVP)

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/health` | Liveness/Healthcheck |
| `GET` | `/version` | Build/Commit-Metadaten |
| `POST` | `/analyze` | Adressanalyse (`{"query":"...","intelligence_mode":"basic|extended|risk","timeout_seconds":15}`) |

**Auth (optional):** Wenn `API_AUTH_TOKEN` gesetzt ist, erfordert `POST /analyze` den Header `Authorization: Bearer <token>`.

**Request-Korrelation:** Für `POST /analyze` wird `X-Request-Id` (alternativ `X-Correlation-Id`) in die Antwort gespiegelt (`X-Request-Id` Header + JSON-Feld `request_id`). Ohne Header erzeugt der Service automatisch eine Request-ID.

**Timeout-Input:** `timeout_seconds` muss eine **endliche Zahl > 0** sein (z. B. kein `nan`/`inf`), sonst antwortet die API mit `400 bad_request`.

### E2E-Tests (Webservice)

```bash
# lokal (immer; inkl. /analyze E2E + Smoke-/Stability-Script-Tests)
# + dev (optional via DEV_BASE_URL)
./scripts/run_webservice_e2e.sh

# dedizierter Remote-Smoke-Test für BL-18.1 (/analyze)
# validiert: HTTP 200, ok=true, result vorhanden, Request-ID-Echo (Header+JSON)
# DEV_BASE_URL muss http(s) sein (auch mit grossgeschriebenem Schema wie HTTP://); führende/trailing Whitespaces sowie /health-/analyze-Suffixe (case-insensitive) werden automatisch normalisiert
# DEV_BASE_URL darf keine Query-/Fragment-Komponenten enthalten (z. B. ?foo=bar oder #frag)
# SMOKE_TIMEOUT_SECONDS/CURL_MAX_TIME müssen endliche Zahlen >0 sein; CURL_RETRY_COUNT/CURL_RETRY_DELAY Ganzzahlen >=0
DEV_BASE_URL="https://<endpoint>" ./scripts/run_remote_api_smoketest.sh

# kurzer Stabilitätslauf (mehrere Remote-Smokes, mit NDJSON-Report)
# optional fail-fast: STABILITY_STOP_ON_FIRST_FAIL=1 (nur 0|1 erlaubt)
DEV_BASE_URL="https://<endpoint>" \
DEV_API_AUTH_TOKEN="<token>" \
./scripts/run_remote_api_stability_check.sh
```

### Kernmodule (src/)

| Modul | Beschreibung |
|---|---|
| `src/address_intel.py` | Adress-Intelligence: Geocoding, GWR-Lookup, Gebäuderegister, City-Ranking |
| `src/gwr_codes.py` | GWR-Code-Tabellen (Gebäudestatus, Heizung, Energie) |
| `src/geo_utils.py` | Geodaten-Utilities: Elevation, Koordinaten-Umrechnung, Haversine |

Alle Module sind **reine Python-Standardbibliothek** — kein externer API-Key nötig.
Optionales Kartenrendering (PNG) benötigt `pycairo`.

#### CLI-Schnellstart

```bash
# Adress-Report
python3 src/address_intel.py "Bahnhofstrasse 1, 8001 Zürich"

# City-Ranking (indikativ, OSM + GeoAdmin)
python3 src/address_intel.py --area-mode city-ranking --city "St. Gallen"

# Geodaten-Utilities
python3 src/geo_utils.py geocode "Hauptbahnhof Zürich"
python3 src/geo_utils.py elevation 47.3769 8.5417
```

### Deployment

Siehe [`docs/DEPLOYMENT_AWS.md`](docs/DEPLOYMENT_AWS.md) für das vollständige Deploy-Runbook.

---

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Systemarchitektur und Komponentenübersicht |
| [docs/DEPLOYMENT_AWS.md](docs/DEPLOYMENT_AWS.md) | AWS-Deployment: Ist-Stand, Runbook, Rollback |
| [docs/NETWORK_INGRESS_DECISIONS.md](docs/NETWORK_INGRESS_DECISIONS.md) | Beschlossenes Netzwerk-/Ingress-Zielbild (BL-05) |
| [docs/DATA_AND_API_SECURITY.md](docs/DATA_AND_API_SECURITY.md) | Datenhaltungsentscheidung + API-Sicherheitskonzept (BL-06/BL-07) |
| [docs/ENV_PROMOTION_STRATEGY.md](docs/ENV_PROMOTION_STRATEGY.md) | Zielbild für staging/prod + Promotion-Gates (BL-09) |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Arbeitsmodus, PR-Regeln, Release-Checkliste |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Zentraler, priorisierter Umsetzungs-Backlog |
| [docs/AWS_INVENTORY.md](docs/AWS_INVENTORY.md) | Vollständiges AWS-Ressourcen-Inventar mit ARNs, Konfig, IaC-Status und Rebuild-Hinweisen (BL-11) |
| [docs/LEGACY_IAM_USER_READINESS.md](docs/LEGACY_IAM_USER_READINESS.md) | Read-only Decommission-Readiness inkl. Go/No-Go für `swisstopo-api-deploy` (BL-15) |
| [docs/LEGACY_CONSUMER_INVENTORY.md](docs/LEGACY_CONSUMER_INVENTORY.md) | Offene Legacy-Consumer-Matrix inkl. Migrationsstatus/Next Actions (BL-15) |
| [docs/AUTONOMOUS_AGENT_MODE.md](docs/AUTONOMOUS_AGENT_MODE.md) | Verbindlicher Arbeitsmodus für Nipa (Subagents + GitHub App Auth) |
| [docs/BL-18_SERVICE_E2E.md](docs/BL-18_SERVICE_E2E.md) | Ist-Analyse + E2E-Runbook für BL-18 |
| [CHANGELOG.md](CHANGELOG.md) | Versions-History |

---

## Projektstruktur

```
geo-ranking-ch/
├── src/                    # Quellcode (Python, stdlib only)
│   ├── address_intel.py    # Adress-Intelligence + City-Ranking
│   ├── gwr_codes.py        # GWR-Code-Tabellen
│   ├── geo_utils.py        # Geodaten-Utilities (Elevation, Geocoding, …)
│   └── web_service.py      # HTTP-API (MVP für ECS)
├── tests/                  # Unit-Tests
│   └── test_core.py
├── scripts/                # Deployment- und Utility-Skripte
├── docs/                   # Projektdokumentation
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT_AWS.md
│   ├── NETWORK_INGRESS_DECISIONS.md
│   ├── DATA_AND_API_SECURITY.md
│   ├── ENV_PROMOTION_STRATEGY.md
│   ├── AWS_INVENTORY.md
│   ├── LEGACY_IAM_USER_READINESS.md
│   ├── LEGACY_CONSUMER_INVENTORY.md
│   └── OPERATIONS.md
├── .github/
│   └── workflows/
│       └── deploy.yml      # CI/CD Pipeline (aktiv: push auf main + workflow_dispatch)
├── Dockerfile              # Container-Build für ECS
├── requirements.txt        # Runtime-Abhängigkeiten (keine)
├── requirements-dev.txt    # Dev-Abhängigkeiten (pytest, pre-commit)
├── CHANGELOG.md
└── README.md
```

---

## CI/CD

Der Workflow `.github/workflows/deploy.yml` ist auf **ECS/Fargate (dev)** ausgerichtet und läuft bei **Push auf `main`** sowie manuell via **GitHub Actions → Run workflow**.

Nach dem ECS-Rollout wartet der Workflow auf `services-stable` und führt anschliessend einen Smoke-Test auf `/health` aus (konfiguriert über `SERVICE_HEALTH_URL`).

### Voraussetzungen für den ECS-Deploy

**GitHub Secrets (Actions):**
- Keine AWS Access Keys erforderlich (Deploy läuft via GitHub OIDC Role Assume).
- Optional: `SERVICE_API_AUTH_TOKEN` (für `/analyze`-Smoke-Test, wenn `API_AUTH_TOKEN` im Service aktiv ist).

**GitHub Variables (Actions):**
- `ECR_REPOSITORY` (z. B. `swisstopo-dev-api`)
- `ECS_CLUSTER` (z. B. `swisstopo-dev`)
- `ECS_SERVICE` (z. B. `swisstopo-dev-api`)
- `ECS_CONTAINER_NAME` (Container-Name in der Task Definition, oft `app` oder `api`)
- `SERVICE_HEALTH_URL` (vollständige URL für Smoke-Test nach Deploy, z. B. `https://<alb-dns>/health`; wenn leer, wird der Smoke-Test mit Hinweis übersprungen)
- Optional: `SERVICE_BASE_URL` (Basis-URL ohne Pfad für `/analyze`-Smoke-Test; falls nicht gesetzt, versucht der Workflow den Wert aus `SERVICE_HEALTH_URL` durch Entfernen von `/health` abzuleiten)

**Zusätzlich erforderlich:**
- GitHub OIDC Deploy-Role in AWS: `arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role`
- passende IAM-Policy für ECR/ECS (`infra/iam/deploy-policy.json`)
- `Dockerfile` im Repo-Root
- bestehender ECS Service inkl. Task Definition

---

## Beitragen

Siehe [`docs/OPERATIONS.md`](docs/OPERATIONS.md) für Commit-Konventionen, PR-Regeln und die Release-Checkliste.

---

## Lizenz

Vorerst **proprietär** (alle Rechte vorbehalten).

> Eine Open-Source-Lizenz ist aktuell nicht gesetzt. Falls später gewünscht, wird die Lizenzentscheidung explizit dokumentiert und als `LICENSE`-Datei ergänzt.
