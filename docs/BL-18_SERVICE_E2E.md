> **Diese Datei wurde archiviert.** Inhalt jetzt in [archive/BL-18_SERVICE_E2E.md](archive/BL-18_SERVICE_E2E.md)

---

# BL-18 — Service-Ist-Analyse + E2E-Testaufbau (lokal + dev)

## Ist-Analyse (vor dieser Iteration)

- Webservice (`src/web_service.py`) hatte nur Basis-Endpunkte (`/health`, `/version`, `/analyze`).
- Für `/analyze` gab es **keine API-Auth-Prüfung**.
- Timeout war serverseitig fix auf `15s` und nicht pro Request steuerbar.
- Fehler-Mapping war teilweise grob:
  - `AddressIntelError` → 422
  - `ValueError` → 400
  - Rest → 500
  - explizites Mapping für Timeout (`504`) fehlte.
- Es gab **keine dedizierten Webservice-E2E-Tests** (lokal/dev), nur umfangreiche Core-Unit-Tests in `tests/test_core.py`.

## Umgesetzte Erweiterungen in dieser Iteration

### Service-Funktionalität

- **Auth (optional, per Env):**
  - `API_AUTH_TOKEN` gesetzt → `/analyze` verlangt einen Bearer-Token im `Authorization`-Header.
  - Das Scheme `Bearer` wird case-insensitive akzeptiert und führende/trailing Whitespaces bzw. multiple Spaces nach dem Scheme werden robust normalisiert (z. B. `bearer <token>`, `  BeArEr    <token>  `).
  - Token-Match bleibt strikt exakt (kein Prefix-Match, keine zusätzlichen Token-Segmente); ohne/mit falschem Token → `401 unauthorized`.
- **Timeout-Handling verbessert:**
  - `ANALYZE_DEFAULT_TIMEOUT_SECONDS` (Default 15)
  - `ANALYZE_MAX_TIMEOUT_SECONDS` (Default 45)
  - Request-Feld `timeout_seconds` erlaubt, validiert (endliche Zahl `> 0`, d. h. Reject von `nan`/`inf`) und auf Max gecappt.
- **Validierung Intelligence-Mode:**
  - Input wird vor der Prüfung getrimmt und case-insensitive normalisiert (z. B. `"  ExTenDeD  "` → `extended`).
  - Zulässig: `basic | extended | risk`
  - Ungültig → `400 bad_request`.
- **Explizites Timeout-Mapping:**
  - `TimeoutError` → `504 timeout`.
- **JSON-/Body-Edgecase-Mapping vereinheitlicht (BL-18.wp2):**
  - Invalides UTF-8 im JSON-Body wird deterministisch als `400 bad_request` behandelt (statt internem 500-Pfad).
  - JSON-Bodys, die kein Objekt sind (z. B. Array/String), werden deterministisch als `400 bad_request` zurückgewiesen.
- **Request-ID-Korrelation für API-Debugging:**
  - `POST /analyze` übernimmt die **erste gültige** ID aus `X-Request-Id`/`X_Request_Id` (primär) oder `X-Correlation-Id`/`X_Correlation_Id` (Fallback) und spiegelt sie in Antwort-Header `X-Request-Id` sowie JSON-Feld `request_id`.
  - Leere/whitespace-only IDs, IDs mit eingebettetem Whitespace, IDs mit Steuerzeichen (z. B. Tabs), IDs mit Trennzeichen `,`/`;`, **Non-ASCII-IDs** sowie IDs >128 Zeichen werden verworfen; ist ein primärer Request-Header dadurch ungültig, wird deterministisch auf die nächste gültige Correlation-ID zurückgefallen.
  - Ohne mitgelieferte gültige ID erzeugt der Service eine interne Request-ID.
- **Port-ENV-Kompatibilität für lokale Runner:**
  - `src/web_service.py` akzeptiert `PORT` weiterhin als primäre Port-Variable.
  - Falls `PORT` fehlt/leer ist, wird auf `WEB_PORT` zurückgefallen (hilfreich für lokale Wrapper/Agent-Runner, die `WEB_PORT` setzen).
- **Test-Fault-Injection (nur lokal/gezielt):**
  - via `ENABLE_E2E_FAULT_INJECTION=1`
  - Query `__timeout__` erzwingt `504`
  - Query `__internal__` erzwingt `500`

### E2E-Testsetup

- **Lokal:** `tests/test_web_e2e.py`
  - startet Service-Prozess lokal auf freiem Port
  - deckt ab:
    - Health/Version (200)
    - Not Found (404)
    - Auth required (401)
    - Happy Path analyze (200)
    - Invalid mode + non-finite `timeout_seconds` / bad request (400)
    - JSON-/Body-Edgecases (leerer Body, malformed JSON, invalides UTF-8, JSON-Array/String statt Objekt) -> `400 bad_request`
    - Timeout (504)
    - Internal (500)
    - Request-ID-Echo inkl. Fallback auf Correlation-Header (`X-Correlation-Id`/`X_Correlation_Id`), wenn primäre Request-Header (`X-Request-Id`/`X_Request_Id`) leer/whitespace sind oder wegen eingebettetem Whitespace/Steuerzeichen/Trennzeichen (`,`/`;`)/Non-ASCII-Zeichen/Überlänge (`>128`) ungültig werden; ist `X-Request-Id` ungültig, aber `X_Request_Id` gültig, wird deterministisch der gültige Unterstrich-Primärheader gespiegelt (vor Correlation-Fallback)
- **Dev:** `tests/test_web_e2e_dev.py`
  - läuft gegen `DEV_BASE_URL`
  - optional mit `DEV_API_AUTH_TOKEN`
  - deckt mindestens Health/Version/404 + Analyze-Endpunkt ab
- **Script-E2E (lokal):**
  - `tests/test_remote_smoke_script.py`: validiert den dedizierten Remote-Smoke-Runner lokal gegen den gestarteten Service (inkl. kombinierter Base-URL-Normalisierung `"  HTTP://.../HeAlTh/AnAlYzE/  "`, wiederholter Suffix-Ketten wie `.../health/analyze/health/analyze///`, wiederholter Reverse-Suffix-Ketten mit internem Double-Slash wie `.../AnAlYzE//health/analyze/health///`, wiederholter Forward-Suffix-Ketten mit internem Double-Slash wie `.../health//analyze/health/analyze///`, redundanter trailing-Slash-Ketten wie `.../health//analyze//`, getrimmter Header-/Flag-Inputs wie `SMOKE_REQUEST_ID_HEADER="  Correlation  "`, `SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 "`, `SMOKE_ENFORCE_REQUEST_ID_ECHO="  fAlSe  "`, `SMOKE_MODE="  basic  "` und `SMOKE_MODE="  ExTenDeD  "`, getrimmtem Query-Input `SMOKE_QUERY="  __ok__  "`, getrimmten Timeout-Inputs `SMOKE_TIMEOUT_SECONDS="\t2.5\t"`/`CURL_MAX_TIME=" 15 "`, getrimmter Retry-Flags wie `CURL_RETRY_COUNT="\t1\t"`/`CURL_RETRY_DELAY="\t1\t"`, getrimmtem optionalen Bearer-Token `DEV_API_AUTH_TOKEN="\tbl18-token  "`, Tab-umhüllter Inputs (`"\thttp://.../health\t"`, `"\tCorrelation\t"`) sowie Negativfällen für whitespace-only `SMOKE_QUERY`, `SMOKE_QUERY` mit Steuerzeichen, `CURL_RETRY_DELAY=-1`, `SMOKE_ENFORCE_REQUEST_ID_ECHO=2`, eingebettete Whitespaces/Trennzeichen (`,`/`;`) oder Non-ASCII-Zeichen in `SMOKE_REQUEST_ID`, zu lange `SMOKE_REQUEST_ID` (`>128`), ungültige Ports in `DEV_BASE_URL` (`:abc`, `:70000`), `DEV_BASE_URL` mit Userinfo `user:pass@host`, whitespace-only `DEV_API_AUTH_TOKEN`, `DEV_API_AUTH_TOKEN` mit Steuerzeichen und `DEV_API_AUTH_TOKEN` mit eingebettetem Whitespace).
  - `tests/test_remote_stability_script.py`: validiert den Mehrfach-Runner inkl. NDJSON-Report, `STABILITY_STOP_ON_FIRST_FAIL` (inkl. boolescher Alias-Inputs wie `"  TrUe  "`/`"  fAlSe  "`) sowie getrimmter numerischer Flag-Inputs (inkl. Space-/Tab-Varianten wie `" 2 "`, `"\t2\t"`, `" 0 "`).
- **Run-Skript:** `scripts/run_webservice_e2e.sh`
  - führt lokal immer aus (`test_web_e2e.py` + Smoke-/Stability-Script-E2E)
  - dev nur, wenn `DEV_BASE_URL` gesetzt ist

## Ausführung

```bash
# lokal + optional dev
./scripts/run_webservice_e2e.sh

# dev explizit
DEV_BASE_URL="https://<dein-dev-endpoint>" ./scripts/run_webservice_e2e.sh

# falls dev auth aktiv ist
DEV_BASE_URL="https://<dein-dev-endpoint>" DEV_API_AUTH_TOKEN="<token>" ./scripts/run_webservice_e2e.sh
```

## Regression-Minimum (lokal + optional dev)

Für schnelle, reproduzierbare BL-18-Regressionschecks (kleines Zeitbudget) gilt folgende Minimal-Sequenz:

```bash
# lokal: API-E2E + Stability-Runner-E2E (ohne Remote-Smoke-Script-Pfad)
python3 -m pytest -q tests/test_web_e2e.py tests/test_remote_stability_script.py

# optional dev: Basis-E2E gegen DEV-Endpoint
DEV_BASE_URL="https://<dein-dev-endpoint>" python3 -m pytest -q tests/test_web_e2e_dev.py
```

