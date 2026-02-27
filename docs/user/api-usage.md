# API Usage Guide

Dieser Guide beschreibt die HTTP-API des Webservice (`src/web_service.py`) inkl. Auth, Request-ID-Verhalten, Validierung und typische Fehlercodes.

## Base URL

Lokal:

```text
http://localhost:8080
```

Dev/Remote (Beispiel):

```text
https://<dein-endpoint>
```

## Endpoint-Referenz

| Methode | Pfad | Zweck | Auth |
|---|---|---|---|
| `GET` | `/health` | Liveness/Service-Erreichbarkeit | nein |
| `GET` | `/version` | Build-/Version-Metadaten | nein |
| `GET` | `/api/v1/dictionaries` | Dictionary-Index (Versionen/ETags/Domain-Pfade) | nein |
| `GET` | `/api/v1/dictionaries/<domain>` | Domain-spezifisches Dictionary (z. B. `heating`) | nein |
| `POST` | `/analyze` | Adressanalyse und Standort-Resultat | optional (`API_AUTH_TOKEN`) |

> BL-20 Vertragsarbeit: Der versionierte Produktvertrag liegt unter [`docs/api/contract-v1.md`](../api/contract-v1.md) (Namespace `/api/v1`).
> Maschinenlesbarer Feldkatalog für Response-Felder: [`docs/api/field_catalog.json`](../api/field_catalog.json).

### Routing-Verhalten (wichtig)

Der Service normalisiert eingehende Pfade robust:

- trailing Slash wird toleriert (`/health/`, `/analyze/`)
- doppelte Slashes werden kollabiert (`//analyze//` → `/analyze`)
- Query/Fragment werden für Routing ignoriert (`/health?probe=1`)

---

## `GET /health`

### Beispiel

```bash
curl -sS "http://localhost:8080/health"
```

### Erfolgsantwort (200)

```json
{
  "ok": true,
  "service": "geo-ranking-ch",
  "ts": "2026-02-26T17:02:31.123456+00:00",
  "request_id": "req-3e5f0a1f0a87419d"
}
```

---

## `GET /version`

Liefert Build-Metadaten aus ENV:

- `APP_VERSION` (Default: `dev`)
- `GIT_SHA` (Default: `unknown`)

### Beispiel

```bash
curl -sS "http://localhost:8080/version"
```

### Erfolgsantwort (200)

```json
{
  "service": "geo-ranking-ch",
  "version": "dev",
  "commit": "unknown",
  "request_id": "req-5ac7d9c5f2b74835"
}
```

---

## `GET /api/v1/dictionaries`

Liefert den Dictionary-Index für code-first Integrationen (BL-20.1.k):

- globale `version` + `etag`
- Domain-Metadaten unter `domains.<name>` mit `version`, `etag`, `path`
- Cache-fähig via `ETag` + `If-None-Match` (`304 Not Modified` bei Treffer)

### Beispiel

```bash
curl -i -sS "http://localhost:8080/api/v1/dictionaries"
```

## `GET /api/v1/dictionaries/<domain>`

Liefert die vollständigen Mapping-Tabellen einer Domain (aktuell u. a. `heating`, `building`).

### Beispiel (`heating`)

```bash
curl -i -sS "http://localhost:8080/api/v1/dictionaries/heating"
```

Conditional-GET mit Cache-Reuse:

```bash
curl -i -sS "http://localhost:8080/api/v1/dictionaries/heating" \
  -H 'If-None-Match: "dict-heating-..."'
```

---

## `POST /analyze`

### Request-Body

| Feld | Typ | Pflicht | Default | Beschreibung |
|---|---|---|---|---|
| `query` | `string` | ja | – | Adresse/Suchtext; wird getrimmt; leer/whitespace-only ist ungültig |
| `intelligence_mode` | `string` | nein | `basic` | Erlaubt: `basic`, `extended`, `risk` (trim + case-insensitive normalisiert) |
| `timeout_seconds` | `number` | nein | `ANALYZE_DEFAULT_TIMEOUT_SECONDS` (15) | Muss endliche Zahl > 0 sein; wird auf `ANALYZE_MAX_TIMEOUT_SECONDS` gecappt |
| `options` | `object` | nein | `{}` | Additiver Feature-Namespace. Relevante Keys: `response_mode=compact|verbose` (Default `compact`) und `include_labels` (`boolean`, Default `false`, temporärer Legacy-Kompatibilitätsmodus). Unbekannte Keys bleiben No-Op. |
| `preferences` | `object` | nein | Contract-Defaults | Optionales Präferenzprofil: entweder direkt über Enum-Felder (`lifestyle_density`, `noise_tolerance`, `nightlife_preference`, `school_proximity`, `family_friendly_focus`, `commute_priority`) oder über `preset` + `preset_version` (`v1`). Optional `weights` mit `0..1`; nur endliche Zahlen, keine Booleans/`NaN`/`Inf`. |

