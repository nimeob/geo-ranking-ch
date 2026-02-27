"""Wiederverwendbare Transform-/Normalisierungsregeln für BL-20.2.b (#64).

Die Regeln orientieren sich an den IDs TR-01..TR-08 aus
`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`.

Hinweis:
- TR-04 (`code_decode_gwr`) bleibt bewusst extern, da die eigentliche
  Decodierung über `src/gwr_codes.py` und Domänenlogik im Address-Flow läuft.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable

SOURCE_POLICY_ORDER = ("official", "licensed", "community", "web", "local_mapping", "unknown")
SOURCE_POLICY_RANK = {name: idx for idx, name in enumerate(SOURCE_POLICY_ORDER)}

ALLOWED_SOURCE_STATUSES = {"ok", "partial", "error", "disabled", "not_used"}
_STATUS_ALIASES = {
    "success": "ok",
    "healthy": "ok",
    "warn": "partial",
    "warning": "partial",
    "degraded": "partial",
    "failed": "error",
    "failure": "error",
    "unavailable": "error",
    "off": "disabled",
    "inactive": "disabled",
    "not-used": "not_used",
    "not used": "not_used",
    "unused": "not_used",
    "skip": "not_used",
    "skipped": "not_used",
    "n/a": "not_used",
    "na": "not_used",
}


def trim_to_null(value: Any) -> Any | None:
    """TR-01: Strings trimmen und leere Werte als `None` behandeln."""
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    return value


def html_strip(value: str | None) -> str | None:
    """TR-02: HTML-Markup aus Strings entfernen, anschließend TR-01 anwenden."""
    cleaned = trim_to_null(value)
    if cleaned is None:
        return None
    return trim_to_null(re.sub(r"<[^>]+>", "", str(cleaned)))


def numeric_parse(value: Any, *, as_int: bool = False) -> float | int | None:
    """TR-03: robuste Zahl-Parser-Logik für String-/Number-Inputs.

    - ignoriert boolesche Werte
    - behandelt leere Werte als None
    - akzeptiert einfache Komma-Dezimalwerte (z. B. "12,5")
    - liefert None bei NaN/Inf oder Parse-Fehler
    """
    if value is None or isinstance(value, bool):
        return None

    number: float
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        raw = trim_to_null(value)
        if raw is None:
            return None
        text = str(raw).replace("'", "").replace(" ", "")
        if text.count(",") == 1 and text.count(".") == 0:
            text = text.replace(",", ".")
        elif "," in text and "." in text:
            text = text.replace(",", "")

        try:
            number = float(text)
        except ValueError:
            return None
    else:
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    if as_int:
        return int(number) if number.is_integer() else None
    return number


def normalize_source_status(value: Any, *, default: str = "not_used") -> str:
    """TR-05: Quellenstatus auf das kontrollierte Set normalisieren."""
    normalized_default = default if default in ALLOWED_SOURCE_STATUSES else "not_used"
    cleaned = trim_to_null(value)
    if cleaned is None:
        return normalized_default

    key = str(cleaned).strip().lower().replace("_", " ")
    key = re.sub(r"\s+", " ", key)

    if key in ALLOWED_SOURCE_STATUSES:
        return key
    mapped = _STATUS_ALIASES.get(key)
    if mapped in ALLOWED_SOURCE_STATUSES:
        return mapped
    return normalized_default


def confidence_clamp(
    value: Any,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
    decimals: int | None = None,
) -> float:
    """TR-06: Konfidenz-/Scorewerte robust parsen und in einen Bereich clampen."""
    low, high = sorted((float(minimum), float(maximum)))
    parsed = numeric_parse(value)
    if parsed is None:
        clamped = low
    else:
        clamped = max(low, min(high, float(parsed)))

    if decimals is not None:
        return round(clamped, int(decimals))
    return clamped


def policy_rank_map(authority: Any) -> int:
    """TR-07: Quellenautorität in den Policy-Rang überführen."""
    cleaned = trim_to_null(authority)
    if cleaned is None:
        return SOURCE_POLICY_RANK["unknown"]
    key = str(cleaned).strip().lower().replace("-", "_")
    return SOURCE_POLICY_RANK.get(key, SOURCE_POLICY_RANK["unknown"])


def normalize_observed_at_iso(value: Any) -> str | None:
    """TR-08: Timestamps auf ISO-8601 UTC (`...Z`) normalisieren."""
    if value is None:
        return None

    dt: datetime
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (ValueError, OSError):
            return None
    else:
        raw = trim_to_null(value)
        if raw is None:
            return None

        text = str(raw)
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(text)
            except (TypeError, ValueError):
                return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    iso_utc = dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    return iso_utc.replace("+00:00", "Z")


TRANSFORM_RULE_HANDLERS: dict[str, Callable[..., Any]] = {
    "TR-01": trim_to_null,
    "TR-02": html_strip,
    "TR-03": numeric_parse,
    "TR-05": normalize_source_status,
    "TR-06": confidence_clamp,
    "TR-07": policy_rank_map,
    "TR-08": normalize_observed_at_iso,
}

EXTERNAL_RULES: dict[str, str] = {
    "TR-04": "code_decode_gwr (domain-spezifisch via src/gwr_codes.py)",
}
