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

## 01:12 CET — Canonical-host Parser-Hardening + Live-Recheck
- ROI-Strang fortgeführt: Parser-Hardening für Canonical-Host-Konfiguration, damit `UI_CANONICAL_HOSTS` robust bleibt, auch wenn Einträge versehentlich als volle Origins/mit Port gesetzt werden.
- Änderungen umgesetzt:
  - `src/ui/service.py`
    - `_normalize_host(...)` nutzt jetzt URL-Parsing statt `split(':', 1)`.
    - Ergebnis: Host-Normalisierung funktioniert für `host:port` **und** `https://host[:port]` korrekt.
  - `scripts/smoke/check_ui_canonical_redirect.py`
    - neue Host-Normalisierung für `--canonical-hosts` (Origin-/Port-Inputs werden korrekt auf Host reduziert).
    - Canonical-Host-Vergleich nutzt dieselbe robuste Normalisierung.
  - Tests erweitert:
    - `tests/test_ui_service.py::UiCanonicalConfigTests`
    - `tests/test_check_ui_canonical_redirect.py`
- Verifikation lokal:
  - `.venv/bin/python -m pytest -q tests/test_check_ui_canonical_redirect.py tests/test_ui_service.py::UiCanonicalConfigTests` → **9 passed**.
  - `python3 -m compileall -q src/ui/service.py scripts/smoke/check_ui_canonical_redirect.py` → **ok**.
- Live-UI-Checks DEV (CLI, da Browser-Gateway weiter timeout):
  - `python3 scripts/smoke/check_ui_canonical_redirect.py --base-url https://www.dev.georanking.ch --canonical-origin https://www.dev.georanking.ch --canonical-hosts 'www.dev.geo-ranking.ch,www.dev.georanking.ch' --next '/results/demo-result' --reason 'night_worker_probe'` → **ok=true, status_code=307**.
  - `https://www.dev.geo-ranking.ch/healthz` → **200** (kein Redirect, wie erwartet).
  - `https://www.dev.geo-ranking.ch/results/demo-result?from=night-worker` → **307** auf `https://www.dev.georanking.ch/...`.
