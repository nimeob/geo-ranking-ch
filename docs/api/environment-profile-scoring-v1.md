# BL-20.4.b — Umfeldprofil-Scoring v1

Stand: 2026-02-27  
Scope: `result.data.modules.intelligence.environment_profile`

## Ziel

BL-20.4.b ergänzt das Radiusmodell aus BL-20.4.a um eine **klare Scoring-Formel**,
**faktorweise Explainability** und eine **reproduzierbare Kalibrierungsbasis**.

## Formel (v1)

Die sechs Kernfaktoren werden additiv auf `0..100` berechnet und anschließend gleich gewichtet:

- `density_score`
- `diversity_score`
- `accessibility_score`
- `family_support_score`
- `vitality_score`
- `quietness_score`

Formel:

`overall_score = Σ(factor_score * factor_weight), factor_weight = 1/6`

Damit bleibt die Berechnung transparent, deterministisch und ohne versteckte Heuristik-Schichten.

## Explainability im Output

Zusätzlich zu `metrics.*` liefert das Profil jetzt `score_model`:

- `score_model.id = environment-profile-scoring-v1`
- `score_model.formula`
- `score_model.factors[]` mit
  - `key`
  - `score`
  - `weight`
  - `weighted_points`
- `score_model.overall_score_raw`

Dadurch kann jeder Integrator direkt nachvollziehen, **welcher Faktor wie stark** in den Endscore eingeht.

## Kalibrierung (v1-Referenzfälle)

Die v1-Kalibrierung wird über deterministische Archetypen in den Tests abgesichert (`tests/test_core.py`, `test_environment_profile_scoring_calibration_archetypes`):

1. **urban_mixed**
   - Erwartung: höherer `vitality_score` als bei `quiet_green`
2. **family_balanced**
   - Erwartung: höherer `family_support_score` als bei `urban_mixed`
3. **quiet_green**
   - Erwartung: höherer `quietness_score` als bei `urban_mixed`

Diese Referenzfälle bilden eine stabile Drift-Basis, ohne externe Live-Datenabhängigkeit.

## Forward-Compatibility (BL-30 Guardrail)

- Faktorweise Explainability bleibt explizit erhalten (`score_model.factors[]`).
- Presets/Personalisierung können additive Gewichtsvarianten einführen, ohne den v1-Envelope zu brechen.
- Deep-Mode-Modelle (BL-30.3) können auf denselben Faktorschlüsseln aufsetzen und optional zusätzliche Faktoren ergänzen.
