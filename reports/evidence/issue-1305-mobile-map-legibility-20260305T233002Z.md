# Issue #1305 — Mobile Map Legibility Verification

Datum: 2026-03-06 (Europe/Berlin)

## Scope
Dev(UI): Karten-/Marker-Lesbarkeit in der Ergebnis-Detailansicht verbessern.

## Verifikation

### 1) Regression-Test (Component/Contract)
```bash
pytest -q tests/test_web_service_gui_mvp.py
```
Ergebnis: **10 passed**

### 2) Viewport-/Screenshot-Check (manuelle Sichtprüfung anhand erzeugter Browser-Screenshots)
- Lokaler UI-Service gestartet:
```bash
env -u UI_API_BASE_URL PYTHONPATH=. PORT=8787 python3 src/ui/service.py
```
- Headless-Chromium (Playwright) für Viewports `390x844` und `768x1024` ausgeführt.
- In beiden Viewports wurde ein Kartenklick ausgelöst (Marker gesetzt), Screenshots erzeugt und Legend-Bounding-Boxes auf Überlappung geprüft.

Artefakte:
- `reports/evidence/issue-1305-mobile390.png`
- `reports/evidence/issue-1305-tablet768.png`
- `reports/evidence/issue-1305-viewport-check.json`

JSON-Kernauszug:
- `legendItems: 5`
- `overlapPairs: 0`
- `hasMarker: true` (beide Viewports)

## Ergebnis
- Legend-Badges bleiben in den geprüften Mobile-/Tablet-Viewports lesbar und ohne Überlappung.
- Marker ist nach Kartenklick sichtbar; Hint-Text aktualisiert (`Letzter Klick: lat..., lon...`).
- DoD-/Acceptance-Test für minimalen UI-Flow ist damit nachvollziehbar belegt.
