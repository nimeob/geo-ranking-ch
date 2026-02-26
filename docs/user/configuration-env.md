# Configuration / ENV Guide

Dieser Guide bündelt alle relevanten Umgebungsvariablen für Service und Betriebs-Skripte.

## 1) Webservice (`src/web_service.py`)

### ENV-Referenz

| Variable | Default | Pflicht | Wirkung |
|---|---|---|---|
| `HOST` | `0.0.0.0` | nein | Bind-Adresse des HTTP-Servers |
| `PORT` | – | nein | Primärer Listen-Port |
| `WEB_PORT` | `8080` | nein | Fallback-Port, wenn `PORT` fehlt/leer ist |
| `API_AUTH_TOKEN` | leer | nein | Aktiviert Bearer-Auth auf `POST /analyze` |
| `ANALYZE_DEFAULT_TIMEOUT_SECONDS` | `15` | nein | Default für Request-Feld `timeout_seconds` |
| `ANALYZE_MAX_TIMEOUT_SECONDS` | `45` | nein | Obergrenze (Cap) für effektiven Analyze-Timeout |
| `APP_VERSION` | `dev` | nein | Ausgabe in `GET /version` (`version`) |
| `GIT_SHA` | `unknown` | nein | Ausgabe in `GET /version` (`commit`) |
| `ENABLE_E2E_FAULT_INJECTION` | `0` | nein | Nur für Tests: `__ok__`, `__timeout__`, `__internal__` in `/analyze` |

### Validierungsregeln (Service)

- `PORT`/`WEB_PORT`: werden getrimmt; `PORT` hat Vorrang, sonst `WEB_PORT`, sonst `8080`.
- `API_AUTH_TOKEN`: wenn nach Trim nicht leer, ist `Authorization: Bearer <token>` Pflicht.
- `ANALYZE_DEFAULT_TIMEOUT_SECONDS`, `ANALYZE_MAX_TIMEOUT_SECONDS`, Request-`timeout_seconds`:
  - müssen **endliche Zahlen > 0** sein (`nan`, `inf`, `<=0` sind ungültig),
  - `timeout_seconds` wird auf `ANALYZE_MAX_TIMEOUT_SECONDS` begrenzt.

---

## 2) Remote-Smoke (`scripts/run_remote_api_smoketest.sh`)

### Pflichtvariable

| Variable | Default | Pflicht | Wirkung |
|---|---|---|---|
| `DEV_BASE_URL` | – | ja | Öffentliche Base-URL für den `/analyze`-Smoke-Call |

### Optionale Variablen

| Variable | Default | Wirkung |
|---|---|---|
| `DEV_API_AUTH_TOKEN` | leer | Optionaler Bearer-Token für geschützte `/analyze`-Endpoints |
| `SMOKE_QUERY` | `St. Leonhard-Strasse 40, St. Gallen` | Anfrageinhalt für `/analyze` |
| `SMOKE_MODE` | `basic` | `basic|extended|risk` (trim + case-insensitive) |
| `SMOKE_TIMEOUT_SECONDS` | `20` | API-Timeout im Request |
| `CURL_MAX_TIME` | `45` | Max-Laufzeit des curl-Requests |
| `CURL_RETRY_COUNT` | `3` | Curl-Retry-Anzahl |
| `CURL_RETRY_DELAY` | `2` | Delay zwischen Retries (Sek.) |
| `SMOKE_REQUEST_ID` | auto-generiert | Request-ID für Korrelation |
| `SMOKE_REQUEST_ID_HEADER` | `request` | Header-Typ (`request|correlation|...` inkl. X-/underscore-Aliasse) |
| `SMOKE_ENFORCE_REQUEST_ID_ECHO` | `1` | Echo-Check ein/aus (`1|0|true|false|yes|no|on|off`) |
| `SMOKE_OUTPUT_JSON` | leer | Optionales JSON-Artefakt für den Smoke-Run |

### Validierungsregeln (Smoke)

- `DEV_BASE_URL`:
  - wird getrimmt,
  - darf keine eingebetteten Whitespaces/Steuerzeichen, Query/Fragment oder Userinfo enthalten,
  - darf mit/ohne `/health`/`/analyze` übergeben werden (wird robust normalisiert).