Preset-Schnellstart: `preferences.preset` + `preferences.preset_version` (`v1`) reicht für einen validen Start.
Wenn zusätzlich Enum-Felder oder `weights` gesetzt sind, gelten diese deterministisch als Overrides.

Vollständige Profilbeispiele inkl. Preset-Katalog: [`docs/api/preference-profiles.md`](../api/preference-profiles.md)

### Beispiel (ohne Auth)

```bash
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: api-guide-001" \
  -d '{
    "query":"Bahnhofstrasse 1, 8001 Zürich",
    "intelligence_mode":"extended",
    "timeout_seconds": 15,
    "preferences": {
      "lifestyle_density": "urban",
      "noise_tolerance": "low",
      "nightlife_preference": "prefer",
      "school_proximity": "neutral",
      "family_friendly_focus": "medium",
      "commute_priority": "pt",
      "weights": {
        "noise_tolerance": 0.8,
        "commute_priority": 0.7
      }
    }
  }'
```

### Beispiel (mit Auth)

```bash
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_AUTH_TOKEN>" \
  -d '{"query":"St. Gallen"}'
```

### Erfolgsantwort (200, verkürzt)

> Contract-Hinweis (BL-20.1.c): Der Webservice trennt Antwortdaten strikt in `result.status` (Qualität/Source-Health/Meta) und `result.data` (fachliche Daten).
>
> Runtime-Personalisierung (BL-20.4.d.wp7): `result.status.personalization` kennzeichnet den Laufzeitpfad als `active`, `partial` oder `deactivated` inkl. Herkunft (`source`).
>
> Code-first Runtime (BL-20.1.k.wp3): `result.status.dictionary` liefert die Dictionary-Referenzen; label-lastige Felder wie `building.decoded` und `energy.decoded_summary` sind im grouped-Result standardmäßig nicht mehr enthalten.

```json
{
  "ok": true,
  "result": {
    "status": {
      "quality": {
        "confidence": {
          "score": 92,
          "max": 100,
          "level": "high"
        },
        "executive_summary": {
          "verdict": "ok"
        }
      },
      "source_health": {
        "geoadmin_search": {
          "status": "ok",
          "records": 1
        }
      },
      "source_meta": {
        "source_attribution": {
          "match": [
            "geoadmin_search"
          ]
        }
      },
      "dictionary": {
        "version": "2026-02-27",
        "etag": "\"dict-index-a1b2c3d4\""
      }
    },
    "data": {
      "entity": {
        "query": "Bahnhofstrasse 1, 8001 Zürich",
        "matched_address": "Bahnhofstrasse 1, 8001 Zürich"
      },
      "modules": {
        "match": {
          "selected_score": 0.99,
          "candidate_count": 3
        }
      },
      "by_source": {
        "geoadmin_search": {
          "source": "geoadmin_search",
          "data": {
            "match": {
              "module_ref": "#/result/data/modules/match",
              "selected_score": 0.99,
              "candidate_count": 3
            }
          }
        }
      }
    }
  },
  "request_id": "api-guide-001"
}
```

Weitere versionierte Beispielpayloads:

- Legacy (vollständig): [`docs/api/examples/v1/location-intelligence.response.success.address.json`](../api/examples/v1/location-intelligence.response.success.address.json)
- Grouped (vollständig): [`docs/api/examples/current/analyze.response.grouped.success.json`](../api/examples/current/analyze.response.grouped.success.json)
- Grouped Edge-Case (fehlende/deaktivierte Daten): [`docs/api/examples/current/analyze.response.grouped.partial-disabled.json`](../api/examples/current/analyze.response.grouped.partial-disabled.json)

### Migration: temporärer Legacy-Kompatibilitätsmodus (`options.include_labels`)

Default-Verhalten ist code-first (`include_labels=false`): `building.decoded`/`energy.decoded_summary` entfallen,
Klartextauflösung läuft über `GET /api/v1/dictionaries*`.

Falls ein bestehender Consumer kurzfristig noch Inline-Labels benötigt:

```bash
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_AUTH_TOKEN>" \
  -d '{
    "query": "Espenmoosstrasse 18, 9008 St. Gallen",
    "options": {
      "include_labels": true
    }
  }'
```

Hinweis: `include_labels` ist eine Migrationsbrücke und kein Zielzustand. Für neue Integrationen immer code-first + Dictionary-Caching verwenden.

## Mapping-/Transform-Regeln richtig lesen (Kurzfassung)

Für Integratoren wichtig: Die API liefert **normalisierte Domain-Daten**, nicht rohe Quellpayloads.

