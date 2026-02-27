"""Personalisierte Zwei-Stufen-Gewichtung für Suitability-Scores.

Dieses Modul normalisiert Nutzerpräferenzen, berechnet daraus stabile
Gewichtsanpassungen (Delta-Matrix) und liefert nachvollziehbare Metadaten
für die Runtime-Personalisierung im Analyze-Flow.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence


_DEFAULT_PROFILE = {
    "lifestyle_density": "suburban",
    "noise_tolerance": "medium",
    "nightlife_preference": "neutral",
    "school_proximity": "neutral",
    "family_friendly_focus": "medium",
    "commute_priority": "mixed",
    "weights": {},
}

# Domain-Matrix für BL-20.4.d (v1 Draft)
# Werte sind additive Delta-Faktoren auf Gewichtsebene.
# Beispiel: +0.10 bedeutet +10% auf das Basisgewicht des Faktors.
_DELTA_MATRIX: Dict[str, Dict[str, Dict[str, float]]] = {
    "lifestyle_density": {
        "urban": {"access": 0.12, "topography": -0.04, "building_state": -0.03},
        "suburban": {},
        "rural": {"topography": 0.10, "building_state": 0.03, "access": -0.08},
    },
    "noise_tolerance": {
        "low": {"topography": 0.04, "access": 0.06},
        "medium": {},
        "high": {"topography": -0.02, "access": -0.03},
    },
    "nightlife_preference": {
        "avoid": {"topography": 0.03, "access": -0.02},
        "neutral": {},
        "prefer": {"access": 0.05, "building_state": -0.01},
    },
    "school_proximity": {
        "avoid": {"building_state": -0.04, "access": -0.01},
        "neutral": {},
        "prefer": {"building_state": 0.06, "access": 0.03},
    },
    "family_friendly_focus": {
        "low": {"building_state": -0.06, "access": -0.02},
        "medium": {},
        "high": {"building_state": 0.08, "topography": 0.03},
    },
    "commute_priority": {
        "car": {"access": -0.04, "topography": 0.04},
        "pt": {"access": 0.10, "topography": -0.02},
        "bike": {"access": 0.08, "topography": -0.01},
        "mixed": {},
    },
}


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return parsed


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalize_factor_rows(factors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for factor in factors:
        key = str(factor.get("key") or "").strip()
        if not key:
            continue
        score = _clamp(_finite(factor.get("score"), 0.0), 0.0, 100.0)
        weight = max(0.0, _finite(factor.get("weight"), 0.0))
        rows.append({"key": key, "score": score, "weight": weight})
    return rows


def _effective_preferences(preferences: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(_DEFAULT_PROFILE)
    if not isinstance(preferences, Mapping):
        return out

    for key in _DEFAULT_PROFILE:
        if key == "weights":
            continue
        if key in preferences:
            out[key] = str(preferences.get(key, "")).strip().lower() or _DEFAULT_PROFILE[key]

    raw_weights = preferences.get("weights")
    norm_weights: dict[str, float] = {}
    if isinstance(raw_weights, Mapping):
        for key, value in raw_weights.items():
            val = _finite(value, -1.0)
            if 0.0 <= val <= 1.0:
                norm_weights[str(key)] = float(val)
    out["weights"] = norm_weights
    return out


def _compute_personalization_delta(
    *,
    factor_keys: Sequence[str],
    preferences: Mapping[str, Any],
) -> tuple[dict[str, float], bool]:
    deltas = {key: 0.0 for key in factor_keys}
    has_signal = False

    custom_weights = preferences.get("weights") if isinstance(preferences.get("weights"), Mapping) else {}

    for dimension, profile_map in _DELTA_MATRIX.items():
        selected_value = str(preferences.get(dimension, "")).strip().lower()
        per_factor = profile_map.get(selected_value) or {}
        if not per_factor:
            continue

        intensity = _finite(custom_weights.get(dimension), 1.0)
        intensity = _clamp(intensity, 0.0, 1.0)
        if intensity <= 0:
            continue

        for factor_key, delta in per_factor.items():
            if factor_key not in deltas:
                continue
            applied_delta = float(delta) * intensity
            if abs(applied_delta) <= 1e-12:
                continue
            deltas[factor_key] += applied_delta
            has_signal = True

    return deltas, has_signal


def compute_two_stage_scores(
    factors: Sequence[Mapping[str, Any]],
    preferences: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Berechnet base_score + personalized_score deterministisch.

    Fallback-Regel (BL-20.4.d):
    - Ohne Präferenzsignal wird `personalized_score` exakt auf `base_score` gesetzt.

    Input-Faktoren erwarten je Zeile mindestens:
    - `key`: eindeutiger Faktorname
    - `score`: Faktorwert 0..100
    - `weight`: Basisgewicht >= 0
    """

    rows = _normalize_factor_rows(factors)
    if not rows:
        return {
            "base_score": 0.0,
            "personalized_score": 0.0,
            "fallback_applied": True,
            "weights": {"base": {}, "personalized": {}, "delta": {}},
            "signal_strength": 0.0,
        }

    base_weights = {row["key"]: float(row["weight"]) for row in rows}
    base_total_weight = sum(base_weights.values())

    base_score = sum(float(row["score"]) * float(row["weight"]) for row in rows)
    base_score = round(base_score, 4)

    effective_preferences = _effective_preferences(preferences)
    delta_map, has_signal = _compute_personalization_delta(
        factor_keys=list(base_weights.keys()),
        preferences=effective_preferences,
    )

    if not has_signal or base_total_weight <= 0:
        return {
            "base_score": base_score,
            "personalized_score": base_score,
            "fallback_applied": True,
            "weights": {
                "base": {k: round(v, 6) for k, v in base_weights.items()},
                "personalized": {k: round(v, 6) for k, v in base_weights.items()},
                "delta": {k: round(delta_map.get(k, 0.0), 6) for k in base_weights},
            },
            "signal_strength": 0.0,
        }

    raw_personalized_weights: dict[str, float] = {}
    for key, weight in base_weights.items():
        multiplier = max(0.05, 1.0 + float(delta_map.get(key, 0.0)))
        raw_personalized_weights[key] = weight * multiplier

    personalized_total = sum(raw_personalized_weights.values())
    if personalized_total <= 0:
        personalized_weights = dict(base_weights)
    else:
        # Normalisierung auf das gleiche Gesamtgewicht wie base (stabile Vergleichbarkeit)
        norm_factor = base_total_weight / personalized_total
        personalized_weights = {
            key: value * norm_factor for key, value in raw_personalized_weights.items()
        }

    personalized_score = sum(
        float(row["score"]) * float(personalized_weights.get(row["key"], 0.0))
        for row in rows
    )

    signal_strength = sum(abs(float(delta_map.get(k, 0.0))) for k in base_weights)

    return {
        "base_score": base_score,
        "personalized_score": round(personalized_score, 4),
        "fallback_applied": False,
        "weights": {
            "base": {k: round(v, 6) for k, v in base_weights.items()},
            "personalized": {k: round(v, 6) for k, v in personalized_weights.items()},
            "delta": {k: round(delta_map.get(k, 0.0), 6) for k in base_weights},
        },
        "signal_strength": round(signal_strength, 6),
    }
