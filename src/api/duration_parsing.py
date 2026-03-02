"""Small helpers for parsing human-friendly durations.

The project has a few places where timeouts/TTLs are configured via ENV/CLI.
To reduce footguns and keep parsing consistent we accept:

- plain numeric values (interpreted as seconds)
- numeric values suffixed with a unit: `s`, `m`, `h`, `d`

Examples: `60`, `15m`, `24h`, `7d`.

Invalid or non-finite values raise `ValueError` (fail-fast).
"""

from __future__ import annotations

import math
from typing import Any


_UNIT_TO_SECONDS: dict[str, float] = {
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
}


def parse_duration_seconds(
    raw: Any,
    *,
    field_name: str = "duration",
) -> float:
    """Parse a duration and return seconds as float.

    Accepted inputs:
    - int/float
    - strings like "60", "15m", "24h", "7d" (case-insensitive unit)

    Rules:
    - If no unit is specified the value is interpreted as seconds.
    - Negative or non-finite values are rejected.

    Raises:
        ValueError: if the value cannot be parsed or is invalid.
    """

    if raw is None:
        raise ValueError(f"{field_name} must be set")

    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        parsed = float(raw)
        if not math.isfinite(parsed) or parsed < 0:
            raise ValueError(f"{field_name} must be a finite number >= 0")
        return parsed

    value = str(raw).strip()
    if not value:
        raise ValueError(f"{field_name} must be set")

    unit = "s"
    last = value[-1]
    if last.isalpha():
        unit = last.lower()
        value = value[:-1].strip()

    if unit not in _UNIT_TO_SECONDS:
        allowed = ", ".join(sorted(_UNIT_TO_SECONDS))
        raise ValueError(f"{field_name} has unknown unit '{unit}' (allowed: {allowed})")

    try:
        magnitude = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be numeric seconds or a duration like '7d'/'24h'"
        ) from exc

    seconds = magnitude * _UNIT_TO_SECONDS[unit]
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"{field_name} must be a finite duration >= 0")

    return float(seconds)
