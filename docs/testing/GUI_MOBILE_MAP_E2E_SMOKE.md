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