Hinweise:
- Für den vollständigen BL-18-Lauf bleibt `./scripts/run_webservice_e2e.sh` der Standard.
- Das Regression-Minimum ist bewusst klein gehalten und eignet sich als täglicher Schnellcheck vor/zwischen größeren Iterationen.

### Kurz-Nachweis (Update 2026-02-26, Worker B, Regression-Minimum)

- Command:
  - `python3 -m pytest -q tests/test_web_e2e.py tests/test_remote_stability_script.py`
- Ergebnis:
  - Exit `0`, `53 passed`, `5 subtests passed`.

### Kurz-Nachweis (Update 2026-02-26, Worker B, BL-18.wp2 JSON-/Body-Edgecases)

- Command:
  - `python3 -m pytest -q tests/test_web_e2e.py`
- Ergebnis:
  - Exit `0`, `33 passed`, `9 subtests passed`.
  - Neue E2E-Cases sichern deterministisch `400 bad_request` für malformed JSON, invalides UTF-8 und JSON-Body-Typfehler (Array/String statt Objekt) ab.

## BL-18.1 — Remote-API-Smoke-Test (Internet)

Für den dedizierten Erfolgsnachweis über öffentliche Erreichbarkeit (`POST /analyze`) steht ein separates Script bereit:

```bash
DEV_BASE_URL="https://<dein-dev-endpoint>" ./scripts/run_remote_api_smoketest.sh

# optional mit Auth
DEV_BASE_URL="https://<dein-dev-endpoint>" DEV_API_AUTH_TOKEN="<token>" ./scripts/run_remote_api_smoketest.sh
```

Der Check validiert mindestens: HTTP `200`, `ok=true`, `result` vorhanden **und** (default) Request-ID-Echo (`X-Request-Id` Header + JSON-Feld `request_id` entsprechen der gesendeten `SMOKE_REQUEST_ID`).
Bei grouped API-Responses enthält das Smoke-Artefakt (`result_keys`) auf Top-Level erwartungsgemäss die Keys `status` und `data`.

### Reproduzierbarkeit / Artefakt-Ausgabe

`run_remote_api_smoketest.sh` unterstützt strukturierte Ausgabe als JSON-Artefakt:

```bash
DEV_BASE_URL="https://<dein-dev-endpoint>" \
SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke.json" \
./scripts/run_remote_api_smoketest.sh
```

Wichtige Optionen:
- `DEV_BASE_URL`: muss mit `http://` oder `https://` starten (Groß-/Kleinschreibung im Schema wird akzeptiert, z. B. `HTTP://`); führende/trailing Whitespaces sowie Suffixe `/health` oder `/analyze` (auch verkettet, case-insensitive und in gemischter Reihenfolge wie `/analyze/health`) werden automatisch auf die Service-Basis normalisiert.
- `DEV_BASE_URL`: darf keine eingebetteten Whitespaces/Steuerzeichen enthalten (z. B. `http://.../hea lth`), sonst fail-fast `exit 2` mit klarer CLI-Fehlermeldung.
- `DEV_BASE_URL`: darf keine Query-/Fragment-Komponenten enthalten (`?foo=bar`, `#frag`), damit der `/analyze`-Zielpfad reproduzierbar bleibt.
- `DEV_BASE_URL`: darf keine Userinfo (`user:pass@host`) enthalten, um versehentliche Credential-Leaks in Runbooks/Logs zu verhindern.
- `DEV_BASE_URL`: muss nach Normalisierung eine gültige Host/Port-Kombination enthalten; nicht-numerische bzw. out-of-range Ports (`:abc`, `:70000`) werden fail-fast mit `exit 2` zurückgewiesen.
- `SMOKE_QUERY`: wird vor dem Request getrimmt, darf nicht leer sein und keine Steuerzeichen enthalten; whitespace-only/Control-Char-Werte werden fail-fast mit `exit 2` abgewiesen, damit der Smoke nicht erst im API-Pfad mit `400` scheitert.
- `DEV_API_AUTH_TOKEN` (optional): wird vor dem Request getrimmt; whitespace-only Werte, Tokens mit eingebettetem Whitespace **und** Tokens mit Steuerzeichen werden fail-fast mit `exit 2` abgewiesen, damit Auth-Fehlersuchen bei Copy/Paste-Inputs reproduzierbar bleiben.
- `SMOKE_TIMEOUT_SECONDS` / `CURL_MAX_TIME`: müssen endliche Zahlen `> 0` sein, werden vor der Validierung getrimmt und `CURL_MAX_TIME` muss zusätzlich `>= SMOKE_TIMEOUT_SECONDS` sein (früher, klarer `exit 2` bei Fehlwerten, inkl. Reject von `nan`/`inf` sowie inkonsistenten Timeout-Kombinationen).
- `CURL_RETRY_COUNT` / `CURL_RETRY_DELAY`: robuste Wiederholungen bei transienten Netzwerkfehlern; müssen Ganzzahlen `>= 0` sein und werden vor der Validierung getrimmt.
- `SMOKE_REQUEST_ID`: optionale korrelierbare Request-ID (z. B. für Logsuche). Eigene Werte werden vor dem Request getrimmt, müssen ASCII-only sein, dürfen keine eingebetteten Whitespaces, keine Steuerzeichen und keine Trennzeichen (`,`/`;`) enthalten und dürfen maximal 128 Zeichen enthalten (sonst `exit 2`); wenn leer/nicht gesetzt, generiert der Runner automatisch eine eindeutige Default-ID (`bl18-<epoch>-<uuid-suffix>`).
- `SMOKE_REQUEST_ID_HEADER` (`request|correlation|request-id|correlation-id|x-request-id|x-correlation-id|request_id|correlation_id|x_request_id|x_correlation_id`, default `request`): wird vor Validierung getrimmt und case-insensitive normalisiert; whitespace-only Werte, eingebettete Whitespaces und Steuerzeichen werden fail-fast mit `exit 2` zurückgewiesen. Header-Namen werden als Alias akzeptiert (`request`/`x-request-id`→`X-Request-Id`, `request-id`→`Request-Id`, `request_id`→`Request_Id`, `x_request_id`→`X_Request_Id`, `correlation`/`x-correlation-id`→`X-Correlation-Id`, `correlation-id`→`Correlation-Id`, `correlation_id`→`Correlation_Id`, `x_correlation_id`→`X_Correlation_Id`) und steuern, über welchen Header die Request-ID gesendet wird; der JSON-Report enthält dazu `request_id_header_name`.
- `SMOKE_ENFORCE_REQUEST_ID_ECHO` (`1|0|true|false|yes|no|on|off`, default `1`): wird vor Validierung getrimmt, robust auf `1|0` normalisiert und steuert die Echo-Prüfung für Header + JSON (`request_id`).
- `SMOKE_MODE`: reproduzierbarer Request-Modus (`basic|extended|risk`), wird vor der Validierung getrimmt und case-insensitive normalisiert (z. B. `"  ExTenDeD  "` → `extended`).
- `SMOKE_OUTPUT_JSON` (optional): wird vor der Verwendung getrimmt; whitespace-only Pfade (nach Trim leer), Pfade mit Steuerzeichen, Verzeichnisziele sowie Pfade mit Datei-Elternpfad (Parent ist kein Verzeichnis) werden fail-fast mit `exit 2` abgewiesen, damit die Artefakt-Ausgabe robust und konsistent bleibt (inkl. Curl-Fehlpfad-Report).

### Stabilitäts-/Abnahme-Lauf (mehrere Requests)

Für kurze Stabilitätschecks (z. B. vor Abnahme oder nach Deploy) gibt es einen Mehrfach-Runner:

```bash
DEV_BASE_URL="https://<dein-dev-endpoint>" \
DEV_API_AUTH_TOKEN="<token>" \
STABILITY_RUNS=6 \
STABILITY_INTERVAL_SECONDS=15 \
STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability.ndjson" \
./scripts/run_remote_api_stability_check.sh
```

Der Runner:
- führt den Remote-Smoke-Test mehrfach aus,
- schreibt pro Lauf eine NDJSON-Zeile,
- unterstützt optionales Fail-Fast via `STABILITY_STOP_ON_FIRST_FAIL=1` (akzeptiert `0|1|true|false|yes|no|on|off`, wird vor Validierung getrimmt und auf `0|1` normalisiert),
- trimmt numerische Runner-Flags (`STABILITY_RUNS`, `STABILITY_INTERVAL_SECONDS`, `STABILITY_MAX_FAILURES`) vor der Validierung für robuste Env-Inputs,
- trimmt `STABILITY_REPORT_PATH` vor der Nutzung, erstellt fehlende Verzeichnis-Elternpfade automatisch und weist whitespace-only, Control-Char-, Verzeichnis-Pfade sowie Pfade mit Datei-Elternpfad (Parent ist kein Verzeichnis) fail-fast mit `exit 2` zurück,
- erlaubt für Tests/Debug ein optionales Script-Override via `STABILITY_SMOKE_SCRIPT=/pfad/zu/run_remote_api_smoketest.sh`, trimmt diesen Pfad vor Nutzung, löst relative Overrides robust gegen `REPO_ROOT` auf und weist whitespace-only/Control-Char-Overrides sowie Nicht-Datei-Pfade (z. B. Verzeichnisse) fail-fast mit `exit 2` zurück,
- zählt fehlende/leer gebliebene Smoke-JSON-Artefakte **und** Reports mit `status!=pass` als Fehlrun (auch wenn das Smoke-Script `rc=0` liefert),
- bricht mit Exit `1` ab, wenn `fail_count > STABILITY_MAX_FAILURES`.

