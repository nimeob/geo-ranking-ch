# Nightwatch Log

## 2026-03-25 00:15 CET — Restart
- Nacht-Worker neu gestartet: Kontext übernommen, auf `origin/main` in frischem Worktree gewechselt (lokaler Alt-Branch war stark diverged).

## 2026-03-25 00:20 CET — Live-Checks (dev)
- `scripts/smoke/check_ui_login_start.py` gegen `https://www.dev.georanking.ch` ausgeführt → **ok** (Entry + Start Redirect zum erwarteten Auth-Host).
- `scripts/smoke/check_bff_auth_proxy_guard.py` gegen `https://api.dev.georanking.ch` + `https://www.dev.georanking.ch` ausgeführt → **ok** (trusted host erlaubt, untrusted host korrekt blockiert).

## 2026-03-25 00:27 CET — CI/Smoke-Härtung
- `scripts/smoke/auth_preflight.sh` robustifiziert:
  - konfigurierbare Curl-Zeitlimits (`OIDC_CONNECT_TIMEOUT_SECONDS`, `OIDC_MAX_TIME_SECONDS`)
  - konfigurierbare Retry-Strategie (`OIDC_MAX_ATTEMPTS`, `OIDC_RETRY_DELAY_SECONDS`, `OIDC_MAX_RETRY_DELAY_SECONDS`)
  - Retry-Loop für transiente OIDC-Fehler (408/429/500/502/503/504)
  - `Retry-After`-Header wird ausgewertet (Delta-Sekunden oder HTTP-Date)
- Tests erweitert und lokal grün:
  - `pytest -q tests/test_auth_preflight_script.py tests/test_run_login_start_smoke_bundle_script_contract.py` → **11 passed**

## 2026-03-25 00:29 CET — Push/PR
- Branch `night/worker-20260325-0015` nach GitHub gepusht.
- PR erstellt: **#1498**  
  https://github.com/nimeob/geo-ranking-ch/pull/1498
- CI-Checks gestartet (`dev-smoke-required`, `gui-webkit-smoke`).

## 2026-03-25 00:31 CET — CI-Resultat
- PR #1498 Checks abgeschlossen: **grün**
  - `dev-smoke-required` ✅
  - `gui-webkit-smoke` ✅

## 2026-03-25 00:53 CET — Auth-Proxy-Guard weiter gehärtet
- Gap identifiziert: `check_bff_auth_proxy_guard.py` prüfte bisher nur `...authorize`-Pfad, aber keinen Allow-List-Host für absolute Redirects.
- Erweiterung umgesetzt:
  - neuer CLI-Parameter `--expected-authorize-host` (comma-separated allow-list)
  - Default-Ableitung aus `--ui-base-url` (`auth.<base-host-ohne-www>` + `<ui-host>`)
  - trusted `/auth/login` schlägt nun fail-closed fehl, wenn Redirect auf nicht erlaubten Host zeigt.
- Test-Suite erweitert:
  - neuer Negativtest für Host-Mismatch
  - neuer Positivtest für expliziten Custom-Allow-List-Host
  - bestehende Tests angepasst (JSON enthält nun `expected_authorize_hosts`)
  - `pytest -q tests/test_check_bff_auth_proxy_guard.py` → **12 passed**
- Live-Retest gegen DEV:
  - `check_bff_auth_proxy_guard.py --api-base-url https://api.dev.georanking.ch --ui-base-url https://www.dev.georanking.ch` → **ok**
  - Ausgabe enthält erwartete Allow-List `auth.dev.georanking.ch`, `www.dev.georanking.ch`.
- Parallel überwacht:
  - Deploy-Run `23517454230` (push, main) ✅ erfolgreich
  - Deploy-Run `23517501302` (schedule, main) läuft weiter (Build grün, Deploy in Arbeit).
