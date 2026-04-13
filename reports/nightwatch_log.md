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

## 2026-04-13 04:45 CET — Bundle-Runner CWD-Härtung (ROI)
- Deploy-Status verifiziert: GitHub Actions Run `24322757032` (**main / Deploy to AWS (ECS dev)**) vollständig **grün** inkl. API/UI-Deploy und Login-/Canonical-/Auth-Guard-Smokes.
- Volltestlauf verifiziert: `pytest -q` → **1967 passed, 2 skipped, 179 subtests passed**.
- ROI-Gap geschlossen: Bundle-Skripte waren bei Aufruf aus fremdem Working-Directory anfällig (relative Pfade + Probe-Skript-Aufruf).
- Umsetzung:
  - `scripts/smoke/run_login_start_smoke_bundle.sh`
  - `scripts/smoke/run_canonical_redirect_smoke_bundle.sh`
  - Beide Runner lösen jetzt `--output-dir`/`--summary-json` relativ zum Repo-Root auf und rufen Probe-Skripte via absolute `REPO_ROOT`-Pfadreferenz auf.
- Regressionstests ergänzt:
  - `tests/test_run_login_start_smoke_bundle_script_contract.py`
  - `tests/test_run_canonical_redirect_smoke_bundle_script_contract.py`
  - Neu: Relative-Path/CWD-Contracts (Aufruf aus fremdem `cwd`) für beide Bundle-Runner.
- Lokal grün: `pytest -q tests/test_run_login_start_smoke_bundle_script_contract.py tests/test_run_canonical_redirect_smoke_bundle_script_contract.py` → **34 passed**.
- Live-Sanity gegen DEV weiterhin **ok**:
  - `check_ui_login_start.py --base-url https://www.dev.georanking.ch`
  - `check_ui_canonical_redirect.py --base-url https://www.dev.georanking.ch`
  - `check_bff_auth_proxy_guard.py --api-base-url https://api.dev.georanking.ch --ui-base-url https://www.dev.georanking.ch`
- Branch-Update:
  - Commit `4ef61ee` — `smoke: resolve bundle paths from repo root`
  - nach `origin/night/worker-20260413-ui-roi` gepusht.

## 2026-04-13 05:30 CET — Dev-UI-Full-Regression CWD-Härtung (ROI-Folge)
- ROI-Lücke identifiziert: `scripts/run_dev_ui_live_full_regression.mjs` war bei Aufruf aus fremdem `cwd` inkonsistent.
  - Relative `DEV_UI_FULL_EVIDENCE_JSON`/`DEV_UI_FULL_SCREENSHOT_DIR` wurden gegen `process.cwd()` statt Repo-Root aufgelöst.
  - Der Login-Start-Fallback (`--fallback-login-start`) nutzte ein relatives Script-Kommando, das außerhalb des Repo-CWD brechen konnte.
- Umsetzung:
  - Script berechnet nun `REPO_ROOT` über `import.meta.url`.
  - Relative Evidence-/Screenshot-Pfade werden mit `resolvePathAgainstRepoRoot(...)` stabil gegen Repo-Root normalisiert.
  - Fallback-Runner wird über absoluten Script-Pfad + `cwd: REPO_ROOT` ausgeführt.
  - Konsolen-Ausgabe verweist auf den effektiv aufgelösten absoluten Evidence-Pfad.
- Regressionen ergänzt:
  - `tests/test_run_dev_ui_live_full_regression_script_contract.py`
    - neuer Guard auf Repo-Root-Path-Resolution + Fallback-Spawn (`cwd: REPO_ROOT`)
    - neuer Laufzeit-Contract: relativer `DEV_UI_FULL_EVIDENCE_JSON` wird bei fremdem `cwd` unter Repo-Root geschrieben.
- Lokal verifiziert:
  - `pytest -q tests/test_run_dev_ui_live_full_regression_script_contract.py tests/test_gui_dev_live_full_regression_script.py` → **16 passed**
  - `pytest -q tests/test_run_* tests/test_dev_smoke_* tests/test_gui_dev_live_auth_analyze_smoke_* tests/test_gui_webkit_smoke_* tests/test_gui_dev_live_full_regression_script.py` → **184 passed, 3 subtests passed**
