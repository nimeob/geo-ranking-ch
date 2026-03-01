# BL-30.6.wp3 — Mobile Geolocation Trace-/Privacy-Guardrails v1

Stand: 2026-03-01

Bezug: [#113](https://github.com/nimeob/geo-ranking-ch/issues/113), [#504](https://github.com/nimeob/geo-ranking-ch/issues/504)

## 1) Ziel und Scope (v1)

Dieses Dokument definiert den **operativen Mindeststandard** für Telemetrie und Privacy im Mobile-Geolocation-Flow.
Ziel ist reproduzierbare Diagnosefähigkeit bei gleichzeitiger Datensparsamkeit.

In Scope (wp3):
- normative Mindestevent-Liste für den Mobile-Geolocation-Lifecycle
- Privacy-/Redaction-Regeln pro Feldklasse
- standardisiertes Trace-Evidence-Format für Nachweise in Incident-/Abnahmefällen

Nicht in Scope:
- produktspezifische SIEM-/Data-Lake-Implementierung
- endgültige regulatorische Jurisdiktionsdetails (folgen in BL-30.6-Folgearbeiten bei Bedarf)

## 2) Mindestevent-Liste (Mobile-Geolocation-Lifecycle)

Pflichtanker (muss pro Mobile-Analyze-Flow korrelierbar vorhanden sein):
- `ui.input.accepted`
- `ui.api.request.start`
- `api.request.start`
- `api.request.end`
- `ui.api.request.end`

Mobile-spezifische Pflichtmarker (additiv, v1):
- `ui.mobile.permission.state` (`prompt|granted|denied`)
- `ui.mobile.locate.start`
- `ui.mobile.locate.end`
- `ui.mobile.offline.state`
- `ui.mobile.retry.triggered`

Korrelation:
- `trace_id` und `request_id` müssen über UI-/API-Events eines Flows stabil sein.
- `session_id` ist verpflichtend, falls Client-Session verfügbar ist.

## 3) Privacy-/Redaction-Regeln pro Feldklasse

| Feldklasse | Beispiele | Logging-Regel (v1) | Aufbewahrung (Minimum) |
|---|---|---|---|
| **Präzise Standortdaten** | `coordinates.lat`, `coordinates.lon` | Nicht roh persistieren; nur redacted/abgeleitet (z. B. gerundete Genauigkeitsklasse) | nur transiente Verarbeitung im Request-Kontext |
| **Location-Metadaten** | `accuracy_meters`, `location_age_seconds`, `source` | erlaubt, sofern nicht zur Re-Identifikation geeignet kombiniert | 7 Tage |
| **Permission-/Gerätezustand** | `permission_state`, `battery_saver`, `network_offline` | erlaubt; keine gerätespezifischen Fingerprints speichern | 14 Tage |
| **Korrelation** | `trace_id`, `request_id`, `session_id` | erlaubt, pseudonymisiert und ohne direkte Personenreferenz | 14 Tage |
| **Freitext/Input** | `query` | nur minimiert/sanitized; PII-Muster redaction-pflichtig | 7 Tage |
| **Credentials/Secrets** | `authorization`, `token`, `api_key`, `cookie` | immer `[REDACTED]` (verbindlich, siehe Logging-Schema) | nie im Klartext speichern |

Zusätzliche Guardrails:
1. Keine dauerhafte Speicherung kombinierter Präzisionskoordinaten + direkte Nutzerkennung.
2. Keine Hintergrundübertragung von Standortevents im `offline_fallback`, solange kein aktiver Analyze-Retry vorliegt.
3. Debug-Exports für Incidents enthalten nur minimierte Felder und müssen als „need-to-know“ behandelt werden.

## 4) Trace-Evidence-Nachweisformat (verbindlich)

Evidence wird als JSONL erstellt (eine Zeile pro Event) und enthält pro Eintrag mindestens:
- `ts`, `event`, `level`, `trace_id`, `request_id`, `session_id`
- `component`, `status`
- `privacy_class` (z. B. `location_precise`, `location_meta`, `correlation`, `secret`)
- `redaction_applied` (`true|false`)

Zusätzlich wird ein Header-Metadatensatz empfohlen:

```json
{
  "evidence_run_id": "bl30-6-mobile-20260301T060000Z",
  "environment": "dev",
  "generated_at_utc": "2026-03-01T06:00:00Z",
  "source": "mobile-geolocation-trace-v1"
}
```

### Akzeptanzkriterien für ein gültiges Evidence-Bundle

1. Alle Pflichtevents aus Abschnitt 2 sind enthalten.
2. Kein Event enthält unredacted Secrets (`authorization`, `token`, `api_key`, `cookie`).
3. Kein Event enthält rohe Präzisionskoordinaten als dauerhaftes Logfeld.
4. Für jeden Flow ist `request_id` durchgängig korrelierbar.
5. Bei Retry/Offline-Pfaden sind `ui.mobile.retry.triggered` und/oder `ui.mobile.offline.state` nachvollziehbar.

## 5) Logging-Schema-Integration

Dieses Guardrail-Profil erweitert den allgemeinen Standard aus [`docs/LOGGING_SCHEMA_V1.md`](../LOGGING_SCHEMA_V1.md).
Die dortigen Pflichtfelder bleiben unverändert; Mobile-Geolocation ergänzt nur additive Eventmarker und Privacy-Klassen.

## 6) Definition-of-Done-Check (#504)

- [x] Mindestevent-Liste für Mobile-Geolocation-Lifecycle dokumentiert
- [x] Privacy-/Redaction-Regeln pro Feldklasse dokumentiert
- [x] Nachweisformat für Trace-Evidence festgelegt
- [x] Logging-Schema-Referenz konsistent ergänzt
- [x] Regressions-Guard für Pflichtmarker ergänzt
