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

### Auth-Preflight Contract (Issue #1024 / #1025)

Für **deploy/nightly auth-required Smokes** ist der Preflight verpflichtend und wird über
`python3 ./scripts/run_deploy_smoke.py ...` automatisch als erster Gate-Step ausgeführt.

Referenz auf den tatsächlich genutzten Pipeline-Pfad:
- Runner: [`scripts/run_deploy_smoke.py`](../../scripts/run_deploy_smoke.py)
- Preflight: [`scripts/smoke/auth_preflight.sh`](../../scripts/smoke/auth_preflight.sh)
- Deploy-Workflow: [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml)

Standardmodus im Deploy-Runner:
- `SMOKE_AUTH_MODE=oidc_client_credentials` (default)
- `SMOKE_AUTH_OUTPUT_FILE=artifacts/smoke_auth.env` (default)

### ENV-Contract (Input + Output)

Pflicht-Input für `SMOKE_AUTH_MODE=oidc_client_credentials`:
- `OIDC_TOKEN_URL` (http/https Token-Endpoint)
- `OIDC_CLIENT_ID`
- `OIDC_CLIENT_SECRET` **oder** `OIDC_CLIENT_SECRET_FILE`

Optionale Inputs:
- `OIDC_SCOPE`
- `OIDC_AUDIENCE`
- `SMOKE_AUTH_OUTPUT_FILE` (Default `artifacts/smoke_auth.env`)

Ausgabe-Contract (`SMOKE_AUTH_OUTPUT_FILE`):
- `SMOKE_AUTH_MODE`
- `SMOKE_BEARER_TOKEN`

Beispiel (manuell):

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
- Deploy-Report (`run_deploy_smoke.py --output-json ...`) markiert den Lauf mit `reason=blocked-by-auth`

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

---

## 4) Lokale Verifikation (Quick Path)

Schneller End-to-End-Check des Deploy-Gates ohne echten Remote-Call:

```bash
python3 ./scripts/run_deploy_smoke.py \
  --profile deploy \
  --target dev \
  --flow sync \
  --dry-run \
  --output-json artifacts/deploy-smoke-dryrun.json
```

Erwartung:
- Report enthält `runner=deploy-smoke-entrypoint`
- erster Check hat `kind=auth_preflight`
- bei `--dry-run`: `status=planned`, `reason=dry_run`

Optionaler Auth-Preflight-Only Check:

```bash
SMOKE_AUTH_MODE=none ./scripts/smoke/auth_preflight.sh
cat artifacts/smoke_auth.env
```

Erwartung:
- Exit `0`
- `SMOKE_AUTH_MODE=none`
- `SMOKE_BEARER_TOKEN=` (leer)

---

## 5) Troubleshooting (häufige Fehler)

### A) `auth-preflight-failed` + Exit 42
Symptom:
- Preflight bricht sofort mit Marker `auth-preflight-failed` ab.

Typische Ursachen:
- `SMOKE_AUTH_MODE` ungültig/leer
- Pflichtvariablen (`OIDC_TOKEN_URL`, `OIDC_CLIENT_ID`, Secret) fehlen
- `OIDC_CLIENT_SECRET_FILE` zeigt auf nicht-lesbare/nicht vorhandene Datei

Fix:
1. `printenv | grep -E '^SMOKE_AUTH_MODE|^OIDC_'` prüfen
2. `SMOKE_AUTH_MODE=oidc_client_credentials|none` korrigieren
3. Secret-Quelle korrigieren (`OIDC_CLIENT_SECRET` oder `OIDC_CLIENT_SECRET_FILE`)

### B) Report `reason=blocked-by-auth`
Symptom:
- `run_deploy_smoke.py --output-json ...` endet mit `status=fail`, `reason=blocked-by-auth`.

Bedeutung:
- Kein API-Funktionsdefekt, sondern Auth-Provisioning vor den Smoke-Schritten fehlgeschlagen.

Fix:
1. In `checks[]` den `kind=auth_preflight` Eintrag prüfen
2. Fehlertext aus `error` lesen (z. B. HTTP 401/403 am Token-Endpoint)
3. OIDC-Credentials/Issuer-Config korrigieren und Lauf wiederholen

### C) Token-Endpoint antwortet nicht erfolgreich (curl/HTTP-Fehler)
Symptom:
- Meldungen wie `Token-Request ... fehlgeschlagen` oder `HTTP 4xx/5xx`.

Typische Ursachen:
- Falscher `OIDC_TOKEN_URL`
- Netzwerk-/Egress-Problem vom Runner
- Falsche Client-Credentials oder fehlender Scope/Audience

Fix:
1. Endpoint separat testen (`curl -i -X POST <OIDC_TOKEN_URL> ...`)
2. `OIDC_SCOPE` / `OIDC_AUDIENCE` entsprechend IdP-Contract setzen
3. Bei 401/403 Credentials rotieren/prüfen, dann Preflight erneut starten

---

## 6) Minimaler Abschlussnachweis für Deploy/Auth-Issues

Für Issue-Abschluss mindestens verlinken:
1. PR/Commit mit Runbook-Änderung
2. ausgeführten Verify-Command + Ergebnis
3. JSON-Evidence (`--output-json`) oder nachvollziehbare Log-Snippets
4. klare Trennung zwischen `blocked-by-auth` und echter API-Regression
