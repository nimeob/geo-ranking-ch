# BL-20.4.a — Umfeldprofil Radiusmodell + Kernkennzahlen (v1)

Stand: 2026-02-27  
Scope: `result.data.modules.intelligence.environment_profile`

## Ziel

Für Vertical B (Adresse -> Umfeldprofil) wird ein reproduzierbares Radiusmodell benötigt,
das POI-Signale robust aggregiert und als erklärbare Kernkennzahlen ausliefert.

## Radiusmodell (v1)

`environment_profile.model` nutzt ein **konzentrisches 3-Ring-Modell**:

- `inner` (stärkste Gewichtung)
- `mid`
- `outer` (schwächste Gewichtung)

Die Ringgrenzen werden aus `radius_m` abgeleitet und je Request im Payload mitgeliefert:

- `model.radius_m`
- `model.rings[]` (`id`, `max_distance_m`, `weight`)
- `model.distance_weighting = ring_weight * (0.4 + 0.6 * proximity)`

Damit bleibt die Berechnung transparent und für Integratoren nachvollziehbar.

## Kernkennzahlen (v1)

`environment_profile.metrics` liefert additive v1-Kernmetriken (`0..100`):

- `density_score` (POI-Dichte im Radius)
- `diversity_score` (Domain-Abdeckung)
- `accessibility_score` (Transit + Daily Needs + Health + Education)
- `family_support_score` (Education + Health + Green)
- `vitality_score` (Daily Needs + Nightlife + Transit)
- `quietness_score` (gegenläufig zu Nightlife, mit Green-Ausgleich)
- `overall_score` (Mittelwert der Kernmetriken)

Zusätzlich:

- `counts.poi_total`
- `counts.by_domain`
- `counts.by_ring`
- `counts.density_per_km2`
- `signals[]` (gewichtete Top-Signale)

## Forward-Compatibility

- Das Modell ist **additiv** in `intelligence` integriert (kein Breaking Change).
- Explainability bleibt faktor-/domain-basiert (`counts`, `signals`, `model`).
- Künftige Presets/Personalisierung können auf `metrics.*` und `counts.by_domain` aufsetzen,
  ohne den Envelope zu brechen.

## Verwandte Spezifikation

- Für die Scoring-Formel, faktorweise Explainability (`score_model`) und Kalibrierungsfälle siehe:
  [`docs/api/environment-profile-scoring-v1.md`](environment-profile-scoring-v1.md)
