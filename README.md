# geo-ranking-ch

> Geographisches Ranking-System für Schweizer Geodaten.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-in%20development-yellow.svg)]()
[![CI/CD](https://img.shields.io/badge/CI%2FCD-workflow__dispatch%20only-orange.svg)](.github/workflows/deploy.yml)

---

## Überblick

`geo-ranking-ch` ist ein Projekt zur Analyse und zum Ranking von geographischen Einheiten (Gemeinden, Kantone, Regionen) in der Schweiz, basierend auf konfigurierbaren Kriterien und Datensätzen.

> **Hinweis:** Das Projekt befindet sich in einem frühen Entwicklungsstadium. Kernfunktionalität und Infrastruktur werden aktiv aufgebaut.

> **AWS-Naming:** AWS-Ressourcen werden intern unter dem Namen **`swisstopo`** geführt (z. B. ECS Cluster `swisstopo-dev`, S3 `swisstopo-dev-*`). Das ist so gewollt und konsistent — der Repo-Name `geo-ranking-ch` und das interne AWS-Naming `swisstopo` koexistieren. Eine Umbenennung der AWS-Ressourcen ist nicht vorgesehen.

> **Umgebungen:** Aktuell existiert ausschließlich eine **`dev`-Umgebung**. `staging` und `prod` sind noch nicht aufgebaut.

## Schnellstart

### Voraussetzungen

- Python ≥ 3.10 (zu verifizieren — wird ergänzt sobald Stack definiert)
- AWS CLI ≥ 2.x (für Deployment-Operationen)
- Zugriff auf AWS Account `523234426229` (Region: `eu-central-1`)

### Lokale Entwicklung

```bash
# Repo klonen
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

# Dev-Abhängigkeiten installieren (nur pytest, keine Runtime-Deps nötig)
pip install -r requirements-dev.txt

# Tests ausführen
pytest tests/ -v
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
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Arbeitsmodus, PR-Regeln, Release-Checkliste |
| [CHANGELOG.md](CHANGELOG.md) | Versions-History |

---

## Projektstruktur

```
geo-ranking-ch/
├── src/                    # Quellcode (Python, stdlib only)
│   ├── address_intel.py    # Adress-Intelligence + City-Ranking
│   ├── gwr_codes.py        # GWR-Code-Tabellen
│   └── geo_utils.py        # Geodaten-Utilities (Elevation, Geocoding, …)
├── tests/                  # Unit-Tests
│   └── test_core.py
├── scripts/                # Deployment- und Utility-Skripte
├── docs/                   # Projektdokumentation
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT_AWS.md
│   └── OPERATIONS.md
├── .github/
│   └── workflows/
│       └── deploy.yml      # CI/CD Pipeline (aktiv, nur workflow_dispatch)
├── requirements.txt        # Runtime-Abhängigkeiten (keine)
├── requirements-dev.txt    # Dev-Abhängigkeiten (pytest)
├── CHANGELOG.md
└── README.md
```

---

## CI/CD

Der Workflow `.github/workflows/deploy.yml` ist aktiv und kann manuell via **GitHub Actions → Run workflow** ausgelöst werden.

> **Auto-Trigger (push/release) ist noch deaktiviert** — erst nach vollständigem Setup aktivieren.

### Voraussetzungen für produktiven Betrieb

| Schritt | Beschreibung |
|---------|-------------|
| 1 | Stack-Typ wählen: ECS Fargate / Lambda / S3 Static |
| 2 | AWS-Ressourcen anlegen (siehe [`docs/DEPLOYMENT_AWS.md`](docs/DEPLOYMENT_AWS.md)) |
| 3 | GitHub Secrets setzen: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ACCOUNT_ID` |
| 4 | Push-Trigger in `.github/workflows/deploy.yml` aktivieren |
| 5 | Stack-spezifische Build/Deploy-Schritte im Workflow eintragen |

---

## Beitragen

Siehe [`docs/OPERATIONS.md`](docs/OPERATIONS.md) für Commit-Konventionen, PR-Regeln und die Release-Checkliste.

---

## Lizenz

MIT — Details in [`LICENSE`](LICENSE) (TODO: Lizenz-Datei anlegen).
