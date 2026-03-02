# Dev Smoke Runbook — API (sync + async)

Ziel: schneller, reproduzierbarer Smoke-Test **in der Entwicklung** – entweder

- **lokal** (developer workstation, `localhost`) oder
- gegen eine **dev**-Umgebung (z. B. `https://api.dev.<domain>`)

Mit klarer PASS/FAIL-Ausgabe und optionaler Evidence als JSON-Artefakt.

> Hinweis: Secrets/Tokens niemals in Issues/PRs posten.

---

## 1) Lokal (empfohlen für deterministische Fixtures)

### 1.1 API lokal starten

```bash
HOST=127.0.0.1 \
PORT=8000 \
API_AUTH_TOKEN="bl18-token" \
ENABLE_E2E_FAULT_INJECTION=1 \
PYTHONPATH="$(pwd)" \
  python3 -m src.web_service
```

- `ENABLE_E2E_FAULT_INJECTION=1` aktiviert die deterministischen E2E-Fixtures.
- Für die Smokes kann dann `SMOKE_QUERY="__ok__"` verwendet werden.

### 1.2 Sync Smoke (POST /analyze)

```bash
DEV_BASE_URL="http://127.0.0.1:8000" \
DEV_API_AUTH_TOKEN="bl18-token" \
SMOKE_QUERY="__ok__" \
SMOKE_MODE="basic" \
SMOKE_TIMEOUT_SECONDS="2" \
SMOKE_OUTPUT_JSON="artifacts/dev-local-smoke-analyze.json" \
  ./scripts/run_remote_api_smoketest.sh
```

### 1.3 Async Smoke (submit → poll → result)

```bash
DEV_BASE_URL="http://127.0.0.1:8000" \
DEV_API_AUTH_TOKEN="bl18-token" \
SMOKE_QUERY="__ok__" \
SMOKE_MODE="basic" \
SMOKE_TIMEOUT_SECONDS="2" \
ASYNC_SMOKE_POLL_TIMEOUT_SECONDS="15" \
ASYNC_SMOKE_POLL_INTERVAL_SECONDS="0.1" \
ASYNC_SMOKE_OUTPUT_JSON="artifacts/dev-local-smoke-async-jobs.json" \
  ./scripts/run_remote_async_jobs_smoketest.sh
```

### 1.4 Quick Test-Gate (<2min)

Wenn du nur die **lokal deterministischen** Smoke-Guards laufen lassen willst:

```bash
.venv/bin/python -m pytest -q \
  tests/test_async_jobs_smoke_script.py \
  tests/test_remote_smoke_script.py::TestRemoteSmokeScript::test_smoke_script_passes_with_valid_token \
  tests/test_remote_stability_script.py::TestRemoteStabilityScript::test_stability_runner_passes_for_two_successful_runs
```

---

## 2) Dev-Umgebung (remote)

> Für remote dev ist `__ok__` **nicht** garantiert verfügbar (abhängig von der Deploy-Konfiguration).
> Verwende eine normale Adresse oder eine intern vereinbarte Smoke-Query.

### 2.1 Sync Smoke (POST /analyze)

```bash
DEV_BASE_URL="https://api.dev.<domain>" \
DEV_API_AUTH_TOKEN="<token>" \
SMOKE_QUERY="St. Leonhard-Strasse 40, St. Gallen" \
SMOKE_MODE="basic" \
SMOKE_TIMEOUT_SECONDS="20" \
SMOKE_OUTPUT_JSON="artifacts/dev-remote-smoke-analyze.json" \
  ./scripts/run_remote_api_smoketest.sh
```

### 2.2 Async Smoke (submit → poll → result)

```bash
DEV_BASE_URL="https://api.dev.<domain>" \
DEV_API_AUTH_TOKEN="<token>" \
SMOKE_QUERY="St. Leonhard-Strasse 40, St. Gallen" \
SMOKE_MODE="basic" \
SMOKE_TIMEOUT_SECONDS="20" \
ASYNC_SMOKE_POLL_TIMEOUT_SECONDS="60" \
ASYNC_SMOKE_OUTPUT_JSON="artifacts/dev-remote-smoke-async-jobs.json" \
  ./scripts/run_remote_async_jobs_smoketest.sh
```

---

## 3) Optional: Dev Self-signed TLS

Falls die dev-Umgebung HTTPS mit Self-signed Zertifikat nutzt:

- `DEV_TLS_CA_CERT=/pfad/zur/ca.crt` (Sync Smoke)
- `DEV_TLS_CA_CERT` oder `TLS_CA_CERT` (Async Smoke)

Siehe: [`docs/testing/dev-self-signed-tls-smoke.md`](dev-self-signed-tls-smoke.md)
