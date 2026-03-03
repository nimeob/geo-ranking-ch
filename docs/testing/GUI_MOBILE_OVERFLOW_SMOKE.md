# GUI Mobile Overflow Smoke (Issue #1039)

## Ziel

Sicherstellen, dass die GUI auf Mobile-Viewport `360x800` **keinen horizontalen Scroll** erzeugt und die Kernfunktionen weiterhin erreichbar bleiben.

## Assertion (E2E)

Die Smoke-Ausführung prüft direkt im Browser:

- `document.scrollingElement.scrollWidth === document.scrollingElement.clientWidth`

## Voraussetzungen

- Lokaler GUI-Server läuft (Default: `http://127.0.0.1:8877/gui`)
- Node + Playwright verfügbar

## Ausführen

```bash
HOST=127.0.0.1 PORT=8877 APP_VERSION=dev python3 -m src.web_service
```

In zweiter Shell:

```bash
node scripts/run_issue_1039_mobile_overflow_smoke.cjs
```

Optional mit anderem Ziel:

```bash
BASE_URL="http://127.0.0.1:8877/gui" node scripts/run_issue_1039_mobile_overflow_smoke.cjs
```

## Artefakte

- JSON Evidence: `reports/evidence/issue-1039-mobile-overflow-smoke-<timestamp>.json`
- Mobile Screenshot: `reports/evidence/issue-1039-mobile-overflow-<timestamp>.png`
- Desktop Screenshot: `reports/evidence/issue-1039-desktop-regression-<timestamp>.png`

## Desktop-Regressionscheck

Der Smoke enthält zusätzlich einen Desktop-Check (`1280x800`) und validiert dort ebenfalls `scrollWidth === clientWidth`, damit der Mobile-Fix kein Desktop-Overflow einführt.
