# API/UI Endpoint Ownership Inventory (Issue #1168)

> Parent Epic: [#1166](https://github.com/nimeob/geo-ranking-ch/issues/1166)
> Stand: 2026-03-05

## Zweck

Diese Inventarliste klassifiziert alle aktuell exponierten HTTP-Endpunkte in **DATA**, **UI** oder **MIXED**, weist einen eindeutigen Ziel-Owner zu und definiert eine priorisierte Migrationsreihenfolge für die Entkopplung API vs. UI.

## Klassen

- **DATA**: gehört dauerhaft in den API/Data-Source-Layer.
- **UI**: gehört dauerhaft in UI/BFF (front-facing Flow/UX/Auth-Session).
- **MIXED**: aktuell doppelt oder überlappend ausgeliefert; muss auf einen Ziel-Owner konsolidiert werden.

<!-- ENDPOINT_INVENTORY:START -->
| Endpoint | Methode(n) | Aktuelle Runtime(s) | Klasse | Ziel-Owner | Priorität (1=früh) | Migrationshinweis |
|---|---|---|---|---|---:|---|
| `/` | GET | API + UI | MIXED | UI-Service (`src/ui/service.py`) | 1 | API-Rendering entfernen, nur UI-Shell beibehalten. |
| `/gui` | GET | API + UI | MIXED | UI-Service (`src/ui/service.py`) | 1 | Gleichlauf mit `/` konsolidieren. |
| `/history` | GET | API + UI | MIXED | UI-Service (`src/ui/service.py`) | 1 | Legacy-Pfad bleibt als Redirect auf `/gui/history`; Rendering nur im UI-Service. |
| `/gui/history` | GET | API + UI | MIXED | UI-Service (`src/ui/service.py`) | 1 | Kanonischer History-UI-Pfad; API liefert nur Deprecation-/`410`-Signal. |
| `/results/<result_id>` | GET | API + UI | MIXED | UI-Service (`src/ui/service.py`) | 1 | Result-Page-Rendering aus API entfernen. |
| `/healthz` | GET | API + UI | MIXED | UI-Service (`src/ui/service.py`) | 1 | `healthz` als UI-Liveness standardisieren. |
| `/health` | GET | API + UI (Alias) | MIXED | API-Service (`src/api/web_service.py`) | 2 | UI-`/health` Alias mittelfristig entfernen; API bleibt kanonisch auf `/health`. |
| `/auth/*` (UI-Redirect) | GET | UI | MIXED | API-BFF Auth (`src/api/web_service.py`) | 2 | Redirect-Bridge bleibt temporär, bis Auth-Einstieg final konsolidiert ist. |
| `/auth/login` | GET | API (BFF) | UI | API-BFF Auth (`src/api/web_service.py`) | 2 | Front-facing Login bleibt im BFF/Auth-Layer. |
| `/auth/callback` | GET | API (BFF) | UI | API-BFF Auth (`src/api/web_service.py`) | 2 | OIDC Callback im BFF belassen. |
| `/auth/logout` | GET | API (BFF) | UI | API-BFF Auth (`src/api/web_service.py`) | 2 | Session/Logout bleibt BFF-owned. |
| `/auth/me` | GET | API (BFF) | UI | API-BFF Auth (`src/api/web_service.py`) | 2 | Session-Status-Endpunkt für UI/BFF. |
| `/jobs` | GET | UI | UI | UI-Service (`src/ui/service.py`) | 3 | Bereits korrekt getrennt; nur stabilisieren. |
| `/jobs/<job_id>` | GET | UI | UI | UI-Service (`src/ui/service.py`) | 3 | Bereits korrekt getrennt; nur stabilisieren. |
| `/version` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Im API-Layer belassen. |
| `/health/details` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Diagnose-Endpunkt bleibt API/Operations-owned. |
| `/analyze` | POST | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Kern-Data-Endpoint, kein UI-Move. |
| `/analyze/history` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Data-API bleibt kanonisch, UI konsumiert nur. |
| `/analyze/jobs/<job_id>` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Data-API bleibt kanonisch. |
| `/analyze/jobs/<job_id>/notifications` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Data-API bleibt kanonisch. |
| `/analyze/jobs/<job_id>/cancel` | POST | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Job-Kontrolle bleibt API-owned. |
| `/analyze/results/<result_id>` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Datenprojektion bleibt API-owned. |
| `/api/v1/dictionaries` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Referenzdaten-Endpunkt bleibt API-owned. |
| `/api/v1/dictionaries/<domain>` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 3 | Referenzdaten-Endpunkt bleibt API-owned. |
| `/trace` (legacy alias) | GET | API | DATA | API-Service (`src/api/web_service.py`) | 4 | Frontlogik entfernt: Endpoint bleibt nur als Deprecation-Hinweis (`410 gone` + Header + Verweis auf `/debug/trace?request_id=<id>`). |
| `/debug/trace` | GET | API | DATA | API-Service (`src/api/web_service.py`) | 4 | Dev/Diagnose im API-Layer belassen (kein UI-Ownership). |
| `/compliance/corrections/<document_id>` | POST | API | DATA | API-Service (`src/api/web_service.py`) | 4 | Fachlicher API-Workflow, kein UI-Move. |
<!-- ENDPOINT_INVENTORY:END -->

## Priorisierte Migrationsreihenfolge (abgeleitet)

1. **UI-Doppelrouten aus API entfernen** (`/`, `/gui`, `/history`, `/gui/history`, `/results/<result_id>`, `/healthz`).
2. **Health/Auth-Konsolidierung** (`/health` Alias-Bereinigung, `/auth/*` Redirect-Bridge stabilisieren).
3. **DATA-Endpunkte absichern und Contract-fixieren** (`/analyze*`, Dictionaries, Version/Health-Details).
4. **Diagnose-/Compliance-Endpunkte hardenen** (`/debug/trace`, `/compliance/corrections/*`) inklusive Non-UI-Boundary-Checks.

## Folgende Issues nutzen diese Reihenfolge

- [#1169](https://github.com/nimeob/geo-ranking-ch/issues/1169)
- [#1170](https://github.com/nimeob/geo-ranking-ch/issues/1170)
- [#1171](https://github.com/nimeob/geo-ranking-ch/issues/1171)
- [#1172](https://github.com/nimeob/geo-ranking-ch/issues/1172)
- [#1173](https://github.com/nimeob/geo-ranking-ch/issues/1173)
- [#1174](https://github.com/nimeob/geo-ranking-ch/issues/1174)
- [#1175](https://github.com/nimeob/geo-ranking-ch/issues/1175)
- [#1176](https://github.com/nimeob/geo-ranking-ch/issues/1176)
