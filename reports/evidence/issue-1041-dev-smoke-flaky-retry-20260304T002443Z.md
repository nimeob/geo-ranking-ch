# Issue #1041 — Dev-Smoke Retry/Flaky Hardening Evidence

Timestamp (UTC): 2026-03-04T00:24:43Z

## Scope umgesetzt
- PR-Gate `dev-smoke-required` auf zentralen Retry-Wrapper umgestellt:
  - `.github/workflows/dev-smoke-required.yml`
  - zentrale Job-Policy via `DEV_SMOKE_MAX_ATTEMPTS` + `DEV_SMOKE_RETRY_DELAY_SECONDS`
- Neuer Wrapper `scripts/run_dev_smoke_required_with_retry.py`:
  - führt `run_deploy_smoke.py --profile pr --flow sync` mit Retry aus
  - erzeugt Retry-Report `artifacts/pr-dev-smoke-required-retry-report.json`
  - markiert flaky Kandidaten pro Check (`flaky_hint`) im Testreport
  - erzeugt CI-Summary-Markdown mit Counts für `retried checks` / `flaky candidates`
- Doku-Sync:
  - `docs/testing/DEPLOY_TEST_TIERS.md`
  - `docs/OPERATIONS.md`

## Reproduzierbare Tests
```bash
/data/.openclaw/workspace/geo-ranking-ch/.venv-test/bin/python -m pytest -q \
  tests/test_run_dev_smoke_required_with_retry.py \
  tests/test_pr_fast_gates_config.py \
  tests/test_markdown_links.py \
  tests/test_user_docs.py
```

Ergebnis: `17 passed in 0.57s`

## DoD/AC Mapping
- Retry-Verhalten zentral konfiguriert: ✅ (`DEV_SMOKE_MAX_ATTEMPTS`, `DEV_SMOKE_RETRY_DELAY_SECONDS` im Workflow)
- Testreport mit Flaky-Hinweis je betroffenem Testfall: ✅ (`flaky_hint` in `tests[]` des Retry-Reports)
- CI-Summary enthält Anzahl flaky/retried Tests: ✅ (`artifacts/pr-dev-smoke-required-summary.md` → `$GITHUB_STEP_SUMMARY`)
- Doku beschreibt Flaky-Definition: ✅ (`docs/testing/DEPLOY_TEST_TIERS.md`, `docs/OPERATIONS.md`)
