# 2026-03-25 – Night Worker Log

## Entscheidung (ROI)
- `run_login_start_smoke_bundle.sh` war bereits zentral im Deploy-Gate verankert, aber die Default-Herleitung für `--expected-authorize-host` deckte Non-`www` Base-URLs nicht sauber ab.
- Risiko: Bei Umgebungen mit Base-URL ohne `www` (z. B. `https://dev.georanking.ch`) könnte der Bundle-Smoke fälschlich fehlschlagen, obwohl Redirects korrekt auf `auth.<host>` laufen.
- Fix priorisiert, weil kleiner Eingriff mit direktem Gate-Stabilitätsgewinn.

## Umsetzung
- Datei geändert: `scripts/smoke/run_login_start_smoke_bundle.sh`
  - Default-Allowlist für Authorize-Hosts erweitert:
    - Für `www.<host>`: `auth.<host-ohne-www>`, `www.<host>`, `<host-ohne-www>`
    - Für Non-`www` Hosts: `auth.<host>`, `<host>`
- Test ergänzt: `tests/test_run_login_start_smoke_bundle_script_contract.py`
  - Neuer Contract-Test stellt sicher, dass die Default-Herleitung sowohl `www`- als auch Non-`www`-Pfad enthält.

## Verifikation
- Lokal:
  - `/data/.openclaw/workspace/geo-ranking-ch/.venv/bin/python -m pytest -q tests/test_run_login_start_smoke_bundle_script_contract.py tests/test_deploy_version_trace_docs.py tests/test_check_ui_login_start.py`
  - Ergebnis: `65 passed`
- Live DEV:
  - `scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev --output-dir artifacts/nightworker-20260325-login-bundle`
  - Ergebnis: PASS für alle GUI/Jobs/Results + Legacy-Routen

## Hinweise
- Browser-Tool war in dieser Session nicht verfügbar (Gateway timeout), daher UI-Checks via bestehende Live-Smoke-Skripte durchgeführt.
