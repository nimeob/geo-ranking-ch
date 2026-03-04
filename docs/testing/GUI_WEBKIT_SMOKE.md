# GUI Native WebKit Smoke (Issue #986)

## Kontext
- Parent: [#975](https://github.com/nimeob/geo-ranking-ch/issues/975)
- Follow-up nach [#981](https://github.com/nimeob/geo-ranking-ch/issues/981)
- Work-Package: [#986](https://github.com/nimeob/geo-ranking-ch/issues/986)

## Ziel
Reproduzierbarer Dev-Smoke auf **nativer Playwright-WebKit Runtime** für `/gui`, inkl. Nachweis für:
1. GUI lädt im nativen WebKit-Kontext
2. Login-Entrypoint ist sichtbar
3. mindestens eine Basis-Map-Interaktion (Pinch-Zoom oder Pan) funktioniert

## Runner-Dependencies (identifiziert)
Der bisherige Chromium-Fallback aus #981 war nötig, weil auf Standard-Runnern die WebKit-Runtime nicht vollständig vorbereitet ist.
Ein Probe-Start von `node scripts/run_issue_986_webkit_smoke.mjs` ohne System-Setup liefert reproduzierbar fehlende Shared-Libraries, u. a.:

- `libicudata.so.66`
- `libicui18n.so.66`
- `libicuuc.so.66`
- `libwoff2dec.so.1.0.2`
- `libevent-2.1.so.7`
- `libwebpdemux.so.2`
- `libharfbuzz-icu.so.0`
- `libjpeg.so.8`
- `libwebpmux.so.3`
- `libwebp.so.6`
- `libenchant-2.so.2`
- `libhyphen.so.0`
- `libffi.so.7`
- `libevdev.so.2`
- `libjson-glib-1.0.so.0`
- `libx264.so`

Für einen stabilen nativen Lauf werden zwei Dependency-Blöcke benötigt:

1. **Node Package:** `playwright` (liefert WebKit-Driver/APIs)
2. **Browser + Systemlibs:** `playwright install --with-deps webkit`

### Setup (Ubuntu/Dev-Runner)
```bash
npm install --no-save playwright@1.52.0
npx playwright install --with-deps webkit
```

## Smoke-Kommando
Voraussetzung: lokaler GUI-Service ist erreichbar (z. B. `PORT=8877 python3 -m src.api.web_service`).

```bash
BASE_URL="http://127.0.0.1:8877/gui" node scripts/run_issue_986_webkit_smoke.mjs
```

Output:
- JSON Evidence: `reports/evidence/issue-986-webkit-smoke-<timestamp>.json`
- Screenshot: `reports/evidence/issue-986-webkit-ios-<timestamp>.png`

## CI-Integration / Artifact
Workflow: `.github/workflows/gui-webkit-smoke.yml`

Der Workflow:
1. installiert Python- und Node-Abhängigkeiten,
2. startet den lokalen GUI-Service,
3. installiert WebKit inkl. System-Dependencies,
4. führt `scripts/run_issue_986_webkit_smoke.mjs` aus,
5. publiziert ein CI-Artifact `gui-webkit-smoke-artifacts` (JSON + Screenshot + Service-Log).
