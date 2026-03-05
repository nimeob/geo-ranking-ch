# Deploy/Test Tier Matrix (PR / Deploy / Nightly)

Status: 2026-03-03 (Ist-Stand)
Parent: #976 · Work-Package: #990

## Ziel

Diese Matrix trennt **schnelle PR-Gates**, **verpflichtende Deploy-Gates** und **periodische Läufe** mit klaren Verantwortlichkeiten. Sie dient als Basis für die technische Konsolidierung der Smoke-Entrypoints in den Folge-WPs.

## Tier-Matrix

| Tier | Trigger | Blocking | Muss bestehen (must-pass) | Primäre Entrypoints / Workflows | Verantwortlich |
|---|---|---|---|---|---|
| **PR Gate** | `pull_request` | Ja (für Merge) | kritischer Dev-Smoke (required) + schnelle deterministische Vertrags-Checks + Doku-Link-Guard | `.github/workflows/dev-smoke-required.yml` (`python3 ./scripts/run_dev_smoke_required_with_retry.py`, delegiert an `run_deploy_smoke.py --profile pr --flow sync`), `.github/workflows/contract-tests.yml` (API-Contract-Tests), `.github/workflows/docs-quality.yml` (`./scripts/check_docs_quality_gate.sh`) | Repo-CI (GitHub Actions) |
| **Deploy Gate (dev)** | `workflow_dispatch` (on-demand) + stündlich per `schedule` | Ja (für erfolgreichen Deploy-Run) | Build/Test + ECS-Rollout + verpflichtende Health-Smokes + Post-Deploy-Verifikation | `.github/workflows/deploy.yml` (`pytest tests/ -v`, API `/health`, UI `/healthz`, Readiness-Gate API `/health` + GUI `/gui`, `python3 scripts/check_deploy_version_trace.py`) | Deploy-Workflow + Operator |
| **Nightly/Periodic** | `schedule` (zeitgesteuert) | Lauf-spezifisch (nicht PR-blocking) | periodische Stabilitäts-/Betriebschecks und automatische Entblockung | `.github/workflows/deploy.yml` (stündlicher Dev-Deploy), `.github/workflows/dependency-unblock.yml` (alle 30 min) | Repo-Automation |

## Required-Check-Namen (stabil)

Für Branch-Protection auf `main` sind die folgenden Status-Checks als stabile, nicht-matrixbasierte Namen vorgesehen:

- `dev-smoke-required` (kritischer Dev-Smoke, PR-blocking)
- `contract-smoke` (API-Contract-Fast-Checks, PR-blocking)
- `docs-link-guard` (Doku-Qualität, PR-blocking)

Konfigurationsdetails und Admin-Setup siehe `docs/OPERATIONS.md` Abschnitt **GitHub-Actions-Cleanup + Required-Checks**.

## API/UI-Matrix v1 (Auth/History/Trace Boundary)

Kanonische Referenz für die entkoppelten API/UI-Pflichtfälle:
- [`docs/testing/API_UI_DEV_SMOKE_MATRIX_V1.md`](./API_UI_DEV_SMOKE_MATRIX_V1.md)

Verbindlich für Dev-Smoke-Gating:
- Die Matrix enthält **genau 6 Pflichtfälle** (Login, Protected-Route-Guard, History-Happy-Path, Trace-Happy-Path, Legacy-Deprecation-Signale, negativer API-Contract-Fall).
- Der minimale Dev-Smoke-Gate-Satz ist in der Matrix unter **"Dev-Smoke-Gate (minimal, verbindlich)"** definiert.

## Pflicht-Checks je Tier

### 1) PR Gate (blocking)
- **Kritischer Dev-Smoke (required status check `dev-smoke-required`):**
  - `python3 ./scripts/run_dev_smoke_required_with_retry.py`
  - zentrale Retry-Policy auf Job-Ebene (`DEV_SMOKE_MAX_RETRIES=1`, `DEV_SMOKE_RETRY_DELAY_SECONDS`)
  - deterministischer Smoke-Seed ist zentral konfigurierbar (`DEV_SMOKE_TEST_SEED`, CI-Default: `dev-smoke-required-v1`)
  - daraus folgt fix: `max_attempts=2` (ein Initial-Run + max. ein Retry)
  - der Wrapper delegiert je Versuch an `python3 ./scripts/run_deploy_smoke.py --profile pr --flow sync`
  - PR-Split-Smoke (`./scripts/check_bl334_split_smokes.sh`) enthält als Pflichtpfad zusätzlich den Core-Flow `login -> search (__ok__) -> ranking list -> detail` via `tests/test_auth_regression_smoke_issue_1019.py`
  - Der Sync-Smoke-Runner prüft im Dev-Target zusätzlich einen expliziten `/analyze`-Fehlerpfad (`SMOKE_ERROR_QUERY=__validation__`) auf konsistentes `request_id`-Echo in Header+Body; Verstöße failen mit klaren Gründen wie `error_path_request_id_header_mismatch` / `error_path_request_id_body_mismatch`.
  - Der Split-Smoke validiert API-/UI-Health jetzt zusätzlich auf erwartete Version (`SMOKE_EXPECT_HEALTH_VERSION`, Default `bl334-split-smoke`) und bricht mit `expected vs observed`-Fehlerbild ab, falls eine stale Runtime antwortet.
  - Laufzeitbudget für den Core-Flow ist fail-closed (`CORE_FLOW_SMOKE_MAX_SECONDS`, Default `300`)
  - Bei Fehlern erzeugt der Runner automatisch Failure-Artefakte unter `reports/evidence/core-flow-smoke/<STAMP>/` (Trace + optional GUI-Screenshot)
  - CI-Summary (`$GITHUB_STEP_SUMMARY`) enthält konsistente Counts für `retried checks` und `flaky candidates` sowie den verwendeten `DEV_SMOKE_TEST_SEED`
  - Bei Fail wird immer ein kompaktes Failure-Artefakt hochgeladen (`dev-smoke-required-failure-<run_id>-<run_attempt>`), inklusive `artifacts/pr-dev-smoke-required-summary.md` mit Abschnitt **Failed checks (final attempt)** (Check + Kurzursache) sowie Retry-Report-JSON.
  - Der Workflow loggt die Artefaktpfade explizit (`Log failure artifact paths`), damit Name/Pfad direkt in den CI-Logs sichtbar sind.
  - Repro für den Fehlerpfad-Request-ID-Gate (lokal):
    ```bash
    DEV_BASE_URL="http://127.0.0.1:8000" \
    DEV_API_AUTH_TOKEN="<token>" \
    SMOKE_ENFORCE_ERROR_PATH_REQUEST_ID_ECHO=1 \
    SMOKE_ERROR_QUERY="__validation__" \
    ./scripts/run_remote_api_smoketest.sh
    ```