### CI-Hook (optional)

Der Deploy-Workflow kann nach dem ECS-Rollout zusätzlich einen optionalen `/analyze`-Smoke-Test ausführen:

- Basis-URL via `SERVICE_BASE_URL` (oder Fallback aus `SERVICE_HEALTH_URL` ohne `/health`)
- optionales Bearer-Token via Secret `SERVICE_API_AUTH_TOKEN`

Damit entstehen reproduzierbare CI-Nachweise für BL-18.1, ohne den Deploy zu blockieren, falls die Analyze-URL noch nicht konfiguriert ist.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Double-Slash-Pfad-Normalisierung (`//health//`, `//analyze//`) + Real-Run, Iteration 48)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="51347" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:51347/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772122638  " SMOKE_REQUEST_ID_HEADER="  request-id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  TrUe  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772122638.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:51347/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  x_correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  off  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL="  no  " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-48/bl18.1-remote-stability-local-worker-1-10m-1772122638.ndjson" ./scripts/run_remote_api_stability_check.sh`
  - API-Realcheck Double-Slash-Pfade: `GET //health//?probe=double-slash` und `POST //analyze//?trace=double-slash` inkl. Request-ID-Echo-Validierung → `artifacts/bl18.1-double-slash-path-normalization-worker-1-10m-1772122638.json`.
- Ergebnis:
  - E2E-Suite: Exit `0`, `124 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden (`request_id_header_name=Request-Id`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`request_id_header_name=X_Correlation_Id`, `request_id_echo_enforced=false`).
  - API-Double-Slash-Normalisierung greift reproduzierbar: `//health//?probe=...` und `//analyze//?trace=...` liefern `200` und spiegeln die gesetzte Request-ID konsistent in Header+JSON.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772122638.json`, `artifacts/worker-1-10m/iteration-48/bl18.1-remote-stability-local-worker-1-10m-1772122638.ndjson`, `artifacts/bl18.1-double-slash-path-normalization-worker-1-10m-1772122638.json`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772122638.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Pfad-Normalisierung (`/analyze/` + Query tolerant), Iteration 47)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="38443" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:38443/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772121986  " SMOKE_REQUEST_ID_HEADER="  correlation-id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  on  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772121986.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:38443/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  x_request_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  No  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL="  off  " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-47/bl18.1-remote-stability-local-worker-1-10m-1772121986.ndjson" ./scripts/run_remote_api_stability_check.sh`
  - API-Realcheck Pfad-Normalisierung: `GET /health/?probe=1` und `POST /analyze/?trace=path-normalization` inkl. Request-ID-Echo-Validierung → `artifacts/bl18.1-path-normalization-worker-1-10m-1772121986.json`.
- Ergebnis:
  - E2E-Suite: Exit `0`, `122 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden (`request_id_header_name=Correlation-Id`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`request_id_header_name=X_Request_Id`, `request_id_echo_enforced=false`).
  - API-Pfad-Normalisierung greift reproduzierbar: `/health/?probe=1` und `/analyze/?trace=...` liefern `200` und spiegeln die gesetzte Request-ID konsistent in Header+JSON.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772121986.json`, `artifacts/worker-1-10m/iteration-47/bl18.1-remote-stability-local-worker-1-10m-1772121986.ndjson`, `artifacts/bl18.1-path-normalization-worker-1-10m-1772121986.json`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772121986.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, `request_id`-Smoke + `x_correlation_id`-Stabilität, Iteration 46)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="40793" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:40793/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  request_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  YeS  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772121276.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:40793/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  x_correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  off  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL="  No  " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-46/bl18.1-remote-stability-local-worker-1-10m-1772121276.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `120 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden (`request_id_header_name=Request_Id`, `request_id_echo_enforced=true`).
  - Default-ID-Guard weiter bestätigt: ohne gesetztes `SMOKE_REQUEST_ID` wurde automatisch `bl18-1772121276-ee1f0ddd1e` erzeugt und konsistent in Header+JSON gespiegelt.
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`request_id_header_name=X_Correlation_Id`, `request_id_echo_enforced=false`).
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772121276.json`, `artifacts/worker-1-10m/iteration-46/bl18.1-remote-stability-local-worker-1-10m-1772121276.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772121276.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, auto-generierte Default-`SMOKE_REQUEST_ID` + Real-Run, Iteration 45)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="41065" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:41065/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request-id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  TrUe  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772120889.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:41065/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  FaLsE  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL="  fAlSe  " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-45/bl18.1-remote-stability-local-worker-1-10m-1772120889.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `120 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden (`request_id_header_name=Request-Id`).
  - Default-ID-Guard greift reproduzierbar: ohne gesetztes `SMOKE_REQUEST_ID` wird automatisch `bl18-1772120889-12623a16bb` generiert und in Header+JSON korrekt gespiegelt.
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`request_id_header_name=Correlation_Id`).
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772120889.json`, `artifacts/worker-1-10m/iteration-45/bl18.1-remote-stability-local-worker-1-10m-1772120889.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772120889.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, echte Short-Alias-Header-Sendung (`Request-Id`/`Correlation_Id`) + Real-Run, Iteration 44)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="40243" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:40243/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772120287  " SMOKE_REQUEST_ID_HEADER="  request-id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  TrUe  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772120287.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:40243/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  FaLsE  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL="  fAlSe  " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-44/bl18.1-remote-stability-local-worker-1-10m-1772120287.ndjson" ./scripts/run_remote_api_stability_check.sh`
  - API-Realcheck Short-Underscore-Aliasse: Request mit `Request_Id="bl18-short-underscore-primary"` (primär) sowie Fallback-Request mit ungültigem primären Request-Alias + `Correlation_Id="bl18-short-underscore-correlation-fallback"` → Report `artifacts/bl18.1-request-id-short-underscore-alias-worker-1-10m-1772120287.json`.
- Ergebnis:
  - E2E-Suite: Exit `0`, `119 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden (`request_id_header_name=Request-Id`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`request_id_header_name=Correlation_Id`).
  - Short-Alias-API-Guard greift reproduzierbar: `Request_Id` wird primär gespiegelt; bei ungültigem primären Request-Alias gewinnt deterministisch `Correlation_Id`.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772120287.json`, `artifacts/worker-1-10m/iteration-44/bl18.1-remote-stability-local-worker-1-10m-1772120287.ndjson`, `artifacts/bl18.1-request-id-short-underscore-alias-worker-1-10m-1772120287.json`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772120287.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Short-Request-ID-Header-Aliasse (`Request-Id`/`Correlation-Id`) + Real-Run, Iteration 43)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="35627" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:35627/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772119525  " SMOKE_REQUEST_ID_HEADER="  request-id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  TrUe  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772119525.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:35627/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  FaLsE  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL="  fAlSe  " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-43/bl18.1-remote-stability-local-worker-1-10m-1772119525.ndjson" ./scripts/run_remote_api_stability_check.sh`
  - API-Realcheck Short-Aliasse: Request mit `Request-Id="bl18-short-primary-alias"` (primär) sowie Fallback-Request mit ungültigem primären Request-Alias + `Correlation-Id="bl18-short-correlation-fallback"` → Report `artifacts/bl18.1-request-id-short-alias-worker-1-10m-1772119525.json`.
