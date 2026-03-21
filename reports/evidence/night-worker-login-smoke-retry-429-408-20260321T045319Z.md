# Night Worker Evidence — Login-Smoke Retry Hardening (408/429)

- **Zeit (UTC):** 2026-03-21T04:53:19Z
- **Branch:** `fix/login-smoke-retry-429-408`
- **Scope:** Härtung von `scripts/smoke/check_ui_login_start.py` gegen transiente HTTP-Fehler (`408`, `429`) inkl. `Retry-After`-Respektierung.

## Änderungen

1. `scripts/smoke/check_ui_login_start.py`
   - Retry-Menge erweitert: `{408, 429, 502, 503, 504}`.
   - Neue Helper-Funktion `_resolve_retry_delay(...)`:
     - unterstützt numerisches `Retry-After`
     - unterstützt HTTP-Date `Retry-After`
     - fällt sicher auf `--retry-delay` zurück.
   - `HTTPError`-Headerzugriff fail-safe (`exc.headers or {}`).

2. `tests/test_check_ui_login_start.py`
   - Neuer Regressionstest:
     - `test_check_login_start_retries_transient_http_429_with_retry_after`

## Verifikation

```bash
./.venv-test/bin/python -m pytest -q tests/test_check_ui_login_start.py
# 13 passed
```

## Live-Dev-Checks (post-deploy)

Deploy-Run beobachtet: `23372242310` (success).

Zusätzliche manuelle Smokes gegen `https://www.dev.georanking.ch`:

- `next=/gui` → `ok=true`, authorize redirect vorhanden
  - `reports/evidence/ui-login-start-nightly-20260321T045252Z-gui.json`
  - `reports/evidence/ui-login-start-nightly-20260321T045252Z-gui.stdout.json`
- `next=/gui/history` → `ok=true`, authorize redirect vorhanden
  - `reports/evidence/ui-login-start-nightly-20260321T045252Z-history.json`
  - `reports/evidence/ui-login-start-nightly-20260321T045252Z-history.stdout.json`