- **Trim + Null-Handling:** Leere/whitespace-only Quellwerte werden zu `null` normalisiert. `null` bedeutet daher oft „nicht belastbar verfügbar“, nicht automatisch „technischer Fehler“.
- **Numerik + Grenzen:** Numerische Felder werden robust geparst; unklare Werte fallen auf `null`. Scores/Konfidenzen werden auf gültige Bereiche begrenzt (z. B. `0..1` oder `0..100`).
- **Status-Vokabular:** Quellenstatus wird auf ein kontrolliertes Set gemappt (`ok`, `partial`, `error`, `disabled`, `not_used`) und ist deshalb über Sources hinweg konsistent interpretierbar.
- **Zeitstempel:** Beobachtungszeitpunkte werden als ISO-8601 UTC normalisiert, damit Event-Reihenfolgen vergleichbar bleiben.
- **`modules` vs. `by_source`:** `modules` ist die fachliche Single-Source-of-Truth; `by_source` ist standardmäßig (`options.response_mode=compact`) eine schlanke Quellenprojektion mit Referenzen (`module_ref`/`module_refs`). Für volle Inline-Projektion kann `options.response_mode=verbose` gesetzt werden.

Technische Tiefendoku (vollständige Regelmatrix + Rule-IDs `TR-01` bis `TR-08`):

- [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](../DATA_SOURCE_FIELD_MAPPING_CH.md)
- [`src/mapping_transform_rules.py`](../../src/mapping_transform_rules.py)

---

## Authentifizierung

`POST /analyze` ist nur dann geschützt, wenn `API_AUTH_TOKEN` gesetzt ist.

### Verhalten

- `API_AUTH_TOKEN` **nicht gesetzt** → Endpoint ist offen.
- `API_AUTH_TOKEN` gesetzt → Header `Authorization: Bearer <token>` ist Pflicht.
- Fehlender/falscher Token → `401 unauthorized`.

---

## Request-ID-Korrelation

Jede Antwort enthält:

- JSON-Feld `request_id`
- Response-Header `X-Request-Id`

Falls kein gültiger Header mitgegeben wurde, erzeugt der Service automatisch eine ID (`req-<suffix>`).

### Unterstützte Header (Priorität)

1. `X-Request-Id`
2. `X_Request_Id`
3. `Request-Id`
4. `Request_Id`
5. `X-Correlation-Id`
6. `X_Correlation_Id`
7. `Correlation-Id`
8. `Correlation_Id`

### Validierungsregeln für Header-IDs

Ein Header-Wert wird nur akzeptiert, wenn er:

- nach Trim nicht leer ist
- keine Steuerzeichen enthält
- keinen Whitespace innerhalb der ID enthält
- keine Trennzeichen `,` oder `;` enthält
- ASCII-only ist
- maximal 128 Zeichen hat

Ungültige Kandidaten werden verworfen, danach greift der nächste Header in Prioritätsreihenfolge.

---

## Statuscodes und Fehlerbilder

| HTTP | `error` | Wann |
|---|---|---|
| `200` | – | erfolgreicher Request |
| `400` | `bad_request` | ungültiger Body, fehlendes `query`, ungültiges `intelligence_mode`, ungültiges `timeout_seconds` |
| `401` | `unauthorized` | Auth aktiv, aber fehlender/falscher Bearer-Token |
| `404` | `not_found` | unbekannter Endpoint |
| `422` | `address_intel` | fachlicher Fehler aus Address-Intelligence-Layer |
| `504` | `timeout` | Upstream/Analyse-Timeout |
| `500` | `internal` | unerwarteter interner Fehler |

### Fehlerantwort (Beispiel)

```json
{
  "ok": false,
  "error": "bad_request",
  "message": "timeout_seconds must be a finite number > 0",
  "request_id": "req-0a5e5c0f89e34713"
}
```

---

## Konfigurations-ENV (API-relevant)

| Variable | Default | Wirkung |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind-Adresse des HTTP-Servers |
| `PORT` | – | Primärer Listen-Port |
| `WEB_PORT` | `8080` | Fallback-Port, falls `PORT` fehlt/leer |
| `API_AUTH_TOKEN` | leer | Aktiviert Bearer-Auth auf `POST /analyze` |
| `ANALYZE_DEFAULT_TIMEOUT_SECONDS` | `15` | Default für `timeout_seconds`, wenn im Request nicht gesetzt |
| `ANALYZE_MAX_TIMEOUT_SECONDS` | `45` | Obergrenze für effektiven Analyze-Timeout |
| `APP_VERSION` | `dev` | Ausgabe in `GET /version` |
| `GIT_SHA` | `unknown` | Ausgabe in `GET /version` |

Hinweis: Eine vollständige ENV-Referenz folgt in **BL-19.3 (Configuration Guide)**.

---

## Schnell-Checks

```bash
# Health
curl -sS "http://localhost:8080/health"

# Version
curl -sS "http://localhost:8080/version"

# Analyze minimal
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query":"St. Gallen"}'
```

Nächste Seiten:

- [Explainability v2 Integrator Guide](./explainability-v2-integrator-guide.md)
- [Configuration / ENV](./configuration-env.md)
- [Troubleshooting](./troubleshooting.md)
