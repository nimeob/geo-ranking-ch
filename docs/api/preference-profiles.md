# Preference-Profile Beispiele (BL-20.4.c)

Stand: 2026-02-27

Dieses Dokument zeigt realistische Request-Profile für `preferences` im v1-Contract.
Die Profile sind additive Optionen; fehlende Felder verwenden die Standardwerte.

## Felddefinitionen

| Feld | Typ | Werte | Default |
|---|---|---|---|
| `lifestyle_density` | `string` | `rural` \| `suburban` \| `urban` | `suburban` |
| `noise_tolerance` | `string` | `low` \| `medium` \| `high` | `medium` |
| `nightlife_preference` | `string` | `avoid` \| `neutral` \| `prefer` | `neutral` |
| `school_proximity` | `string` | `avoid` \| `neutral` \| `prefer` | `neutral` |
| `family_friendly_focus` | `string` | `low` \| `medium` \| `high` | `medium` |
| `commute_priority` | `string` | `car` \| `pt` \| `bike` \| `mixed` | `mixed` |
| `weights.*` | `number` | `0..1` | leer (`{}`) |

## Profile 1 — Urban Pendler:in mit ÖV-Fokus

```json
{
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
}
```

## Profile 2 — Familienfokus im Vorort

```json
{
  "preferences": {
    "lifestyle_density": "suburban",
    "noise_tolerance": "low",
    "nightlife_preference": "avoid",
    "school_proximity": "prefer",
    "family_friendly_focus": "high",
    "commute_priority": "mixed",
    "weights": {
      "school_proximity": 0.9,
      "family_friendly_focus": 0.85
    }
  }
}
```

## Profile 3 — Ländlich, autozentriert, ruhig

```json
{
  "preferences": {
    "lifestyle_density": "rural",
    "noise_tolerance": "low",
    "nightlife_preference": "avoid",
    "school_proximity": "neutral",
    "family_friendly_focus": "medium",
    "commute_priority": "car",
    "weights": {
      "lifestyle_density": 0.75,
      "noise_tolerance": 0.7
    }
  }
}
```

## Profile 4 — Bike-first, urban-neutral

```json
{
  "preferences": {
    "lifestyle_density": "urban",
    "noise_tolerance": "medium",
    "nightlife_preference": "neutral",
    "school_proximity": "neutral",
    "family_friendly_focus": "low",
    "commute_priority": "bike",
    "weights": {
      "commute_priority": 0.9
    }
  }
}
```

## Profile 5 — Minimalprofil (partiell, Defaults aktiv)

```json
{
  "preferences": {
    "lifestyle_density": "rural",
    "weights": {
      "school_proximity": 0.6
    }
  }
}
```

Hinweis: Nicht gesetzte Felder bleiben gültig und werden mit Contract-Defaults aufgefüllt.