- Ergebnis:
  - E2E-Suite: Exit `0`, `115 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden (`request_id_header_name=X-Request-Id`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`request_id_header_name=X_Correlation_Id`).
  - API-Short-Alias-Guard greift reproduzierbar: `Request-Id` wird primär gespiegelt; bei ungültigem primären Request-Alias gewinnt deterministisch `Correlation-Id`.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772119525.json`, `artifacts/worker-1-10m/iteration-43/bl18.1-remote-stability-local-worker-1-10m-1772119525.ndjson`, `artifacts/bl18.1-request-id-short-alias-worker-1-10m-1772119525.json`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772119525.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A-10m, ASCII-Only Request-ID-Guard + Real-Run, Iteration 42)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="38215" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:38215/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-a-10m-run-1772119023  " SMOKE_REQUEST_ID_HEADER="  request-id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  TrUe  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-10m-1772119023.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:38215/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  FaLsE  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL="  fAlSe  " STABILITY_REPORT_PATH="artifacts/worker-a-10m/iteration-42/bl18.1-remote-stability-local-worker-a-10m-1772119023.ndjson" ./scripts/run_remote_api_stability_check.sh`
  - API-Fallback-Realcheck Non-ASCII: Request mit `X-Request-Id="bl18-é-bad-id"` + `X-Correlation-Id="bl18-e2e-correlation-nonascii-fallback"` → Response spiegelt deterministisch Correlation-ID (`artifacts/bl18.1-request-id-nonascii-fallback-worker-a-10m-1772119039.json`).
- Ergebnis:
  - E2E-Suite: Exit `0`, `113 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden (`request_id_header_name=X-Request-Id`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`request_id_header_name=X_Correlation_Id`).
  - Neuer Guard greift reproduzierbar: Non-ASCII `X-Request-Id` wird verworfen, Correlation-ID gewinnt in Header + JSON.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-a-10m-1772119023.json`, `artifacts/worker-a-10m/iteration-42/bl18.1-remote-stability-local-worker-a-10m-1772119023.ndjson`, `artifacts/bl18.1-request-id-nonascii-fallback-worker-a-10m-1772119039.json`.
  - Server-Logs: `artifacts/bl18.1-worker-a-10m-server-1772119023.log`, `artifacts/bl18.1-worker-a-10m-server-nonascii-1772119039.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Bool-Flag-Aliasse für Echo/Stop-on-first-fail + Real-Run, Iteration 41)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="39977" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39977/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772118464  " SMOKE_REQUEST_ID_HEADER="  request-id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  TrUe  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772118464.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39977/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO="  FaLsE  " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL="  fAlSe  " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-41/bl18.1-remote-stability-local-worker-1-10m-1772118464.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `111 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; boolescher Echo-Flag-Alias (`SMOKE_ENFORCE_REQUEST_ID_ECHO="TrUe"`) wird robust normalisiert und weiterhin strikt als Echo-Check durchgesetzt (`request_id_echo_enforced=true`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; boolesche Aliasse (`SMOKE_ENFORCE_REQUEST_ID_ECHO="FaLsE"`, `STABILITY_STOP_ON_FIRST_FAIL="fAlSe"`) werden robust auf `0` normalisiert (`request_id_echo_enforced=false` in allen NDJSON-Runs) und der Runner bleibt erwartungsgemäß ohne Early-Stop.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772118464.json`, `artifacts/worker-1-10m/iteration-41/bl18.1-remote-stability-local-worker-1-10m-1772118464.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772118464.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Short-Alias-Support für `SMOKE_REQUEST_ID_HEADER` + Real-Run, Iteration 40)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="50541" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:50541/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772117788  " SMOKE_REQUEST_ID_HEADER="  request-id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772117788.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:50541/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-40/bl18.1-remote-stability-local-worker-1-10m-1772117788.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `108 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; Short-Alias `request-id` wird robust auf Request-Mode normalisiert und real als `X-Request-Id` gesendet (`request_id_header_name=X-Request-Id`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Short-Alias `correlation_id` wird robust auf Correlation-Mode normalisiert und real als `X_Correlation_Id` gesendet (`request_id_header_name=X_Correlation_Id`).
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772117788.json`, `artifacts/worker-1-10m/iteration-40/bl18.1-remote-stability-local-worker-1-10m-1772117788.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772117788.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Request-ID-Delimiter-Guard + Real-Run, Iteration 39)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="55187" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:55187/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772117243  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772117243.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:55187/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-39/bl18.1-remote-stability-local-worker-1-10m-1772117243.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `106 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; `request`-Header-Mode bleibt stabil (`request_id_header_name=X-Request-Id`) und Echo Header+JSON konsistent.
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Runs 1..3 alle `status=pass`.
  - API-Guard: neuer E2E-Fall + Realcheck bestätigen, dass `X-Request-Id` mit Trennzeichen (`,`/`;`) als ungültig verworfen wird und deterministisch `X-Correlation-Id` in Header+JSON gespiegelt wird.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772117243.json`, `artifacts/worker-1-10m/iteration-39/bl18.1-remote-stability-local-worker-1-10m-1772117243.ndjson`, `artifacts/bl18.1-request-id-delimiter-fallback-worker-1-10m-1772117243.json`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772117243.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, lowercase `_`-Request-Alias E2E-Abdeckung + Real-Run, Iteration 38)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="35647" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:35647/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772116556  " SMOKE_REQUEST_ID_HEADER="  x_request_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772116556.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:35647/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  x_request_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-38/bl18.1-remote-stability-local-worker-1-10m-1772116556.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `104 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; lowercase `_`-Request-Alias (`x_request_id`) wird robust akzeptiert, real als `X_Request_Id` gesendet und konsistent in Header+JSON gespiegelt (`request_id_header_name=X_Request_Id`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Runs 1..3 alle `status=pass`.
  - API-Guard: neue E2E-Fälle sichern sowohl CLI- als auch API-seitig ab, dass lowercase Unterstrich-Primärheader (`x_request_id`) robust akzeptiert bleiben.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772116556.json`, `artifacts/worker-1-10m/iteration-38/bl18.1-remote-stability-local-worker-1-10m-1772116556.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772116556.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, lowercase `_`-Correlation-Alias + invalides `_`-Primärheader-Fallback, Iteration 37)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="39849" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39849/health//analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  x_correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772115947.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39849/health//analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  x_correlation_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-37/bl18.1-remote-stability-local-worker-1-10m-1772115947.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `102 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; lowercase `_`-Correlation-Alias (`x_correlation_id`) wird robust akzeptiert, real als `X_Correlation_Id` gesendet und konsistent in Header+JSON gespiegelt (`request_id_header_name=X_Correlation_Id`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Runs 1..3 alle `status=pass`.
  - API-Guard: neuer E2E-Fall bestätigt explizit die Fallback-Kette, wenn `X-Request-Id` **und** `X_Request_Id` ungültig sind; danach gewinnt deterministisch `X-Correlation-Id`.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772115947.json`, `artifacts/worker-1-10m/iteration-37/bl18.1-remote-stability-local-worker-1-10m-1772115947.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772115947.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, lowercase `_`-Header-Alias-Real-Run, Iteration 36)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="50175" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:50175/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  BaSiC  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772115249  " SMOKE_REQUEST_ID_HEADER="  x_request_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772115249.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:50175/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  BaSiC  " SMOKE_REQUEST_ID_HEADER="  x_request_id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-36/bl18.1-remote-stability-local-worker-1-10m-1772115249.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `100 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; lowercase `_`-Alias (`x_request_id`) wird robust akzeptiert, real als `X_Request_Id` gesendet und konsistent in Header+JSON gespiegelt (`request_id_header_name=X_Request_Id`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Runs 1..3 alle `status=pass`.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772115249.json`, `artifacts/worker-1-10m/iteration-36/bl18.1-remote-stability-local-worker-1-10m-1772115249.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772115249.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Primärheader-Priorität `X_Request_Id` + Correlation-`_`-Real-Run, Iteration 35)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="59511" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59511/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772114701  " SMOKE_REQUEST_ID_HEADER="  X_Correlation_Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772114701.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59511/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  X_Correlation_Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-35/bl18.1-remote-stability-local-worker-1-10m-1772114701.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `100 passed`.
  - API-Guard: neuer E2E-Fall bestätigt Prioritätslogik, dass bei ungültigem `X-Request-Id` ein gültiges `X_Request_Id` deterministisch vor Correlation-Fallback gewinnt.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; `X_Correlation_Id` wird real gesendet und Echo Header+JSON bleibt konsistent (`request_id_header_name=X_Correlation_Id`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Runs 1..3 alle `status=pass`.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772114701.json`, `artifacts/worker-1-10m/iteration-35/bl18.1-remote-stability-local-worker-1-10m-1772114701.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772114701.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, echte `_`-Header im Smoke + API-Akzeptanz `_`-Request-ID-Header, Iteration 34)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="57937" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57937/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772114297  " SMOKE_REQUEST_ID_HEADER="  X_Request_Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772114297.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57937/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  X_Request_Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-34/bl18.1-remote-stability-local-worker-1-10m-1772114297.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `99 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; Unterstrich-Header wird jetzt real gesendet und im Report explizit ausgewiesen (`request_id_header_name=X_Request_Id`), Echo Header+JSON konsistent.
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Runs 1..3 alle `status=pass` mit `request_id_header_name=X_Request_Id`.
  - API-Guards: Service akzeptiert jetzt primäre/fallback Request-ID-Header auch in `_`-Variante (`X_Request_Id`/`X_Correlation_Id`), lokal E2E-abgesichert.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772114297.json`, `artifacts/worker-1-10m/iteration-34/bl18.1-remote-stability-local-worker-1-10m-1772114297.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772114297.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A, case-insensitive `intelligence_mode` + 3x Stabilität, Iteration 33)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="48855" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48855/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID="  bl18-worker-a-run-1772113545  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772113545.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48855/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 3 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-a/iteration-33/bl18.1-remote-stability-local-worker-a-1772113545.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `97 passed`.
  - API: `intelligence_mode` wird jetzt getrimmt + case-insensitive normalisiert (z. B. `"  ExTenDeD  "`), wodurch robuste Client-Inputs ohne Verhaltensbruch akzeptiert werden.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; Header-Mode `correlation` weiterhin konsistent (`request_id_header_source=correlation`, Echo Header+JSON identisch).
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Runs 1..3 alle `status=pass`.
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-a-1772113545.json`, `artifacts/worker-a/iteration-33/bl18.1-remote-stability-local-worker-a-1772113545.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-a-server-1772113545.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Fail-fast-Guards für `SMOKE_REQUEST_ID_HEADER` (whitespace/control) + 5x Stabilität, Iteration 32)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="43071" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:43071/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772112911  " SMOKE_REQUEST_ID_HEADER="  X_Request_Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772112911.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:43071/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  X_Correlation_Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-32/bl18.1-remote-stability-local-worker-1-10m-1772112911.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `96 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; Alias `X_Request_Id` wird weiter robust auf `request` normalisiert (`request_id_header_source=request`, Echo Header+JSON konsistent).
  - Stabilität: `pass=5`, `fail=0`, Exit `0`; Alias `X_Correlation_Id` wird weiter robust auf `correlation` normalisiert (Runs 1..5 alle `status=pass`).
  - Neue Guard-Abdeckung: `SMOKE_REQUEST_ID_HEADER` rejectet jetzt whitespace-only Inputs, eingebettete Whitespaces und Steuerzeichen fail-fast mit `exit 2` (lokal über `tests/test_remote_smoke_script.py` abgesichert).
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772112911.json`, `artifacts/worker-1-10m/iteration-32/bl18.1-remote-stability-local-worker-1-10m-1772112911.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772112911.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Unterstrich-Header-Aliasse für `SMOKE_REQUEST_ID_HEADER` + 5x Stabilität, Iteration 31)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="48953" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48953/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772112297  " SMOKE_REQUEST_ID_HEADER="  X_Request_Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772112297.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48953/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  X_Correlation_Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-31/bl18.1-remote-stability-local-worker-1-10m-1772112297.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `93 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; Unterstrich-Alias `X_Request_Id` wird auf `request` normalisiert (`request_id_header_source=request`, Echo Header+JSON konsistent).
  - Stabilität: `pass=5`, `fail=0`, Exit `0`; Unterstrich-Alias `X_Correlation_Id` wird auf `correlation` normalisiert (Runs 1..5 alle `status=pass`).
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772112297.json`, `artifacts/worker-1-10m/iteration-31/bl18.1-remote-stability-local-worker-1-10m-1772112297.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772112297.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Header-Alias-Normalisierung für `SMOKE_REQUEST_ID_HEADER` + 5x Stabilität, Iteration 30)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="56051" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:56051/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772111763  " SMOKE_REQUEST_ID_HEADER="  X-Request-Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772111763.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:56051/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  X-Correlation-Id  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-30/bl18.1-remote-stability-local-worker-1-10m-1772111763.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `91 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden; Header-Alias `X-Request-Id` wird auf `request` normalisiert (`request_id_header_source=request`, Echo Header+JSON konsistent).
  - Stabilität: `pass=5`, `fail=0`, Exit `0`; Header-Alias `X-Correlation-Id` wird auf `correlation` normalisiert (Runs 1..5 alle `status=pass`).
  - Evidenz: `artifacts/bl18.1-smoke-local-worker-1-10m-1772111763.json`, `artifacts/worker-1-10m/iteration-30/bl18.1-remote-stability-local-worker-1-10m-1772111763.ndjson`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772111763.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, API-Guard für `X-Request-Id`-Überlänge + 5x Stabilität, Iteration 29)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="53097" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:53097/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772111118  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772111118.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:53097/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-29/bl18.1-remote-stability-local-worker-1-10m-1772111118.ndjson" ./scripts/run_remote_api_stability_check.sh`
  - Verifikations-Call für den neuen API-Guard: `POST /analyze` mit `X-Request-Id`-Länge `129` + `X-Correlation-Id: "bl18-correlation-length-fallback-real"`
