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

# Abhängigkeiten installieren (wird ergänzt)
# pip install -r requirements.txt   # TODO

# Tests ausführen (wird ergänzt)
# pytest                              # TODO
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
├── src/                    # Quellcode (TODO)
├── scripts/                # Deployment- und Utility-Skripte
├── docs/                   # Projektdokumentation
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT_AWS.md
│   └── OPERATIONS.md
├── .github/
│   └── workflows/
│       └── deploy.yml      # CI/CD Pipeline (aktiv, nur workflow_dispatch)
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
