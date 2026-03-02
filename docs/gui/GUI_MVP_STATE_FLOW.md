# BL-20.6 — GUI-MVP (Adresse + Kartenklick + Result-Panel)

## Zielbild

Die GUI-MVP unter `GET /gui` bildet jetzt den vollständigen MVP-Flow für BL-20.6 ab:

> Source-Stand seit BL-334.4: kanonisch `src/shared/gui_mvp.py` (Wrapper `src/ui/gui_mvp.py` und `src/gui_mvp.py` bleiben kompatibel).

- Kernnavigation (`Input`, `Karte`, `Result-Panel`)
- API-first Adresseingabe via `POST /analyze`
- Kartenklick-Flow via `POST /analyze` mit `coordinates.lat/lon` + `snap_mode=ch_bounds`
- reproduzierbarer UI-State-Flow: `idle -> loading -> success|error`
- clientseitiger Request-Timeout-Guard (`AbortController`): kein dauerhaftes `loading` bei ausbleibender API-Antwort
- korrelierbares UI-Structured-Logging (`ui.state.transition`, `ui.api.request.start/end`) inkl. `X-Request-Id`/`X-Session-Id` für UI↔API-Tracing
- sichtbare Kernfaktoren (Top-Faktoren aus Explainability) und rohe JSON-Antwort
- Trace-Debug-Panel mit Deep-Link-Unterstützung (`/gui?view=trace&request_id=<id>`) und Timeline-Lookup via `GET /debug/trace`

## Struktur

1. **Input-Panel**
   - Adresse, Intelligence-Mode, optionaler API-Token
   - Submit triggert deterministisch eine Analyze-Anfrage
2. **Kartenpanel**
   - echte, interaktive OSM-Basemap (Tile-Render) mit deterministischem Pan/Zoom
   - Klick setzt Marker und startet unmittelbar dieselbe Analyze-Pipeline über Koordinateninput
   - Degraded-State bei Tile-Ausfall bleibt funktional (Analyze via `coordinates.lat/lon` weiter möglich)
   - Keyboard-Fallback (`Enter`/`Space`) triggert Center-Analyse; Pfeiltasten/+/- unterstützen Pan/Zoom für Accessibility
3. **Result-Panel**
   - Status-Pill pro State
   - Request-ID + Input-Metadaten
   - Request-ID-UX mit klickbarem Trace-Link (`Trace ansehen`) und Copy-Action (`Copy ID`) inkl. Live-Feedback
   - Fehlerbox für API-/Netzwerkfehler
   - Kernfaktoren-Liste (`top 4` nach |contribution|)
   - Roh-JSON zur transparenten MVP-Diagnose

## State-Flow (technisch)

Frontend-State (clientseitig):

- `phase`: `idle | loading | success | error`
- `lastRequestId`: korrelierbare Request-ID aus API-Response
- `lastPayload`: letzte JSON-Antwort (oder Fehlerobjekt)
- `lastError`: menschenlesbare Fehlermeldung
- `lastInput`: letzter Input-Kontext (Adresse oder Kartenpunkt)
- `coreFactors`: extrahierte Top-Faktoren aus Explainability

Transitions:

- `idle -> loading` beim Submit oder Kartenklick
- `loading -> success` bei `HTTP 2xx` + `ok=true`
- `loading -> error` bei API-Fehler, Auth-Fehler, Netzwerkfehler oder Client-Timeout (`timeout: ... abgebrochen`)
- `error -> loading` beim nächsten Submit/Kartenklick (clean retry)

## Async Submit (Async v1)

Die GUI kann optional im **Async Mode** auslösen (Checkbox im Input-Panel). Dann sendet sie additiv:

- `options.async_mode.requested=true`

Erwartetes Verhalten:

- API antwortet mit `HTTP 202 Accepted` und liefert ein `job`-Objekt inkl. `job_id`.
- Das Result-Panel rendert den `job_id` sichtbar und bietet einen Deep-Link auf die UI-Service Job-Page: `GET /jobs/<job_id>`.
- Sync-Requests (ohne Async Mode) bleiben unverändert.

