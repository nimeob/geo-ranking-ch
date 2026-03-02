"""OSM POI configuration helpers.

Goal: keep OSM/Overpass category selection in one place and make it adjustable
without code changes for experiments.

This module intentionally keeps the default behaviour stable while allowing
safe overrides via environment variables.

Env vars:
- OSM_POI_OVERPASS_TAG_KEYS: comma-separated tag keys queried via Overpass
  (default: shop,amenity,office,leisure,tourism,craft)
- OSM_POI_OVERPASS_ELEMENT_TYPES: comma-separated Overpass element types
  (default: node,way,relation)

Validation is strict (only [a-z0-9_]+ for tag keys; element types must be one of
node/way/relation). Invalid values are ignored; if everything is invalid we
fall back to defaults.
"""

from __future__ import annotations

import functools
import os
import re
from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple


_OSM_POI_OVERPASS_TAG_KEYS_ENV = "OSM_POI_OVERPASS_TAG_KEYS"
_OSM_POI_OVERPASS_ELEMENT_TYPES_ENV = "OSM_POI_OVERPASS_ELEMENT_TYPES"

DEFAULT_OSM_POI_OVERPASS_TAG_KEYS: Tuple[str, ...] = (
    "shop",
    "amenity",
    "office",
    "leisure",
    "tourism",
    "craft",
)

DEFAULT_OSM_POI_OVERPASS_ELEMENT_TYPES: Tuple[str, ...] = (
    "node",
    "way",
    "relation",
)

_TAG_KEY_RE = re.compile(r"^[a-z0-9_]+$")
_ALLOWED_ELEMENT_TYPES = {"node", "way", "relation"}


@dataclass(frozen=True)
class OsmPoiOverpassQueryConfig:
    tag_keys: Tuple[str, ...]
    element_types: Tuple[str, ...]


def _parse_csv(raw: str) -> list[str]:
    return [part.strip().lower() for part in (raw or "").split(",") if part.strip()]


def _validate_tag_keys(keys: Iterable[str]) -> Tuple[str, ...]:
    out: list[str] = []
    seen = set()
    for key in keys:
        k = str(key or "").strip().lower()
        if not k or not _TAG_KEY_RE.match(k):
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return tuple(out)


def _validate_element_types(types: Iterable[str]) -> Tuple[str, ...]:
    out: list[str] = []
    seen = set()
    for typ in types:
        t = str(typ or "").strip().lower()
        if t not in _ALLOWED_ELEMENT_TYPES:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return tuple(out)


@functools.lru_cache(maxsize=1)
def load_osm_poi_overpass_query_config() -> OsmPoiOverpassQueryConfig:
    tag_keys = _validate_tag_keys(_parse_csv(os.getenv(_OSM_POI_OVERPASS_TAG_KEYS_ENV, "")))
    if not tag_keys:
        tag_keys = DEFAULT_OSM_POI_OVERPASS_TAG_KEYS

    element_types = _validate_element_types(_parse_csv(os.getenv(_OSM_POI_OVERPASS_ELEMENT_TYPES_ENV, "")))
    if not element_types:
        element_types = DEFAULT_OSM_POI_OVERPASS_ELEMENT_TYPES

    return OsmPoiOverpassQueryConfig(tag_keys=tag_keys, element_types=element_types)


def build_osm_poi_overpass_query(
    *,
    radius_m: int,
    lat_s: str,
    lon_s: str,
    tag_keys: Sequence[str],
    element_types: Sequence[str],
) -> str:
    """Builds the Overpass QL query used for `osm_poi_overpass`.

    This is a pure helper (no IO), designed for unit tests.
    """

    radius = int(radius_m)
    parts: list[str] = ["[out:json][timeout:25];("]
    for el_type in element_types:
        for key in tag_keys:
            parts.append(f"{el_type}(around:{radius},{lat_s},{lon_s})[name][{key}];")
    parts.append(");out body center;")
    return "".join(parts)