- Ergebnis:
  - E2E-Suite: Exit `0`, `89 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772111118.json`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/worker-1-10m/iteration-29/bl18.1-remote-stability-local-worker-1-10m-1772111118.ndjson`; Runs 1..5 alle `status=pass`).
  - API-Guard real verifiziert: `X-Request-Id` mit Überlänge (`129`) wird verworfen, Fallback auf `X-Correlation-Id` greift konsistent in Header+JSON (`artifacts/bl18.1-request-id-length-fallback-worker-1-10m-1772111118.json`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772111118.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, API-Guard für eingebetteten Whitespace in `X-Request-Id` + 5x Stabilität, Iteration 28)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="18180" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="http://127.0.0.1:18180/health/analyze/" DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_MODE=" ExTenDeD " SMOKE_QUERY="  St. Leonhard-Strasse 40, St. Gallen  " SMOKE_REQUEST_ID_HEADER=" request " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772110559.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18180/health/analyze/" DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_MODE=" ExTenDeD " SMOKE_QUERY="  St. Leonhard-Strasse 40, St. Gallen  " STABILITY_RUNS="5" STABILITY_INTERVAL_SECONDS="0" STABILITY_MAX_FAILURES="0" STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-28/bl18.1-remote-stability-local-worker-1-10m-1772110559.ndjson" ./scripts/run_remote_api_stability_check.sh`
  - Verifikations-Call für den neuen API-Guard: `POST /analyze` mit `X-Request-Id: "bl18 bad-id"` + `X-Correlation-Id: "bl18-correlation-fallback-real"`
- Ergebnis:
  - E2E-Suite: Exit `0`, `88 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772110559.json`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/worker-1-10m/iteration-28/bl18.1-remote-stability-local-worker-1-10m-1772110559.ndjson`; Runs 1..5 alle `status=pass`).
  - API-Guard real verifiziert: eingebetteter Whitespace in `X-Request-Id` wird verworfen, Fallback auf `X-Correlation-Id` greift konsistent in Header+JSON (`artifacts/bl18.1-request-id-fallback-worker-1-10m-1772110577.json`).
  - Server-Logs: `artifacts/bl18.1-worker-1-10m-server-1772110559.log`, `artifacts/bl18.1-worker-1-10m-requestid-server-1772110577.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A, Timeout-Konsistenz-Guard `CURL_MAX_TIME >= SMOKE_TIMEOUT_SECONDS` + 3x Stabilität, Iteration 28)

- Command:
  - `pytest -q tests/test_remote_smoke_script.py tests/test_remote_stability_script.py`
  - `HOST="127.0.0.1" PORT="38697" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:38697/AnAlYzE//health/analyze/health///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 3 " CURL_MAX_TIME=" 3.5 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772109929.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:38697/health" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_MODE="basic" SMOKE_TIMEOUT_SECONDS="2" CURL_MAX_TIME="4" CURL_RETRY_COUNT="1" CURL_RETRY_DELAY="1" STABILITY_RUNS="3" STABILITY_INTERVAL_SECONDS="1" STABILITY_MAX_FAILURES="0" STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772109929.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - Script-E2E-Tests: Exit `0`, `75 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-1772109929.json`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772109929.ndjson`; Runs 1..3 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-a-server-1772109929.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Auto-Mkdir für fehlende `STABILITY_REPORT_PATH`-Verzeichnisse + 5x Stabilität, Iteration 27)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="50117" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:50117/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772109315  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772109315.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:50117/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/worker-1-10m/iteration-27/bl18.1-remote-stability-local-worker-1-10m-1772109315.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `86 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772109315.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/worker-1-10m/iteration-27/bl18.1-remote-stability-local-worker-1-10m-1772109315.ndjson`; Runs 1..5 alle `status=pass`) bei automatisch erzeugtem, zuvor fehlendem Verzeichnis-Elternpfad.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772109315.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Datei-Elternpfad-Guard für `STABILITY_REPORT_PATH` + 5x Stabilität, Iteration 26)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="48915" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48915/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772108666  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772108666.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48915/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772108666.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `85 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772108666.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772108666.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772108666.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A, Datei-Elternpfad-Guard für `SMOKE_OUTPUT_JSON` + 5x Stabilität, Iteration 25)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="48051" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48051/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772108086  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772108086.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48051/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772108086.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `84 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-1772108086.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772108086.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-a-server-1772108086.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Verzeichnis-Guard für `SMOKE_OUTPUT_JSON` + 5x Stabilität, Iteration 24)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="46225" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:46225/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772107493  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772107493.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:46225/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772107493.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `83 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772107493.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772107493.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772107493.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Verzeichnis-Guard für `STABILITY_REPORT_PATH` + 5x Stabilität, Iteration 23)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="57979" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57979/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772106884  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772106884.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57979/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772106884.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `82 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772106884.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772106884.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772106884.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, REPO_ROOT-Resolve + File-Guard für `STABILITY_SMOKE_SCRIPT` + 5x Stabilität, Iteration 22)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="46943" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:46943/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772106342  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772106342.json" ./scripts/run_remote_api_smoketest.sh`
  - `(cd /tmp/bl18-foreign-1772106342 && DEV_BASE_URL="  HTTP://127.0.0.1:46943/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_SMOKE_SCRIPT="$(printf '  ./scripts/run_remote_api_smoketest.sh\t')" STABILITY_REPORT_PATH="$PWD/artifacts/bl18.1-remote-stability-local-worker-1-10m-1772106342.ndjson" /data/.openclaw/workspace/geo-ranking-ch/scripts/run_remote_api_stability_check.sh)`
