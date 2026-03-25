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
