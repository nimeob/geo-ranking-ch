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
| `POST` | `/analyze` | Adressanalyse (`{"query":"..."}`) |

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
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Arbeitsmodus, PR-Regeln, Release-Checkliste |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Zentraler, priorisierter Umsetzungs-Backlog |
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
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID`

**GitHub Variables (Actions):**
- `ECR_REPOSITORY` (z. B. `swisstopo-dev-api`)
- `ECS_CLUSTER` (z. B. `swisstopo-dev`)
- `ECS_SERVICE` (z. B. `swisstopo-dev-api`)
- `ECS_CONTAINER_NAME` (Container-Name in der Task Definition, oft `app` oder `api`)
- `SERVICE_HEALTH_URL` (vollständige URL für Smoke-Test nach Deploy, z. B. `https://<alb-dns>/health`; wenn leer, wird der Smoke-Test mit Hinweis übersprungen)

**Zusätzlich erforderlich:**
- `Dockerfile` im Repo-Root
- bestehender ECS Service inkl. Task Definition

---

## Beitragen

Siehe [`docs/OPERATIONS.md`](docs/OPERATIONS.md) für Commit-Konventionen, PR-Regeln und die Release-Checkliste.

---

## Lizenz

Vorerst **proprietär** (alle Rechte vorbehalten).

> Eine Open-Source-Lizenz ist aktuell nicht gesetzt. Falls später gewünscht, wird die Lizenzentscheidung explizit dokumentiert und als `LICENSE`-Datei ergänzt.