- **API-Contract-Fast-Checks (status check `contract-smoke`):**
  - `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py`
  - `python3 scripts/validate_field_catalog.py`
- **Doku-Qualität (status check `docs-link-guard`):** `./scripts/check_docs_quality_gate.sh`

### Flaky in Dev-CI

Definition (für dieses Repo): Ein Check ist **flaky**, wenn er im selben CI-Run zuerst fehlschlägt und innerhalb des erlaubten Retry-Budgets danach erfolgreich ist.

Verbindliche Regeln:
- Retry-Budget im PR-Gate bleibt auf **max. 1 Retry** begrenzt (`DEV_SMOKE_MAX_RETRIES=1`).
- Flaky-Fälle werden im Retry-Report explizit markiert (`flaky_hint` + `flaky_context`) inkl. Testname und Build-Kontext (`run_id`, `run_attempt`, `run_url`).
- Der Workflow enthält einen deterministischen Demo-Lauf (`scripts/smoke/dev_smoke_flaky_demo_runner.py`), der die Flaky-Markierung reproduzierbar erzeugt.

Umgang im PR-Review:
1. Flaky-Markierung ist **kein stilles PASS**: betroffenen Check im PR benennen und Issue/Follow-up referenzieren.
2. Wenn derselbe Check wiederholt flaky ist, Entflakung priorisieren (Testdaten/Timing/Isolation) statt Retry-Budget zu erhöhen.
3. Retry-Budget-Erhöhung über 1 ist im Dev-PR-Gate nicht erlaubt (fail-closed in `run_dev_smoke_required_with_retry.py`).

### 2) Deploy Gate (blocking)
- **Build & Test:** `pytest tests/ -v --tb=short`
- **Deploy API + UI** inkl. `services-stable`
- **Pflicht-Smokes:**
  - API Health (`/health`) via `SERVICE_HEALTH_URL` oder `${SERVICE_API_BASE_URL}/health`
  - UI Health (`/healthz`) via `${SERVICE_APP_BASE_URL}/healthz`
  - Readiness-Gate: API `/health` + GUI `/gui` müssen innerhalb des Retry-Fensters erfolgreich sein (Default: max. 90s)
- **Post-Deploy-Verifikation:** `python3 scripts/check_deploy_version_trace.py`
- **Auth-required Deploy-Smokes (sync/async):**
  - laufen über `python3 ./scripts/run_deploy_smoke.py --profile deploy|nightly ...`
  - enthalten verpflichtend `./scripts/smoke/auth_preflight.sh` als ersten Gate-Step
  - bei fehlender Auth-Konfiguration: fail-fast mit `reason=blocked-by-auth` (statt irreführender API-Regression)
- **Optional, aber vorgesehen:**
  - Strict Split Smoke (`./scripts/run_bl31_routing_tls_smoke.sh`) nur wenn Base-URLs vorhanden

### 3) Nightly/Periodic
- **Stündlicher Dev-Deploy-Lauf** als kontinuierlicher Betriebscheck (`deploy.yml` via cron)
- **Dependency-Unblock-Automation** (`dependency-unblock.yml`) zur Pflege von `status:blocked -> status:todo`

## Verantwortlichkeiten

- **PR Gate:** schützt Merge-Qualität (schnell, deterministisch, fail-fast).
- **Deploy Gate:** schützt Runtime-Qualität nach Build/Deploy.
- **Nightly/Periodic:** überwacht Stabilität und hält Backlog-Status aktuell.

## Konsolidierungsleitplanken für Folge-WPs

1. Neue Smoke-Pfade sollen auf **kanonische Entrypoints** zeigen (kein Duplication-Drift).
2. Neue Checks müssen einem Tier explizit zugeordnet sein (`PR`, `Deploy`, `Nightly`).
3. `must-pass` vs. `informational` muss im Runner-/Report-Schema eindeutig sein (Folge-WP #992).

## Runtime-Benchmark (Issue #993)

Reproduzierbare Auswertung der Deploy-Gate-Laufzeiten vor/nach Runner-Konsolidierung:

```bash
python3 ./scripts/bench_deploy_gate_runtime.py \
  --repo nimeob/geo-ranking-ch \
  --workflow deploy.yml \
  --cutoff-sha f67fdbe \
  --limit 120 \
  --conclusion success \
  --output-json artifacts/issue-993-deploy-gate-benchmark.json \
  > artifacts/issue-993-deploy-gate-benchmark.md
```

Evidence-Referenz: `reports/evidence/issue-993-deploy-gate-benchmark-20260303T202749Z.md`
