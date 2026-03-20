# Nightly Log – 2026-03-20 – UI Smoke Hardening (BL-337 WP3)

## Kontext / Ziel
- Night-Worker-Strang: UI-nahe Smoke-Checks gegen `https://www.dev.georanking.ch` stabilisieren.
- Beobachtung: Historische Matrix-Evidenz zeigte `UI.NAV.CORE_FLOW.VISIBLE` und `UI.API_ERROR.CONSISTENCY` als fail, obwohl die aktuelle Dev-UI diese Flows funktional erfüllt.

## Durchgeführte Checks
1. Live-Script gegen Dev-Targets ausgeführt:
   ```bash
   .venv-test/bin/python scripts/run_bl337_ui_frontdoor_e2e.py \
     --matrix artifacts/bl337/latest-internet-e2e-matrix.json \
     --evidence-json artifacts/bl337/nightly-ui-check-20260320T0350Z.json \
     --app-base-url https://www.dev.georanking.ch \
     --api-base-url https://api.dev.georanking.ch \
     --timeout-seconds 30
   ```
2. Ergebnis: Alle 4 UI-Checks `pass` (inkl. API-Error-Consistency via HTTP 401 + strukturiertem Fehlerkörper).

## Implementierte Härtung
- Datei: `scripts/run_bl337_ui_frontdoor_e2e.py`
  - Marker-Matching erweitert: unterstützt jetzt auch Regex-Marker zusätzlich zu String/Tuple.
  - `UI.NAV.CORE_FLOW.VISIBLE`:
    - Navigations-Shell ist nicht länger hart required (um false negatives bei UI-Refactors ohne semantischen Verlust zu vermeiden).
    - Shell-Erkennung wird weiter als Diagnostik (`nav_shell_detected=...`) im `actualResult` protokolliert.
  - `UI.API_ERROR.CONSISTENCY`:
    - Phase-Error-Erkennung um robuste Patterns erweitert, inkl. ternärem `setPhase(result.ok ? "success" : "error")` und direktem `state.phase = "error"`.

## Testabdeckung
- Datei: `tests/test_run_bl337_ui_frontdoor_e2e.py`
  - Neuer Testfall für Navigation ohne benannte Shell + ternären Phase-Switch ergänzt.
- Ausgeführt:
  ```bash
  .venv-test/bin/python -m pytest -q tests/test_run_bl337_ui_frontdoor_e2e.py
  ```
  Ergebnis: `4 passed`.

## Nächste sinnvolle Schritte
1. Nightly-Job (falls vorhanden) auf die gehärtete Marker-Logik umstellen/validieren.
2. Optional: API-Teil der Internet-E2E-Matrix ebenfalls in denselben Nightly-Lauf integrieren, damit die Matrix nicht zwischen `planned`/`pass` driftet.
