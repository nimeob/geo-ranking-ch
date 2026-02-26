# BL-18.1 — Erfolgreicher API-Test über das Internet

## Ziel

Nachweis, dass ein OpenClaw-Agent den öffentlichen API-Endpunkt über das Internet erreichen und auf `POST /analyze` erfolgreich eine Antwort mit Adressdaten erhalten kann.

Akzeptanzkriterium für den Smoke-Check:
- HTTP `200`
- JSON-Feld `ok=true`
- JSON-Feld `result` vorhanden und nicht leer

## Smoke-Script

Für den reproduzierbaren Nachweis steht folgendes Script bereit:

```bash
DEV_BASE_URL="https://<dein-dev-endpoint>" ./scripts/run_remote_api_smoketest.sh
```

Optional mit Auth-Token:

```bash
DEV_BASE_URL="https://<dein-dev-endpoint>" \
DEV_API_AUTH_TOKEN="<token>" \
./scripts/run_remote_api_smoketest.sh
```

## Wichtige Optionen

- `DEV_BASE_URL` (Pflicht): Service-Basis-URL; `/health` oder `/analyze` als Suffix werden automatisch normalisiert.
- `SMOKE_QUERY` (optional): Anfrage für den Testlauf (Default: `St. Leonhard-Strasse 40, St. Gallen`).
- `SMOKE_MODE` (optional): `basic|extended|risk` (Default: `basic`).
- `SMOKE_TIMEOUT_SECONDS` (optional): Timeout-Wert im Request (Default: `20`).
- `CURL_MAX_TIME` (optional): Curl-Timeout (Default: `30`, muss >= `SMOKE_TIMEOUT_SECONDS` sein).
- `SMOKE_REQUEST_ID` (optional): Request-ID für Korrelation in Logs.
- `SMOKE_OUTPUT_JSON` (optional): JSON-Artefaktpfad für den strukturierten Testreport.

Beispiel mit Artefakt:

```bash
DEV_BASE_URL="https://<dein-dev-endpoint>" \
SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke.json" \
./scripts/run_remote_api_smoketest.sh
```

## Ergebnisformat

Bei gesetztem `SMOKE_OUTPUT_JSON` schreibt der Runner einen Bericht mit mindestens:
- `status` (`pass|fail`)
- `reason` (`ok`, `http_status`, `missing_result`, `invalid_json`, `curl_error`)
- `http_status`
- `url`
- `request_id`
- `started_at_utc`, `ended_at_utc`, `duration_seconds`
- `result_keys` (bei Erfolg)

## Lokale Testabdeckung

`tests/test_remote_smoke_script.py` deckt den Runner gegen einen lokalen Testserver ab, inkl.:
- Happy Path (inkl. Report-Datei)
- URL-Normalisierung bei `/health`
- Fail-fast bei fehlendem `DEV_BASE_URL`
- Unauthorized-Fall (`401`) ohne Token
- Erfolgsfall mit getrimmtem Auth-Token
