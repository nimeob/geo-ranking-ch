# GUI DEV Live Mobile Regression

Kanonischer Entry-Point für mobile-orientierte Live-Smokes gegen `https://www.dev.georanking.ch/gui`.

## Scope

Der Bundle-Runner führt diese Smokes in Serie aus und erzeugt ein konsolidiertes Evidence-JSON:

- Issue #1016 — Mobile UX (Burger-Menü + Pinch-Zoom Smoothness)
- Issue #981 — Mobile E2E (iOS/Android Profile, Geolocation/Fallback)
- Issue #1039 — Mobile Overflow (horizontal scroll + core selectors)
- Issue #986 — WebKit Smoke (mit Chromium-Fallback, wenn native WebKit fehlt)

## Lokal ausführen

```bash
npm ci
npx playwright install --with-deps chromium

node scripts/run_dev_ui_mobile_regression_bundle.mjs \
  --base-url https://www.dev.georanking.ch/gui \
  --evidence-json artifacts/dev-ui-mobile/latest/dev-ui-mobile-regression.json \
  --screenshot-dir artifacts/dev-ui-mobile/latest/screenshots \
  --headless
```

Shortcut:

```bash
npm run smoke:gui:dev-live-mobile
```

## Output

- Consolidated summary: `artifacts/dev-ui-mobile/latest/dev-ui-mobile-regression.json`
- Per-step JSONs: `artifacts/dev-ui-mobile/latest/issue-*.json`
- Copied screenshots: `artifacts/dev-ui-mobile/latest/screenshots/`

## CI Workflow

Workflow: `.github/workflows/gui-dev-live-mobile-regression.yml` (manual dispatch).

Artifact-Name: `gui-dev-live-mobile-regression-artifacts`
