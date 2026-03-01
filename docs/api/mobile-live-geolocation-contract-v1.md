# BL-30.6.wp1 — Mobile Live-Geolocation API-Contract v1 (additiv zu /analyze)

Bezug: [#113](https://github.com/nimeob/geo-ranking-ch/issues/113), [#502](https://github.com/nimeob/geo-ranking-ch/issues/502)

## 1) Ziel und Scope (v1)

Dieser Contract definiert einen **additiven** Mobile-Geolocation-Pfad für `POST /analyze`, ohne den bestehenden v1-Contract zu brechen.

In Scope (wp1):
- normativer Request-Envelope für mobile Geolocation-Metadaten
- additive Response-Statusfelder für Transparenz/Fallback
- deterministische Fehlercodes für Contract-Verletzungen

Nicht in Scope (Folgearbeit):
- UI-/State-Maschine (siehe #503)
- Telemetrie-/Privacy-Operationalisierung (siehe #504)

## 2) Request-Contract (additiv)

Bestehende Kernfelder bleiben unverändert (`query` **oder** `coordinates.lat/lon`).

Neuer optionaler Envelope:

- `options.mobile_geolocation` (Objekt, optional)
  - `enabled` (bool, optional; Default `false`)
  - `permission_state` (`granted|prompt|denied`, optional)
  - `accuracy_meters` (Zahl > 0, optional)
  - `location_age_seconds` (Zahl >= 0, optional)
  - `battery_saver` (bool, optional)
  - `source` (`device_gps|device_fused|manual_pin`, optional)

Zusätzliche Kompatibilitätsregeln:
- Wenn `options.mobile_geolocation.enabled=true`, muss der Request einen gültigen Standortpfad liefern (`coordinates.lat` + `coordinates.lon`).
- Fehlende oder ungültige Mobile-Felder führen zu `400 bad_request` (kein 5xx/Crash-Pfad).
- Unbekannte Keys in `options.mobile_geolocation` sind aktuell **No-Op** (additive Forward-Compatibility).

## 3) Response-Contract (additiv)

Neues optionales Statusobjekt:

- `result.status.mobile_geolocation` (Objekt, optional)
  - `requested` (bool)
  - `resolved` (bool)
  - `source` (`device_gps|device_fused|manual_pin|none`)
  - `permission_state` (`granted|prompt|denied|unknown`)
  - `accuracy_meters` (Zahl oder `null`)
  - `location_age_seconds` (Zahl oder `null`)
  - `fallback_reason` (`none|permission_denied|stale_location|low_accuracy|missing_coordinates`)

Optionale Capability-/Entitlement-Querverweise bleiben im bestehenden Envelope:
- `result.status.capabilities.mobile_live_geolocation` (optional)
- `result.status.entitlements.mobile_live_geolocation` (optional)

## 4) Fehler- und Fallback-Semantik (deterministisch)

Empfohlene `error_code`-Werte im `400 bad_request`-Pfad:
- `mobile_geolocation_invalid_envelope`
- `mobile_geolocation_coordinates_required`
- `mobile_geolocation_invalid_permission_state`
- `mobile_geolocation_invalid_accuracy`
- `mobile_geolocation_invalid_location_age`

Graceful-Degradation-Regel:
- Bei `permission_state=denied` oder fehlender frischer Genauigkeit bleibt der Analyze-Flow lauffähig.
- Das Ergebnis signalisiert den Fallback ausschließlich über `result.status.mobile_geolocation.fallback_reason`.

## 5) Logging-/Trace-Mindestbezug (vorläufig)

Bis zur vollständigen Operationalisierung in #504 gelten folgende Mindestanker:
- `api.request.start` / `api.request.end` enthalten korrelierbare Request-IDs.
- Mobile-Geolocation-Felder dürfen in Logs nur nach Redaction-Regeln auftauchen.
- Keine persistente Speicherung von präzisen Standortdaten außerhalb des Request-Kontexts ohne expliziten Folgebeschluss.

## 6) Additive Kompatibilität zu Contract v1

- Bestehende Clients ohne `options.mobile_geolocation` bleiben vollständig kompatibel.
- Bestehende `query`- oder `coordinates`-Flows bleiben unverändert.
- Die neuen Felder sind optional, versionierbar und ohne Breaking Change einführbar.

Referenz-Hauptvertrag:
- [`docs/api/contract-v1.md`](./contract-v1.md)

## 7) Folgepunkte / Status

- #503 — Mobile State-/Interaction-Contract für Permission/Retry/Offline (umgesetzt; v1-Doku: [`docs/gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md`](../gui/MOBILE_GEOLOCATION_STATE_INTERACTION_V1.md)).
- #504 — Mobile Trace-/Privacy-Guardrails inkl. Evidence-Schema (umgesetzt; v1-Doku: [`docs/testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md`](../testing/MOBILE_GEOLOCATION_TRACE_PRIVACY_V1.md)).

## 8) Definition-of-Done-Check (#502)

- [x] Request-/Response-Erweiterung als additive v1-Regel dokumentiert
- [x] Fehler-/Fallback-Semantik deterministisch beschrieben
- [x] Follow-up-Abhängigkeiten (#503/#504) explizit verlinkt
- [x] Regressions-Guard für Doku/Verlinkung ergänzt
