# Explainability v2 Integrator Guide (BL-20.1.g.wp3)

Dieser Guide beschreibt, wie Frontends/Integratoren Explainability-v2-Faktoren robust und verständlich darstellen.

## 1) Relevante Datenpfade

Explainability v2 liegt in beiden Response-Shapes unter denselben Buckets:

- Legacy-Shape: `result.explainability.base.factors[*]`, `result.explainability.personalized.factors[*]`
- Grouped-Shape: `result.data.modules.explainability.base.factors[*]`, `result.data.modules.explainability.personalized.factors[*]`

Pflichtfelder je Faktor:

- `key`
- `raw_value`
- `normalized`
- `weight`
- `contribution`
- `direction` (`pro|contra|neutral`)
- `reason`
- `source`

## 2) Rendering-Regeln (verbindliche Empfehlung)

### 2.1 Semantik von `direction` + `contribution`

- `direction=pro` → positiver Treiber (UI z. B. grün)
- `direction=contra` → negativer Treiber (UI z. B. rot)
- `direction=neutral` → informativer Faktor ohne klare Präferenzrichtung (UI z. B. grau)

Für Rangfolge/Top-Faktoren zählt die **Stärke** über `abs(contribution)`.

### 2.2 Sortierung/Gruppierung

Empfohlen pro Bucket (`base`, `personalized`):

1. Faktoren nach `abs(contribution)` absteigend sortieren.
2. In UI in zwei Gruppen splitten:
   - **Pro**: `direction=pro`
   - **Contra**: `direction=contra`
3. Optional eigene Gruppe **Neutral** (`direction=neutral`) am Ende.

Default für kompakte UIs:

- Top 3 Pro + Top 3 Contra zeigen
- Rest hinter „Weitere Faktoren“ einklappen

### 2.3 Anzeigeformat pro Faktor

Empfohlene Zeile/Karte:

- Titel: lokalisierter Label-Key aus `key` (siehe i18n-Regeln)
- Badge: `direction`
- Primärer Wert: `contribution` (inkl. Vorzeichen)
- Sekundär: `raw_value`, `normalized`, `weight`
- Tooltip/Detail: `reason` + `source`

## 3) JSON-Beispiel (grouped, gekürzt)

```json
{
  "result": {
    "data": {
      "modules": {
        "explainability": {
          "base": {
            "factors": [
              {
                "key": "noise",
                "raw_value": 61,
                "normalized": 0.61,
                "weight": 0.3,
                "contribution": -0.183,
                "direction": "contra",
                "reason": "Lärmbelastung im Radius 500m über Referenzmedian.",
                "source": "laermkataster_ch"
              },
              {
                "key": "schools",
                "raw_value": 4,
                "normalized": 0.8,
                "weight": 0.2,
                "contribution": 0.16,
                "direction": "pro",
                "reason": "Mehrere Schulen/Kitas in fußläufiger Distanz.",
                "source": "poi_school_index"
              }
            ]
          },
          "personalized": {
            "factors": [
              {
                "key": "noise",
                "raw_value": 61,
                "normalized": 0.61,
                "weight": 0.48,
                "contribution": -0.2928,
                "direction": "contra",
                "reason": "Quiet-Profil erhöht das Gewicht für Lärmfaktoren.",
                "source": "laermkataster_ch"
              },
              {
                "key": "schools",
                "raw_value": 4,
                "normalized": 0.8,
                "weight": 0.28,
                "contribution": 0.224,
                "direction": "pro",
                "reason": "Family-orientierter Bias priorisiert Schulnähe stärker.",
                "source": "poi_school_index"
              }
            ]
          }
        }
      }
    }
  }
}
```

Interpretation:

- `noise` wirkt in beiden Buckets negativ (`contra`), im personalisierten Profil stärker.
- `schools` wirkt in beiden Buckets positiv (`pro`), ebenfalls stärker gewichtet im personalisierten Profil.

## 4) Fallback- und Degradationsregeln

### 4.1 Explainability-Block fehlt komplett

Wenn `...explainability` nicht vorhanden ist:

- Explainability-Widget nicht „leer“ rendern, sondern klaren Fallback anzeigen: 
  - „Für dieses Ergebnis liegen aktuell keine Explainability-Faktoren vor.“
- Keine Fake-Nullwerte erzeugen.

### 4.2 Nur ein Bucket vorhanden

Wenn nur `base` oder nur `personalized` vorhanden ist:

- Vorhandenen Bucket normal rendern.
- Fehlenden Bucket als „nicht verfügbar“ markieren (kein Fehlerzustand).

### 4.3 Einzelne Felder/Faktoren unvollständig

Obwohl Felder laut Contract Pflicht sind, sollten Integratoren defensiv bleiben:

- Faktor ohne `key` oder ohne numerischen `contribution` überspringen.
- Unbekanntes `direction` als `neutral` behandeln.
- Fehlende `reason`/`source` als „n/a“ anzeigen.

### 4.4 Leere Arrays

Wenn `factors=[]`:

- Bucket als „keine relevanten Faktoren“ anzeigen.
- Keine Fehlermeldung für Endnutzer erzeugen.

## 5) i18n- und Labeling-Regeln (`key` -> UI-Label)

Empfohlene Mapping-Strategie:

1. Domain-Key über i18n-Map auflösen (z. B. `explainability.factor.noise`).
2. Wenn kein Mapping vorhanden: key lesbar machen (snake_case -> Titel).
3. Zusätzlich technische Original-ID (`key`) in Tooltip/Debug-Ansicht behalten.

Beispiel-Mapping:

| `key` | i18n-Key | de-CH Label (Beispiel) |
|---|---|---|
| `noise` | `explainability.factor.noise` | Lärmbelastung |
| `schools` | `explainability.factor.schools` | Schulnähe |
| `traffic` | `explainability.factor.traffic` | Verkehrsbelastung |
| `nightlife` | `explainability.factor.nightlife` | Nachtleben |

## 6) Referenzen

- Contract: [`docs/api/contract-v1.md`](../api/contract-v1.md)
- Feldreferenz: [`docs/api/field-reference-v1.md`](../api/field-reference-v1.md)
- Legacy-Beispiel: [`docs/api/examples/v1/location-intelligence.response.success.address.json`](../api/examples/v1/location-intelligence.response.success.address.json)
- Grouped-Beispiel: [`docs/api/examples/current/analyze.response.grouped.success.json`](../api/examples/current/analyze.response.grouped.success.json)
- Grouped Edge-Case (fehlende/deaktivierte Daten): [`docs/api/examples/current/analyze.response.grouped.partial-disabled.json`](../api/examples/current/analyze.response.grouped.partial-disabled.json)
