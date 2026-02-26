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
# optionaler Port via ENV: PORT (primär) oder WEB_PORT (Fallback für lokale Wrapper)
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

**Request-Korrelation:** Für `POST /analyze` wird die **erste gültige** ID aus `X-Request-Id`/`X_Request_Id`/`Request-Id`/`Request_Id` (primär) bzw. `X-Correlation-Id`/`X_Correlation_Id`/`Correlation-Id`/`Correlation_Id` (Fallback) in die Antwort gespiegelt (`X-Request-Id` Header + JSON-Feld `request_id`). Leere/whitespace-only IDs, IDs mit eingebettetem Whitespace, IDs mit Steuerzeichen, IDs mit Trennzeichen (`,`/`;`), Non-ASCII-IDs sowie IDs länger als 128 Zeichen werden verworfen; ohne gültige Header-ID erzeugt der Service automatisch eine Request-ID.

**Timeout-Input:** `timeout_seconds` muss eine **endliche Zahl > 0** sein (z. B. kein `nan`/`inf`), sonst antwortet die API mit `400 bad_request`.

**Mode-Input:** `intelligence_mode` wird vor der Validierung getrimmt und case-insensitive normalisiert (z. B. `"  ExTenDeD  "` → `extended`); erlaubt sind `basic|extended|risk`.

**Routing-Kompatibilität:** Die Endpunkte tolerieren optionale trailing Slashes und ignorieren Query/Fragment-Teile bei der Routenauflösung (z. B. `/health/?probe=1`, `/version/?ts=1`, `/analyze/?trace=1`).

### E2E-Tests (Webservice)

