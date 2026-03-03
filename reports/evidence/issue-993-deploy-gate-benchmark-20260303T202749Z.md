# Issue #993 — Deploy-Gate Laufzeitbenchmark + Auth/API-Regression

Zeitpunkt (UTC): 2026-03-03T20:27:49Z  
Parent: #976  
Work-Package: #993

## 1) Baseline-vs-neu Messung (Deploy-Gate Runtime)

### Reproduzierbarer Mess-Command

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

- Cutoff-Commit `f67fdbe` = Merge des konsolidierten Smoke-Entrypoints (#991).
- Messbasis: GitHub Actions Workflow-Runs `deploy.yml` (success only), Dauer = `updatedAt - startedAt`.

### Ergebnis (aus `artifacts/issue-993-deploy-gate-benchmark.md`)

| Bucket | n | Median | Mean |
|---|---:|---:|---:|
| before | 70 | 08:27 | 08:18 |
| after | 1 | 08:12 | 08:12 |

- Median-Delta (before - after): **00:15** (**+2.96% schneller**)
- Artefakte:
  - `artifacts/issue-993-deploy-gate-benchmark.md`
  - `artifacts/issue-993-deploy-gate-benchmark.json`

> Hinweis zur Stichprobe: `after` enthält derzeit 1 erfolgreichen Lauf seit dem Cutoff; zusätzliche Läufe erhöhen die statistische Sicherheit.

## 2) Kritische Auth-/API-Regression verifiziert

### Reproduzierbarer Test-Command

```bash
../../.venv/bin/python -m pytest -q \
  tests/test_bench_deploy_gate_runtime.py \
  tests/test_run_deploy_smoke.py \
  tests/test_remote_smoke_script.py \
  tests/test_async_jobs_smoke_script.py \
  tests/test_bff_session.py \
  tests/test_bff_token_delegation.py
```

### Ergebnis

- **174 passed in 36.36s**
- Damit sind zentrale Deploy-Smoke-, Auth-Session- und Token-Delegationspfade im Regressionstest grün.

## 3) Parent-Sync (#976)

- Dieses Evidence-Dokument + Benchmark-Artefakte dienen als Nachweis für:
  - Deploy-Gate Laufzeitvergleich (Baseline vs neu)
  - Keine Regression auf kritischen Auth-/API-Pfaden
- Parent-Checklist/Backlog-Sync wird im Abschluss der Iteration aktualisiert.
