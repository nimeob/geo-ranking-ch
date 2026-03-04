# API Data-only Guide + UI-Migrationsanleitung (Issue #1176)

> Parent Epic: [#1166](https://github.com/nimeob/geo-ranking-ch/issues/1166)  
> Stand: 2026-03-04

## Zielgruppe

Diese Anleitung richtet sich an Teams, die bestehende Integrationen auf die aktuelle API/UI-Grenze migrieren müssen:

- **API = Data-Source-Layer** (maschinenlesbare Daten, Health, Diagnose)
- **UI = Front-Facing-Layer** (Login, Session, History-/Trace-Ansichten, Nutzerführung)

Sie ergänzt den Boundary-Contract in [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) und das Endpoint-Inventar in [`docs/api/API_UI_ENDPOINT_OWNERSHIP_INVENTORY.md`](./API_UI_ENDPOINT_OWNERSHIP_INVENTORY.md).

## 1) Data-only Contract (verbindlich)

### 1.1 Was die API liefern darf

Die API liefert ausschließlich Daten-/Service-Responses, keine neuen front-facing Seiten.

Kanonische Data-Endpunkte (Auszug):

- `POST /analyze`
- `GET /analyze/history`
- `GET /analyze/results/<result_id>`
- `GET /analyze/jobs/<job_id>`
- `GET /analyze/jobs/<job_id>/notifications`
- `POST /analyze/jobs/<job_id>/cancel`
- `GET /health`, `GET /healthz`, `GET /health/details`, `GET /version`
- `GET /debug/trace` (Diagnose, dev-orientiert)

### 1.2 Was die API **nicht** mehr liefern soll

Nicht mehr zulässig als Zielbild:

- neue HTML-/UI-Ansichten aus dem API-Service
- neue Login-/Session-UX-Flows außerhalb der UI/BFF-Ownership
- UX-spezifische View-/Filter-/Pagination-Logik in API-Routen

## 2) UI-Ownership (verbindlich)

Die UI ist Owner für alle user-facing Flows:

- Login-/Logout-/Session-Interaktion (`/auth/*` als front-facing Einstieg)
- Seiten `/`, `/gui`, `/history`, `/results/<result_id>`, `/jobs`, `/jobs/<job_id>`
- UX-Logik für Filter, Navigation, Empty/Error/Retry-States, Deep-Links

Boundary-Details (Normtext): [`docs/ARCHITECTURE.md#7-apiui-boundary-contract-v1`](../ARCHITECTURE.md#7-apiui-boundary-contract-v1)

## 3) Breaking Changes und Deprecation-Signale

Für Legacy-Routen gilt: geordnete Abschaltung mit klaren Signalen.

Erwartete Header/Signale bei Deprecated-Pfaden:

- `Deprecation: true`
- `Sunset: <RFC-1123 UTC timestamp>`
- `Warning: 299 - "deprecated endpoint; migrate to successor"`
- `Link: <...>; rel="deprecation"` mit Verweis auf Migrationsdoku

Aktuelle Mapping-Tabelle (kanonisch):

- [`docs/ARCHITECTURE.md#api-deprecation-mapping-dev`](../ARCHITECTURE.md#api-deprecation-mapping-dev)

## 4) Migrationsbeispiele (before -> after)

### 4.1 Login-Einstieg

- **Before (legacy):** `GET /login`, `/signin`, `/oauth/login`
- **After (verbindlich):** `GET /auth/login` (UI/BFF-Einstieg)

### 4.2 History-Ansicht

- **Before (front-facing via API):** Browser-Flow direkt über `GET /history` auf API-Host
- **After:** Browser nutzt UI-Route `GET /history` (UI-Service), Datenabruf intern über `GET /analyze/history` als Data-Source

### 4.3 Trace-Nutzung

- **Before (legacy):** `GET /trace`
- **After:** UI-Flow + Diagnose über `GET /debug/trace?request_id=<id>`

### 4.4 Kurz-Check für Integratoren

```bash
# 1) UI-Login-Entrypoint erreichbar
curl -i "${BASE_URL}/auth/login"

# 2) Deprecated Legacy-Pfad signalisiert Migration
curl -i "${BASE_URL}/login"

# 3) Data-Source-History weiterhin maschinenlesbar
curl -i -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/analyze/history?limit=5"
```

Erwartung:
- Legacy-Pfade liefern Deprecation/Sunset/Warning/Link-Signale.
- Data-Endpunkte bleiben stabil maschinenlesbar (JSON, dokumentierter Statuscode).

## 5) Onboarding-Checkliste (30 Minuten)

- [ ] Boundary-Contract lesen: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md)
- [ ] Endpoint-Ownership prüfen: [`docs/api/API_UI_ENDPOINT_OWNERSHIP_INVENTORY.md`](./API_UI_ENDPOINT_OWNERSHIP_INVENTORY.md)
- [ ] Legacy-Aufrufe im eigenen Consumer-Inventar markieren (Login/History/Trace)
- [ ] Für jeden Legacy-Pfad den UI-Successor festlegen und testbar dokumentieren
- [ ] Mindestens einen Smoke in CI oder lokal automatisieren (`before -> after`)

Wenn ein Consumer noch auf Legacy-Pfade angewiesen ist: Follow-up-Issue mit Sunset-Plan anlegen (Owner, Deadline, Nachweis).
