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
  - `API_AUTH_TOKEN` gesetzt → `/analyze` verlangt `Authorization: Bearer <token>`.
  - Ohne/mit falschem Token → `401 unauthorized`.
- **Timeout-Handling verbessert:**
  - `ANALYZE_DEFAULT_TIMEOUT_SECONDS` (Default 15)
  - `ANALYZE_MAX_TIMEOUT_SECONDS` (Default 45)
  - Request-Feld `timeout_seconds` erlaubt, validiert (endliche Zahl `> 0`, d. h. Reject von `nan`/`inf`) und auf Max gecappt.
- **Validierung Intelligence-Mode:**
  - Zulässig: `basic | extended | risk`
  - Ungültig → `400 bad_request`.
- **Explizites Timeout-Mapping:**
  - `TimeoutError` → `504 timeout`.
- **Request-ID-Korrelation für API-Debugging:**
  - `POST /analyze` übernimmt die **erste gültige** ID aus `X-Request-Id` (primär) oder `X-Correlation-Id` (Fallback) und spiegelt sie in Antwort-Header `X-Request-Id` sowie JSON-Feld `request_id`.
  - Leere/whitespace-only IDs **und** IDs mit Steuerzeichen (z. B. Tabs) werden verworfen; ist `X-Request-Id` dadurch ungültig, wird deterministisch auf `X-Correlation-Id` zurückgefallen.
  - Ohne mitgelieferte gültige ID erzeugt der Service eine interne Request-ID.
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
    - Timeout (504)
    - Internal (500)
    - Request-ID-Echo inkl. Fallback auf `X-Correlation-Id`, wenn `X-Request-Id` leer/whitespace **oder wegen Steuerzeichen ungültig** ist
- **Dev:** `tests/test_web_e2e_dev.py`
  - läuft gegen `DEV_BASE_URL`
  - optional mit `DEV_API_AUTH_TOKEN`
  - deckt mindestens Health/Version/404 + Analyze-Endpunkt ab
- **Script-E2E (lokal):**
  - `tests/test_remote_smoke_script.py`: validiert den dedizierten Remote-Smoke-Runner lokal gegen den gestarteten Service (inkl. kombinierter Base-URL-Normalisierung `"  HTTP://.../HeAlTh/AnAlYzE/  "`, wiederholter Suffix-Ketten wie `.../health/analyze/health/analyze///`, wiederholter Reverse-Suffix-Ketten mit internem Double-Slash wie `.../AnAlYzE//health/analyze/health///`, wiederholter Forward-Suffix-Ketten mit internem Double-Slash wie `.../health//analyze/health/analyze///`, redundanter trailing-Slash-Ketten wie `.../health//analyze//`, getrimmter Header-/Flag-Inputs wie `SMOKE_REQUEST_ID_HEADER="  Correlation  "`, `SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 "`, `SMOKE_MODE="  basic  "`, getrimmten Timeout-Inputs `SMOKE_TIMEOUT_SECONDS="\t2.5\t"`/`CURL_MAX_TIME=" 15 "` und getrimmter Retry-Flags wie `CURL_RETRY_COUNT="\t1\t"`/`CURL_RETRY_DELAY="\t1\t"`, Tab-umhüllter Inputs (`"\thttp://.../health\t"`, `"\tCorrelation\t"`) sowie Negativfällen für `CURL_RETRY_DELAY=-1`, `SMOKE_ENFORCE_REQUEST_ID_ECHO=2`, zu lange `SMOKE_REQUEST_ID` (`>128`), ungültige Ports in `DEV_BASE_URL` (`:abc`, `:70000`) und `DEV_BASE_URL` mit Userinfo `user:pass@host`).
  - `tests/test_remote_stability_script.py`: validiert den Mehrfach-Runner inkl. NDJSON-Report, `STABILITY_STOP_ON_FIRST_FAIL` sowie getrimmter numerischer Flag-Inputs (inkl. Space-/Tab-Varianten wie `" 2 "`, `"\t2\t"`, `" 0 "`).
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