- Dev-Sanity (live endpoint-basiert):
  - `run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev` → **passed**
  - `run_canonical_redirect_smoke_bundle.sh --base-url https://www.dev.georanking.ch --env-name dev` → **passed**

## 2026-04-13 06:27 CET — Legacy `--out` Alias für UI-Full-Regression wiederhergestellt (ROI)
- Konkreter Operator-Blocker reproduziert: `scripts/run_dev_ui_live_full_regression.mjs` brach bei altem Aufrufschema mit `Unknown option: --out` ab.
- Umsetzung:
  - `scripts/run_dev_ui_live_full_regression.mjs` akzeptiert jetzt `--out <path>` als Legacy-Alias für `--evidence-json <path>`.
  - `--help` dokumentiert den Alias explizit (Legacy-Compatibility), damit Night-Runs/alte Snippets nicht mehr hart fehlschlagen.
- Regressionen ergänzt:
  - `tests/test_run_dev_ui_live_full_regression_script_contract.py`
    - neuer Laufzeit-Contract: `--out` schreibt Evidence korrekt.
    - `--help`-Contract prüft jetzt zusätzlich die sichtbare `--out`-Option.
- Lokal verifiziert:
  - `pytest -q tests/test_run_dev_ui_live_full_regression_script_contract.py tests/test_gui_dev_live_full_regression_script.py tests/test_run_dev_ui_auth_analyze_smoke_script_contract.py tests/test_run_dev_smoke_bundle_cli.py` → **47 passed**.
  - CLI-Sanity: `DEV_UI_BASE_URL=https://www.dev.georanking.ch node scripts/run_dev_ui_live_full_regression.mjs --out <tmp>/evidence.json` → erwarteter Credentials-Fail, aber Evidence wurde korrekt geschrieben (kein Unknown-Option-Fail).
- Dev-UI-Sanity (degraded, mangels Live-Creds):
  - `node scripts/run_dev_ui_live_full_regression.mjs --base-url https://www.dev.georanking.ch --fallback-login-start --headless --out reports/evidence/night-ui-full-legacy-out-20260413T042710Z.json` → **PASSED (degraded mode)**.

## 2026-04-13 06:30 CET — Issue-986 Smoke-CLI kompatibel gemacht (`--base-url/--json-out`)
- Nächster ROI-Blocker reproduziert: `scripts/run_issue_986_webkit_smoke.mjs` akzeptierte bisher nur `--help`; typische Runner-Aufrufe mit `--base-url --headless --json-out` scheiterten mit `unknown_cli_args`.
- Umsetzung:
  - CLI-Parser erweitert um
    - `--base-url <url>`
    - `--evidence-json <path>`
    - `--json-out <path>` (Legacy-Alias)
    - `--headless` (kompatibler No-Op, Runner bleibt headless)
  - Evidence-Output kann jetzt optional auf expliziten Zielpfad geschrieben werden (statt nur Auto-Stamp in `reports/evidence/`).
- Regressionen ergänzt:
  - `tests/test_issue_986_webkit_smoke_script_contract.py` (CLI-Override-Guards)
  - `tests/test_issue_mobile_smoke_cli_usage.py` (Help-Run mit Legacy-Flags darf nicht als unknown failen)
- Lokal verifiziert:
  - `pytest -q tests/test_issue_986_webkit_smoke_script_contract.py tests/test_issue_mobile_smoke_cli_usage.py` → **16 passed**.
- Dev-UI-Livecheck ausgeführt (mit neuer CLI):
  - `node scripts/run_issue_986_webkit_smoke.mjs --base-url https://www.dev.georanking.ch/gui --headless --json-out reports/evidence/night-issue-986-cli-compat-20260413T043017Z.json`
  - Ergebnis: **ok=true**, Login-Entry sichtbar, Map-Interaktion bestanden; auf Runner weiterhin erwarteter Chromium-Fallback wegen fehlender nativer WebKit-Libs (`runtime.webkitMissingLibraries`).

