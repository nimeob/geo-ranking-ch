# Remote / Internet Smoke Runbook — API (sync + async)

Ziel: Reproduzierbare **Internet-Smokes** für `staging`/`prod` (und optional dev) mit klarer PASS/FAIL-Ausgabe und optionaler Evidence als JSON-Artefakt.

Für lokale dev-Smokes (inkl. deterministischer E2E-Fixtures via `__ok__`) siehe: [`DEV_API_SMOKE_RUNBOOK.md`](DEV_API_SMOKE_RUNBOOK.md)

> Hinweis: Secrets/Tokens niemals in Issues/PRs posten.

## 0) Kanonischer Entrypoint (Profile `pr` / `deploy` / `nightly`)

Der konsolidierte Smoke-Entrypoint ist:

```bash
python3 ./scripts/run_deploy_smoke.py --profile <pr|deploy|nightly> [--target <dev|remote|staging|prod>] [--flow <sync|async|both>]
```

Kurzregeln:
- `--profile pr` → lokaler PR-Split-Smoke (`check_bl334_split_smokes.sh`)
- `--profile deploy` → Remote-Smoke(s) für ein Ziel (`--target ...`, default `--flow sync`)
- `--profile nightly` → periodischer Remote-Smoke (default `--target dev`, default `--flow both`)

Die environment-spezifischen Wrapper (`run_staging_*`, `run_prod_*`) delegieren intern auf diesen Entrypoint.

### JSON-Schema (Issue #992)

Smoke-Artefakte nutzen das gemeinsame Schema `deploy-smoke-report/v1` mit den Kernfeldern:

- `schema_version`
- `runner`
- `classification` (`must-pass` oder `informational`)
- `status` (`pass`/`fail`/`planned`)
- `reason`

Details + Feldliste: [`DEPLOY_SMOKE_JSON_SCHEMA.md`](DEPLOY_SMOKE_JSON_SCHEMA.md)

### Auth-Preflight Contract (Issue #1024)

Für auth-required Smokes kann vorab der Preflight-Runner verwendet werden:

```bash
SMOKE_AUTH_MODE="oidc_client_credentials" \
OIDC_TOKEN_URL="https://<issuer>/oauth2/token" \
OIDC_CLIENT_ID="<client-id>" \
OIDC_CLIENT_SECRET="<client-secret>" \
SMOKE_AUTH_OUTPUT_FILE="artifacts/smoke_auth.env" \
  ./scripts/smoke/auth_preflight.sh

source artifacts/smoke_auth.env
DEV_API_AUTH_TOKEN="${SMOKE_BEARER_TOKEN}" ./scripts/run_remote_api_smoketest.sh
```

Fail-fast-Signal bei fehlender/ungültiger Auth-Konfiguration:
- Exit-Code: `42`
- Stderr enthält: `auth-preflight-failed`

---

## 1) Sync Flow — `POST /analyze` (HTTP 200)

### Staging

```bash
STAGING_BASE_URL="https://api.staging.<domain>" \
  ./scripts/run_staging_api_smoketest.sh

# Optional (auth)
STAGING_BASE_URL="https://api.staging.<domain>" \
STAGING_API_AUTH_TOKEN="<token>" \
  ./scripts/run_staging_api_smoketest.sh
```

Evidence (Default): `artifacts/staging-smoke-analyze.json`

### Prod

```bash
PROD_BASE_URL="https://api.<domain>" \
  ./scripts/run_prod_api_smoketest.sh

# Optional (auth)
PROD_BASE_URL="https://api.<domain>" \
PROD_API_AUTH_TOKEN="<token>" \
  ./scripts/run_prod_api_smoketest.sh
```

Evidence (Default): `artifacts/prod-smoke-analyze.json`

### Generic (any remote)

```bash
DEV_BASE_URL="https://api.<domain>" \
  ./scripts/run_remote_api_smoketest.sh
```

Evidence (optional): set `SMOKE_OUTPUT_JSON=...`

---

## 2) Async Flow — Async Jobs API (submit → poll → result)

### Staging

```bash
STAGING_BASE_URL="https://api.staging.<domain>" \
  ./scripts/run_staging_async_jobs_smoketest.sh

# Optional (auth)
STAGING_BASE_URL="https://api.staging.<domain>" \
STAGING_API_AUTH_TOKEN="<token>" \
  ./scripts/run_staging_async_jobs_smoketest.sh
```

Evidence (Default): `artifacts/staging-smoke-async-jobs.json`

### Prod

```bash
PROD_BASE_URL="https://api.<domain>" \
  ./scripts/run_prod_async_jobs_smoketest.sh

# Optional (auth)
PROD_BASE_URL="https://api.<domain>" \
PROD_API_AUTH_TOKEN="<token>" \
  ./scripts/run_prod_async_jobs_smoketest.sh
```

Evidence (Default): `artifacts/prod-smoke-async-jobs.json`

### Generic (any remote)

```bash
DEV_BASE_URL="https://api.<domain>" \
  ./scripts/run_remote_async_jobs_smoketest.sh
```

Evidence (Default): `artifacts/remote-smoke-async-jobs.json` (override via `ASYNC_SMOKE_OUTPUT_JSON`).

---

## 3) Optional knobs (both flows)

```bash
SMOKE_QUERY="St. Leonhard-Strasse 40, St. Gallen" \
SMOKE_MODE="basic" \
SMOKE_TIMEOUT_SECONDS="20" \
  ... <script>
```

Async-only knobs:

```bash
ASYNC_SMOKE_POLL_TIMEOUT_SECONDS="60" \
ASYNC_SMOKE_POLL_INTERVAL_SECONDS="0.5" \
  ... <async script>
```
