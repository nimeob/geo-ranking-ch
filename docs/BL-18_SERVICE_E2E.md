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
  - `POST /analyze` übernimmt `X-Request-Id` (oder `X-Correlation-Id`) und spiegelt sie in Antwort-Header `X-Request-Id` sowie JSON-Feld `request_id`.
  - Ohne mitgelieferte ID erzeugt der Service eine interne Request-ID.
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
- **Dev:** `tests/test_web_e2e_dev.py`
  - läuft gegen `DEV_BASE_URL`
  - optional mit `DEV_API_AUTH_TOKEN`
  - deckt mindestens Health/Version/404 + Analyze-Endpunkt ab
- **Script-E2E (lokal):**
  - `tests/test_remote_smoke_script.py`: validiert den dedizierten Remote-Smoke-Runner lokal gegen den gestarteten Service (inkl. kombinierter Base-URL-Normalisierung `"  HTTP://.../HeAlTh/AnAlYzE/  "`, redundanter trailing-Slash-Ketten wie `.../health//analyze//` sowie Negativfällen für `CURL_RETRY_DELAY=-1` und `SMOKE_ENFORCE_REQUEST_ID_ECHO=2`).
  - `tests/test_remote_stability_script.py`: validiert den Mehrfach-Runner inkl. NDJSON-Report und `STABILITY_STOP_ON_FIRST_FAIL`.
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
- `DEV_BASE_URL`: darf keine Query-/Fragment-Komponenten enthalten (`?foo=bar`, `#frag`), damit der `/analyze`-Zielpfad reproduzierbar bleibt.
- `SMOKE_TIMEOUT_SECONDS` / `CURL_MAX_TIME`: müssen endliche Zahlen `> 0` sein (früher, klarer `exit 2` bei Fehlwerten, inkl. Reject von `nan`/`inf`).
- `CURL_RETRY_COUNT` / `CURL_RETRY_DELAY`: robuste Wiederholungen bei transienten Netzwerkfehlern; müssen Ganzzahlen `>= 0` sein.
- `SMOKE_REQUEST_ID`: korrelierbare Request-ID (z. B. für Logsuche); wird vor dem Request getrimmt und muss frei von Steuerzeichen sein (sonst `exit 2`).
- `SMOKE_ENFORCE_REQUEST_ID_ECHO` (`1|0`, default `1`): erzwingt Echo-Prüfung für Header + JSON (`request_id`)
- `SMOKE_MODE`: reproduzierbarer Request-Modus (`basic|extended|risk`)

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
- unterstützt optionales Fail-Fast via `STABILITY_STOP_ON_FIRST_FAIL=1` (nur `0|1` erlaubt),
- erlaubt für Tests/Debug ein optionales Script-Override via `STABILITY_SMOKE_SCRIPT=/pfad/zu/run_remote_api_smoketest.sh`,
- zählt fehlende/leer gebliebene Smoke-JSON-Artefakte **und** Reports mit `status!=pass` als Fehlrun (auch wenn das Smoke-Script `rc=0` liefert),
- bricht mit Exit `1` ab, wenn `fail_count > STABILITY_MAX_FAILURES`.

### CI-Hook (optional)

Der Deploy-Workflow kann nach dem ECS-Rollout zusätzlich einen optionalen `/analyze`-Smoke-Test ausführen:

- Basis-URL via `SERVICE_BASE_URL` (oder Fallback aus `SERVICE_HEALTH_URL` ohne `/health`)
- optionales Bearer-Token via Secret `SERVICE_API_AUTH_TOKEN`

Damit entstehen reproduzierbare CI-Nachweise für BL-18.1, ohne den Deploy zu blockieren, falls die Analyze-URL noch nicht konfiguriert ist.

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