```bash
# lokal (immer; inkl. /analyze E2E + Smoke-/Stability-Script-Tests)
# + dev (optional via DEV_BASE_URL)
./scripts/run_webservice_e2e.sh

# dedizierter Remote-Smoke-Test für BL-18.1 (/analyze)
# validiert: HTTP 200, ok=true, result vorhanden, Request-ID-Echo (Header+JSON)
# DEV_BASE_URL muss http(s) sein (auch mit grossgeschriebenem Schema wie HTTP://); führende/trailing Whitespaces, redundante trailing Slashes sowie /health-/analyze-Suffixe (case-insensitive, auch verkettet, in gemischter Reihenfolge wie /analyze/health und auch als wiederholte Kette wie /health/analyze/health/analyze///; inkl. kombinierten Inputs wie "  HTTP://.../AnAlYzE/health//  " und "  HTTP://.../health//analyze/health/analyze///  ") werden automatisch normalisiert
# DEV_BASE_URL darf keine eingebetteten Whitespaces/Steuerzeichen enthalten (z. B. "http://.../hea lth")
# DEV_BASE_URL darf keine Query-/Fragment-Komponenten enthalten (z. B. ?foo=bar oder #frag)
# DEV_BASE_URL darf keine Userinfo enthalten (z. B. user:pass@host), um Secret-Leaks in Logs zu verhindern
# DEV_BASE_URL muss eine valide Host/Port-Kombination enthalten (nicht-numerische oder out-of-range Ports wie :abc / :70000 werden fail-fast mit exit 2 abgewiesen)
# SMOKE_QUERY wird vor dem Request getrimmt, darf nicht leer sein und keine Steuerzeichen enthalten (whitespace-only/control chars -> fail-fast exit 2)
# SMOKE_TIMEOUT_SECONDS/CURL_MAX_TIME müssen endliche Zahlen >0 sein; CURL_RETRY_COUNT/CURL_RETRY_DELAY Ganzzahlen >=0 (alle Werte werden vor Validierung getrimmt)
# optional: SMOKE_MODE=basic|extended|risk (Wert wird vor Validierung getrimmt + case-insensitive normalisiert)
# optional: SMOKE_REQUEST_ID (wenn leer/nicht gesetzt wird eine eindeutige ID auto-generiert); eigene Werte werden getrimmt, müssen ASCII-only sein, dürfen weder Steuerzeichen, Trennzeichen (`,`/`;`) noch eingebettete Whitespaces enthalten und müssen <=128 Zeichen sein (Fail-fast bei Fehlwerten)
# optional: SMOKE_REQUEST_ID_HEADER=request|correlation|request-id|correlation-id|x-request-id|x-correlation-id|request_id|correlation_id|x_request_id|x_correlation_id (Default request; Wert wird getrimmt + case-insensitive normalisiert; Short-Aliasse senden Request-Id/Correlation-Id bzw. Request_Id/Correlation_Id, X-Aliasse senden X-Request-Id/X-Correlation-Id bzw. X_Request_Id/X_Correlation_Id; embedded Whitespaces/Steuerzeichen sind nicht erlaubt)
# optional: SMOKE_ENFORCE_REQUEST_ID_ECHO=1|0|true|false|yes|no|on|off (Wert wird vor Validierung getrimmt + normalisiert)
# optional: DEV_API_AUTH_TOKEN wird vor Verwendung getrimmt; whitespace-only Werte, eingebettete Whitespaces und Steuerzeichen werden fail-fast mit exit 2 abgewiesen
# optional: SMOKE_OUTPUT_JSON wird vor der Nutzung getrimmt; whitespace-only Pfade, Pfade mit Steuerzeichen, Verzeichnisziele und Pfade mit Datei-Elternpfad (Parent ist kein Verzeichnis) werden fail-fast mit exit 2 abgewiesen (robuste/sichere Artefaktausgabe auch bei whitespace-umhüllten Pfaden)
DEV_BASE_URL="https://<endpoint>" ./scripts/run_remote_api_smoketest.sh

# kurzer Stabilitätslauf (mehrere Remote-Smokes, mit NDJSON-Report)
# optional fail-fast: STABILITY_STOP_ON_FIRST_FAIL=1|0|true|false|yes|no|on|off (Wert wird vor Validierung getrimmt + normalisiert)
# STABILITY_RUNS / STABILITY_INTERVAL_SECONDS / STABILITY_MAX_FAILURES werden ebenfalls vor Validierung getrimmt
# STABILITY_REPORT_PATH wird vor Nutzung getrimmt; whitespace-only Werte, Pfade mit Steuerzeichen, Verzeichnisziele oder Pfade mit Datei-Elternpfad (Parent ist kein Verzeichnis) werden fail-fast mit exit 2 abgewiesen; fehlende Verzeichnis-Elternpfade werden automatisch erstellt
# optionales Script-Override (Tests/Debug): STABILITY_SMOKE_SCRIPT=/pfad/zu/run_remote_api_smoketest.sh
# STABILITY_SMOKE_SCRIPT wird vor Nutzung getrimmt; whitespace-only Werte oder Pfade mit Steuerzeichen werden fail-fast mit exit 2 abgewiesen
# relative Overrides (z. B. ./scripts/run_remote_api_smoketest.sh) werden robust gegen REPO_ROOT aufgelöst; Ziel muss eine ausführbare Datei sein
# Safety-Guard: fehlendes/leer gebliebenes Smoke-JSON **oder** ein Report mit `status!=pass` zählt als Fehlrun (auch wenn das Smoke-Script rc=0 liefert)
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
| [docs/user/README.md](docs/user/README.md) | User-Doku Einstieg (BL-19.1) |
| [docs/user/getting-started.md](docs/user/getting-started.md) | Schnellstart bis zum ersten erfolgreichen `/analyze`-Call (BL-19.2) |
| [docs/BL-18_SERVICE_E2E.md](docs/BL-18_SERVICE_E2E.md) | Ist-Analyse + E2E-Runbook für BL-18 |
| [docs/VISION_PRODUCT.md](docs/VISION_PRODUCT.md) | Produktvision: API + GUI für Standort-/Gebäude-Intelligence CH |
| [CHANGELOG.md](CHANGELOG.md) | Versions-History |

---

## Projektstruktur

```text
geo-ranking-ch/
├── src/                              # Service- und Core-Logik
│   ├── address_intel.py
│   ├── geo_utils.py
│   ├── gwr_codes.py
│   └── web_service.py                # HTTP-API (/health, /version, /analyze)
├── tests/                            # Unit- und E2E-Tests
│   ├── test_core.py
│   ├── test_web_e2e.py
│   ├── test_web_e2e_dev.py
│   ├── test_remote_smoke_script.py
│   └── test_remote_stability_script.py
├── scripts/                          # Audit-, Deploy- und E2E-/Smoke-Runner
│   ├── run_webservice_e2e.sh
│   ├── run_remote_api_smoketest.sh
│   ├── run_remote_api_stability_check.sh
│   ├── check_bl17_oidc_assumerole_posture.sh
│   ├── audit_legacy_aws_consumer_refs.sh
│   ├── audit_legacy_runtime_consumers.sh
│   └── audit_legacy_cloudtrail_consumers.sh
├── docs/                             # Architektur, Backlog, Security, Runbooks
│   ├── BACKLOG.md
│   ├── BL-18_SERVICE_E2E.md
│   ├── DEPLOYMENT_AWS.md
│   ├── LEGACY_IAM_USER_READINESS.md
│   └── LEGACY_CONSUMER_INVENTORY.md
├── infra/
│   ├── terraform/                    # IaC für AWS-Ressourcen
│   ├── iam/                          # IAM Policies/Trusts
│   └── lambda/                       # Lambda-Funktionen (health_probe, sns_to_telegram)
├── .github/workflows/deploy.yml      # CI/CD (push main + manual dispatch)
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── CHANGELOG.md
└── README.md
```

> Hinweis: `artifacts/` enthält Laufartefakte (Smoke/Stability/Evidenz) und ist hier bewusst nicht als Kernstruktur aufgeführt.

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
