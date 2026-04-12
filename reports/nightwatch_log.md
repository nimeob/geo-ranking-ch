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

## 2026-03-26 02:22 CET — Canonical-Redirect-Smoke ohne Env-Abhängigkeit gehärtet
- ROI-Fokus: Die Canonical-Host-Smoke (`check_ui_canonical_redirect.py`) war faktisch abhängig von gesetztem `UI_CANONICAL_HOSTS`. Ohne diese Variable wurde der Check als `skipped_no_alias_hosts` beendet (Signalverlust trotz vorhandener `geo-ranking` ↔ `georanking` Alias-Konvention).
- Umsetzung:
  - `scripts/smoke/check_ui_canonical_redirect.py` erweitert um automatische Alias-Inferenz aus `canonical_origin`:
    - `geo-ranking` → `georanking`
    - `georanking` → `geo-ranking`
  - Fallback greift nur, wenn weder `--alias-host` noch `--canonical-hosts` einen Alias liefern.
  - CLI-Hilfe für `--canonical-hosts` präzisiert (Alias-Inferenz dokumentiert).
- Tests:
  - `tests/test_check_ui_canonical_redirect.py` um Inferenz-Regression erweitert.
  - Skip-Regression auf neutralen Host (`www.example.com`) umgestellt, damit die neue Inferenz nicht versehentlich als Regression zählt.
  - Lokal grün:
    - `pytest -q tests/test_check_ui_canonical_redirect.py` → **17 passed**
    - `pytest -q tests/test_check_ui_login_start.py tests/test_check_ui_canonical_redirect.py` → **59 passed**
- Live-Verifikation (DEV UI):
  - `python3 scripts/smoke/check_ui_canonical_redirect.py --base-url https://www.dev.georanking.ch` → **ok**, nicht mehr `skipped`, Alias automatisch `www.dev.geo-ranking.ch`.
- Blocker/Entscheidung:
  - Browser-Tool war heute Nacht im Runner nicht verfügbar (`browser.open` timeout / Gateway-Hinweis). Deshalb UI-Verifikation über Live-HTTP-Smokes fortgeführt statt GUI-Interaktion zu blockieren.

## 2026-04-01 05:30 CET — Route-Subset-Hints im Live-Auth-Runner gehärtet
- Live-Verifikation gegen DEV durchgeführt:
  - `check_ui_login_start.py --base-url https://www.dev.georanking.ch` → **ok**
  - `check_ui_canonical_redirect.py --base-url https://www.dev.georanking.ch` → **ok**
  - `check_bff_auth_proxy_guard.py --api-base-url https://api.dev.georanking.ch --ui-base-url https://www.dev.georanking.ch` → **ok**
  - `run_gui_live_auth_analyze_route_set.sh --fallback-login-start-on-preflight-fail --routes "/,/gui,/jobs/demo-job"` → erwarteter **degraded fallback** (fehlende Live-Secrets), Login-Start-Bundle **ok**.
- ROI-Gap identifiziert: Bei Preflight-Blockern verloren die CLI-Hints die explizite `--routes`-Auswahl; dadurch drohten unnötig breite Retests.
- Umsetzung in `run_gui_live_auth_analyze_route_set.sh`:
  - Route-Subset einmal zentral normalisiert (`fallback_route_args`) und sowohl für den echten Fallback-Run als auch für die Manual-Hints genutzt.
  - Fehler-Hints tragen jetzt optional `--routes <normalisierte_subset_csv>` sowohl für `run_login_start_smoke_bundle.sh` als auch für den Auto-Fallback-Aufruf.
- Regressionstest ergänzt:
  - `tests/test_run_gui_live_auth_analyze_route_set_preflight.py` prüft jetzt, dass bei Secret-Blockern + whitespace/duplicate-CSV die Hinweise das normalisierte Subset (`/gui,/jobs?source=smoke`) enthalten.
- Teststatus lokal:
  - `pytest -q tests/test_run_gui_live_auth_analyze_route_set_preflight.py` → **16 passed**
  - `pytest -q tests/test_run_gui_live_auth_analyze_route_set_preflight.py tests/test_run_login_start_smoke_bundle_script_contract.py tests/test_run_canonical_redirect_smoke_bundle_script_contract.py` → **30 passed**