## 2026-04-13 06:37 CET — CLI-Kompatibilität auch für Issue-981/1016 Mobile-Smokes
- ROI-Ziel: Konsistente Runner-Operatorik für mobile Issue-Smokes, damit bestehende Aufrufmuster (`--base-url --headless --json-out`) nicht auf einzelnen Scripts brechen.
- Umsetzung:
  - `scripts/run_issue_981_mobile_smoke.mjs`
  - `scripts/run_issue_1016_mobile_ux_smoke.mjs`
  - Beide akzeptieren jetzt:
    - `--base-url <url>`
    - `--evidence-json <path>`
    - `--json-out <path>` (Alias)
    - `--headless` (kompatibler No-Op)
  - Optionaler JSON-Output kann auf expliziten Pfad geschrieben werden.
- Regressionen ergänzt:
  - `tests/test_issue_mobile_smoke_cli_usage.py` (Help mit Legacy-Flags für 1016/981/986)
  - `tests/test_issue_1016_mobile_ux_smoke_script_contract.py` (CLI-Override-Snippets)
  - `tests/test_issue_981_mobile_smoke_script_contract.py` (CLI-Override-Snippets)
- Lokal verifiziert:
  - `pytest -q tests/test_issue_mobile_smoke_cli_usage.py tests/test_issue_1016_mobile_ux_smoke_script_contract.py tests/test_issue_981_mobile_smoke_script_contract.py tests/test_issue_986_webkit_smoke_script_contract.py` → **24 passed**
- Dev-Livechecks mit neuer CLI:
  - `node scripts/run_issue_981_mobile_smoke.mjs --base-url https://www.dev.georanking.ch/gui --headless --json-out reports/evidence/night-issue-981-cli-compat-20260413T043641Z.json` → **ok=true**
  - `node scripts/run_issue_1016_mobile_ux_smoke.mjs --base-url https://www.dev.georanking.ch/gui --headless --json-out reports/evidence/night-issue-1016-cli-compat-20260413T043657Z.json` → **ok=true**

## 2026-04-13 06:40 CET — Dev-UI-Auth-Analyze CLI Missing-Value-Härtung
- ROI-Regression geschlossen: `scripts/run_dev_ui_auth_analyze_smoke.mjs` konnte bisher Kurzflags (`-h`) fälschlich als Wert zu `--<flag>` konsumieren.
- Umsetzung:
  - CLI-Parser-Guard in `consumeValue(...)` auf `next.startsWith('-')` gehärtet (statt nur `--`), damit fehlende Werte konsistent als `missing_value_for_--...` fehlschlagen.
- Regressionstest ergänzt:
  - `tests/test_run_dev_ui_auth_analyze_smoke_script_contract.py`
  - neuer Contract: `--summary-json -h` → Exit-Code `2`, Usage auf `stderr`, **keine** Evidence-Nebenwirkung.
- Lokal verifiziert:
  - `pytest -q tests/test_run_dev_ui_auth_analyze_smoke_script_contract.py` → **27 passed**.
- Dev-Sanity (Fallback-Mode ohne Live-Creds):
  - `node scripts/run_dev_ui_auth_analyze_smoke.mjs --base-url https://www.dev.georanking.ch --gui-path /gui --fallback-login-start --headless --summary-json reports/evidence/night-dev-ui-auth-analyze-20260413T044032Z.json`
  - Ergebnis: **PASS**, Summary + Evidence geschrieben.
## 2026-04-13 07:58 CET — CWD-unabhängige Issue-Smoke-Runner + GH-Auth-Entblockung
- ROI-Ziel: Night-Runner robust machen, auch wenn Scripts nicht aus Repo-Root gestartet werden (z. B. externe Runner/tmp-CWD).
- Umsetzung (Pfadauflösung auf Script-Standort statt `process.cwd()`):
  - `scripts/run_issue_1016_mobile_ux_smoke.mjs`
  - `scripts/run_issue_981_mobile_smoke.mjs`
  - `scripts/run_issue_986_webkit_smoke.mjs`
  - `scripts/run_issue_1039_mobile_overflow_smoke.cjs`
  - `scripts/run_issue_1142_mobile_table_overflow_smoke.cjs`
