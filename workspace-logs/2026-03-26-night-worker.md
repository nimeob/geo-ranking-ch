# 2026-03-26 – Night Worker Log

## 00:03 CET — Session gestartet + UI/Smoke-Status geprüft
- Browser-Tool weiterhin blockiert (`browser.start` Timeout im Gateway).
- Ausweichpfad aktiv genutzt: Live-Smokes gegen DEV statt Browser-UI-Klickpfad.
- `run_login_start_smoke_bundle.sh` geprüft für:
  - `https://www.dev.georanking.ch`
  - `https://www.dev.geo-ranking.ch`
- Ergebnis: beide Bundles **PASS** (Auth-Redirects + Route-Matrix stabil).

## 00:06 CET — ROI-Fix: WebKit-Smoke robust gegen fehlende lokale Node-Abhängigkeiten
- Problem reproduziert: `node scripts/run_issue_986_webkit_smoke.mjs` brach in frischem Worktree mit `ERR_MODULE_NOT_FOUND` (`playwright`) hart ab (ungefilterter Node-Stacktrace, wenig operativ nutzbar).
- Umsetzung:
  - `scripts/run_issue_986_webkit_smoke.mjs`
    - statischen Playwright-Import durch lazy/dynamic import ersetzt.
    - neue Guard-Fehlermeldung mit klarer Install-Anleitung: `npm ci && npx playwright install --with-deps webkit`.
    - bestehende JSON-Evidence-Ausgabe bleibt erhalten (auch bei Dependency-Fehlern), sodass Night-Runs maschinenlesbar bleiben.
  - `tests/test_issue_986_webkit_smoke_script_contract.py`
    - Contract-Test ergänzt für den Missing-Dependency-Guard und actionable hint.

## Verifikation
- `pytest -q tests/test_issue_986_webkit_smoke_script_contract.py` → **3 passed**
- `pytest -q tests/test_gui_webkit_smoke_docs.py tests/test_issue_986_webkit_smoke_script_contract.py` → **5 passed**
- Repro nach Fix:
  - `node scripts/run_issue_986_webkit_smoke.mjs` ohne installiertes Playwright erzeugt nun strukturierte JSON-Evidence mit verständlicher `runError`-Hint statt Crash-Noise.

## 01:15 CET — Follow-up Hardening + Live-Checks (Alias/CNAME stabil, Dependency-Fehler strukturierter)
- ROI-Entscheidung: direkt auf **origin/main (inkl. #1514)** weiterarbeiten und nur einen kleinen, klaren Follow-up-Härtungsschritt ergänzen (kein Busywork).
- Browser/Gateway-Blocker erneut geprüft:
  - `browser.start` weiterhin Timeout.
  - `openclaw gateway status/restart` zeigt lokale OpenClaw-Konfig-Fehler (`ReferenceError: ANTHROPIC_MODEL_ALIASES before initialization`) + deaktivierten systemd-Service.
  - Konsequenz: UI weiterhin über Live-Smokes verifiziert statt Browser-Tool.
- Live-Smoke-Verifikation DEV:
  - `./scripts/check_bl334_split_smokes.sh` → **PASS**
  - `./scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.georanking.ch` → **PASS**
  - `./scripts/smoke/run_login_start_smoke_bundle.sh --base-url https://www.dev.geo-ranking.ch` → **PASS**
- Code-Hardening umgesetzt:
  - `scripts/run_issue_986_webkit_smoke.mjs`
    - `PlaywrightDependencyError` eingeführt (statt generischem `Error`), inkl. installHint-Capture.
    - bei Top-Level-Abbruch (`.catch`) jetzt strukturierte Runtime-Felder:
      - `runtime.playwrightDependencyMissing`
      - `runtime.playwrightInstallHint`
      - `runtime.browser='playwright-dependency-missing'` bei Import-Fehler
      - `limitations[]` enthält klaren Operator-Hinweis
    - Ziel: Night-Reports/CI-Artefakte bleiben bei fehlender Node-Abhängigkeit sofort triagierbar.
  - `tests/test_issue_986_webkit_smoke_script_contract.py`
    - Contract-Checks für neue strukturierte Missing-Dependency-Felder ergänzt.
- Verifikation:
  - `node --check scripts/run_issue_986_webkit_smoke.mjs` → **OK**
  - `pytest -q tests/test_issue_986_webkit_smoke_script_contract.py tests/test_gui_webkit_smoke_docs.py` → **5 passed**