- Ergebnis:
  - E2E-Suite: Exit `0`, `81 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772106342.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772106342.ndjson`; Runs 1..5 alle `status=pass`) trotz tab-umhülltem, relativem `STABILITY_SMOKE_SCRIPT`-Override aus fremdem `cwd`.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772106342.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Trim-/Guard für `STABILITY_SMOKE_SCRIPT` + 5x Stabilität, Iteration 21)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="39269" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39269/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772105805  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772105805.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39269/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="$(printf '  bl18-token\t')" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_SMOKE_SCRIPT="$(printf '  ./scripts/run_remote_api_smoketest.sh\t')" STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772105805.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `79 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772105805.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772105805.ndjson`; Runs 1..5 alle `status=pass`) trotz tab-umhülltem `STABILITY_SMOKE_SCRIPT`-Override.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772105805.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Trim-/Guard für `STABILITY_REPORT_PATH` + 5x Stabilität, Iteration 20)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="55227" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:55227/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token\t" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-run-1772105148  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772105148.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:55227/AnAlYzE//health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token\t" SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH=$'  artifacts/bl18.1-remote-stability-local-worker-1-10m-1772105148.ndjson\t' ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `76 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-1-10m-1772105148.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772105148.ndjson`; Runs 1..5 alle `status=pass`) trotz tab-umhülltem `STABILITY_REPORT_PATH`-Input.
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772105148.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A, Whitespace-only-Guard für `SMOKE_OUTPUT_JSON` + 5x Stabilität, Iteration 19)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="47845" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:47845/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772104523  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="  artifacts/bl18.1-smoke-local-worker-a-1772104523.json  " ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:47845/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY="  __ok__  " SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772104523.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `73 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode (`artifacts/bl18.1-smoke-local-worker-a-1772104523.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T11:15:24Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772104523.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-a-server-1772104523.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Embedded-Whitespace-Guard für `DEV_API_AUTH_TOKEN` + 5x Stabilität, Iteration 18)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="38983" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:38983/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-langlauf-1772103860  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="  artifacts/bl18.1-smoke-local-worker-1-10m-1772103860.json  " ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:38983/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772103860.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `72 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode (`artifacts/bl18.1-smoke-local-worker-1-10m-1772103860.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T11:04:21Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772103860.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772103860.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Control-Char-Guard für `SMOKE_OUTPUT_JSON` + 5x Stabilität, Iteration 17)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="57943" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57943/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-langlauf-1772103286  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="  artifacts/bl18.1-smoke-local-worker-1-10m-1772103286.json  " ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57943/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772103286.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `71 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode (`artifacts/bl18.1-smoke-local-worker-1-10m-1772103286.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T10:54:47Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772103286.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772103286.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Trim-Guard für `SMOKE_OUTPUT_JSON` (inkl. Curl-Fehlpfad) + 5x Stabilität, Iteration 16)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="46743" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:46743/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-langlauf-1772102717  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="  artifacts/bl18.1-smoke-local-worker-1-10m-1772102717.json  " ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:46743/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772102717.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `70 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode trotz whitespace-umhülltem `SMOKE_OUTPUT_JSON` (`artifacts/bl18.1-smoke-local-worker-1-10m-1772102717.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T10:45:33Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772102717.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772102717.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A, Embedded-Whitespace-Guard für `SMOKE_REQUEST_ID` + 5x Stabilität, Iteration 15)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="54457" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:40607/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772102261  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772102261.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:40607/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772102261.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `69 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode (`artifacts/bl18.1-smoke-local-worker-a-1772102261.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T10:37:41Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772102261.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-a-server-1772102261.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Control-Char-Guard für `SMOKE_QUERY` + 5x Stabilität, Iteration 14)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="43251" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:43251/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-langlauf-1772101465  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772101465.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:43251/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  __ok__  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772101465.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `68 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode (`artifacts/bl18.1-smoke-local-worker-1-10m-1772101465.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T10:24:44Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772101465.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772101465.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1-10m, Trim-/Empty-Guard für `SMOKE_QUERY` + 5x Stabilität, Iteration 13)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="41271" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:41271/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  \t__ok__\t  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-1-10m-langlauf-1772101014  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-10m-1772101014.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:41271/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY=$'  \t__ok__\t  ' SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-10m-1772101014.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `67 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode trotz getrimmtem `SMOKE_QUERY` mit Tab/Spaces (`artifacts/bl18.1-smoke-local-worker-1-10m-1772101014.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T10:16:55Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-1-10m-1772101014.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-1-10m-server-1772101014.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker B, Control-Char-Guard für `DEV_API_AUTH_TOKEN` + 5x Stabilität, Iteration 12)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" WEB_PORT="57025" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" ENABLE_E2E_FAULT_INJECTION="1" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57025/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY="__ok__" SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772100694  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-1772100694.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57025/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token  " SMOKE_QUERY="__ok__" SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-1772100694.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `65 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode trotz Space-umhülltem `DEV_API_AUTH_TOKEN` (`artifacts/bl18.1-smoke-local-worker-b-1772100694.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T10:11:34Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-1772100694.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-b-server-1772100694.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A, Trim-Guard für `DEV_API_AUTH_TOKEN` + 5x Stabilität, Iteration 11)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `HOST="127.0.0.1" PORT="59917" API_AUTH_TOKEN="bl18-token" PYTHONPATH="$PWD" python3 -m src.web_service` (isolierter lokaler Service-Start)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59917/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token\t" SMOKE_QUERY="__ok__" SMOKE_MODE="  rIsK  " SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772100333  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772100333.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59917/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="  bl18-token\t" SMOKE_QUERY="__ok__" SMOKE_MODE="  rIsK  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772100333.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `64 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode trotz Space/Tab-umhülltem `DEV_API_AUTH_TOKEN` (`artifacts/bl18.1-smoke-local-worker-a-1772100333.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T10:05:33Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772100333.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-a-server-1772100333.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker C, WEB_PORT-Fallback + Request-Header-Mode + 5x Stabilität, Iteration 10)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `env -u PORT HOST="127.0.0.1" WEB_PORT="42503" API_AUTH_TOKEN="bl18-token" python3 -m src.web_service` (isolierter lokaler Service-Start; Validierung des `WEB_PORT`-Fallbacks bei explizit entferntem `PORT`)
  - `DEV_BASE_URL="  HTTP://127.0.0.1:42503/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772099864  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-1772099864.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:42503/health/analyze//health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_MODE="  RiSk  " SMOKE_REQUEST_ID_HEADER="  request  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.75 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-1772099864.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `62 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten `request`-Header-Mode trotz Space-umhüllter Inputs und kombinierter Suffix-Kette (`artifacts/bl18.1-smoke-local-worker-c-1772099864.json`, `request_id_header_source=request`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T09:57:54Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-1772099864.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-worker-c-server-1772099864.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Recheck Tab-Trim + kombinierte Suffix-Kette + 5x Stabilität, Iteration 9)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL=$' \tHTTP://127.0.0.1:43577/AnAlYzE//health/analyze/health/analyze///\t ' DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_MODE=$' \tExTenDeD\t ' SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772099418  " SMOKE_REQUEST_ID_HEADER=$' \tCorrelation\t ' SMOKE_ENFORCE_REQUEST_ID_ECHO=$' \t1\t ' SMOKE_TIMEOUT_SECONDS=$'\t2.5\t' CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=$'\t1\t' CURL_RETRY_DELAY=$'\t1\t' SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772099418.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL=$' \tHTTP://127.0.0.1:43577/AnAlYzE//health/analyze/health/analyze///\t ' DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_MODE=$' \tExTenDeD\t ' SMOKE_REQUEST_ID_HEADER=$' \tCorrelation\t ' SMOKE_ENFORCE_REQUEST_ID_ECHO=$' \t1\t ' SMOKE_TIMEOUT_SECONDS=$'\t2.5\t' CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=$'\t1\t' CURL_RETRY_DELAY=$'\t1\t' STABILITY_RUNS="5" STABILITY_INTERVAL_SECONDS="1" STABILITY_MAX_FAILURES="0" STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772099418.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `61 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode trotz Tab-umhüllter Inputs und kombinierter Suffix-Kette (`artifacts/bl18.1-smoke-local-worker-a-1772099418.json`, `request_id_header_source=correlation`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T09:50:18Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772099418.ndjson`; Runs 1..5 alle `status=pass`).
  - Server-Log: `artifacts/bl18.1-service-worker-a-1772099418.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Recheck case-insensitive `SMOKE_MODE` + 5x Stabilität, Iteration 8)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59977/health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772099150  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772099150.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59977/health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_MODE="  ExTenDeD  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772099150.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `61 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode trotz gemischt geschriebenem `SMOKE_MODE="  ExTenDeD  "` (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772099150.json`, `request_id_header_source=correlation`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T09:45:50Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772099150.ndjson`).
  - Server-Log: `artifacts/bl18.1-worker-b-server-1772099150.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker C, Request-ID-Control-Char-Fallback + 5x Stabilität, Iteration 7)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39761/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772098788  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-langlauf-1772098788.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39761/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772098788.ndjson" ./scripts/run_remote_api_stability_check.sh`
  - `python3 -c '<POST /analyze mit X-Request-Id="bl18\tbad-id" + X-Correlation-Id="bl18-correlation-fallback-1772098788"; assert fallback>'` (Artefakt: `artifacts/bl18.1-request-id-control-fallback-worker-c-1772098788.json`)
- Ergebnis:
  - E2E-Suite: Exit `0`, `60 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode (`artifacts/bl18.1-smoke-local-worker-c-langlauf-1772098788.json`, `request_id_header_source=correlation`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T09:39:49Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772098788.ndjson`).
  - API-Guard real verifiziert: bei `X-Request-Id` mit Steuerzeichen (`"bl18\tbad-id"`) fällt `/analyze` deterministisch auf `X-Correlation-Id` zurück; Header+JSON spiegeln konsistent `bl18-correlation-fallback-1772098788` (`artifacts/bl18.1-request-id-control-fallback-worker-c-1772098788.json`, `fallback_applied=true`).
  - Server-Log: `artifacts/bl18.1-worker-c-server-1772098788.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1, Langlauf-Recheck getrimmte Timeout-Inputs + 5x Stabilität, Iteration 6)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59099/health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-1-langlauf-1772098485  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-langlauf-1772098485.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59099/health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_TIMEOUT_SECONDS=" 2.5 " CURL_MAX_TIME=" 15 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-langlauf-1772098485.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `59 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode trotz Space-umhüllter Timeout-Inputs (`SMOKE_TIMEOUT_SECONDS=" 2.5 "`, `CURL_MAX_TIME=" 15 "`) (`artifacts/bl18.1-smoke-local-worker-1-langlauf-1772098485.json`, `request_id_header_source=correlation`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T09:34:45Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` mit getrimmten Timeout-/Retry-/Stability-Flags (`artifacts/bl18.1-remote-stability-local-worker-1-langlauf-1772098485.ndjson`).
  - Server-Log: `artifacts/bl18.1-worker-1-server-1772098485.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Recheck getrimmte Retry-Flags + getrimmter SMOKE_MODE, Iteration 5)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48757/health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772101928  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772101928.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:48757/health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " CURL_RETRY_COUNT=" 1 " CURL_RETRY_DELAY=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772101928.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `58 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode trotz Space-umhüllter Retry-Flags (`CURL_RETRY_COUNT=" 1 "`, `CURL_RETRY_DELAY=" 1 "`) (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772101928.json`, `request_id_header_source=correlation`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T09:28:50Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` mit getrimmten numerischen Stability-Flags + getrimmten Retry-Flags (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772101928.ndjson`).
  - Server-Log: `artifacts/bl18.1-worker-b-server-1772101928.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Recheck Tab-Whitespace-Trim + 5x Stabilität, Iteration 4)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL=$' \tHTTP://127.0.0.1:46603/analyze//health/analyze/health///\t ' DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772097841  " SMOKE_REQUEST_ID_HEADER=$' \tCorrelation\t ' SMOKE_ENFORCE_REQUEST_ID_ECHO=$' \t1\t ' SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-langlauf-1772097841.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL=$' \tHTTP://127.0.0.1:46603/analyze//health/analyze/health///\t ' DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER=$' \tCorrelation\t ' SMOKE_ENFORCE_REQUEST_ID_ECHO=$' \t1\t ' STABILITY_RUNS=$' \t5\t ' STABILITY_INTERVAL_SECONDS=$' \t0\t ' STABILITY_MAX_FAILURES=$' \t0\t ' STABILITY_STOP_ON_FIRST_FAIL=$' \t0\t ' STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772097841.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `56 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode trotz Tab-umhüllter Inputs (`artifacts/bl18.1-smoke-local-worker-a-langlauf-1772097841.json`, `request_id_header_source=correlation`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T09:24:09Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` mit Tab-umhüllten numerischen Flags (`"\t5\t"`, `"\t0\t"`) und getrimmtem Echo-Flag (`"\t1\t"`) (`artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772097841.ndjson`).
  - Server-Log: `artifacts/bl18.1-worker-a-server-1772097841.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Recheck getrimmtes Echo-Flag + 5x Stabilität, Iteration 3)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59499/health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772097551  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-langlauf-1772097551.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:59499/health/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772097551.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `54 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode mit explizit getrimmtem Echo-Flag (`artifacts/bl18.1-smoke-local-worker-c-langlauf-1772097551.json`, `request_id_header_source=correlation`, `request_id_echo_enforced=true`, `started_at_utc=2026-02-26T09:19:11Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` trotz absichtlich getrimmter numerischer Flags (`" 5 "`, `" 0 "`), getrimmtem Stop-Flag (`" 0 "`) und getrimmtem Echo-Flag (`" 1 "`) (`artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772097551.ndjson`, Run-IDs inkl. PID-Suffix wie `bl18-stability-1-1772097551-73915`).
  - Server-Log: `artifacts/bl18.1-worker-c-server-1772097551.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Recheck getrimmter Correlation-Mode + 5x Stabilität, Iteration 2)