## Trace-Debug-View (BL-422.2)

Das Result-Column enthält zusätzlich ein dediziertes Trace-Debug-Panel:

- Formularfelder: `request_id`, optional `lookback_seconds`, optional `max_events`
- Deep-Link-Rehydrierung aus URL-Parametern (`request_id`, optional `lookback_seconds`, `max_events`)
- Auto-Lookup beim Laden, wenn ein Deep-Link vorhanden ist
- Timeline-Rendering sortiert robust nach Timestamp und fällt bei Teil-/Fehldaten auf sichere Defaults zurück
- Accessibility-Basics: Fokus-fähiger Link/Button-Flow und `aria-live` Feedback für Copy-/Status-Rückmeldungen

Trace-State-Flow (clientseitig):

- `idle` → kein Lookup gestartet
- `loading` → laufender `GET /debug/trace` Request
- `success` → Timeline verfügbar
- `empty` → keine Events (ohne Unknown-Hinweis)
- `unknown` → `request_id` unbekannt oder außerhalb des Zeitfensters
- `error` → API-/Netzwerk-/Validierungsfehler

## Logging & Korrelation (BL-340.3)

Die GUI emittiert strukturierte Client-Events (JSONL via Browser-Console) und korreliert API-Requests über dieselbe Request-ID:

- `ui.api.request.start` / `ui.api.request.end` mit `trace_id`, `request_id`, `session_id`, `status_code`, `duration_ms`
- `ui.trace.request.start` / `ui.trace.request.end` für Trace-Lookups inkl. `trace_request_id`, Timeline-State und Fehlerklassifikation
- `ui.state.transition` für Analyze-Zustandswechsel (`idle/loading/success/error`)
- `ui.trace.state.transition` für Trace-Zustandswechsel (`idle/loading/success/empty/unknown/error`)
- Input-/Interaktionsereignisse (`ui.interaction.form.submit`, `ui.interaction.map.analyze_trigger`, `ui.interaction.trace.submit`, `ui.input.accepted`)
- Validierungs-/Degraded-Signale (`ui.validation.error`, `ui.output.map_status`)

Für die UI→API-Korrelation setzt der Client pro Analyze-Request:

- `X-Request-Id`
- `X-Session-Id`

Damit lassen sich UI-Ereignisse direkt mit API-Lifecycle-Logs (`api.request.start/end`) verbinden.

## Manuelle E2E-Prüfung (BL-20.6.b)

Durchgeführt am **2026-02-28** (lokal):

1. `python3 -m src.web_service` gestartet
2. `GET /gui` geöffnet
3. Karte per Drag/Mousewheel bewegt und gezoomt, danach Kartenklick ausgelöst
4. Verifiziert:
   - Basemap-Tiles werden gerendert (OSM)
   - Pan/Zoom reagieren deterministisch
   - Marker wird gesetzt
   - Request geht über `coordinates.lat/lon`
   - Status wechselt `loading -> success`
   - Result-Panel zeigt Request-ID + Kernfaktoren + JSON

Hinweis: Die Regression für ausgelieferte GUI-Marker läuft zusätzlich über `tests/test_web_service_gui_mvp.py`.

## Forward-Compatibility (BL-30)

Die GUI bleibt bewusst **API-first**: keine UI-exklusive Fachlogik, alle fachlichen Ergebnisse kommen aus `POST /analyze`. Der Kartenklick nutzt denselben Backend-Contract wie zukünftige Mobile-/HTML5-Clients (nur anderer Input-Kanal), wodurch BL-30.4/30.6 ohne Rewrite anschließen kann. Die Kernfaktoren-Darstellung wertet Explainability additiv aus mehreren möglichen Pfaden aus, sodass zukünftige Schema-Erweiterungen die bestehende UI nicht brechen.

Spezifische BL-30.6-Referenzen:
- API-Contract (wp1): [`docs/api/mobile-live-geolocation-contract-v1.md`](../api/mobile-live-geolocation-contract-v1.md)
- Mobile State-/Interaction-Contract (wp2): [`docs/gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md`](./MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md)
