# User-Dokumentation (BL-19)

Ziel dieser Doku: den Service schnell nutzbar machen — für lokale Entwicklung, API-Integration und Betrieb.

## Zielgruppen

1. **API-Consumer (Frontend, Integrationen, Partner)**
   - wollen wissen: Endpoint, Auth, Request/Response, Fehlerfälle.
2. **Entwickler:innen im Projekt**
   - wollen schnell lokal starten, testen und reproduzierbar arbeiten.
3. **Betrieb/Support**
   - wollen bei Störungen schnell zu den richtigen Runbooks.

## Doku-Navigation

- **[Getting Started](./getting-started.md)**
  - Schnellster Weg von 0 → erster erfolgreicher `/analyze`-Call.
- **[API Usage Guide](./api-usage.md)**
  - Endpoints, Header, Request/Response-Schema, Beispiele.
- **(folgt) Configuration / ENV**
  - Alle relevanten Umgebungsvariablen inkl. Defaults/Validierung.
- **(folgt) Troubleshooting**
  - Häufige Fehlerbilder (401/400/504, URL/Auth/Timeout).
- **(folgt) Operations Quick Guide**
  - Smoke/Stability/Deploy-Checks für den Tagesbetrieb.

## Empfohlene Lesereihenfolge

1. Getting Started
2. API Usage Guide
3. Configuration / ENV
4. Troubleshooting
5. Operations

## Scope-Hinweis

Diese User-Doku ist bewusst nutzerorientiert.
Architektur-/Infra-Details bleiben in:
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT_AWS.md`
- `docs/OPERATIONS.md`
