# Remote / Internet Smoke Runbook — API (sync + async)

Ziel: Reproduzierbare **Internet-Smokes** für `staging`/`prod` (und optional dev) mit klarer PASS/FAIL-Ausgabe und optionaler Evidence als JSON-Artefakt.

> Hinweis: Secrets/Tokens niemals in Issues/PRs posten.

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