- Command:
  - `python3 -m pytest -q tests/test_web_e2e.py tests/test_remote_smoke_script.py tests/test_remote_stability_script.py`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39243/analyze//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772097377  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772097377.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39243/analyze//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="  Correlation  " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772097377.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `54 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772097377.json`, `request_id_header_source=correlation`, `started_at_utc=2026-02-26T09:16:17Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` trotz absichtlich getrimmter numerischer Flags (`" 5 "`, `" 0 "`) und getrimmtem Stop-Flag (`" 0 "`) (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772097377.ndjson`, Run-IDs inkl. PID-Suffix wie `bl18-stability-1-1772097377-72356`).
  - Server-Log: `artifacts/bl18.1-worker-b-server-1772097377.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker 1, Langlauf-Recheck getrimmte Stability-Flags + 5x Stabilität)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:35179/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-1-langlauf-1772097177  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-1-langlauf-1772097177.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:35179/analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="  Correlation  " STABILITY_RUNS=" 5 " STABILITY_INTERVAL_SECONDS=" 0 " STABILITY_MAX_FAILURES=" 0 " STABILITY_STOP_ON_FIRST_FAIL=" 0 " STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-1-langlauf-1772097177.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `54 passed` (inkl. neuer Stability-E2E-Abdeckung für getrimmte numerische Flag-Inputs).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode (`artifacts/bl18.1-smoke-local-worker-1-langlauf-1772097177.json`, `request_id_header_source=correlation`, `started_at_utc=2026-02-26T09:12:58Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` trotz absichtlich getrimmter numerischer Flags (`" 5 "`, `" 0 "`) und getrimmtem Stop-Flag (`" 0 "`) (`artifacts/bl18.1-remote-stability-local-worker-1-langlauf-1772097177.ndjson`).
  - Server-Log: `artifacts/bl18.1-worker-1-server-1772097177.log`.

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Recheck getrimmter Correlation-Mode + 5x Stabilität)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:56915/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772096909  " SMOKE_REQUEST_ID_HEADER="  Correlation  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-langlauf-1772096909.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:56915/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="  Correlation  " STABILITY_RUNS=5 STABILITY_INTERVAL_SECONDS=0 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772096909.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `53 passed` (inkl. neuer Smoke-E2E-Abdeckung für getrimmte Inputs bei `SMOKE_REQUEST_ID_HEADER` und `SMOKE_ENFORCE_REQUEST_ID_ECHO`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im getrimmten Correlation-Mode (`artifacts/bl18.1-smoke-local-worker-c-langlauf-1772096909.json`, `request_id_header_source=correlation`, `started_at_utc=2026-02-26T09:08:30Z`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772096909.ndjson`, Run-IDs inkl. PID-Suffix).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Recheck Correlation-Mode + 5x Stabilität)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:45757/analyze//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772096678  " SMOKE_REQUEST_ID_HEADER="correlation" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772096678.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:45757/analyze//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="correlation" STABILITY_RUNS=5 STABILITY_INTERVAL_SECONDS=0 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772096678.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `51 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im Correlation-Mode (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772096678.json`, `request_id_header_source=correlation`).
  - Stabilität: `pass=5`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772096678.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Iteration Correlation-Header-Mode im Smoke-Runner)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39597/AnAlYzE/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772096518  " SMOKE_REQUEST_ID_HEADER="correlation" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-langlauf-1772096518.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:39597/AnAlYzE/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID_HEADER="correlation" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=0 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772096518.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `51 passed` (inkl. neuer Smoke-E2E-Abdeckung für `SMOKE_REQUEST_ID_HEADER=correlation` + Validierungs-Guard für ungültige Header-Modi).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt im Correlation-Mode (`artifacts/bl18.1-smoke-local-worker-a-langlauf-1772096518.json`, `request_id_header_source=correlation`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772096518.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Iteration Request-ID-Fallback auf `X-Correlation-Id`)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:52255/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772096264  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-langlauf-1772096264.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:52255/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=0 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772096264.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `49 passed` (inkl. neuem API-E2E-Guard: Fallback auf `X-Correlation-Id`, wenn `X-Request-Id` leer/whitespace ist).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-langlauf-1772096264.json`, `started_at_utc=2026-02-26T08:57:50Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772096264.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Iteration Forward-Suffix-Chain mit internem Double-Slash)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:49769/health//analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772095998  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772095998.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:49769/health//analyze/health/analyze///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=0 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772095998.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `48 passed` (inkl. neuem Smoke-E2E-Guard für wiederholte Forward-Suffix-Kette mit internem Double-Slash + Schema-Case + Whitespace `"  HTTP://.../health//analyze/health/analyze///  "`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772095998.json`, `started_at_utc=2026-02-26T08:53:19Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772095998.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Iteration Embedded-Whitespace-Guard)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:53077/AnAlYzE/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772095778  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-langlauf-1772095778.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:53077/AnAlYzE/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772095778.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `47 passed` (inkl. neuem Smoke-E2E-Negativtest für eingebettete Whitespaces in `DEV_BASE_URL`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-langlauf-1772095778.json`, `started_at_utc=2026-02-26T08:49:39Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772095778.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Iteration Request-ID-Längen-Guard)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:35615/AnAlYzE//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772095524  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-langlauf-1772095524.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:35615/AnAlYzE//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772095524.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `46 passed` (inkl. neuem Smoke-E2E-Negativtest für `SMOKE_REQUEST_ID` mit >128 Zeichen).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-langlauf-1772095524.json`, `started_at_utc=2026-02-26T08:45:24Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772095524.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Iteration Port-Validierungs-Guard)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:58269/AnAlYzE/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772095294  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772095294.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:58269/AnAlYzE/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772095294.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `45 passed` (inkl. neuer Smoke-E2E-Negativtests für ungültige Ports `DEV_BASE_URL=:abc` und `:70000`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772095294.json`, `started_at_utc=2026-02-26T08:41:35Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772095294.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Iteration Userinfo-Guard + Reproduzierbarkeits-Run)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57041/AnAlYzE//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772095085  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-langlauf-1772095085.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57041/AnAlYzE//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772095085.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `43 passed` (inkl. neuem Smoke-E2E-Negativtest für `DEV_BASE_URL` mit Userinfo `user:pass@host`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-langlauf-1772095085.json`, `started_at_utc=2026-02-26T08:38:05Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772095085.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Recheck Reverse-Suffix-Kette mit internem Double-Slash)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:52617/AnAlYzE//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772094827  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-langlauf-1772094827.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:52617/AnAlYzE//health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772094827.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `42 passed` (inkl. neuem Smoke-E2E-Guard für wiederholte Reverse-Suffix-Ketten mit internem Double-Slash + Schema-Case + Whitespace `"  HTTP://.../AnAlYzE//health/analyze/health///  "`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-langlauf-1772094827.json`, `started_at_utc=2026-02-26T08:33:47Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772094827.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Recheck wiederholte Reverse-Suffix-Kette `/AnAlYzE/health/analyze/health///`)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:47249/AnAlYzE/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772094625  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772094625.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:47249/AnAlYzE/health/analyze/health///  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772094625.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `41 passed` (inkl. neuem Smoke-E2E-Guard für wiederholte Reverse-Suffix-Kette mit Schema-Case + Whitespace `"  HTTP://.../AnAlYzE/health/analyze/health///  "`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772094625.json`, `started_at_utc=2026-02-26T08:30:25Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772094625.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Recheck wiederholte Suffix-Kette `/health/analyze/health/analyze///`)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:59769/health/analyze/health/analyze///" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772094394  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-langlauf-1772094394.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:59769/health/analyze/health/analyze///" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772094394.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `40 passed` (inkl. neuem Smoke-E2E-Guard für wiederholte Suffix-Kette `.../health/analyze/health/analyze///`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-langlauf-1772094394.json`, `started_at_utc=2026-02-26T08:26:34Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772094394.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Recheck Reverse-Suffix-Kette + Kombi-Normalisierung)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:34463/AnAlYzE/health//  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772094175  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-langlauf-1772094175.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:34463/AnAlYzE/health//  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772094175.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `39 passed` (inkl. neuem Smoke-E2E-Guard für kombinierte Reverse-Suffix-Kette `"  HTTP://.../AnAlYzE/health//  "`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-langlauf-1772094175.json`, `started_at_utc=2026-02-26T08:22:55Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772094175.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Recheck Reproduzierbarkeit/Stabilität)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:40205/health" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772094021  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772094021.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:40205/health" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772094021.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `38 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772094021.json`, `started_at_utc=2026-02-26T08:20:22Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772094021.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Iteration Non-PASS-Report-Guard im Stability-Runner)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:35035/health/analyze/health//" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-a-langlauf-1772093853  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-langlauf-1772093853.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:35035/health/analyze/health//" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772093853.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `38 passed` (inkl. neuem Stability-E2E-Guard für Reports mit `status!=pass` bei `rc=0`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-langlauf-1772093853.json`, `started_at_utc=2026-02-26T08:17:33Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772093853.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Recheck Suffix-Reihenfolge `/analyze/health`)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:46567/analyze/health//" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-c-langlauf-1772093532  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-langlauf-1772093532.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:46567/analyze/health//" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772093532.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `37 passed` (inkl. neuer Smoke-E2E-Abdeckung für verkettete Suffix-Reihenfolge `.../analyze/health//`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-langlauf-1772093532.json`, `started_at_utc=2026-02-26T08:12:12Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772093532.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Iteration Stability-Report-Guard + Request-ID-Entkopplung)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:57373/health" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-b-langlauf-1772093324  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-langlauf-1772093324.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:57373/health" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772093324.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `36 passed` (inkl. neuer Stability-E2E-Abdeckung für fehlendes Smoke-Report-Artefakt trotz `rc=0`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b-langlauf-1772093324.json`, `started_at_utc=2026-02-26T08:08:44Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0`; Run-IDs jetzt mit PID-Suffix zur besseren Parallelisierungs-Entkopplung (`bl18-stability-<run>-<epoch>-<pid>`) (`artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772093324.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Iteration Request-ID-Trim/Steuerzeichen-Guard)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18110/health" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_REQUEST_ID="  bl18-worker-a-1772093014  " SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772093014.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18110/health" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772093014.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `35 passed` (inkl. neuer Smoke-E2E-Checks für getrimmte `SMOKE_REQUEST_ID` sowie Fail-fast bei Whitespace-only/Steuerzeichen).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-1772093014.json`, `started_at_utc=2026-02-26T08:03:35Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772093014.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Recheck redundante trailing-Slash-Normalisierung)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18110/health//analyze//" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-1772092769.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18110/health//analyze//" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-1772092769.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `32 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-1772092769.json`, `started_at_utc=2026-02-26T07:59:29Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-1772092769.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B2, Langlauf-Recheck kombinierte Base-URL-Normalisierung)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57385/HeAlTh/AnAlYzE/  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b2-1772092596.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:57385/HeAlTh/AnAlYzE/  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b2-1772092596.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `31 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b2-1772092596.json`, `started_at_utc=2026-02-26T07:56:37Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b2-1772092596.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Recheck kombinierte Base-URL-Normalisierung)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:37775/HeAlTh/AnAlYzE/  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772092447.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  HTTP://127.0.0.1:37775/HeAlTh/AnAlYzE/  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772092447.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `31 passed` (inkl. neuer Smoke-E2E-Abdeckung für kombinierte Normalisierung + Negativfälle `CURL_RETRY_DELAY=-1` und `SMOKE_ENFORCE_REQUEST_ID_ECHO=2`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-1772092447.json`, `started_at_utc=2026-02-26T07:54:08Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772092447.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Recheck mit `HTTP://.../HeAlTh`)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="HTTP://127.0.0.1:18086/HeAlTh" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-1772092067.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="HTTP://127.0.0.1:18086/HeAlTh" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-1772092067.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `28 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-1772092067.json`, `started_at_utc=2026-02-26T07:47:47Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-1772092067.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Iteration Suffix-Case-Normalisierung)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:49115/HeAlTh/AnAlYzE" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-1772091885.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:49115/HeAlTh/AnAlYzE" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-1772091885.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `28 passed` (inkl. neuem Smoke-E2E-Happy-Path für case-insensitive Suffix-Normalisierung `.../HeAlTh/AnAlYzE`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b-1772091885.json`, `started_at_utc=2026-02-26T07:44:45Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-1772091885.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Iteration Whitespace-Trim + `/health`-Input)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="  http://127.0.0.1:58813/health  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772091687.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="  http://127.0.0.1:58813/health  " DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772091687.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `27 passed` (inkl. neuer Smoke-E2E-Checks für getrimmte `DEV_BASE_URL`-Whitespaces + Negativfall whitespace-only).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-1772091687.json`, `started_at_utc=2026-02-26T07:41:27Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772091687.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, Langlauf-Iteration HTTP-Scheme-Case-Härtung)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:33139" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-1772091468.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:33139" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-1772091468.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `25 passed` (inkl. neuem Smoke-E2E-Happy-Path für `DEV_BASE_URL` mit grossgeschriebenem HTTP-Schema `HTTP://...`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-1772091468.json`, `started_at_utc=2026-02-26T07:37:50Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-1772091468.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Iteration Query/Fragment-Guard)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:57997" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-1772091225.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:57997" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-1772091225.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `24 passed` (inkl. neuer Smoke-E2E-Checks für verkettete Suffix-Normalisierung + Query/Fragment-Reject).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b-1772091225.json`, `started_at_utc=2026-02-26T07:33:45Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-1772091225.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, Langlauf-Check `/health`-Normalisierung)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:33897" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772090927.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:33897" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772090927.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `22 passed` (inkl. neuem Smoke-E2E für `DEV_BASE_URL=.../health`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-1772090927.json`, `started_at_utc=2026-02-26T07:28:48Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772090927.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker C, langlaufender Recheck)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:42835" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c-1772090698.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:42835" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c-1772090698.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `21 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c-1772090698.json`, `started_at_utc=2026-02-26T07:24:58Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c-1772090698.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker B, Langlauf-Iteration)

