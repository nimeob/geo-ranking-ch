# Staging Smoke Runbook — API `POST /analyze` (HTTP 200)

Ziel: reproduzierbarer Smoke gegen die **staging** API-Base-URL, inkl. Evidence.

## Voraussetzungen

- Eine erreichbare staging API Base-URL existiert (z. B. `https://api.staging.<domain>`).
- Optional: Bearer-Token falls `/analyze` auth-geschützt ist.

## Command (lokal)

```bash
# Minimal
STAGING_BASE_URL="https://api.staging.<domain>" \
  ./scripts/run_staging_api_smoketest.sh

# Mit optionalem Auth-Token
STAGING_BASE_URL="https://api.staging.<domain>" \
STAGING_API_AUTH_TOKEN="<token>" \
  ./scripts/run_staging_api_smoketest.sh
```

Optional (Forwarded knobs):

```bash
STAGING_BASE_URL="https://api.staging.<domain>" \
SMOKE_QUERY="St. Leonhard-Strasse 40, St. Gallen" \
SMOKE_MODE="basic" \
SMOKE_TIMEOUT_SECONDS="20" \
  ./scripts/run_staging_api_smoketest.sh
```

## Evidence

- Das Script schreibt (per Default) ein JSON-Artefakt nach:
  - `artifacts/staging-smoke-analyze.json`
- Im Issue/PR-Evidence:
  1) den verwendeten Command (ohne Token) dokumentieren
  2) relevante Auszüge aus dem Output einfügen (Statuscode + ok/result)
  3) optional: das JSON als Artefakt referenzieren oder als Snippet anhängen

> Hinweis: Secrets/Tokens niemals in Issues/PRs posten.
