# Deploy Smoke JSON Schema (`deploy-smoke-report/v1`)

Dieses Dokument definiert das gemeinsame JSON-Minimalschema für Deploy-/Remote-Smokes.

## Pflichtfelder (alle Reports)

- `schema_version` — aktuell: `deploy-smoke-report/v1`
- `runner` — Name des ausführenden Runners/Skripts
- `classification` — `must-pass` oder `informational`
- `status` — `pass`, `fail` oder `planned`
- `reason` — kurze Maschinenbegründung (`ok`, `dry_run`, `command_failed`, ...)

## Entrypoint `scripts/run_deploy_smoke.py`

Dry-Run (`--dry-run`) und optionales Report-File (`--output-json`) liefern:

- `profile`, `target`, `flow`
- `checks[]` mit
  - `name`
  - `command`
  - `env`
  - `classification`
  - `status`

Bei echter Ausführung enthält `checks[]` zusätzlich `exit_code` sowie auf Top-Level:

- `started_at_utc`
- `ended_at_utc`
- `duration_seconds`

## Sync-Script `scripts/run_remote_api_smoketest.sh`

Zusätzlich zu den Pflichtfeldern enthält der Report u. a.:

- `http_status`, `curl_exit` (bei curl-Fehlern)
- `request_id*` Felder (`request_id`, `request_id_header_name`, Echo-Status)
- `url`, `started_at_utc`, `ended_at_utc`, `duration_seconds`
- `result_keys`

Klassifikation per Env:

- `SMOKE_CLASSIFICATION=must-pass|informational` (Default: `must-pass`)

## Async-Script `scripts/run_async_jobs_smoketest.py`

Pass-Reports enthalten ebenfalls die Pflichtfelder plus:

- `ok`, `base_url`, `request_id`
- `submit`, `job`, `result`, `timing`

Klassifikation per Env/CLI:

- `ASYNC_SMOKE_CLASSIFICATION` oder `--classification`
