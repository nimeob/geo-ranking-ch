# Preference-Profile Beispiele (BL-20.4.e)

Stand: 2026-02-27

Dieses Dokument definiert den **Preset-Katalog v1** für `preferences.preset`.
Ziel: Integratoren können mit **einem Feld** starten und bei Bedarf deterministisch feintunen.

## 1) Contract-Erweiterung (additiv)

Neue optionale Felder im `preferences`-Objekt:

- `preset` (`string`): vordefiniertes Profil
- `preset_version` (`string`): aktuell `v1`
- `weights` (`object`, optional): manuelle Intensitäts-Overrides je Dimension (`0..1`)

Erlaubte Presets in `v1`:

- `urban_lifestyle`
- `family_friendly`
- `quiet_residential`
- `car_commuter`
- `pt_commuter`

## 2) Konfliktregeln (Preset + Overrides)

Deterministische Auflösung (verbindlich):

1. Contract-Defaults
2. Preset-Werte (falls gesetzt)
3. Explizite Enum-Felder im Request überschreiben Preset-Felder
4. Explizite `weights` im Request überschreiben Preset-`weights` pro Key

Damit bleibt das Verhalten reproduzierbar und für Integratoren transparent.

## 3) Preset-Katalog v1 (Semantik + Referenz-Gewichte)

| Preset | Semantik | Enum-Profil | Referenz-`weights` |
|---|---|---|---|
| `urban_lifestyle` | Urbanes Leben mit ÖV-/Nightlife-Nähe | `lifestyle_density=urban`, `noise_tolerance=medium`, `nightlife_preference=prefer`, `school_proximity=neutral`, `family_friendly_focus=low`, `commute_priority=pt` | `nightlife_preference=0.85`, `commute_priority=0.90`, `noise_tolerance=0.45` |
| `family_friendly` | Familienfokus im Vorort | `lifestyle_density=suburban`, `noise_tolerance=low`, `nightlife_preference=avoid`, `school_proximity=prefer`, `family_friendly_focus=high`, `commute_priority=mixed` | `school_proximity=0.95`, `family_friendly_focus=0.95`, `noise_tolerance=0.75` |
| `quiet_residential` | Ruhige Wohnlage, geringe Nightlife-Affinität | `lifestyle_density=suburban`, `noise_tolerance=low`, `nightlife_preference=avoid`, `school_proximity=neutral`, `family_friendly_focus=medium`, `commute_priority=mixed` | `noise_tolerance=0.95`, `nightlife_preference=0.70`, `lifestyle_density=0.60` |
| `car_commuter` | Pendeln primär mit Auto | `lifestyle_density=suburban`, `noise_tolerance=medium`, `nightlife_preference=neutral`, `school_proximity=neutral`, `family_friendly_focus=medium`, `commute_priority=car` | `commute_priority=0.95`, `lifestyle_density=0.55`, `noise_tolerance=0.40` |
| `pt_commuter` | Pendeln primär mit ÖV | `lifestyle_density=urban`, `noise_tolerance=medium`, `nightlife_preference=neutral`, `school_proximity=neutral`, `family_friendly_focus=medium`, `commute_priority=pt` | `commute_priority=0.95`, `lifestyle_density=0.55`, `noise_tolerance=0.40` |

## 4) Beispiele je Preset (Request + Response-Fragment)

> Die Response-Fragmente zeigen den relevanten Nachweis unter `result.status.personalization`.

### 4.1 `urban_lifestyle`

```json
{
  "preferences": {
    "preset": "urban_lifestyle",
    "preset_version": "v1"
  }
}
```

```json
{
  "result": {
    "status": {
      "personalization": {
        "state": "active",
        "source": "personalized_reweighting"
      }
    }
  }
}
```

### 4.2 `family_friendly`

```json
{
  "preferences": {
    "preset": "family_friendly",
    "preset_version": "v1"
  }
}
```

```json
{
  "result": {
    "status": {
      "personalization": {
        "state": "active",
        "source": "personalized_reweighting"
      }
    }
  }
}
```

### 4.3 `quiet_residential`

```json
{
  "preferences": {
    "preset": "quiet_residential",
    "preset_version": "v1"
  }
}
```

```json
{
  "result": {
    "status": {
      "personalization": {
        "state": "active",
        "source": "personalized_reweighting"
      }
    }
  }
}
```

### 4.4 `car_commuter`

```json
{
  "preferences": {
    "preset": "car_commuter",
    "preset_version": "v1"
  }
}
```

```json
{
  "result": {
    "status": {
      "personalization": {
        "state": "active",
        "source": "personalized_reweighting"
      }
    }
  }
}
```

### 4.5 `pt_commuter` mit manuellem Override

```json
{
  "preferences": {
    "preset": "pt_commuter",
    "preset_version": "v1",
    "weights": {
      "commute_priority": 0.7
    }
  }
}
```

```json
{
  "result": {
    "status": {
      "personalization": {
        "state": "active",
        "source": "personalized_reweighting"
      }
    }
  }
}
```