- Regressionen ergänzt:
  - `tests/test_issue_1016_mobile_ux_smoke_script_contract.py`
  - `tests/test_issue_981_mobile_smoke_script_contract.py`
  - `tests/test_issue_986_webkit_smoke_script_contract.py`
  - `tests/test_issue_1039_mobile_overflow_smoke_script.py`
  - `tests/test_issue_1142_mobile_overflow_script_contract.py`
- Lokal verifiziert:
  - `python3 -m pytest -q tests/test_issue_1016_mobile_ux_smoke_script_contract.py tests/test_issue_981_mobile_smoke_script_contract.py tests/test_issue_986_webkit_smoke_script_contract.py tests/test_issue_1039_mobile_overflow_smoke_script.py tests/test_issue_1142_mobile_overflow_script_contract.py tests/test_issue_mobile_smoke_cli_usage.py`
  - Ergebnis: **38 passed**.
- Laufzeit-Check (CWD-unabhängig):
  - Start aus `/tmp` mit `--json-out reports/evidence/...` für Issue-1039 + Issue-981.
  - Ergebnis: Evidence landet korrekt unter `<repo>/reports/evidence/...` (nicht unter `/tmp/reports/evidence`).
- Git:
  - Commit: `e9cda80` (`fix(smoke): resolve repo root from script path for issue runners`)
  - Branch: `night/worker-20260413-ui-roi`
  - Push: `origin/night/worker-20260413-ui-roi`
- Blocker-Entschärfung:
  - `gh issue list` mit globalem Token weiter 401.
  - Repo-spezifisch funktioniert API über `./scripts/gha ...` (GH-App-Token wrapper) zuverlässig.
  - Offenen `status:todo`-Strang identifiziert: `#1519` (Alias-Host TLS-Mismatch im Route-Matrix-Kontext).

## 2026-04-13 08:09 CET — Alias-Route-Matrix: angefragten Origin optional strikt prüfen (#1519)
- Problemfokus: `run_login_start_smoke_bundle.sh` kanonisiert Legacy-Non-WWW-Hosts standardmäßig auf `www.*`; dadurch kann Alias-Origin-Drift/TLS-Breakage in Workflow-Smokes verdeckt werden.
- Umsetzung:
  - Neuer Flag in `scripts/smoke/run_login_start_smoke_bundle.sh`: `--preserve-requested-base-url`
  - Bei gesetztem Flag wird die Legacy-Host-Kanonisierung bewusst übersprungen, damit exakt der angefragte Alias-Origin geprüft wird.
  - Dev-Deploy-Alias-Smoke wired mit strict-origin Modus:
    - `.github/workflows/deploy.yml` (Alias-Route-Matrix-Step nutzt jetzt `--preserve-requested-base-url`).
- Regressionen:
  - `tests/test_run_login_start_smoke_bundle_script_contract.py`
    - Option-Surface erweitert
    - neuer Contract: Legacy-Origin + `--preserve-requested-base-url` erzeugt **keine** Kanonisierungs-Warnung.
  - `tests/test_deploy_version_trace_docs.py`
    - Workflow-Guard erweitert: Alias-Smoke muss `--preserve-requested-base-url` enthalten.
- Verifikation:
  - `python3 -m pytest -q tests/test_run_login_start_smoke_bundle_script_contract.py tests/test_deploy_version_trace_docs.py`
  - Ergebnis: **44 passed**.
- Live-Verifikation (direkter Alias-Origin, ohne Kanonisierung):
  - `scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://dev.geo-ranking.ch --env-name dev-alias-manual --preserve-requested-base-url --output-dir reports/evidence --routes /gui --timeout 8 --max-attempts 1 --retry-delay 0 --max-retry-delay 1` → **PASS** (`reason=ok`, `status_code=302`).
  - `scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://dev.georanking.ch --env-name dev-alias-manual-georanking --preserve-requested-base-url --output-dir reports/evidence --routes /gui --timeout 8 --max-attempts 1 --retry-delay 0 --max-retry-delay 1` → **PASS** (`reason=ok`, `status_code=302`).
