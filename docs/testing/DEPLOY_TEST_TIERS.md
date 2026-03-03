# Deploy/Test Tier Matrix (PR / Deploy / Nightly)

Status: 2026-03-03 (Ist-Stand)
Parent: #976 · Work-Package: #990

## Ziel

Diese Matrix trennt **schnelle PR-Gates**, **verpflichtende Deploy-Gates** und **periodische Läufe** mit klaren Verantwortlichkeiten. Sie dient als Basis für die technische Konsolidierung der Smoke-Entrypoints in den Folge-WPs.

## Tier-Matrix

| Tier | Trigger | Blocking | Muss bestehen (must-pass) | Primäre Entrypoints / Workflows | Verantwortlich |
|---|---|---|---|---|---|
| **PR Gate** | `pull_request` | Ja (für Merge) | schnelle deterministische Vertrags-/Smoke-Checks + Doku-Link-Guard | `.github/workflows/contract-tests.yml` (`./scripts/check_bl334_split_smokes.sh`, API-Contract-Tests), `.github/workflows/docs-quality.yml` (`./scripts/check_docs_quality_gate.sh`) | Repo-CI (GitHub Actions) |
| **Deploy Gate (dev)** | `workflow_dispatch` (on-demand) + stündlich per `schedule` | Ja (für erfolgreichen Deploy-Run) | Build/Test + ECS-Rollout + verpflichtende Health-Smokes + Post-Deploy-Verifikation | `.github/workflows/deploy.yml` (`pytest tests/ -v`, API `/health`, UI `/healthz`, `python3 scripts/check_deploy_version_trace.py`) | Deploy-Workflow + Operator |
| **Nightly/Periodic** | `schedule` (zeitgesteuert) | Lauf-spezifisch (nicht PR-blocking) | periodische Stabilitäts-/Betriebschecks und automatische Entblockung | `.github/workflows/deploy.yml` (stündlicher Dev-Deploy), `.github/workflows/dependency-unblock.yml` (alle 30 min) | Repo-Automation |

## Pflicht-Checks je Tier

### 1) PR Gate (blocking)
- **Service-Split-Smoke:** `./scripts/check_bl334_split_smokes.sh`
- **API-Contract-Fast-Checks:**
  - `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py`
  - `python3 scripts/validate_field_catalog.py`
- **Doku-Qualität:** `./scripts/check_docs_quality_gate.sh`

### 2) Deploy Gate (blocking)
- **Build & Test:** `pytest tests/ -v --tb=short`
- **Deploy API + UI** inkl. `services-stable`
- **Pflicht-Smokes:**
  - API Health (`/health`) via `SERVICE_HEALTH_URL` oder `${SERVICE_API_BASE_URL}/health`
  - UI Health (`/healthz`) via `${SERVICE_APP_BASE_URL}/healthz`
- **Post-Deploy-Verifikation:** `python3 scripts/check_deploy_version_trace.py`
- **Optional, aber vorgesehen:**
  - API `/analyze` Smoke (`./scripts/run_remote_api_smoketest.sh`) nur bei gesetztem `SERVICE_API_AUTH_TOKEN`
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
