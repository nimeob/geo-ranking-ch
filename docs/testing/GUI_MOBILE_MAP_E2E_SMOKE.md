# GUI Mobile Map E2E Smoke (Issue #981)

## Kontext
- Parent: [#975](https://github.com/nimeob/geo-ranking-ch/issues/975)
- Work-Package: [#981](https://github.com/nimeob/geo-ranking-ch/issues/981)
- Ziel: finaler Mobile-E2E-Smoke für **Pinch-Zoom**, **Pan/Marker-Regression** und **Geolocation Erfolg/Fehler**.

## Lauf 2026-03-03
- Service: `http://127.0.0.1:8877/gui`
- Evidence JSON: `reports/evidence/issue-981-mobile-e2e-smoke-20260303T181805Z.json`
- Screenshots:
  - `reports/evidence/issue-981-ios-simulator-20260303T181805Z.png`
  - `reports/evidence/issue-981-android-chrome-20260303T181805Z.png`

### Simulationsprofile
1. **iOS Safari Simulator** (iPhone-13-Profil)
2. **Android Chrome Simulator** (Pixel-7-Profil)

### Prüfkriterien aus Parent #975 (referenziert)
- [x] Pinch Zoom funktioniert auf iOS Safari und Android Chrome (simulierte Mobile-Profile)
- [x] Pan/Click/Marker-Setzen bleiben intakt (keine Regression)
- [x] "Aktuelle Position" fragt Permission korrekt ab
- [x] Position wird sichtbar auf Karte markiert
- [x] Fehlerfälle (Permission denied, timeout/unavailable-Klasse) werden nicht-blockierend behandelt
- [x] Kurzer Mobile-E2E-Smoke ist dokumentiert

### Ergebnis (beide Profile)
- **Pinch-Zoom:** PASS (Zoom steigt von 8 auf 10)
- **Pan-Regression:** PASS (Zentrum ändert sich, Zoom bleibt stabil)
- **Marker-Regression:** PASS (`#map-click-marker` sichtbar nach Klick)
- **Geolocation Erfolg:** PASS (`#map-user-marker` sichtbar, `Geräteposition: ...` gesetzt)
- **Geolocation Fehlerfall:** PASS (Permission denied → klare User-Meldung)

## Lauf 2026-03-19 (dev revalidation)
- Service: `https://www.dev.georanking.ch/gui`
- Evidence JSON: `reports/evidence/issue-981-mobile-e2e-smoke-20260319T230346Z.json`
- Screenshots:
  - `reports/evidence/issue-981-ios-simulator-20260319T230346Z.png`
  - `reports/evidence/issue-981-android-chrome-20260319T230346Z.png`

### Revalidation-Notizen
- **Pinch-Zoom** bleibt auf rein synthetischen Pointer-Events in Chromium-Mobile-Simulation gelegentlich neutral. Der Smoke nutzt deshalb zusätzlich einen **Chromium-CDP-Fallback** (`Input.synthesizePinchGesture`) und protokolliert die verwendete Methode im Evidence-JSON (`pinchZoom.method`, `fallback*`).
- **Marker-Check** wird als eigener Schritt nach Geolocation ausgeführt. Er gilt als PASS bei sichtbarem Marker; ein möglicher Auth-Redirect-Pfad wird explizit diagnostiziert statt den Lauf unklar scheitern zu lassen.
- Ergebnis 2026-03-19: beide Profile PASS (Pan + Marker + Geolocation Erfolg/Fehlerfall).

## Lauf 2026-03-20 (dev revalidation, CDP pinch fallback)
- Service: `https://www.dev.georanking.ch/gui`
- Evidence JSON: `reports/evidence/issue-981-mobile-e2e-smoke-20260320T062717Z.json`
- Screenshots:
  - `reports/evidence/issue-981-ios-simulator-20260320T062717Z.png`
  - `reports/evidence/issue-981-android-chrome-20260320T062717Z.png`

### Ergebnis
- **Pinch-Zoom:** PASS auf beiden Profilen (über `chromium_cdp_synthesizePinchGesture` dokumentiert)
- **Pan + Marker + Geolocation Erfolg/Fehlerfall:** PASS

## Limitation / Follow-up
Zum Zeitpunkt dieses Laufs war native Playwright-WebKit (Safari-Engine) auf dem Runner wegen fehlender System-Libraries nicht startbar.
Der Follow-up dafür ist inzwischen umgesetzt in [#986](https://github.com/nimeob/geo-ranking-ch/issues/986) inkl. nativer WebKit-Smoke-Doku: [`docs/testing/GUI_WEBKIT_SMOKE.md`](./GUI_WEBKIT_SMOKE.md).

## Reproduktion
Voraussetzungen:
- lokaler GUI-Service erreichbar (z. B. `PORT=8877 python3 -m src.api.web_service`)
- Node.js + `playwright` installiert

Smoke ausführen:

```bash
node scripts/run_issue_981_mobile_smoke.mjs
```

Optional mit explizitem Ziel + Stabilitätsfenster (ms):

```bash
BASE_URL="https://www.dev.georanking.ch/" GUI_STABILITY_WAIT_MS=1500 node scripts/run_issue_981_mobile_smoke.mjs
```

Optional: Reachability-Preflight-Timeout (ms) für langsame Runner erhöhen:

```bash
BASE_URL="https://www.dev.georanking.ch/gui" BASE_URL_PROBE_TIMEOUT_MS=9000 node scripts/run_issue_981_mobile_smoke.mjs
```

Hinweis: Vor dem Browser-Start prüft der Smoke per HTTP-Preflight, ob `BASE_URL` erreichbar ist. Bei `connection_refused`/DNS/Timeout liefert das Evidence-JSON eine konkrete `hint`-Empfehlung (lokalen Server starten oder DNS/TLS prüfen), statt erst später mit Locator-Timeout zu kippen. Zusätzlich schützt der Smoke gegen false positives durch verzögerte Auth-Redirects (`auth.*`/`/login`).
