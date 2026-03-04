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

> Ergänzung aus Issue #1184: Für **History** und **Trace** gilt ein expliziter Runbook-Pfad
> `before -> transition -> after` inkl. verifizierbarer Checks und Rollback-Hinweisen.

### 4.1 Login-Einstieg

- **Before (legacy):** `GET /login`, `/signin`, `/oauth/login`
- **After (verbindlich):** `GET /auth/login` (UI/BFF-Einstieg)

### 4.2 Runbook-Flow: History (`before -> transition -> after`)

#### Before (Legacy-Betrieb)
- Browser kann noch Legacy-Pfad `GET /history` auf API-Host treffen.
- API liefert bereits Deprecation-/Sunset-Signale für Migrationsfähigkeit.

**Verifizierbarer Check (Before):**
```bash
curl -si "${API_BASE_URL}/history" | sed -n '1,20p'
```
Erwartung: Response enthält `Deprecation`, `Sunset`, `Warning` und einen `Link` auf Nachfolger-Doku.

#### Transition (Dual-Readiness)
- UI-Route `GET /history` ist produktiv und user-facing.
- Datenzugriff erfolgt intern über API-Data-Contract `GET /analyze/history`.
- Legacy-Pfad bleibt nur als kontrollierter Übergangspfad mit Warnsignalen aktiv.

**Verifizierbare Checks (Transition):**
```bash
# 1) UI-History erreichbar (Front-Facing)
curl -si "${UI_BASE_URL}/history" | sed -n '1,20p'

# 2) Data-Source-History maschinenlesbar
curl -si -H "Authorization: Bearer ${TOKEN}" \
  "${API_BASE_URL}/analyze/history?limit=5" | sed -n '1,40p'
```
Erwartung:
- UI-Route liefert HTML/UX-Flow (kein API-JSON-Frontend als Primärziel).
- API-Route liefert stabilen JSON-Response im dokumentierten Contract.

#### After (UI-only Ownership)
- Nutzerführung erfolgt ausschließlich über UI-Domain/Route.
- Legacy-API-History ist abgeschaltet oder auf klaren Deprecation-Endzustand gesetzt.

**Verifizierbarer Check (After):**
```bash
curl -si "${API_BASE_URL}/history" | sed -n '1,20p'
```
Erwartung: Kein front-facing Rendering mehr über API; stattdessen klarer Migrationshinweis (`410 gone` oder dokumentierter Übergangsstatus mit Sunset-Header).

**Rollback-Hinweise (History):**
- Rollback nur als **zeitlich begrenzter** Übergang: Legacy-Hinweispfad reaktivieren, keine dauerhafte Rücknahme der UI-Ownership.
- Bei Rollback immer Incident-/Change-Notiz mit Trigger, Start-/Endzeit und Rückkehrkriterium dokumentieren.
- Nach Rollback sofort Re-Migrationsfenster terminieren (Owner + Deadline + Verifikationscheck).

### 4.3 Runbook-Flow: Trace (`before -> transition -> after`)

#### Before (Legacy-Betrieb)
- Legacy-Pfad `GET /trace` kann noch in Consumern referenziert sein.

**Verifizierbarer Check (Before):**
```bash
curl -si "${API_BASE_URL}/trace?request_id=test" | sed -n '1,20p'
```
Erwartung: Legacy-Pfad signalisiert Deprecation/Migration klar über Header bzw. dokumentierten Response.

#### Transition (Dual-Readiness)
- UI bietet Trace-Ansicht/Drilldown als primären Nutzerpfad.
- API stellt Diagnose-Daten über `GET /debug/trace?request_id=<id>` bereit.
- Legacy-`/trace` bleibt nur als kontrollierte Übergangskompatibilität.

**Verifizierbare Checks (Transition):**
```bash
# 1) UI-Trace-Deep-Link erreichbar
curl -si "${UI_BASE_URL}/gui?view=trace&request_id=test" | sed -n '1,20p'

# 2) API-Diagnosepfad erreichbar
curl -si -H "Authorization: Bearer ${TOKEN}" \
  "${API_BASE_URL}/debug/trace?request_id=test" | sed -n '1,40p'
```
Erwartung:
- UI repräsentiert den user-facing Trace-Flow.
- API liefert nur die Diagnose-/Datenebene, keine neue Frontlogik.

#### After (UI-only Ownership)
- User-facing Trace-Interaktion läuft vollständig über UI.
- Legacy-Trace-Endpunkt ist deprecated-finalisiert oder entfernt.

**Verifizierbarer Check (After):**
```bash
curl -si "${API_BASE_URL}/trace?request_id=test" | sed -n '1,20p'
```
Erwartung: Legacy-Pfad liefert keinen front-facing Trace-Flow mehr (`410 gone` oder dokumentierter Endzustand mit Sunset-Hinweis).

**Rollback-Hinweise (Trace):**
- Kurzfristiger Rollback nur zur Incident-Stabilisierung, nicht als permanenter Betriebsmodus.
- Bei Rückfall auf Legacy-Trace müssen Deprecation-/Sunset-Hinweise aktiv bleiben.
- Rückkehr auf Zielbild mit fixem Termin + owner-gebundenem Follow-up-Issue planen.

### 4.4 Kurz-Check für Integratoren

```bash
# 1) UI-Login-Entrypoint erreichbar
curl -i "${UI_BASE_URL}/auth/login"

# 2) Legacy-Login signalisiert Migration
curl -i "${API_BASE_URL}/login"

# 3) Data-Source-History weiterhin maschinenlesbar
curl -i -H "Authorization: Bearer ${TOKEN}" "${API_BASE_URL}/analyze/history?limit=5"

# 4) Trace-Diagnosepfad erreichbar
curl -i -H "Authorization: Bearer ${TOKEN}" "${API_BASE_URL}/debug/trace?request_id=test"
```

Erwartung:
- Legacy-Pfade liefern Deprecation/Sunset/Warning/Link-Signale.
- Data-Endpunkte bleiben stabil maschinenlesbar (JSON, dokumentierter Statuscode).
- UI bleibt ausschließlich user-facing für Login/History/Trace.

## 5) Onboarding-Checkliste (30 Minuten)

- [ ] Boundary-Contract lesen: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md)
- [ ] Endpoint-Ownership prüfen: [`docs/api/API_UI_ENDPOINT_OWNERSHIP_INVENTORY.md`](./API_UI_ENDPOINT_OWNERSHIP_INVENTORY.md)
- [ ] Legacy-Aufrufe im eigenen Consumer-Inventar markieren (Login/History/Trace)
- [ ] Für jeden Legacy-Pfad den UI-Successor festlegen und testbar dokumentieren
- [ ] Mindestens einen Smoke in CI oder lokal automatisieren (`before -> after`)

Wenn ein Consumer noch auf Legacy-Pfade angewiesen ist: Follow-up-Issue mit Sunset-Plan anlegen (Owner, Deadline, Nachweis).