- `DEV_API_AUTH_TOKEN`: wird getrimmt; whitespace-only, eingebetteter Whitespace oder Steuerzeichen sind ungültig (fail-fast `exit 2`).
- `SMOKE_QUERY`: wird getrimmt; leer/whitespace-only oder Steuerzeichen sind ungültig.
- `SMOKE_MODE`: nur `basic|extended|risk`.
- `SMOKE_TIMEOUT_SECONDS`, `CURL_MAX_TIME`: endliche Zahl `> 0`.
- `CURL_RETRY_COUNT`, `CURL_RETRY_DELAY`: Ganzzahlen `>= 0`.
- `SMOKE_REQUEST_ID`:
  - auto-generiert, falls nicht gesetzt,
  - sonst trim + ASCII-only, ohne Steuerzeichen/Whitespace/`,`/`;`, max. 128 Zeichen.
- `SMOKE_OUTPUT_JSON`: wird getrimmt; whitespace-only, Steuerzeichen, Verzeichnisziel oder Datei-Elternpfad als Nicht-Verzeichnis sind ungültig.

---

## 3) Stabilitätslauf (`scripts/run_remote_api_stability_check.sh`)

| Variable | Default | Wirkung |
|---|---|---|
| `DEV_BASE_URL` | – | Pflicht: Ziel-Base-URL für alle Smoke-Runs |
| `STABILITY_RUNS` | `6` | Anzahl Wiederholungen |
| `STABILITY_INTERVAL_SECONDS` | `15` | Pause zwischen Runs |
| `STABILITY_MAX_FAILURES` | `0` | Erlaubte Fehlruns, bevor der Job failt |
| `STABILITY_STOP_ON_FIRST_FAIL` | `0` | Sofortabbruch bei erstem Fail (`1|0|true|false|yes|no|on|off`) |
| `STABILITY_REPORT_PATH` | `artifacts/bl18.1-remote-stability.ndjson` | NDJSON-Reportpfad |
| `STABILITY_SMOKE_SCRIPT` | `scripts/run_remote_api_smoketest.sh` | Optionales Smoke-Script-Override |
| _(plus alle Smoke-Variablen)_ | – | Werden pro Lauf an das Smoke-Script durchgereicht |

### Validierungsregeln (Stability)

- `STABILITY_RUNS`: positive Ganzzahl.
- `STABILITY_INTERVAL_SECONDS`, `STABILITY_MAX_FAILURES`: Ganzzahl `>= 0`.
- `STABILITY_STOP_ON_FIRST_FAIL`: normalisiert auf `0|1`.
- `STABILITY_REPORT_PATH`:
  - trim + Control-Char-Guard,
  - kein Verzeichnisziel,
  - Parent muss Verzeichnis sein (oder wird erstellt, wenn fehlend).
- `STABILITY_SMOKE_SCRIPT`:
  - trim + Control-Char-Guard,
  - relative Pfade werden gegen Repo-Root aufgelöst,
  - Ziel muss ausführbare Datei sein (`-f` + `-x`).

---

## 4) Konfigurationsbeispiele

### Lokal (ohne Auth)

```bash
HOST="127.0.0.1" PORT="8080" python -m src.web_service
```

### Lokal (mit Auth + strikteren Timeouts)

```bash
HOST="127.0.0.1" PORT="8080" \
API_AUTH_TOKEN="dev-secret" \
ANALYZE_DEFAULT_TIMEOUT_SECONDS="10" \
ANALYZE_MAX_TIMEOUT_SECONDS="30" \
python -m src.web_service
```

### Dev/Prod-ähnlicher Smoke gegen Remote-Endpoint

```bash
DEV_BASE_URL="https://<endpoint>" \
DEV_API_AUTH_TOKEN="<token>" \
SMOKE_MODE="extended" \
SMOKE_TIMEOUT_SECONDS="20" \
SMOKE_OUTPUT_JSON="artifacts/smoke.json" \
./scripts/run_remote_api_smoketest.sh
```

### Dev/Prod-ähnlicher Stabilitätslauf

```bash
DEV_BASE_URL="https://<endpoint>" \
DEV_API_AUTH_TOKEN="<token>" \
STABILITY_RUNS="5" \
STABILITY_INTERVAL_SECONDS="10" \
STABILITY_MAX_FAILURES="0" \
STABILITY_REPORT_PATH="artifacts/stability.ndjson" \
./scripts/run_remote_api_stability_check.sh
```

---

Weiterführend:
- [Getting Started](./getting-started.md)
- [API Usage Guide](./api-usage.md)
- [Troubleshooting](./troubleshooting.md)
- [Operations Quick Guide](./operations-runbooks.md)
