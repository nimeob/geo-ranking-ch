# geo-ranking-ch

> Geographisches Ranking-System für Schweizer Geodaten.

**Contributing (Dev):** siehe [`CONTRIBUTING.md`](CONTRIBUTING.md).

[![License](https://img.shields.io/badge/license-propriet%C3%A4r-lightgrey.svg)]()
[![Status](https://img.shields.io/badge/status-in%20development-yellow.svg)]()
[![CI/CD](https://img.shields.io/badge/CI%2FCD-ECS%20dev%20(manual)-orange.svg)](.github/workflows/deploy.yml)

---

## Überblick

`geo-ranking-ch` ist ein Projekt zur Analyse und zum Ranking von geographischen Einheiten (Gemeinden, Kantone, Regionen) in der Schweiz, basierend auf konfigurierbaren Kriterien und Datensätzen.

> **Hinweis:** Das Projekt befindet sich in einem frühen Entwicklungsstadium. Kernfunktionalität und Infrastruktur werden aktiv aufgebaut.

> **AWS-Naming:** AWS-Ressourcen werden intern unter dem Namen **`swisstopo`** geführt (z. B. ECS Cluster `swisstopo-dev`, S3 `swisstopo-dev-*`). Das ist so gewollt und konsistent — der Repo-Name `geo-ranking-ch` und das interne AWS-Naming `swisstopo` koexistieren. Eine Umbenennung der AWS-Ressourcen ist nicht vorgesehen.

> **Umgebungen:** Aktuell existiert ausschließlich eine **`dev`-Umgebung**. `staging` und `prod` sind noch nicht aufgebaut.

### Webservice-Features (thematisch geordnet)

- **API-Grundfunktionen**
  - `GET /gui` als GUI-MVP-Shell (BL-20.6: Adresse + **interaktive OSM-Karte (Pan/Zoom/Klick)** + Result-Panel, API-first)
  - `GET /health` für Liveness-Checks
  - `GET /version` für Build-/Commit-Transparenz
  - `POST /analyze` für adressbasierte Standortanalyse
- **Sicherheit & Zugriff**
  - optionale Bearer-Auth via `API_AUTH_TOKEN`
  - robuste Request-ID-Sanitization (ASCII-only, Längenlimit, Delimiter-/Whitespace-Guards)
- **Robuste API-Eingänge**
  - `intelligence_mode` mit Trim + case-insensitive Normalisierung (`basic|extended|risk`)
  - `timeout_seconds` als endliche Zahl `> 0` (inkl. serverseitigem Max-Cap)
  - optionales `preferences`-Profil mit Enum-/Range-Validierung, Preset-Schnellstart (`preset`/`preset_version`) und `weights` im Bereich `0..1`
  - tolerantes Routing (trailing slash, double slash, Query/Fragment-ignorant)
- **Betrieb & Nachvollziehbarkeit**
  - konsistente Request-Korrelation über Header + JSON-Feld `request_id`
  - lokale/dev E2E-, Smoke- und Stabilitäts-Runner mit Artefakt-Ausgabe
- **Developer Experience**
  - kanonische Service-Entrypoints: API `src/api/web_service.py`, UI `src/ui/service.py`
  - Legacy-Wrapper unter `src/*.py` bleiben für bestehende Integrationen kompatibel
  - klar dokumentierte User-Guides unter `docs/user/`

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
# fokussierter Crawler-Regressionscheck (Workstream-Balance + TODO-Filter + Vision↔Issue-Coverage + Code↔Doku-Drift)
pytest tests/test_github_repo_crawler.py -v

# reproduzierbarer Crawler-Regressionscheck (lokal + CI-Workflow)
./scripts/check_crawler_regression.sh

# Consistency-Reports (JSON + Markdown) ohne GitHub-Mutationen erzeugen
python3 scripts/github_repo_crawler.py --dry-run
# Output: reports/consistency_report.json + reports/consistency_report.md

pre-commit run --all-files

# Doku-Qualitätsgate (BL-19.8): Linkcheck + Strukturcheck im frischen venv
./scripts/check_docs_quality_gate.sh

# Service-getrennte Smoke-Checks (BL-334.5)
# - API-only: src.api.web_service
# - UI-only:  src.ui.service
./scripts/check_bl334_split_smokes.sh

# API-Service starten (kanonischer Entrypoint; ECS-ready)
python -m src.api.web_service
# optionaler Port via ENV: PORT (primär) oder WEB_PORT (Fallback für Legacy-Wrapper)
# Healthcheck (ECS/Liveness): http://localhost:8080/health
# Dev-Healthcheck (mit Build-Info, dev-only): http://localhost:8080/healthz

# Optional: Dev-TLS mit self-signed Zertifikat
# (bevorzugt reproduzierbar via Helper-Script)
./scripts/generate_dev_tls_cert.sh

# oder manuell via openssl
openssl req -x509 -newkey rsa:2048 -nodes -days 7 \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
  -keyout /tmp/geo-dev.key \
  -out /tmp/geo-dev.crt
TLS_CERT_FILE=/tmp/geo-dev.crt \
TLS_KEY_FILE=/tmp/geo-dev.key \
PORT=8443 \
python -m src.api.web_service
# Healthcheck (ECS/Liveness): https://localhost:8443/health
# Dev-Healthcheck (mit Build-Info, dev-only): https://localhost:8443/healthz

# Optional: zusätzlicher HTTP->HTTPS Redirect-Listener (Dev)
TLS_CERT_FILE=/tmp/geo-dev.crt \
TLS_KEY_FILE=/tmp/geo-dev.key \
PORT=8443 \
TLS_ENABLE_HTTP_REDIRECT=1 \
TLS_REDIRECT_HTTP_PORT=8080 \
python -m src.api.web_service
```

### Docker (wie in ECS)

```bash
# API-Image (service-lokaler Build-Kontext via Dockerfile.dockerignore)
docker build -f Dockerfile -t geo-ranking-ch:api-dev .
docker run --rm -p 8080:8080 geo-ranking-ch:api-dev
# Healthcheck (ECS/Liveness)
curl http://localhost:8080/health
# Dev-Healthcheck (mit Build-Info, dev-only)
curl http://localhost:8080/healthz

# UI-Image (service-lokaler Build-Kontext via Dockerfile.ui.dockerignore)
docker build -f Dockerfile.ui -t geo-ranking-ch:ui-dev .
docker run --rm -p 8081:8080 geo-ranking-ch:ui-dev
# Healthcheck
curl http://localhost:8081/healthz
```

### Migrationshinweis zur Source-Trennung (BL-334)

- **Kanonisch für neue Änderungen:**
  - API: `python -m src.api.web_service`
  - UI: `python -m src.ui.service`
- **Legacy-Kompatibilität bleibt aktiv:**
  - `python -m src.web_service` und `python -m src.ui_service` funktionieren weiterhin als Wrapper.
- **Wichtig für CI/Smokes:**
  - service-getrennte Smoke-Ausführung läuft über `./scripts/check_bl334_split_smokes.sh`.

### Webservice-Endpoints (MVP)

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/gui` | GUI-MVP-Shell (Adresseingabe + Kartenklick + Result-Panel inkl. Kernfaktoren + Burger-Menü) |
| `GET` | `/history` | Historische Abfragen (persistiert; Links zu separater Result-Page) |
| `GET` | `/results/<result_id>` | Result-Page mit Tabs (Overview, Sources/Evidence, Generated/Derived, Raw JSON) |
| `GET` | `/analyze/history` | History-JSON für UI (`?limit=...`) |
| `GET` | `/analyze/results/<result_id>` | Result-JSON für Result-Pages (`?view=latest|requested`) |
| `GET` | `/health` | Liveness/Healthcheck (ECS) |
| `GET` | `/healthz` | Dev-Healthcheck (dev-only, no-store): Status + Build-Info + Timestamp |
| `GET` | `/version` | Build/Commit-Metadaten |
| `POST` | `/analyze` | Adressanalyse (`{"query":"...","intelligence_mode":"basic|extended|risk","timeout_seconds":15,"preferences":{...}}`) |

#### Historische Abfragen (persistiert)

- Persistenz erfolgt über den bestehenden file-backed Store `src/api/async_jobs.py`.
- Default-Store-Datei: `runtime/async_jobs/store.v1.json` (override via `ASYNC_JOBS_STORE_FILE`).
- Sync-Requests (`POST /analyze` ohne Async-Mode) schreiben ebenfalls einen Job + Final-Result in den Store (steuerbar via `ENABLE_QUERY_HISTORY=0/1`, Default: `1`).

**Auth — default-deny (Phase 1):** Sobald `PHASE1_AUTH_USERS_JSON` oder `OIDC_JWKS_URL` gesetzt ist, gilt **default-deny**: alle protected Endpoints erfordern einen gültigen `Authorization: Bearer <token>` Header, sonst folgt `401 unauthorized`. Öffentlich bleiben nur `/health`, `/healthz`, `/version`.

Protected Endpoints:
- `POST /analyze`
- `GET /analyze/history`
- `GET /analyze/results/<result_id>`
- `GET /analyze/jobs/<job_id>`
- `GET /analyze/jobs/<job_id>/notifications`
- `POST /analyze/jobs/<job_id>/cancel`

Fehler-Response (401): `{"ok": false, "error": "unauthorized", "message": "missing or invalid bearer token", "request_id": "..."}`

Beispiel curl:
```bash
curl -H "Authorization: Bearer <your-token>" http://localhost:8080/analyze/history
curl -H "Authorization: Bearer <your-token>" http://localhost:8080/analyze/results/<result_id>
curl -H "Authorization: Bearer <your-token>" http://localhost:8080/analyze/jobs/<job_id>
```

**Legacy-Auth:** `API_AUTH_TOKEN` (einzelner Token) wird weiterhin für `POST /analyze` unterstützt (Abwärtskompatibilität). Für neue Deployments `PHASE1_AUTH_USERS_JSON` oder OIDC verwenden.

**Request-Korrelation:** Für `POST /analyze` wird die **erste gültige** ID aus `X-Request-Id`/`X_Request_Id`/`Request-Id`/`Request_Id` (primär) bzw. `X-Correlation-Id`/`X_Correlation_Id`/`Correlation-Id`/`Correlation_Id` (Fallback) in die Antwort gespiegelt (`X-Request-Id` Header + JSON-Feld `request_id`). Leere/whitespace-only IDs, IDs mit eingebettetem Whitespace, IDs mit Steuerzeichen, IDs mit Trennzeichen (`,`/`;`), Non-ASCII-IDs sowie IDs länger als 128 Zeichen werden verworfen; ohne gültige Header-ID erzeugt der Service automatisch eine Request-ID.

**Timeout-Input:** `timeout_seconds` muss eine **endliche Zahl > 0** sein (z. B. kein `nan`/`inf`), sonst antwortet die API mit `400 bad_request`.

**Mode-Input:** `intelligence_mode` wird vor der Validierung getrimmt und case-insensitive normalisiert (z. B. `"  ExTenDeD  "` → `extended`); erlaubt sind `basic|extended|risk`.

**Preferences-Input (optional):** `preferences` muss ein Objekt sein; erlaubte Enum-Dimensionen sind `lifestyle_density`, `noise_tolerance`, `nightlife_preference`, `school_proximity`, `family_friendly_focus`, `commute_priority`. Alternativ kann mit `preferences.preset` + `preferences.preset_version` (`v1`) gestartet werden. Optionale Gewichte liegen unter `preferences.weights` und müssen numerisch im Bereich `0..1` liegen. Ungültige oder unbekannte Keys führen zu `400 bad_request`.

**Ranking/Explainability (dev-only):** `suitability_light` liefert zusätzlich `top_factors` (max. 5) als kompakte Treiberliste pro Ergebnis (Sortierung nach `abs(contribution)` absteigend). `contribution` ist **signiert & normalisiert** relativ zu `score=50` (neutral). Pfade:
- `result.data.modules.suitability_light.top_factors`
- `result.data.modules.summary_compact.suitability_light.top_factors`

**Routing-Kompatibilität:** Die Endpunkte tolerieren optionale trailing Slashes, kollabieren doppelte Slash-Segmente (`//`) auf einen Slash und ignorieren Query/Fragment-Teile bei der Routenauflösung (z. B. `/gui/?probe=1`, `/health/?probe=1`, `//version///?ts=1`, `//analyze//?trace=1`).

👉 Detaillierte API-Referenz: [`docs/user/api-usage.md`](docs/user/api-usage.md)

### E2E-Tests (Webservice)

Regression-Minimum (schneller Lokal-Check) ist in [`docs/BL-18_SERVICE_E2E.md#regression-minimum-lokal-optional-dev`](docs/BL-18_SERVICE_E2E.md#regression-minimum-lokal-optional-dev) dokumentiert.

```bash
# Regression-Minimum lokal (schneller Check)
python3 -m pytest -q tests/test_web_e2e.py tests/test_remote_stability_script.py

# lokal (voller Lauf; inkl. /analyze E2E + Smoke-/Stability-Script-Tests)
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
# optional: DEV_TLS_CA_CERT=/pfad/zu/dev-self-signed.crt (nur Datei, lesbar, keine Steuerzeichen; wird als Trust-Anchor via `curl --cacert` genutzt — kein globales `-k`)
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
| [docs/TLS_CERTIFICATE_MIGRATION_RUNBOOK.md](docs/TLS_CERTIFICATE_MIGRATION_RUNBOOK.md) | Migrationspfad Dev self-signed → offizielles Zertifikat (TLS-Baseline, Rotation, Rollback) |
| [docs/NETWORK_INGRESS_DECISIONS.md](docs/NETWORK_INGRESS_DECISIONS.md) | Beschlossenes Netzwerk-/Ingress-Zielbild (BL-05) |
| [docs/DATA_AND_API_SECURITY.md](docs/DATA_AND_API_SECURITY.md) | Datenhaltungsentscheidung + API-Sicherheitskonzept (BL-06/BL-07) |
| [docs/ENV_PROMOTION_STRATEGY.md](docs/ENV_PROMOTION_STRATEGY.md) | Zielbild für staging/prod + Promotion-Gates (BL-09) |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Arbeitsmodus, PR-Regeln, Release-Checkliste |
| [docs/LOGGING_SCHEMA_V1.md](docs/LOGGING_SCHEMA_V1.md) | Normatives JSON-Logging-Schema v1 inkl. Redaction-Regeln (BL-340.1) |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Zentraler, priorisierter Umsetzungs-Backlog |
| [docs/AWS_INVENTORY.md](docs/AWS_INVENTORY.md) | Vollständiges AWS-Ressourcen-Inventar mit ARNs, Konfig, IaC-Status und Rebuild-Hinweisen (BL-11) |
| [docs/LEGACY_IAM_USER_READINESS.md](docs/LEGACY_IAM_USER_READINESS.md) | Read-only Decommission-Readiness inkl. Go/No-Go für `swisstopo-api-deploy` (BL-15) |
| [docs/LEGACY_CONSUMER_INVENTORY.md](docs/LEGACY_CONSUMER_INVENTORY.md) | Offene Legacy-Consumer-Matrix inkl. Migrationsstatus/Next Actions (BL-15) |
| [docs/AUTONOMOUS_AGENT_MODE.md](docs/AUTONOMOUS_AGENT_MODE.md) | Verbindlicher Arbeitsmodus für Nipa (Subagents + GitHub App Auth) |
| [docs/user/README.md](docs/user/README.md) | User-Doku Einstieg (BL-19.1) |
| [docs/user/getting-started.md](docs/user/getting-started.md) | Schnellstart bis zum ersten erfolgreichen `/analyze`-Call (BL-19.2) |
| [docs/user/configuration-env.md](docs/user/configuration-env.md) | Konfigurations-/ENV-Referenz inkl. Defaults, Validierung und lokalen/prodnahen Beispielen (BL-19.3) |
| [docs/user/api-usage.md](docs/user/api-usage.md) | API-Referenz mit Auth, Headern, Inputs/Outputs und Statuscodes (BL-19.4) |
| [docs/user/troubleshooting.md](docs/user/troubleshooting.md) | Häufige Fehlerbilder (401/400/504/404), Diagnose-Checks und Eskalationspfad (BL-19.5) |
| [docs/user/operations-runbooks.md](docs/user/operations-runbooks.md) | Tagesbetrieb-Runbook (Quick-Checks, Smoke/Stability, Deploy-Checks, Incident-Minirunbook) (BL-19.6) |
| [docs/BL-18_SERVICE_E2E.md](docs/BL-18_SERVICE_E2E.md) | Ist-Analyse + E2E-Runbook für BL-18 |
| [docs/testing/dev-self-signed-tls-smoke.md](docs/testing/dev-self-signed-tls-smoke.md) | Dev-Runbook für self-signed TLS + verifizierten HTTPS-Smoke ohne globales `-k` |
| [docs/VISION_PRODUCT.md](docs/VISION_PRODUCT.md) | Produktvision: API + GUI für Standort-/Gebäude-Intelligence CH |
| [docs/gui/GUI_MVP_STATE_FLOW.md](docs/gui/GUI_MVP_STATE_FLOW.md) | GUI-MVP Shell: Adresse/Kartenklick, Zustandsautomat, Kernfaktoren-Panel und Forward-Compatibility (BL-20.6) |
| [docs/DATA_SOURCE_FIELD_MAPPING_CH.md](docs/DATA_SOURCE_FIELD_MAPPING_CH.md) | Technisches Feld-Mapping Quelle -> Domain inkl. Transform-Regeln und Follow-up-Gaps (BL-20.2.b) |
| [docs/api/contract-v1.md](docs/api/contract-v1.md) | Versionierter API-Vertrag v1 für BL-20 (`/api/v1`, Schemas, Fehlercodes, Beispielpayloads) |
| [docs/api/field-reference-v1.md](docs/api/field-reference-v1.md) | Menschenlesbare Feldreferenz für `legacy` + `grouped` (Semantik, Typ, Pflicht/Optionalität, Modus-Abhängigkeiten) (BL-20.1.d.wp2) |
| [docs/api/contract-stability-policy.md](docs/api/contract-stability-policy.md) | Stabilitätsleitfaden (`stable`/`beta`/`internal`) + Breaking/Non-Breaking-Policy inkl. Changelog-/Release-Prozess (BL-20.1.d.wp4) |
| [docs/GO_TO_MARKET_MVP.md](docs/GO_TO_MARKET_MVP.md) | GTM-MVP-Artefakte: Value Proposition, Scope, Demo-Storyline, offene Risiken (BL-20.7.b) |
| [docs/PACKAGING_BASELINE.md](docs/PACKAGING_BASELINE.md) | Reproduzierbare Build/Run-Baseline für API-only Packaging inkl. Konfigurationsmatrix (Pflicht/Optional, Default/Beispiel), Verify-Checks und Basis-Release-Checkliste (BL-20.7.a.r1/r2/r3) |
| [docs/BFF_FLOW.md](docs/BFF_FLOW.md) | BFF (Backend-for-Frontend): OIDC-Login-Flow, Session-Cookie-Lifecycle, Token-Delegation, CSRF, Env-Variablen-Tabelle (#806) |
| [CHANGELOG.md](CHANGELOG.md) | Versions-History |

---

## BFF — Portal Authentication (Backend-for-Frontend)

Das BFF-Modul (`src/api/bff_*.py`) implementiert sicheren Web-Login für das Portal-SPA ohne Browser-Tokens:

- **Login:** OIDC Auth Code + PKCE gegen Cognito; nur httpOnly Session-Cookie zum Browser
- **Session:** Opaker Session-ID-Cookie; Tokens ausschließlich serverseitig gespeichert
- **Token Delegation:** `bff_api_call` injiziert `Authorization: Bearer <token>` automatisch; Auto-Refresh bei Ablauf
- **CSRF-Schutz:** `X-BFF-CSRF: 1` Custom-Header-Check für alle State-ändernden Anfragen
- **Logout:** Session invalidieren + Cookie löschen + (optional) Cognito-Redirect

Dokumentation: [`docs/BFF_FLOW.md`](docs/BFF_FLOW.md)

---

## Projektstruktur

```text
geo-ranking-ch/
├── src/                              # Service- und Core-Logik
│   ├── api/                          # Kanonischer API-Source-Bereich
│   │   └── web_service.py            # HTTP-API (/gui, /health, /version, /analyze)
│   ├── ui/                           # Kanonischer UI-Source-Bereich
│   │   ├── service.py                # Eigenständiger UI-Service (/ , /gui, /healthz)
│   │   └── gui_mvp.py                # Kompatibilitäts-Wrapper -> src.shared.gui_mvp
│   ├── shared/                       # Shared-Namespace (neutral)
│   │   └── gui_mvp.py                # Kanonische GUI-MVP Shell (von API + UI genutzt)
│   ├── web_service.py                # Legacy-Wrapper -> src.api.web_service
│   ├── ui_service.py                 # Legacy-Wrapper -> src.ui.service
│   ├── gui_mvp.py                    # Legacy-Wrapper -> src.shared.gui_mvp
│   ├── geo_utils.py
│   └── gwr_codes.py
├── tests/                            # Unit-, E2E- und Doku-Qualitäts-Tests
│   ├── test_core.py
│   ├── test_web_e2e.py
│   ├── test_web_e2e_dev.py
│   ├── test_remote_smoke_script.py
│   ├── test_remote_stability_script.py
│   ├── test_user_docs.py
│   └── test_markdown_links.py
├── scripts/                          # Audit-, Deploy-, E2E-/Smoke- und Qualitäts-Runner
│   ├── run_webservice_e2e.sh
│   ├── run_remote_api_smoketest.sh
│   ├── run_remote_api_stability_check.sh
│   ├── check_docs_quality_gate.sh
│   ├── check_bl334_split_smokes.sh
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
├── .github/workflows/deploy.yml      # CI/CD Deploy (manual workflow_dispatch, API+UI)
├── .github/workflows/docs-quality.yml# Manual-Fallback für Doku-Gate (OpenClaw ist Primärpfad)
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── CHANGELOG.md
└── README.md
```

> Hinweis: `artifacts/` enthält Laufartefakte (Smoke/Stability/Evidenz) und ist hier bewusst nicht als Kernstruktur aufgeführt.

---

## CI/CD

Der Workflow `.github/workflows/deploy.yml` ist auf **ECS/Fargate (dev)** ausgerichtet und läuft aktuell **nur manuell** via **GitHub Actions → Run workflow** (`workflow_dispatch`).

Für `contract-tests`, `crawler-regression` und `docs-quality` ist OpenClaw der Primärpfad (siehe [`docs/OPERATIONS.md`](docs/OPERATIONS.md#github-actions-cleanup-required-checks-bl-20ywp4)); die gleichnamigen GitHub-Workflows bleiben als `workflow_dispatch`-Fallback erhalten.

Der Deploy-Workflow ist service-getrennt: API und UI werden nacheinander ausgerollt (`services-stable` je Service), danach laufen die Smokes (`/health`, optional `/analyze`, `/healthz`) und optional ein strikter Split-Smoke.

### Voraussetzungen für den ECS-Deploy

**GitHub Secrets (Actions):**
- Keine AWS Access Keys erforderlich (Deploy läuft via GitHub OIDC Role Assume).
- Optional: `SERVICE_API_AUTH_TOKEN` (für `/analyze`-Smoke-Test, wenn `API_AUTH_TOKEN` im Service aktiv ist).

**GitHub Variables (Actions):**
- `ECS_CLUSTER` (z. B. `swisstopo-dev`)
- `ECS_API_SERVICE` (z. B. `swisstopo-dev-api`)
- `ECS_UI_SERVICE` (z. B. `swisstopo-dev-ui`)
- `ECS_API_CONTAINER_NAME` (Containername in der API-Task Definition)
- `ECS_UI_CONTAINER_NAME` (Containername in der UI-Task Definition)
- `ECR_API_REPOSITORY` (z. B. `swisstopo-dev-api`)
- `ECR_UI_REPOSITORY` (z. B. `swisstopo-dev-ui`)
- `SERVICE_API_BASE_URL` (z. B. `https://api.<domain>`)
- `SERVICE_APP_BASE_URL` (z. B. `https://www.<domain>`)
- Optional: `SERVICE_HEALTH_URL` (Override für API-Health; sonst wird `${SERVICE_API_BASE_URL}/health` verwendet)

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
