# Issue #1094 — Dev-CI Flaky Retry Cap + Markierung (Evidence)

- Timestamp (UTC): 2026-03-04T02:57:41Z
- Branch: `fix/issue-1094`
- Scope: Dev-PR-Gate auf max. 1 Retry begrenzen, Flaky-Kontext im Report erweitern, reproduzierbaren CI-Demo-Run ergänzen.

## Änderungen

1. **Retry-Policy fail-closed auf max. 1 Retry**
   - `scripts/run_dev_smoke_required_with_retry.py`
   - Neue zentrale Policy: `DEV_SMOKE_MAX_RETRIES=1` (oder `--max-retries 1`), Legacy-`max_attempts` wird validiert und >1 Retry hart abgelehnt.

2. **Flaky-Markierung mit Build-Kontext**
   - Retry-Report enthält nun `build_context` (`run_id`, `run_attempt`, `run_url`, `workflow`, `job`, …).
   - Pro flaky Check: `flaky_hint` + `flaky_context` inkl. Build-Kontext.

3. **Deterministischer Flaky-Demo-Lauf in CI**
   - Neuer Runner: `scripts/smoke/dev_smoke_flaky_demo_runner.py` (fail first, pass second).
   - Workflow: `.github/workflows/dev-smoke-required.yml` führt den Demo-Lauf über den Retry-Wrapper aus und hängt Summary an `$GITHUB_STEP_SUMMARY`.

4. **Doku ergänzt**
   - `docs/testing/DEPLOY_TEST_TIERS.md`: neuer Abschnitt **"Flaky in Dev-CI"** mit Definition, Review-Regeln und Entflakungs-Next-Step.
   - `docs/OPERATIONS.md`: Required-Check-Abschnitt auf `DEV_SMOKE_MAX_RETRIES=1` + Build-Kontext-Markierung aktualisiert.

## Testnachweis

```bash
/data/.openclaw/workspace/geo-ranking-ch/.venv-test/bin/python -m pytest -q \
  tests/test_run_dev_smoke_required_with_retry.py \
  tests/test_dev_smoke_flaky_demo_runner.py \
  tests/test_dev_smoke_flaky_docs.py \
  tests/test_pr_fast_gates_config.py \
  tests/test_markdown_links.py
```

Ergebnis: **13 passed**
