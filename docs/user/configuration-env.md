# Configuration / ENV Guide

Dieser Guide dokumentiert die relevanten Umgebungsvariablen für den Webservice (`src/web_service.py`) und den zugrunde liegenden Address-Intelligence-Layer (`src/address_intel.py`).

## Ziel

- klare Übersicht: **Pflicht/Optional**, **Default**, **Validierung**
- reproduzierbares Verhalten zwischen lokal/dev/CI
- schnelle Diagnose bei Fehlkonfigurationen

---

## Service-ENV (`src/web_service.py`)

| Variable | Pflicht | Default | Validierung / Verhalten | Wirkung |
|---|---|---|---|---|
| `HOST` | nein | `0.0.0.0` | keine zusätzliche Validierung im Service | Bind-Adresse des HTTP-Servers |
| `PORT` | nein | – | wird getrimmt; wenn leer/nicht gesetzt, greift `WEB_PORT` | Primärer Listen-Port |
| `WEB_PORT` | nein | `8080` | wird getrimmt und als Integer geparst; nur relevant wenn `PORT` fehlt/leer ist | Fallback-Port (z. B. lokal) |
| `API_AUTH_TOKEN` | nein | leer | wird getrimmt; wenn nach Trim nicht leer, ist Bearer-Auth aktiv | Schützt `POST /analyze` via `Authorization: Bearer <token>` |
| `ANALYZE_DEFAULT_TIMEOUT_SECONDS` | nein | `15` | muss endliche Zahl `> 0` sein | Default für Request-Feld `timeout_seconds` |
| `ANALYZE_MAX_TIMEOUT_SECONDS` | nein | `45` | muss endliche Zahl `> 0` sein | Obergrenze für effektiven Analyze-Timeout |
| `APP_VERSION` | nein | `dev` | String | Ausgabe in `GET /version` (`version`) |
| `GIT_SHA` | nein | `unknown` | String | Ausgabe in `GET /version` (`commit`) |
| `ENABLE_E2E_FAULT_INJECTION` | nein | `0` | aktiv bei exakt `1` | Test-/E2E-Stub-Pfade für `__ok__`, `__timeout__`, `__internal__` |

### Wichtige Prioritätsregeln

1. **Port-Auflösung:** `PORT` hat Vorrang vor `WEB_PORT`.
2. **Auth-Schalter:** Nur wenn `API_AUTH_TOKEN` (nach Trim) gesetzt ist, wird `POST /analyze` auth-pflichtig.
3. **Timeout-Kappung:** Effektiver Request-Timeout ist `min(timeout_seconds, ANALYZE_MAX_TIMEOUT_SECONDS)`.

### Fehlkonfigurationen (Service)

- Ungültige Port-Werte (`PORT`/`WEB_PORT` nicht als Integer parsbar) führen beim Start zu einem Fehler.
- Ungültige Analyze-Timeout-ENV-Werte (z. B. `nan`, `inf`, `<=0`) führen bei `/analyze` zu `400 bad_request`.

---

## Address-Intel-ENV (`src/address_intel.py`)

| Variable | Pflicht | Default | Validierung / Verhalten | Wirkung |
|---|---|---|---|---|
| `ADDRESS_INTEL_MIN_REQUEST_INTERVAL` | nein | `0.25` | beim Import als `float(...)` geparst | Mindestabstand zwischen externen Requests (Rate-Limit-Schonung) |
| `ADDRESS_INTEL_MAX_RETRY_AFTER` | nein | `30` | beim Import als `float(...)` geparst | Obergrenze für Retry-After-Backoff (Sekunden) |

### Hinweis zu Import-Zeitpunkt

Diese beiden Variablen werden beim Import von `src/address_intel.py` geparst. Nicht-numerische Werte können daher bereits beim Service-Start zu einem Fehler führen.

---

## Konfigurationsbeispiele

### Lokal (ohne Auth)

```bash
HOST="0.0.0.0"
WEB_PORT="8080"
ANALYZE_DEFAULT_TIMEOUT_SECONDS="15"
ANALYZE_MAX_TIMEOUT_SECONDS="45"
python -m src.web_service
```

### Lokal/Dev (mit Auth)

```bash
PORT="8080"
API_AUTH_TOKEN="dev-secret"
ANALYZE_DEFAULT_TIMEOUT_SECONDS="10"
ANALYZE_MAX_TIMEOUT_SECONDS="30"
APP_VERSION="dev"
GIT_SHA="$(git rev-parse --short HEAD)"
python -m src.web_service
```

### E2E-Testmodus (nur lokal/CI)

```bash
ENABLE_E2E_FAULT_INJECTION="1" \
python -m src.web_service
```

> `ENABLE_E2E_FAULT_INJECTION=1` nicht in produktiven Deployments aktivieren.

---

## Verifikation

Schneller Sanity-Check nach ENV-Änderungen:

```bash
./scripts/run_webservice_e2e.sh
```

Optional gegen dev-Endpoint:

```bash
DEV_BASE_URL="https://<endpoint>" ./scripts/run_webservice_e2e.sh
```
