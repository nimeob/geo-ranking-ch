# Issue #1116 — Core Dev Smoke (login -> ranking list -> detail) + Failure Artifacts

## Umsetzung

- `scripts/check_bl334_split_smokes.sh`
  - Core-Flow-Szenario präzisiert auf `login -> search -> ranking list -> detail`.
  - Core-Flow-Unittest läuft jetzt über dediziertes Logfile (`core-flow-smoke.log`).
  - Bei Core-Flow-Failures werden automatisch Evidence-Artefakte erzeugt unter:
    - `reports/evidence/core-flow-smoke/<STAMP>/core-flow-failure-trace.md`
    - `reports/evidence/core-flow-smoke/<STAMP>/core-flow-failure-gui.png` (wenn Chromium verfügbar)
    - plus kopierte Logs (`core-flow-unittest.log`, `api-smoke.log`, `ui-smoke.log`).
  - Erfolgs-JSON (`artifacts/bl334/*-bl334-split-smokes.json`) enthält zusätzlich den `core_flow.log`-Pfad.
- Doku-Sync:
  - `docs/testing/GUI_AUTH_SMOKE_RUNBOOK.md`
  - `docs/testing/DEPLOY_TEST_TIERS.md`
- Guard-Test-Sync:
  - `tests/test_bl334_split_smokes_script.py`

## Nachweise (lokal)

```bash
pytest -q tests/test_bl334_split_smokes_script.py tests/test_gui_auth_smoke_runbook_docs.py tests/test_markdown_links.py tests/test_user_docs.py
```

Ergebnis: `11 passed`.

```bash
python3 -m unittest -q tests.test_auth_regression_smoke_issue_1019
```

Ergebnis: `OK`.

```bash
./scripts/check_bl334_split_smokes.sh
```

Ergebnis: `pass`.

- Evidence JSON: `artifacts/bl334/20260304T041954Z-bl334-split-smokes.json`
- API-Log: `artifacts/bl334/20260304T041954Z-api-smoke.log`
- UI-Log: `artifacts/bl334/20260304T041954Z-ui-smoke.log`
- Core-Flow-Log: `artifacts/bl334/20260304T041954Z-core-flow-smoke.log`