- Command:
  - `./scripts/run_webservice_e2e.sh` (zusätzlich 5x Re-Run für Flake-Check, jeweils `21 passed`)
  - `DEV_BASE_URL="http://127.0.0.1:18120" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b-1772090574.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18120" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b-1772090574.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, stabil über Wiederholung (`21 passed` in allen 5 Re-Runs).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b-1772090574.json`, `started_at_utc=2026-02-26T07:22:54Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b-1772090574.ndjson`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, isolierter Real-Run)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:56459" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a-1772090470.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:56459" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a-1772090470.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `21 passed`.
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a-1772090470.json`, `started_at_utc=2026-02-26T07:21:10Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a-1772090470.ndjson`).

### Kurz-Nachweis (2026-02-26, lokal reproduzierbar)

- Command:
  - `./scripts/run_webservice_e2e.sh` (lokale E2E-Suite inkl. Script-E2E; Ergebnis: `21 passed`)
  - `DEV_BASE_URL="http://127.0.0.1:18082" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-c.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18082" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=2 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-c.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-c.json`, `started_at_utc=2026-02-26T07:08:22Z`).
  - Stabilität: `pass=2`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-c.ndjson`).
  - NDJSON-Report mit zwei erfolgreichen Runs (`status=pass`, `http_status=200`, `reason=ok`).

### Kurz-Nachweis (Update 2026-02-26, Worker A, lokal reproduzierbar)

- Command:
  - `DEV_BASE_URL="http://127.0.0.1:18080" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-a.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18080" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-a.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-a.json`, `started_at_utc=2026-02-26T07:11:08Z`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-a.ndjson`).
  - NDJSON-Report mit drei erfolgreichen Runs (`status=pass`, `http_status=200`, `reason=ok`).

### Kurz-Nachweis (Update 2026-02-26, Worker B2, lokal reproduzierbar)

- Command:
  - `./scripts/run_webservice_e2e.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18084" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke-local-worker-b2-1772090073.json" ./scripts/run_remote_api_smoketest.sh`
  - `DEV_BASE_URL="http://127.0.0.1:18084" DEV_API_AUTH_TOKEN="bl18-token" SMOKE_QUERY="__ok__" STABILITY_RUNS=3 STABILITY_INTERVAL_SECONDS=1 STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability-local-worker-b2-1772090073.ndjson" ./scripts/run_remote_api_stability_check.sh`
- Ergebnis:
  - E2E-Suite: Exit `0`, `21 passed` (`tests/test_web_e2e.py` + `tests/test_remote_smoke_script.py` + `tests/test_remote_stability_script.py`).
  - Smoke: Exit `0`, `HTTP 200`, `ok=true`, `result` vorhanden, Request-ID-Echo Header+JSON korrekt (`artifacts/bl18.1-smoke-local-worker-b2-1772090073.json`).
  - Stabilität: `pass=3`, `fail=0`, Exit `0` (`artifacts/bl18.1-remote-stability-local-worker-b2-1772090073.ndjson`).
  - NDJSON-Report mit drei erfolgreichen Runs (`status=pass`, `http_status=200`, `reason=ok`).
