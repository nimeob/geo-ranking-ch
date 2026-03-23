# Night Worker Log — 2026-03-24

## 00:35 CET — CI/UI canonical-host hardening (in progress)
- Basis geprüft: `origin/main` ist auf `37c9e64` (PR #1477 bereits gemerged, Deploy grün).
- Live-Check DEV per curl durchgeführt:
  - `https://www.dev.georanking.ch/healthz` = 200
  - `https://www.dev.geo-ranking.ch/healthz` = 200
  - Alias-Login (`www.dev.geo-ranking.ch/login?...start=1`) liefert `307` auf kanonische Domain.
- Browser-Tool-Check versucht, aber OpenClaw Browser-Gateway timeout; daher auf CLI-/HTTP-Smokes ausgewichen.

## 00:48 CET — Umsetzung
- Neues Smoke-Skript hinzugefügt: `scripts/smoke/check_ui_canonical_redirect.py`
  - Prüft Alias-Host → Canonical-Host Redirect-Vertrag für `/login?...&start=1` inkl. Query-Erhalt.
  - Unterstützt Retry-Budget und JSON-Artefakt-Ausgabe.
  - Behandelt fehlende Alias-Hosts als expliziten `skipped_no_alias_hosts` (exit 0).
- Workflows erweitert:
  - `.github/workflows/deploy.yml`
  - `.github/workflows/deploy-staging.yml`
  - Neuer Step: **Smoke-Test UI canonical-host redirect**
  - Artefaktpfade ergänzt:
    - `artifacts/dev-canonical-host-redirect-smoke.json`
    - `artifacts/staging-canonical-host-redirect-smoke.json`
- Testabdeckung ergänzt:
  - `tests/test_check_ui_canonical_redirect.py`
  - `tests/test_deploy_version_trace_docs.py` um Canonical-Host-Smoke-Guardrails erweitert.

## 00:52 CET — Verifikation
- `pytest -q tests/test_check_ui_canonical_redirect.py tests/test_deploy_version_trace_docs.py` → **23 passed**.
- `pytest -q tests/test_check_ui_login_start.py tests/test_check_ui_canonical_redirect.py tests/test_deploy_version_trace_docs.py` → **46 passed**.
- Live-Skriptcheck DEV:
  - `python3 scripts/smoke/check_ui_canonical_redirect.py --base-url https://www.dev.georanking.ch --canonical-origin https://www.dev.georanking.ch --canonical-hosts 'www.dev.geo-ranking.ch,www.dev.georanking.ch'`
  - Ergebnis: `{"ok": true, "reason": "ok", "status_code": 307, ...}`.
