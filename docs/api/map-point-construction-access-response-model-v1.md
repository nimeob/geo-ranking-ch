# BL-30.5.wp3 — Response-Modell v1 für Bau-/Zufahrtseignung (additiv)

## 1) Zielbild und Contract-Einordnung

Dieses Work-Package (#496) definiert ein **implementierbares v1-Response-Modell** für Kartenpunkt-basierte Bau-/Zufahrtseignung im bestehenden grouped Contract.

Der Scope ist explizit additiv:
- kein Breaking-Change an `POST /analyze`
- keine Strukturverschiebung bestehender Kernpfade
- neue Informationen hängen unter einem klaren Modulpfad

Einordnung:
- Parent: #110
- Parent-Epic: #128
- Vorarbeit: #494 (Workflow), #495 (Daten-/Lizenzmatrix)
- Follow-up: #498 (produktive Tile-/ODbL-Compliance-Entscheide)

## 2) Modulpfad im grouped Response-Contract

Das v1-Modell wird als additiver Modulzweig geführt:

- `result.data.modules.map_site_suitability`

Mapping zu grouped-response Konventionen:
- Moduldaten liegen unter `result.data.modules.*`
- Quellenprojektion bleibt unter `result.data.by_source.*`
- Quellgesundheit/Verfügbarkeit bleibt unter `result.status.source_health.*`
- Quellmetadaten bleiben unter `result.status.source_meta.*`

Konkrete Ankerpfade für den Kartenfall:
- `result.data.by_source.map_intelligence.data.module_ref = "map_site_suitability"`
- `result.status.source_health.map_intelligence`
- `result.status.source_meta.map_intelligence`

## 3) V1-Feldmodell (normativ)

### 3.1 Pflichtfelder (MUST)

| Pfad | Typ | Regel |
|---|---|---|
| `result.data.modules.map_site_suitability.version` | `string` | MUST = `"v1"` |
| `result.data.modules.map_site_suitability.assessment.status` | `string` | MUST in `{fit, conditional, not_recommended, unknown}` |
| `result.data.modules.map_site_suitability.assessment.summary` | `string` | MUST, kurze begründete Aussage |
| `result.data.modules.map_site_suitability.confidence.score` | `number` | MUST in `[0,1]` |
| `result.data.modules.map_site_suitability.confidence.level` | `string` | MUST in `{high, medium, low}` |
| `result.data.modules.map_site_suitability.explainability.factors[]` | `array<object>` | MUST, mindestens 1 Faktor |
| `result.data.modules.map_site_suitability.sources[]` | `array<object>` | MUST, mindestens 1 Quelle |
| `result.data.modules.map_site_suitability.sources[].source` | `string` | MUST, kanonischer Source-Key |
| `result.data.modules.map_site_suitability.sources[].as_of` | `string` | MUST, ISO-8601 UTC (`...Z`) |

### 3.2 Explainability-Faktorstruktur (MUST)

Jeder Faktor in `...explainability.factors[]` enthält:
- `key` (`string`, MUST)
- `label` (`string`, SHOULD)
- `value` (`number|string|boolean`, MUST)
- `impact` (`string`, MUST in `{pro, contra, neutral}`)
- `confidence` (`number`, MUST in `[0,1]`)
- `source` (`string`, MUST)

### 3.3 Typische additive Felder (MAY)

- `result.data.modules.map_site_suitability.assessment.constraints[]`
- `result.data.modules.map_site_suitability.assessment.recommendations[]`
- `result.data.modules.map_site_suitability.access.road_type`
- `result.data.modules.map_site_suitability.access.heavy_vehicle_feasibility`
- `result.data.modules.map_site_suitability.topography.slope_percent`

## 4) Beispielpayload (v1, kompakt)

```json
{
  "ok": true,
  "request_id": "req_map_20260301_01",
  "result": {
    "status": {
      "source_health": {
        "map_intelligence": "healthy"
      },
      "source_meta": {
        "map_intelligence": {
          "provider": "osm+swisstopo-mix",
          "as_of": "2026-03-01T05:20:00Z"
        }
      }
    },
    "data": {
      "modules": {
        "map_site_suitability": {
          "version": "v1",
          "assessment": {
            "status": "conditional",
            "summary": "Grundsätzlich geeignet, Zufahrt für Schwerlast nur eingeschränkt.",
            "constraints": [
              "Steigung im letzten Abschnitt erhöht"
            ],
            "recommendations": [
              "Voranalyse für Kranstellung inkl. Zufahrtsfenster durchführen"
            ]
          },
          "confidence": {
            "score": 0.74,
            "level": "medium"
          },
          "explainability": {
            "factors": [
              {
                "key": "slope_segment_120m",
                "label": "Hangneigung 120m Segment",
                "value": 13.4,
                "impact": "contra",
                "confidence": 0.77,
                "source": "swisstopo-terrain"
              },
              {
                "key": "road_class_last_meter",
                "label": "Straßenklasse letzter Zufahrtsabschnitt",
                "value": "secondary",
                "impact": "pro",
                "confidence": 0.82,
                "source": "osm-way-tags"
              }
            ]
          },
          "sources": [
            {
              "source": "swisstopo-terrain",
              "as_of": "2026-02-28T23:10:00Z",
              "license_class": "official_registry"
            },
            {
              "source": "osm-way-tags",
              "as_of": "2026-02-28T22:45:00Z",
              "license_class": "odbl"
            }
          ]
        }
      },
      "by_source": {
        "map_intelligence": {
          "data": {
            "module_ref": "map_site_suitability"
          }
        }
      }
    }
  }
}
```

## 5) Pflichtmarker: Explainability / Confidence / Source

Für BL-30.5.wp3 gilt als Mindeststandard:
- Jede Bau-/Zufahrtsaussage ist über `explainability.factors[]` nachvollziehbar.
- Jede Kernaussage trägt `confidence.score` und `confidence.level`.
- Jede verwendete Datenbasis ist über `sources[].source` + `sources[].as_of` nachweisbar.
- Fehlt ein Pflichtmarker, darf keine finale Eignungsaussage (`fit|conditional|not_recommended`) ausgegeben werden; stattdessen `unknown`.

## 6) Follow-up-Pfade für Runtime-Implementierung

1. Runtime-Projektion in `src/api/address_intel.py` ergänzen (modular, additiv).
2. Contract-/Schema-Abgleich gegen grouped Core-Paths + Field-Catalog durchführen.
3. Lizenz-/Attribution-Boundaries aus #498 in Runtime-Hinweise und Exporte übernehmen.
4. API-Example-Payloads und ggf. Golden-Cases nachziehen, sobald Runtime-Felder live sind.

## 7) Definition-of-Done-Check (#496)

- [x] Feldmodell ist eindeutig und additive-kompatibel.
- [x] Explainability-/Confidence-Felder sind normativ beschrieben.
- [x] Follow-up-Pfade für Runtime-Implementierung sind benannt.
- [x] Tests und Backlog-Status sind synchron.
