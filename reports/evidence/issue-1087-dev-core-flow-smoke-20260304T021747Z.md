# Issue #1087 — Dev Core-Flow Smoke Evidence

- Timestamp (UTC): 20260304T021747Z
- Scope: Login -> Search (`__ok__`) -> Ranking view in required dev smoke gate

## Änderungen
- `tests/test_auth_regression_smoke_issue_1019.py`
  - Kernpfad auf `login -> search -> ranking -> logout` erweitert
  - stabile GUI-/Ranking-Selektoren im Smoke abgesichert
- `scripts/check_bl334_split_smokes.sh`
  - Pflichtschritt BL-334.6 ergänzt: Core-Flow-Auth-Smoke via `python -m unittest -q tests.test_auth_regression_smoke_issue_1019`
  - Laufzeitbudget-Guard `CORE_FLOW_SMOKE_MAX_SECONDS` (Default 300s, fail-closed)
  - Evidence-JSON erweitert um `core_flow`-Block (Dauer/Budget)
- `docs/testing/DEPLOY_TEST_TIERS.md`
  - PR-Gate-Dokumentation um Core-Flow-Smoke + Budget-Guard ergänzt
- `docs/testing/GUI_AUTH_SMOKE_RUNBOOK.md`
  - automatisierter Smoke auf Kernpfad inkl. Ranking-Ansicht aktualisiert

## Ausgeführte Verifikation

```bash
python3 -m unittest -q tests.test_auth_regression_smoke_issue_1019
python3 ./scripts/run_dev_smoke_required_with_retry.py \
  --output-json artifacts/pr-dev-smoke-required.json \
  --report-json artifacts/pr-dev-smoke-required-retry-report.json \
  --summary-markdown artifacts/pr-dev-smoke-required-summary.md
pytest -q tests/test_bl334_split_smokes_script.py tests/test_gui_auth_smoke_runbook_docs.py tests/test_markdown_links.py tests/test_user_docs.py
```

## Ergebnisse
- `tests.test_auth_regression_smoke_issue_1019`: **OK** (1 test)
- `run_dev_smoke_required_with_retry.py`: **PASS**
- Doku-/Guard-Tests: **11 passed**

## Artefakte
- `artifacts/pr-dev-smoke-required.json`
- `artifacts/pr-dev-smoke-required-retry-report.json`
- `artifacts/pr-dev-smoke-required-summary.md`
- `artifacts/bl334/20260304T021716Z-bl334-split-smokes.json` (enthält `core_flow.duration_seconds` + `core_flow.budget_seconds`)