- Nächstes Paket (direkt danach): weitere ROI-Härtung der Smoke-Runner-Operatorik (Fehlermeldungen/Artefakt-Transparenz) entlang echter DEV-Checks.

## 2026-04-01 05:35 CET — Unterstützte Routen bei CSV-Fehlern sichtbar gemacht
- Folge-ROI aus Operatorik: Bei `--routes`-Fehleingaben war zwar der fehlerhafte Token sichtbar, aber nicht sofort die gültige Matrix.
- Umsetzung in `scripts/smoke/gui_smoke_routes.sh`:
  - neue Helper `gui_smoke_supported_routes_csv` + `gui_smoke_print_supported_routes_hint`.
  - Bei `invalid` und `unsupported` Route-Tokens wird jetzt zusätzlich `HINT: Supported routes: ...` ausgegeben.
- Wirkung: gilt automatisch für alle Bundle-Runner, die den Shared-Parser nutzen (`run_gui_live_auth_analyze_route_set.sh`, `run_login_start_smoke_bundle.sh`, `run_canonical_redirect_smoke_bundle.sh`).
- Tests aktualisiert:
  - `tests/test_run_gui_live_auth_analyze_route_set_preflight.py`
  - `tests/test_run_login_start_smoke_bundle_script_contract.py`
  - `tests/test_run_canonical_redirect_smoke_bundle_script_contract.py`
  - Lokal: `pytest -q ...` (alle drei Dateien) → **30 passed**.
- Live-Sanity:
  - `run_gui_live_auth_analyze_route_set.sh --base-url https://www.dev.georanking.ch --routes "/gui,/jobs?source=smoke"` (ohne Secrets) zeigt jetzt fallback-Hints inkl. normalisiertem Route-Subset.
- Nächstes Paket: weitere Smoke-UX-Härtung (präzisere Blocker-/Fallback-Evidence) falls nächtliche Runs erneute Ambiguitäten zeigen.

## 2026-04-03 07:35 CET — Canonical-Redirect-Bundle Log-Rauschen reduziert + DEV-Sanity
- Live-Checks gegen `https://www.dev.georanking.ch` erneut ausgeführt:
  - `run_login_start_smoke_bundle.sh --route-presets all` → **passed** (alle Entry-Routen 302→Login-Start ok)
  - `run_canonical_redirect_smoke_bundle.sh --route-presets all` → **passed** (Alias→Canonical Redirects konsistent)
- ROI-Gap identifiziert: Canonical-Bundle schrieb bisher pro Route die komplette JSON-Payload auf stdout (sehr laute CI/Nacht-Logs, schwieriger zu scannen).
- Umsetzung:
  - `check_ui_canonical_redirect.py` um `--quiet` erweitert (unterdrückt stdout-JSON, Artefakt-JSON via `--output-json` bleibt unverändert).
  - `run_canonical_redirect_smoke_bundle.sh` nutzt `--quiet` jetzt im Probe-Loop und emittiert stattdessen kompakte Statuszeilen je Route:
    - `route`, `rc`, `reason`, `status_code`, `skipped`.
- Regressionen ergänzt:
  - `tests/test_check_ui_canonical_redirect.py`: neuer Quiet-Contract (kein stdout, JSON-Datei weiterhin korrekt)
  - `tests/test_run_canonical_redirect_smoke_bundle_script_contract.py`: prüft `--quiet`-Nutzung + kompakte Route-Statuszeilen
- Lokale Tests:
  - `pytest -q tests/test_check_ui_canonical_redirect.py tests/test_run_canonical_redirect_smoke_bundle_script_contract.py` → **33 passed**
  - `pytest -q tests/test_smoke_probe_cli_usage.py tests/test_run_canonical_redirect_smoke_bundle_script_contract.py tests/test_check_ui_canonical_redirect.py` → **35 passed**
- Live-Sanity nach Änderung:
  - `run_canonical_redirect_smoke_bundle.sh --route-presets minimal` zeigt jetzt kurze, scannbare Route-Zeilen und bleibt **passed**.
