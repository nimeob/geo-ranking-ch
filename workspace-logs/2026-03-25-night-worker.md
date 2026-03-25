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

---

## 01:47 CET — Branch erstellt + UI-Blocker aktiv angegangen
- Aktion: Branch `night/worker-20260325-0145` von `origin/main` in sauberem Worktree erstellt (ROI: isolierte, pushbare Änderung ohne Altlasten aus dem Root-Worktree).
- UI-Blocker: OpenClaw Browser (`browser.start`) lieferte wiederholt `context canceled`.
- Gegenmaßnahme: `openclaw gateway status/restart/start` geprüft; Browser-Session blieb dennoch nicht nutzbar.
- Entscheidung: Nicht blockieren lassen → UI weiterhin über Live-Smoke gegen `https://www.dev.georanking.ch` / Alias verifiziert.

## 01:55 CET — Reproduktion eines echten Alias-Regression-Gaps (hoher ROI)
- Live-Test: `scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.geo-ranking.ch --env-name dev`
- Befund: Bundle failte, weil Default-Allowlist `auth.dev.geo-ranking.ch` erwartete, tatsächlicher Redirect aber auf `auth.dev.georanking.ch` ging.
- Impact: False-Negative bei legitimen Alias→Canonical Flows (UI-nahe Smoke-Checks instabil).

## 02:06 CET — Fix implementiert (UI-nahe Smoke-Härtung)
- Geändert:
  - `scripts/smoke/run_login_start_smoke_bundle.sh`
    - Default-`--expected-authorize-host` erweitert: bei Hosts mit `geo-ranking` wird zusätzlich die `georanking`-Variante erlaubt.
  - `scripts/smoke/check_ui_login_start.py`
    - Parser für `--expected-authorize-host` erweitert: `geo-ranking`-Alias wird intern um `georanking`-Variante ergänzt.
  - `scripts/smoke/check_bff_auth_proxy_guard.py`
    - gleiche Alias-Normalisierung für Default- und Override-Allowlist, um BFF/UI konsistent zu halten.

## 02:16 CET — Tests + Live-Retests erfolgreich
- Lokal:
  - `pytest -q tests/test_check_ui_login_start.py tests/test_check_bff_auth_proxy_guard.py tests/test_run_login_start_smoke_bundle_script_contract.py`
  - Ergebnis: **61 passed**.
- Live/UI:
  - `run_login_start_smoke_bundle.sh` gegen Alias-Host (`www.dev.geo-ranking.ch`) → **passed**.
  - `run_login_start_smoke_bundle.sh` gegen Canonical (`www.dev.georanking.ch`) → **passed** (keine Regression).
  - `check_bff_auth_proxy_guard.py --ui-base-url https://www.dev.geo-ranking.ch` → **ok=true**.

## Offene Blocker / Nächster Schritt
- Blocker offen: Browser-Tool weiterhin instabil (`context canceled`), trotz Gateway-Checks.
- Nächster Schritt nach Push: PR öffnen + Merge anstoßen; danach optional Deploy-/Nightly-Recheck verfolgen.