## BL-18.1 — Remote-API-Smoke-Test (Internet)

Für den dedizierten Erfolgsnachweis über öffentliche Erreichbarkeit (`POST /analyze`) steht ein separates Script bereit:

```bash
DEV_BASE_URL="https://<dein-dev-endpoint>" ./scripts/run_remote_api_smoketest.sh

# optional mit Auth
DEV_BASE_URL="https://<dein-dev-endpoint>" DEV_API_AUTH_TOKEN="<token>" ./scripts/run_remote_api_smoketest.sh
```

Der Check validiert mindestens: HTTP `200`, `ok=true`, `result` vorhanden **und** (default) Request-ID-Echo (`X-Request-Id` Header + JSON-Feld `request_id` entsprechen der gesendeten `SMOKE_REQUEST_ID`).

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
- `SMOKE_TIMEOUT_SECONDS` / `CURL_MAX_TIME`: müssen endliche Zahlen `> 0` sein und werden vor der Validierung getrimmt (früher, klarer `exit 2` bei Fehlwerten, inkl. Reject von `nan`/`inf`).
- `CURL_RETRY_COUNT` / `CURL_RETRY_DELAY`: robuste Wiederholungen bei transienten Netzwerkfehlern; müssen Ganzzahlen `>= 0` sein und werden vor der Validierung getrimmt.
- `SMOKE_REQUEST_ID`: korrelierbare Request-ID (z. B. für Logsuche); wird vor dem Request getrimmt, muss frei von Steuerzeichen sein und darf maximal 128 Zeichen enthalten (sonst `exit 2`).
- `SMOKE_REQUEST_ID_HEADER` (`request|correlation`, default `request`): wird vor Validierung getrimmt und case-insensitive normalisiert; wählt, ob die Request-ID via `X-Request-Id` (Standard) oder via `X-Correlation-Id` gesendet wird; `correlation` erlaubt einen reproduzierbaren Fallback-Check für Services, die `X-Request-Id` leer/unset oder wegen ungültiger Zeichen verwerfen.
- `SMOKE_ENFORCE_REQUEST_ID_ECHO` (`1|0`, default `1`): wird vor Validierung getrimmt und erzwingt Echo-Prüfung für Header + JSON (`request_id`).
- `SMOKE_MODE`: reproduzierbarer Request-Modus (`basic|extended|risk`), wird vor der Validierung getrimmt.

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
- unterstützt optionales Fail-Fast via `STABILITY_STOP_ON_FIRST_FAIL=1` (nur `0|1` erlaubt; Wert wird vor Validierung getrimmt),
- trimmt numerische Runner-Flags (`STABILITY_RUNS`, `STABILITY_INTERVAL_SECONDS`, `STABILITY_MAX_FAILURES`) vor der Validierung für robuste Env-Inputs,
- erlaubt für Tests/Debug ein optionales Script-Override via `STABILITY_SMOKE_SCRIPT=/pfad/zu/run_remote_api_smoketest.sh`,
- zählt fehlende/leer gebliebene Smoke-JSON-Artefakte **und** Reports mit `status!=pass` als Fehlrun (auch wenn das Smoke-Script `rc=0` liefert),
- bricht mit Exit `1` ab, wenn `fail_count > STABILITY_MAX_FAILURES`.

### CI-Hook (optional)

Der Deploy-Workflow kann nach dem ECS-Rollout zusätzlich einen optionalen `/analyze`-Smoke-Test ausführen:

- Basis-URL via `SERVICE_BASE_URL` (oder Fallback aus `SERVICE_HEALTH_URL` ohne `/health`)
- optionales Bearer-Token via Secret `SERVICE_API_AUTH_TOKEN`

Damit entstehen reproduzierbare CI-Nachweise für BL-18.1, ohne den Deploy zu blockieren, falls die Analyze-URL noch nicht konfiguriert ist.

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
