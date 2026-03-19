from __future__ import annotations

import math
from typing import Any


def _is_present_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized not in {"", "null", "none", "n/a", "nan", "-"}
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def _first_present(*values: Any) -> Any:
    for value in values:
        if _is_present_value(value):
            return value
    return None


def _to_optional_int(value: Any) -> int | None:
    if not _is_present_value(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    rounded = int(round(number))
    return rounded if rounded >= 0 else None


def _to_optional_float(value: Any) -> float | None:
    if not _is_present_value(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number if number >= 0 else None


def build_building_core_profile(
    *,
    gwr: dict[str, Any],
    decoded: dict[str, Any],
    address_registry: dict[str, Any],
) -> dict[str, Any]:
    """Aggregiert Gebäude-Kernfelder robust mit klarer Priorisierungslogik."""
    name = _first_present(
        gwr.get("gbez"),
        gwr.get("strname_deinr"),
        address_registry.get("adr_street"),
    )
    baujahr = _to_optional_int(_first_present(gwr.get("gbauj"), decoded.get("baujahr")))
    flaeche = _to_optional_float(_first_present(gwr.get("garea"), decoded.get("grundflaeche_m2")))
    geschosse = _to_optional_int(_first_present(gwr.get("gastw"), decoded.get("stockwerke")))
    wohnungen = _to_optional_int(gwr.get("ganzwhg"))

    if isinstance(name, str):
        name = name.strip() or None

    return {
        "name": name,
        "baujahr": baujahr,
        "bauperiode": _first_present(gwr.get("gbaup")),
        "flaeche_m2": flaeche,
        "geschosse": geschosse,
        "wohnungen": wohnungen,
        "codes": {
            "gstat": gwr.get("gstat"),
            "gkat": gwr.get("gkat"),
            "gklas": gwr.get("gklas"),
        },
        "decoded": decoded,
    }


def compact_energy_summary(decoded: dict[str, Any]) -> dict[str, str]:
    hz = decoded.get("heizung") or []
    ww = decoded.get("warmwasser") or []
    return {
        "heizung": ", ".join(hz) if hz else "keine Angabe",
        "warmwasser": ", ".join(ww) if ww else "keine Angabe",
    }
