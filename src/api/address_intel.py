#!/usr/bin/env python3
"""
Adress-Intelligence für die Schweiz (swisstopo + GWR + freie Quellen)

Robuster Adressreport mit:
- Retry/Backoff und strukturierter Fehlerbehandlung
- Kandidaten-Matching mit Auswahlheuristik
- Verbesserter Confidence-Logik inkl. Konsistenzprüfung
- Optionalem Compact-Summary-Modus
- Batch-Modus mit JSONL/CSV + Error-Report

Quellen:
- swisstopo GeoAdmin SearchServer
- swisstopo amtliches Gebäudeadressverzeichnis
- BFS GWR (Gebäude-/Energieattribute)
- BFS Heiz-Layer (Klartext)
- swisstopo PLZ-Ortschafts-Layer (Identify am Punkt)
- optional OSM Nominatim Reverse-Geocoding
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    import cairo

    CAIRO_AVAILABLE = True
except Exception:
    cairo = None  # type: ignore[assignment]
    CAIRO_AVAILABLE = False

try:
    from src.api.suitability_light import evaluate_suitability_light
except ModuleNotFoundError:
    from suitability_light import evaluate_suitability_light  # type: ignore[no-redef]

try:
    from src.compliance.export_logging import record_export_log_entry
except ModuleNotFoundError:  # pragma: no cover - fallback for direct script execution
    def record_export_log_entry(**_: Any) -> dict[str, Any]:
        return {}

UA = "openclaw-swisstopo-address-intel/2.2"
DEFAULT_TIMEOUT = 15
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.6
DEFAULT_CACHE_TTL = 120.0
DEFAULT_MIN_REQUEST_INTERVAL = float(os.getenv("ADDRESS_INTEL_MIN_REQUEST_INTERVAL", "0.25"))
MAX_RETRY_AFTER_SECONDS = float(os.getenv("ADDRESS_INTEL_MAX_RETRY_AFTER", "30"))
HTTP_DISK_CACHE_SUBDIR = ".cache/http_json"
HTTP_DISK_CACHE_MAX_AGE = 7 * 24 * 3600.0

RETRYABLE_HTTP_CODES = {408, 409, 425, 429, 500, 502, 503, 504}

SKILL_DIR = Path(__file__).resolve().parent
SRC_ROOT_DIR = SKILL_DIR.parent
GWR_CODES_PATH = SRC_ROOT_DIR / "gwr_codes.py"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_MATCH = 3
EXIT_EXTERNAL = 4
EXIT_RUNTIME = 5
EXIT_BATCH_PARTIAL = 6

SOURCE_POLICY_ORDER = ["official", "licensed", "community", "web", "local_mapping", "unknown"]
SOURCE_POLICY_RANK = {name: idx for idx, name in enumerate(SOURCE_POLICY_ORDER)}
INTELLIGENCE_MODES = ("basic", "extended", "risk")
AREA_MODES = ("address-report", "city-ranking")

AREA_WEIGHT_KEYS = ("ruhe", "oev", "einkauf", "gruen", "sicherheit", "nachtaktivitaet")
DEFAULT_AREA_WEIGHTS: Dict[str, float] = {
    "ruhe": 1.1,
    "oev": 1.0,
    "einkauf": 0.9,
    "gruen": 1.0,
    "sicherheit": 1.4,
    "nachtaktivitaet": 0.6,
}

AREA_WEIGHT_ALIASES = {
    "ruhe": "ruhe",
    "quiet": "ruhe",
    "oev": "oev",
    "ov": "oev",
    "public_transport": "oev",
    "einkauf": "einkauf",
    "shopping": "einkauf",
    "gruen": "gruen",
    "grun": "gruen",
    "green": "gruen",
    "sicherheit": "sicherheit",
    "safety": "sicherheit",
    "nachtaktivitaet": "nachtaktivitaet",
    "nachtaktivitat": "nachtaktivitaet",
    "nightlife": "nachtaktivitaet",
    "night": "nachtaktivitaet",
}

MAP_STYLE_ALIASES = {
    "osm": "osm-standard",
    "osm-standard": "osm-standard",
    "standard": "osm-standard",
    "hot": "osm-hot",
    "humanitarian": "osm-hot",
    "osm-hot": "osm-hot",
    "topo": "opentopomap",
    "topographic": "opentopomap",
    "opentopo": "opentopomap",
    "opentopomap": "opentopomap",
}
MAP_STYLE_CONFIG: Dict[str, Dict[str, Any]] = {
    "osm-standard": {
        "label": "OpenStreetMap Standard",
        "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors (ODbL)",
        "provider": "tile.openstreetmap.org",
        "license_note": "ODbL / OSMF tile usage policy",
        "fallback_style": "osm-standard",
        "max_zoom": 19,
    },
    "osm-hot": {
        "label": "OpenStreetMap Humanitarian",
        "tile_url": "https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors (ODbL), style by Humanitarian OpenStreetMap Team",
        "provider": "a.tile.openstreetmap.fr/hot",
        "license_note": "ODbL + HOT style attribution",
        "fallback_style": "osm-standard",
        "max_zoom": 19,
    },
    "opentopomap": {
        "label": "OpenTopoMap",
        "tile_url": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors, SRTM, style: © OpenTopoMap (CC-BY-SA)",
        "provider": "tile.opentopomap.org",
        "license_note": "CC-BY-SA map style + OSM attribution",
        "fallback_style": "osm-standard",
        "max_zoom": 17,
    },
}
DEFAULT_MAP_STYLE = "osm-standard"
DEFAULT_MAP_WIDTH = 1180
DEFAULT_MAP_HEIGHT = 860
DEFAULT_MAP_PADDING = 90
DEFAULT_TILE_MIN_DELAY = 0.2
DEFAULT_MAP_LEGEND_MODE = "auto"
TILE_ERROR_CACHE_MAX_AGE = 45 * 60.0

CSV_EXPORT_FIELDS = [
    "row",
    "query",
    "status",
    "error_code",
    "error_type",
    "error",
    "matched_address",
    "confidence_score",
    "confidence_level",
    "needs_review",
    "ambiguity_level",
    "ambiguity_gap",
    "intelligence_mode",
    "risk_traffic_light",
    "risk_score",
    "egid",
    "egrid",
    "gemeinde",
    "kanton",
    "baujahr",
    "elevation_m",
    "heizung",
    "warmwasser",
    "warnings",
    "risk_reasons",
    "map_link",
    "sources_ok",
]

SOURCE_CATALOG: Dict[str, Dict[str, Any]] = {
    "geoadmin_search": {"tier": "core", "authority": "official", "purpose": "candidate_search"},
    "geoadmin_search_fallback": {"tier": "fallback", "authority": "official", "purpose": "candidate_search"},
    "geoadmin_address": {"tier": "core", "authority": "official", "purpose": "address_registry"},
    "geoadmin_gwr": {"tier": "core", "authority": "official", "purpose": "building_registry"},
    "bfs_heating_layer": {"tier": "enrichment", "authority": "official", "purpose": "heating_clarification"},
    "plz_layer_identify": {"tier": "crosscheck", "authority": "official", "purpose": "postal_consistency"},
    "swissboundaries_identify": {"tier": "crosscheck", "authority": "official", "purpose": "admin_consistency"},
    "swisstopo_height": {"tier": "enrichment", "authority": "official", "purpose": "elevation_context"},
    "osm_reverse": {"tier": "crosscheck", "authority": "community", "purpose": "external_consistency"},
    "osm_poi_overpass": {"tier": "intelligence", "authority": "community", "purpose": "poi_tenant_noise_signals"},
    "osm_area_profile_overpass": {"tier": "intelligence", "authority": "community", "purpose": "city_zone_profile_signals"},
    "osm_tile_server": {"tier": "visualization", "authority": "community", "purpose": "city_map_png_tiles"},
    "google_news_rss": {"tier": "intelligence", "authority": "web", "purpose": "incident_hints"},
    "google_news_rss_city": {"tier": "intelligence", "authority": "web", "purpose": "city_incident_hints"},
    "geoadmin_city_search": {"tier": "core", "authority": "official", "purpose": "city_anchor"},
    "geoadmin_target_search": {"tier": "core", "authority": "official", "purpose": "city_target_address_anchor"},
    "gwr_codes": {"tier": "local", "authority": "local_mapping", "purpose": "code_decoding"},
}

_REQUIRED_SOURCES = ["geoadmin_search", "geoadmin_gwr", "geoadmin_address"]


def _upstream_target_fields(url: str) -> Dict[str, str]:
    parsed = urllib.parse.urlsplit(str(url or ""))
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    return {
        "target_host": host,
        "target_path": path,
    }


def _infer_provider_record_count(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in ("results", "features", "elements", "events", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return 1
    if isinstance(payload, list):
        return len(payload)
    return 0


_LAST_OSM_REQUEST_TS = 0.0
_LAST_OSM_TILE_REQUEST_TS = 0.0
_GWR_CODES_MODULE = None


class AddressIntelError(RuntimeError):
    """Basisklasse für domänenspezifische Fehler."""


class NoAddressMatchError(AddressIntelError):
    """Keine brauchbare Adresse gefunden."""


class ExternalRequestError(AddressIntelError):
    """Externer Request fehlgeschlagen (inkl. HTTP/Timeout/Decode)."""

    def __init__(
        self,
        source: str,
        url: str,
        message: str,
        *,
        status_code: Optional[int] = None,
        attempt: Optional[int] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.source = source
        self.url = url
        self.status_code = status_code
        self.attempt = attempt
        self.retryable = retryable

    def short(self) -> str:
        prefix = f"[{self.source}]"
        if self.status_code is not None:
            prefix += f" HTTP {self.status_code}"
        return f"{prefix} {self.args[0]}"


@dataclass
class QueryParts:
    raw: str
    normalized: str
    street: Optional[str]
    house_number: Optional[str]
    postal_code: Optional[str]
    city: Optional[str]
    tokens: List[str]


@dataclass
class CandidateEval:
    feature_id: str
    label: str
    detail: str
    origin: Optional[str]
    rank: Optional[int]
    lat: Optional[float]
    lon: Optional[float]
    pre_score: float
    pre_reasons: List[str] = field(default_factory=list)
    detail_score: float = 0.0
    detail_reasons: List[str] = field(default_factory=list)
    total_score: float = 0.0
    attrs: Dict[str, Any] = field(default_factory=dict)
    address_attrs: Dict[str, Any] = field(default_factory=dict)
    gwr_attrs: Dict[str, Any] = field(default_factory=dict)

    def to_preview(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "label": self.label,
            "origin": self.origin,
            "rank": self.rank,
            "score": round(self.total_score if self.total_score else self.pre_score, 2),
            "pre_score": round(self.pre_score, 2),
            "detail_score": round(self.detail_score, 2),
            "reasons": self.pre_reasons + self.detail_reasons,
        }


@dataclass
class SourceInfo:
    status: str = "not_used"  # ok|partial|error|disabled|not_used
    optional: bool = False
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    records: int = 0
    last_error: Optional[str] = None
    last_url: Optional[str] = None


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: Dict[str, SourceInfo] = {}

    def disable(self, name: str, message: str = "deaktiviert") -> None:
        info = self._sources.setdefault(name, SourceInfo())
        info.status = "disabled"
        info.last_error = message

    def note_success(self, name: str, url: str, *, records: int = 1, optional: bool = False) -> None:
        info = self._sources.setdefault(name, SourceInfo(optional=optional))
        info.optional = optional
        info.attempts += 1
        info.successes += 1
        info.records += max(records, 0)
        info.last_url = url
        info.last_error = None
        info.status = "ok" if info.failures == 0 else "partial"

    def note_error(self, name: str, url: str, error: str, *, optional: bool = False) -> None:
        info = self._sources.setdefault(name, SourceInfo(optional=optional))
        info.optional = optional
        info.attempts += 1
        info.failures += 1
        info.last_url = url
        info.last_error = error
        info.status = "error" if info.successes == 0 else "partial"

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "status": info.status,
                "optional": info.optional,
                "attempts": info.attempts,
                "successes": info.successes,
                "failures": info.failures,
                "records": info.records,
                "last_error": info.last_error,
                "last_url": info.last_url,
            }
            for name, info in self._sources.items()
        }

    def required_success_ratio(self, required_names: Sequence[str]) -> float:
        if not required_names:
            return 1.0
        ok = 0
        total = 0
        for name in required_names:
            total += 1
            info = self._sources.get(name)
            if info and info.successes > 0:
                ok += 1
        return ok / total if total else 1.0


@dataclass
class HttpClient:
    timeout: int = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES
    backoff_seconds: float = DEFAULT_BACKOFF
    min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL
    user_agent: str = UA
    cache_ttl_seconds: float = DEFAULT_CACHE_TTL
    enable_disk_cache: bool = True
    upstream_log_emitter: Optional[Callable[..., None]] = None
    upstream_trace_id: str = ""
    upstream_request_id: str = ""
    upstream_session_id: str = ""
    _cache: Dict[str, Tuple[float, Dict[str, Any]]] = field(default_factory=dict)
    _last_request_started_at: float = 0.0

    def _disk_cache_file(self, url: str) -> Path:
        digest = hashlib.sha1(url.encode("utf-8", errors="ignore")).hexdigest()
        return SKILL_DIR / HTTP_DISK_CACHE_SUBDIR / f"{digest}.json"

    def _emit_upstream_event(
        self,
        *,
        event: str,
        source: str,
        url: str,
        level: str = "info",
        **fields: Any,
    ) -> None:
        emitter = self.upstream_log_emitter
        if emitter is None:
            return

        source_meta = SOURCE_CATALOG.get(source, {})
        payload: Dict[str, Any] = {
            "component": "api.address_intel",
            "source": source,
            "provider_tier": source_meta.get("tier") or "unknown",
            "provider_authority": source_meta.get("authority") or "unknown",
            "provider_purpose": source_meta.get("purpose") or "unknown",
            **_upstream_target_fields(url),
        }
        payload.update(fields)

        try:
            emitter(
                event=event,
                level=level,
                trace_id=self.upstream_trace_id,
                request_id=self.upstream_request_id,
                session_id=self.upstream_session_id,
                **payload,
            )
        except Exception:
            return

    def _read_disk_cache(self, url: str) -> Optional[Dict[str, Any]]:
        if not self.enable_disk_cache or self.cache_ttl_seconds <= 0:
            return None
        cache_file = self._disk_cache_file(url)
        if not cache_file.exists():
            return None
        try:
            age = time.time() - cache_file.stat().st_mtime
            if age < 0:
                age = 0.0
            if age > min(max(self.cache_ttl_seconds, 1.0), HTTP_DISK_CACHE_MAX_AGE):
                return None
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                self._cache[url] = (time.time(), payload)
                return payload
        except Exception:
            return None
        return None

    def _write_disk_cache(self, url: str, payload: Dict[str, Any]) -> None:
        if not self.enable_disk_cache or self.cache_ttl_seconds <= 0:
            return
        cache_file = self._disk_cache_file(url)
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(cache_file)
        except Exception:
            return

    def get_json(self, url: str, *, source: str) -> Dict[str, Any]:
        now = time.time()
        cached = self._cache.get(url)
        if cached and now - cached[0] <= self.cache_ttl_seconds:
            payload = cached[1]
            self._emit_upstream_event(
                event="api.upstream.response.summary",
                level="info",
                source=source,
                url=url,
                direction="upstream->api",
                status="cache_hit",
                cache="memory",
                records=_infer_provider_record_count(payload),
                payload_kind=type(payload).__name__,
                retry_count=0,
            )
            return payload

        disk_cached = self._read_disk_cache(url)
        if disk_cached is not None:
            self._emit_upstream_event(
                event="api.upstream.response.summary",
                level="info",
                source=source,
                url=url,
                direction="upstream->api",
                status="cache_hit",
                cache="disk",
                records=_infer_provider_record_count(disk_cached),
                payload_kind=type(disk_cached).__name__,
                retry_count=0,
            )
            return disk_cached

        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        last_error: Optional[ExternalRequestError] = None
        max_attempts = self.retries + 1

        for attempt in range(1, max_attempts + 1):
            attempt_started_at = time.perf_counter()
            self._emit_upstream_event(
                event="api.upstream.request.start",
                level="info",
                source=source,
                url=url,
                direction="api->upstream",
                status="sent",
                attempt=attempt,
                max_attempts=max_attempts,
                retry_count=max(0, attempt - 1),
                timeout_seconds=float(self.timeout),
            )
            try:
                self._enforce_min_interval()
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    status_code = int(getattr(resp, "status", 200) or 200)
                payload = json.loads(raw.decode("utf-8"))
                self._cache[url] = (time.time(), payload)
                self._write_disk_cache(url, payload)

                duration_ms = round((time.perf_counter() - attempt_started_at) * 1000.0, 3)
                self._emit_upstream_event(
                    event="api.upstream.request.end",
                    level="info",
                    source=source,
                    url=url,
                    direction="upstream->api",
                    status="ok",
                    status_code=status_code,
                    duration_ms=duration_ms,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_count=max(0, attempt - 1),
                )
                self._emit_upstream_event(
                    event="api.upstream.response.summary",
                    level="info",
                    source=source,
                    url=url,
                    direction="upstream->api",
                    status="ok",
                    cache="miss",
                    status_code=status_code,
                    records=_infer_provider_record_count(payload),
                    payload_kind=type(payload).__name__,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_count=max(0, attempt - 1),
                )
                return payload
            except urllib.error.HTTPError as exc:
                duration_ms = round((time.perf_counter() - attempt_started_at) * 1000.0, 3)
                body = ""
                try:
                    body = (exc.read() or b"").decode("utf-8", errors="ignore")
                except Exception:
                    body = ""
                msg = f"HTTP-Fehler ({exc.code})"
                if body:
                    msg += f": {body[:220]}"
                retryable = exc.code in RETRYABLE_HTTP_CODES
                last_error = ExternalRequestError(
                    source,
                    url,
                    msg,
                    status_code=exc.code,
                    attempt=attempt,
                    retryable=retryable,
                )
                will_retry = self._should_retry(attempt, retryable)
                self._emit_upstream_event(
                    event="api.upstream.request.end",
                    level="warn" if will_retry else "error",
                    source=source,
                    url=url,
                    direction="upstream->api",
                    status="retrying" if will_retry else "error",
                    status_code=int(exc.code),
                    duration_ms=duration_ms,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_count=max(0, attempt - 1),
                    retryable=retryable,
                    error_class="http_error",
                    error_message=msg,
                )
                if not will_retry:
                    raise last_error
                retry_after_raw = exc.headers.get("Retry-After") if getattr(exc, "headers", None) else None
                self._sleep_retry_after_or_backoff(attempt, retry_after_raw)
            except (urllib.error.URLError, TimeoutError) as exc:
                duration_ms = round((time.perf_counter() - attempt_started_at) * 1000.0, 3)
                msg = f"Netzwerkfehler: {exc}"
                last_error = ExternalRequestError(
                    source,
                    url,
                    msg,
                    attempt=attempt,
                    retryable=True,
                )
                will_retry = self._should_retry(attempt, True)
                self._emit_upstream_event(
                    event="api.upstream.request.end",
                    level="warn" if will_retry else "error",
                    source=source,
                    url=url,
                    direction="upstream->api",
                    status="retrying" if will_retry else "error",
                    duration_ms=duration_ms,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_count=max(0, attempt - 1),
                    retryable=True,
                    error_class="network_error",
                    error_message=msg,
                )
                if not will_retry:
                    raise last_error
                self._sleep_backoff(attempt)
            except json.JSONDecodeError as exc:
                duration_ms = round((time.perf_counter() - attempt_started_at) * 1000.0, 3)
                msg = f"Ungültige JSON-Antwort: {exc}"
                last_error = ExternalRequestError(
                    source,
                    url,
                    msg,
                    attempt=attempt,
                    retryable=False,
                )
                self._emit_upstream_event(
                    event="api.upstream.request.end",
                    level="error",
                    source=source,
                    url=url,
                    direction="upstream->api",
                    status="error",
                    duration_ms=duration_ms,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_count=max(0, attempt - 1),
                    retryable=False,
                    error_class="decode_error",
                    error_message=msg,
                )
                raise last_error

        if last_error is None:
            raise ExternalRequestError(source, url, "Unbekannter Fehler")
        raise last_error

    def _should_retry(self, attempt: int, retryable: bool) -> bool:
        return retryable and attempt <= self.retries

    def _sleep_backoff(self, attempt: int) -> None:
        delay = self.backoff_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(0, max(self.backoff_seconds / 3, 0.001))
        time.sleep(delay + jitter)

    def _enforce_min_interval(self) -> None:
        interval = max(0.0, float(self.min_request_interval_seconds))
        if interval <= 0:
            self._last_request_started_at = time.time()
            return
        now = time.time()
        wait = (self._last_request_started_at + interval) - now
        if wait > 0:
            time.sleep(wait)
            now = time.time()
        self._last_request_started_at = now

    def _sleep_retry_after_or_backoff(self, attempt: int, retry_after_raw: Optional[str]) -> None:
        retry_after_seconds = self._parse_retry_after_seconds(retry_after_raw)
        if retry_after_seconds is None:
            self._sleep_backoff(attempt)
            return
        retry_after_seconds = min(max(0.0, retry_after_seconds), MAX_RETRY_AFTER_SECONDS)
        # Niemals aggressiver als unser exponentieller Backoff.
        fallback = self.backoff_seconds * (2 ** (attempt - 1))
        wait = max(retry_after_seconds, fallback)
        jitter = random.uniform(0, max(self.backoff_seconds / 3, 0.001))
        time.sleep(wait + jitter)

    def _parse_retry_after_seconds(self, raw: Optional[str]) -> Optional[float]:
        if not raw:
            return None
        s = str(raw).strip()
        if not s:
            return None
        try:
            v = float(s)
            if v >= 0:
                return v
        except ValueError:
            pass
        try:
            dt = parsedate_to_datetime(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = (dt - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, delta)
        except Exception:
            return None


def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = strip_html(text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-z0-9]+", normalize_text(text))


def normalize_address_query_input(query: str) -> str:
    """Normalisiert Roh-Adressstrings robust für provider-neutrale Weiterverarbeitung."""
    text = str(query or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[;|\n\r]+", ",", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,")
    return text


def _normalize_street_fragment(fragment: str) -> str:
    street = normalize_text(fragment)
    if not street:
        return ""
    # Provider-neutrale Vereinheitlichung typischer Abkürzungen.
    street = re.sub(r"\bstr\.?\b", "strasse", street)
    street = re.sub(r"\s+", " ", street).strip(" ,.-")
    return street


def _clean_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    return raw or None


def _as_int_coordinate(value: Any) -> Optional[int]:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return int(round(num))


def _as_wgs84_coordinate(value: Any) -> Optional[float]:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return num


def derive_resolution_identifiers(
    *,
    feature_id: Any,
    gwr_attrs: Dict[str, Any],
    lat: Any,
    lon: Any,
) -> Dict[str, Optional[str]]:
    """Leitet stabile, provider-neutrale Entity-/Location-IDs additiv ab."""
    egid = _clean_id(gwr_attrs.get("egid"))
    egrid = _clean_id(gwr_attrs.get("egrid"))
    feature = _clean_id(feature_id)

    if egid:
        entity_id = f"ch:egid:{egid}"
    elif egrid:
        entity_id = f"ch:egrid:{egrid.upper()}"
    elif feature:
        entity_id = f"ch:feature:{feature}"
    else:
        entity_id = None

    lv95_e = _as_int_coordinate(gwr_attrs.get("gkode"))
    lv95_n = _as_int_coordinate(gwr_attrs.get("gkodn"))
    if lv95_e is not None and lv95_n is not None:
        location_id = f"ch:lv95:{lv95_e}:{lv95_n}"
    else:
        lat_num = _as_wgs84_coordinate(lat)
        lon_num = _as_wgs84_coordinate(lon)
        if lat_num is not None and lon_num is not None:
            location_id = f"ch:wgs84:{lat_num:.6f}:{lon_num:.6f}"
        else:
            location_id = None

    seed = "|".join(
        [
            entity_id or "",
            location_id or "",
            feature or "",
        ]
    )
    resolution_hash = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16] if seed else None
    resolution_id = f"ch:resolution:v1:{resolution_hash}" if resolution_hash else None

    return {
        "entity_id": entity_id,
        "location_id": location_id,
        "resolution_id": resolution_id,
    }


def canonical_area_weight_key(raw: str) -> Optional[str]:
    key = normalize_text(raw or "")
    key = key.replace("ö", "oe").replace("ä", "ae").replace("ü", "ue")
    key = key.replace("-", "_").replace(" ", "_")
    return AREA_WEIGHT_ALIASES.get(key)


def parse_area_weights(overrides: Optional[str]) -> Dict[str, float]:
    weights = dict(DEFAULT_AREA_WEIGHTS)
    if not overrides:
        return weights

    parts = [p.strip() for p in str(overrides).split(",") if p.strip()]
    for part in parts:
        if "=" in part:
            raw_key, raw_val = part.split("=", 1)
        elif ":" in part:
            raw_key, raw_val = part.split(":", 1)
        else:
            raise ValueError(f"Ungültiges Gewichtsformat '{part}'. Erwartet key=value.")

        key = canonical_area_weight_key(raw_key)
        if not key:
            raise ValueError(
                f"Unbekannter Gewichtsschlüssel '{raw_key}'. Erlaubt: {', '.join(AREA_WEIGHT_KEYS)}"
            )
        try:
            value = float(raw_val)
        except ValueError as ex:
            raise ValueError(f"Ungültiger Gewichtswert '{raw_val}' für '{raw_key}'.") from ex
        if value < 0:
            raise ValueError(f"Gewicht '{raw_key}' darf nicht negativ sein.")
        weights[key] = round(value, 4)

    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Mindestens ein Gewicht muss > 0 sein.")
    return weights


def normalize_weight_profile(weights: Dict[str, float]) -> Dict[str, float]:
    profile = {k: float(weights.get(k, 0.0)) for k in AREA_WEIGHT_KEYS}
    total = sum(v for v in profile.values() if v > 0)
    if total <= 0:
        return {k: 0.0 for k in AREA_WEIGHT_KEYS}
    return {k: round(max(0.0, v) / total, 6) for k, v in profile.items()}


def points_to_score(points: float, scale: float) -> float:
    if points <= 0:
        return 0.0
    eff_scale = max(scale, 0.1)
    return clamp((1.0 - math.exp(-points / eff_scale)) * 100.0, 0.0, 100.0)


def zone_compass_label(row_offset: int, col_offset: int) -> str:
    if row_offset == 0 and col_offset == 0:
        return "Zentrum"
    ns = ""
    ew = ""
    if row_offset < 0:
        ns = f"N{abs(row_offset)}"
    elif row_offset > 0:
        ns = f"S{row_offset}"
    if col_offset < 0:
        ew = f"W{abs(col_offset)}"
    elif col_offset > 0:
        ew = f"E{col_offset}"
    return "-".join([x for x in (ns, ew) if x])


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def strip_html(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"<[^>]+>", "", s)


def _hex_to_rgb_tuple(color_hex: str) -> Tuple[float, float, float]:
    raw = str(color_hex or "").strip().lstrip("#")
    if len(raw) != 6:
        raw = "888888"
    try:
        r = int(raw[0:2], 16) / 255.0
        g = int(raw[2:4], 16) / 255.0
        b = int(raw[4:6], 16) / 255.0
    except ValueError:
        r, g, b = (0.53, 0.53, 0.53)
    return (r, g, b)


def _rgb_tuple_to_hex(rgb: Tuple[float, float, float]) -> str:
    r, g, b = rgb
    return "#%02X%02X%02X" % (
        int(clamp(r, 0.0, 1.0) * 255.0),
        int(clamp(g, 0.0, 1.0) * 255.0),
        int(clamp(b, 0.0, 1.0) * 255.0),
    )


def _lerp_color_hex(color_a: str, color_b: str, t: float) -> str:
    ar, ag, ab = _hex_to_rgb_tuple(color_a)
    br, bg, bb = _hex_to_rgb_tuple(color_b)
    q = clamp(float(t), 0.0, 1.0)
    return _rgb_tuple_to_hex((ar + (br - ar) * q, ag + (bg - ag) * q, ab + (bb - ab) * q))


def zone_traffic_light(score: float) -> str:
    val = clamp(float(score), 0.0, 100.0)
    if val >= 72:
        return "green"
    if val >= 52:
        return "yellow"
    return "red"


def zone_score_band(score: float) -> str:
    val = clamp(float(score), 0.0, 100.0)
    if val < 38:
        return "critical"
    if val < 52:
        return "elevated"
    if val < 62:
        return "watch"
    if val < 72:
        return "balanced"
    if val < 84:
        return "strong"
    return "excellent"


def zone_score_color(score: float) -> str:
    val = clamp(float(score), 0.0, 100.0)
    if val < 38:
        return _lerp_color_hex("#B71C1C", "#D84315", val / 38.0)
    if val < 52:
        return _lerp_color_hex("#D84315", "#F39C12", (val - 38.0) / 14.0)
    if val < 62:
        return _lerp_color_hex("#F39C12", "#FBC02D", (val - 52.0) / 10.0)
    if val < 72:
        return _lerp_color_hex("#FBC02D", "#C0CA33", (val - 62.0) / 10.0)
    if val < 84:
        return _lerp_color_hex("#8BC34A", "#43A047", (val - 72.0) / 12.0)
    return _lerp_color_hex("#43A047", "#1B5E20", (val - 84.0) / 16.0)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def source_authority(source_name: str) -> str:
    meta = SOURCE_CATALOG.get(source_name) or {}
    return str(meta.get("authority") or "unknown")


def source_policy_rank(source_name: str) -> int:
    authority = source_authority(source_name)
    return SOURCE_POLICY_RANK.get(authority, SOURCE_POLICY_RANK["unknown"])


def classify_statement_status(confidence: float, evidence: Optional[Sequence[Dict[str, Any]]] = None) -> str:
    evidence = list(evidence or [])
    best_rank = SOURCE_POLICY_RANK["unknown"]
    for ev in evidence:
        rank = SOURCE_POLICY_RANK.get(str(ev.get("source_authority") or "unknown"), SOURCE_POLICY_RANK["unknown"])
        if rank < best_rank:
            best_rank = rank

    if confidence >= 0.8 and best_rank <= SOURCE_POLICY_RANK["licensed"]:
        return "gesichert"
    if confidence >= 0.5:
        return "indiz"
    return "unklar"


def evidence_item(
    *,
    source: str,
    confidence: float,
    url: Optional[str] = None,
    observed_at: Optional[str] = None,
    snippet: Optional[str] = None,
    field_path: Optional[str] = None,
) -> Dict[str, Any]:
    meta = SOURCE_CATALOG.get(source) or {}
    return {
        "source": source,
        "source_authority": meta.get("authority", "unknown"),
        "source_tier": meta.get("tier", "unknown"),
        "source_policy_rank": source_policy_rank(source),
        "url": url,
        "observed_at": observed_at or utc_now_iso(),
        "confidence": round(clamp(confidence, 0.0, 1.0), 2),
        "snippet": snippet,
        "field_path": field_path,
    }


def statement(
    text: str,
    *,
    confidence: float,
    evidence: Sequence[Dict[str, Any]],
    field_path: Optional[str] = None,
) -> Dict[str, Any]:
    evidence_list = list(evidence)
    status = classify_statement_status(confidence, evidence_list)
    primary = evidence_list[0] if evidence_list else None
    return {
        "text": text,
        "status": status,
        "confidence": round(clamp(confidence, 0.0, 1.0), 2),
        "field_provenance": {
            "field": field_path,
            "primary_source": (primary or {}).get("source"),
            "primary_url": (primary or {}).get("url"),
            "observed_at": (primary or {}).get("observed_at"),
        },
        "evidence": evidence_list,
    }


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def parse_rss_datetime(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except Exception:
        return None


def load_gwr_codes(module_path: Path):
    global _GWR_CODES_MODULE
    if _GWR_CODES_MODULE is not None:
        return _GWR_CODES_MODULE

    spec = importlib.util.spec_from_file_location("gwr_codes", str(module_path))
    if spec is None or spec.loader is None:
        raise AddressIntelError(f"gwr_codes.py konnte nicht geladen werden: {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _GWR_CODES_MODULE = mod
    return mod


def parse_query_parts(query: str) -> QueryParts:
    normalized_input = normalize_address_query_input(query)
    norm = normalize_text(normalized_input)
    tokens = tokenize(norm)

    postal_match = re.search(r"\b(\d{4})\b", norm)
    postal_code = postal_match.group(1) if postal_match else None

    street = None
    house_number = None
    city = None

    parts = [p.strip() for p in re.split(r",", normalized_input) if p.strip()]
    first = parts[0] if parts else normalized_input
    first_norm = normalize_text(first)

    m = re.match(
        r"^(?P<street>.+?)\s+(?P<number>\d+[a-zA-Z]?(?:[/-]\d+[a-zA-Z]?)?)\s*$",
        first_norm,
    )
    if m:
        street = _normalize_street_fragment(m.group("street")) or None
        house_number = m.group("number").lower()
    else:
        street = _normalize_street_fragment(first_norm) or None

    if postal_code:
        m_city = re.search(rf"\b{postal_code}\b\s*([a-z0-9\-\.\s'/]+)$", norm)
        if m_city:
            city = m_city.group(1).strip(" ,")
    if not city and len(parts) >= 2:
        second_norm = normalize_text(parts[-1])
        if second_norm and not re.fullmatch(r"\d{4}", second_norm):
            city = re.sub(r"^\d{4}\s*", "", second_norm).strip() or None

    return QueryParts(
        raw=query,
        normalized=norm,
        street=street,
        house_number=house_number,
        postal_code=postal_code,
        city=city,
        tokens=tokens,
    )


def build_search_url(query: str, *, limit: int, origins: Optional[str] = "address") -> str:
    params: Dict[str, Any] = {
        "searchText": query,
        "type": "locations",
        "limit": max(1, min(limit, 50)),
        "lang": "de",
    }
    if origins:
        params["origins"] = origins
    return "https://api3.geo.admin.ch/rest/services/api/SearchServer?" + urllib.parse.urlencode(params)


def tracked_get_json(
    client: HttpClient,
    sources: SourceRegistry,
    source_name: str,
    url: str,
    *,
    optional: bool,
) -> Optional[Dict[str, Any]]:
    try:
        data = client.get_json(url, source=source_name)
        record_count = len(data.get("results", [])) if isinstance(data, dict) else 1
        sources.note_success(source_name, url, records=record_count, optional=optional)
        return data
    except ExternalRequestError as exc:
        sources.note_error(source_name, url, exc.short(), optional=optional)
        if optional:
            return None
        raise


def search_candidates(
    client: HttpClient,
    sources: SourceRegistry,
    address: str,
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    primary_url = build_search_url(address, limit=limit, origins="address")
    primary = tracked_get_json(client, sources, "geoadmin_search", primary_url, optional=False) or {}
    results = primary.get("results") or []

    if results:
        return [r.get("attrs") or {} for r in results if isinstance(r, dict)]

    fallback_url = build_search_url(address, limit=max(limit, 8), origins=None)
    fallback = tracked_get_json(client, sources, "geoadmin_search_fallback", fallback_url, optional=True) or {}
    fb_results = fallback.get("results") or []
    return [r.get("attrs") or {} for r in fb_results if isinstance(r, dict)]


def score_candidate_pre(attrs: Dict[str, Any], query: QueryParts) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []

    label = strip_html(attrs.get("label") or "") or ""
    detail = attrs.get("detail") or ""
    haystack = f"{normalize_text(label)} {normalize_text(detail)}"

    # Street
    if query.street:
        street_norm = normalize_text(query.street)
        street_tokens = tokenize(street_norm)
        if street_norm and street_norm in haystack:
            score += 35
            reasons.append("Strasse exakt im Treffertext")
        elif street_tokens and all(t in haystack for t in street_tokens):
            score += 18
            reasons.append("Strassen-Tokens vollständig enthalten")
        else:
            score -= 20
            reasons.append("Strasse nicht ausreichend enthalten")

    # House number
    if query.house_number:
        if re.search(rf"\b{re.escape(query.house_number)}\b", haystack):
            score += 14
            reasons.append("Hausnummer passt")
        else:
            score -= 8
            reasons.append("Hausnummer fehlt")

    # Postal code
    if query.postal_code:
        if re.search(rf"\b{re.escape(query.postal_code)}\b", haystack):
            score += 20
            reasons.append("PLZ passt")
        else:
            score -= 8
            reasons.append("PLZ fehlt")

    # City
    if query.city:
        city_norm = normalize_text(query.city)
        city_tokens = tokenize(city_norm)
        if city_norm and city_norm in haystack:
            score += 15
            reasons.append("Ort passt")
        elif city_tokens and all(t in haystack for t in city_tokens):
            score += 10
            reasons.append("Orts-Tokens passen")
        else:
            score -= 6
            reasons.append("Ort nicht erkannt")

    if attrs.get("origin") == "address":
        score += 5
        reasons.append("Origin=address")

    rank = attrs.get("rank")
    if isinstance(rank, (int, float)):
        rank_bonus = clamp(10 - float(rank), 0, 8)
        score += rank_bonus
        reasons.append(f"Search-Rank-Bonus {rank_bonus:.1f}")

    feature_id = str(attrs.get("featureId") or "")
    if feature_id:
        score += 5
        reasons.append("Feature-ID vorhanden")

    if query.street and label:
        if normalize_text(label).startswith(normalize_text(query.street)):
            score += 6
            reasons.append("Label startet mit Strasse")

    return score, reasons


def score_candidate_detail(
    query: QueryParts,
    address_attrs: Dict[str, Any],
    gwr_attrs: Dict[str, Any],
) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []

    gwr_street = normalize_text(gwr_attrs.get("strname_deinr") or "")

    if query.street and gwr_street:
        street_norm = normalize_text(query.street)
        if street_norm and street_norm in gwr_street:
            score += 20
            reasons.append("GWR-Strasse bestätigt")
        elif all(t in gwr_street for t in tokenize(street_norm)):
            score += 10
            reasons.append("GWR-Strassen-Tokens bestätigt")
        else:
            score -= 8
            reasons.append("GWR-Strasse weicht ab")

    if query.house_number and gwr_street:
        if re.search(rf"\b{re.escape(query.house_number)}\b", gwr_street):
            score += 8
            reasons.append("GWR-Hausnummer bestätigt")
        else:
            score -= 4
            reasons.append("GWR-Hausnummer abweichend")

    gwr_plz = str(gwr_attrs.get("plz_plz6") or "")[:4]
    if query.postal_code and gwr_plz:
        if gwr_plz == query.postal_code:
            score += 12
            reasons.append("GWR-PLZ bestätigt")
        else:
            score -= 7
            reasons.append("GWR-PLZ abweichend")

    if query.city:
        city_norm = normalize_text(query.city)
        gwr_city = normalize_text(gwr_attrs.get("dplzname") or gwr_attrs.get("ggdename") or "")
        if city_norm and gwr_city:
            if city_norm in gwr_city or gwr_city in city_norm:
                score += 8
                reasons.append("GWR-Ort/Gemeinde bestätigt")
            elif all(t in gwr_city for t in tokenize(city_norm)):
                score += 5
                reasons.append("GWR-Orts-Tokens bestätigt")
            else:
                score -= 4
                reasons.append("GWR-Ort/Gemeinde abweichend")

    if address_attrs.get("adr_official") is True:
        score += 5
        reasons.append("Amtliche Adresse")

    if gwr_attrs.get("gstat") == 1004:
        score += 3
        reasons.append("Gebäudestatus=Bestehend")

    return score, reasons


def mapserver_feature_url(layer: str, feature_id: str) -> str:
    return f"https://api3.geo.admin.ch/rest/services/ech/MapServer/{layer}/{feature_id}"


def fetch_feature_attributes(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    layer: str,
    feature_id: str,
    source_name: str,
    optional: bool = False,
) -> Dict[str, Any]:
    url = mapserver_feature_url(layer, feature_id)
    data = tracked_get_json(client, sources, source_name, url, optional=optional)
    if data is None:
        return {}
    attrs = ((data.get("feature") or {}).get("attributes")) if isinstance(data, dict) else None
    if not isinstance(attrs, dict):
        msg = f"Ungültige Feature-Antwort in {source_name}"
        sources.note_error(source_name, url, msg, optional=optional)
        if optional:
            return {}
        raise AddressIntelError(msg)
    return attrs


def fetch_heating_layer(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    egid: str,
) -> Dict[str, Any]:
    url = (
        "https://api3.geo.admin.ch/rest/services/api/MapServer/"
        f"ch.bfs.gebaeude_wohnungs_register_waermequelle_heizung/{egid}"
    )
    data = tracked_get_json(client, sources, "bfs_heating_layer", url, optional=True)
    if not data:
        return {}
    attrs = ((data.get("feature") or {}).get("attributes")) if isinstance(data, dict) else None
    if not isinstance(attrs, dict):
        return {}
    return attrs


def fetch_plz_layer_at_lv95(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    lv95_e: Optional[float],
    lv95_n: Optional[float],
) -> Dict[str, Any]:
    if lv95_e is None or lv95_n is None:
        sources.disable("plz_layer_identify", "keine LV95-Koordinaten verfügbar")
        return {}

    margin = 200
    params = {
        "geometry": f"{lv95_e},{lv95_n}",
        "geometryType": "esriGeometryPoint",
        "imageDisplay": "500,500,96",
        "mapExtent": f"{lv95_e-margin},{lv95_n-margin},{lv95_e+margin},{lv95_n+margin}",
        "tolerance": "5",
        "layers": "all:ch.swisstopo-vd.ortschaftenverzeichnis_plz",
        "sr": "2056",
        "lang": "de",
        "returnGeometry": "false",
        "f": "json",
    }
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify?" + urllib.parse.urlencode(params)
    data = tracked_get_json(client, sources, "plz_layer_identify", url, optional=True)
    if not data:
        return {}
    results = data.get("results") or []
    if not results:
        return {}
    attrs = (results[0] or {}).get("attributes") or {}
    return attrs if isinstance(attrs, dict) else {}


def fetch_swissboundaries_at_lv95(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    lv95_e: Optional[float],
    lv95_n: Optional[float],
) -> Dict[str, Any]:
    if lv95_e is None or lv95_n is None:
        sources.disable("swissboundaries_identify", "keine LV95-Koordinaten verfügbar")
        return {}

    margin = 200
    params = {
        "geometry": f"{lv95_e},{lv95_n}",
        "geometryType": "esriGeometryPoint",
        "imageDisplay": "500,500,96",
        "mapExtent": f"{lv95_e-margin},{lv95_n-margin},{lv95_e+margin},{lv95_n+margin}",
        "tolerance": "5",
        "layers": "all:ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill",
        "sr": "2056",
        "lang": "de",
        "returnGeometry": "false",
        "f": "json",
    }
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify?" + urllib.parse.urlencode(params)
    data = tracked_get_json(client, sources, "swissboundaries_identify", url, optional=True)
    if not data:
        return {}

    results = data.get("results") or []
    best: Optional[Dict[str, Any]] = None
    for result in results:
        attrs = (result or {}).get("attributes") or {}
        if not isinstance(attrs, dict):
            continue
        if attrs.get("is_current_jahr"):
            best = attrs
            break
        if best is None:
            best = attrs
    return best or {}


def fetch_swisstopo_height(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    lv95_e: Optional[float],
    lv95_n: Optional[float],
) -> Dict[str, Any]:
    if lv95_e is None or lv95_n is None:
        sources.disable("swisstopo_height", "keine LV95-Koordinaten verfügbar")
        return {}

    params = urllib.parse.urlencode({"easting": lv95_e, "northing": lv95_n})
    url = f"https://api3.geo.admin.ch/rest/services/height?{params}"
    data = tracked_get_json(client, sources, "swisstopo_height", url, optional=True)
    if not data:
        return {}

    height_raw = data.get("height") if isinstance(data, dict) else None
    try:
        height = float(height_raw) if height_raw is not None else None
    except (TypeError, ValueError):
        height = None
    return {"height_m": height}


def fetch_osm_reverse(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    lat: Optional[float],
    lon: Optional[float],
    min_delay_s: float,
) -> Dict[str, Any]:
    if lat is None or lon is None:
        sources.disable("osm_reverse", "keine WGS84-Koordinaten verfügbar")
        return {}

    global _LAST_OSM_REQUEST_TS
    now = time.time()
    wait = (min_delay_s or 0.0) - (now - _LAST_OSM_REQUEST_TS)
    if wait > 0:
        time.sleep(wait)

    params = urllib.parse.urlencode(
        {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": 18,
        }
    )
    url = f"https://nominatim.openstreetmap.org/reverse?{params}"
    data = tracked_get_json(client, sources, "osm_reverse", url, optional=True)
    _LAST_OSM_REQUEST_TS = time.time()
    return data or {}


def intelligence_mode_settings(mode: str) -> Dict[str, Any]:
    if mode == "risk":
        return {
            "enable_external": True,
            "poi_radius_m": 280,
            "poi_limit": 140,
            "tenant_limit": 14,
            "incident_limit": 12,
            "news_focus": "address_and_incident",
        }
    if mode == "extended":
        return {
            "enable_external": True,
            "poi_radius_m": 190,
            "poi_limit": 90,
            "tenant_limit": 10,
            "incident_limit": 8,
            "news_focus": "address_and_incident",
        }
    return {
        "enable_external": False,
        "poi_radius_m": 120,
        "poi_limit": 40,
        "tenant_limit": 5,
        "incident_limit": 3,
        "news_focus": "address_only",
    }


def fetch_osm_poi_overpass(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    lat: Optional[float],
    lon: Optional[float],
    radius_m: int,
    max_items: int,
) -> Dict[str, Any]:
    if lat is None or lon is None:
        sources.disable("osm_poi_overpass", "keine WGS84-Koordinaten verfügbar")
        return {"source_url": None, "pois": []}

    lat_s = f"{float(lat):.6f}"
    lon_s = f"{float(lon):.6f}"
    query = (
        "[out:json][timeout:25];"
        "("
        f"node(around:{radius_m},{lat_s},{lon_s})[name][shop];"
        f"node(around:{radius_m},{lat_s},{lon_s})[name][amenity];"
        f"node(around:{radius_m},{lat_s},{lon_s})[name][office];"
        f"node(around:{radius_m},{lat_s},{lon_s})[name][leisure];"
        f"node(around:{radius_m},{lat_s},{lon_s})[name][tourism];"
        f"way(around:{radius_m},{lat_s},{lon_s})[name][shop];"
        f"way(around:{radius_m},{lat_s},{lon_s})[name][amenity];"
        f"way(around:{radius_m},{lat_s},{lon_s})[name][office];"
        f"relation(around:{radius_m},{lat_s},{lon_s})[name][shop];"
        f"relation(around:{radius_m},{lat_s},{lon_s})[name][amenity];"
        ");"
        "out body center;"
    )

    source_url = "https://overpass-api.de/api/interpreter?" + urllib.parse.urlencode({"data": query})
    payload = tracked_get_json(client, sources, "osm_poi_overpass", source_url, optional=True) or {}
    elements = payload.get("elements") or []

    pois: List[Dict[str, Any]] = []
    for element in elements:
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue

        point_lat = element.get("lat")
        point_lon = element.get("lon")
        center = element.get("center") or {}
        if point_lat is None:
            point_lat = center.get("lat")
        if point_lon is None:
            point_lon = center.get("lon")
        if point_lat is None or point_lon is None:
            continue

        try:
            p_lat = float(point_lat)
            p_lon = float(point_lon)
        except (TypeError, ValueError):
            continue

        category = None
        subcategory = None
        for key in ("shop", "amenity", "office", "leisure", "tourism", "craft"):
            if tags.get(key):
                category = key
                subcategory = tags.get(key)
                break

        if not category:
            continue

        distance = haversine_distance_m(float(lat), float(lon), p_lat, p_lon)
        pois.append(
            {
                "name": tags.get("name"),
                "category": category,
                "subcategory": subcategory,
                "distance_m": round(distance, 1),
                "lat": p_lat,
                "lon": p_lon,
                "address_hint": ", ".join(
                    str(tags.get(k))
                    for k in ("addr:street", "addr:housenumber", "addr:postcode", "addr:city")
                    if tags.get(k)
                )
                or None,
                "tags": tags,
            }
        )

    pois.sort(key=lambda x: x.get("distance_m") or 999999)
    return {"source_url": source_url, "pois": pois[: max(0, max_items)]}


def fetch_google_news_rss(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    query: str,
    limit: int,
    source_name: str = "google_news_rss",
) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        sources.disable(source_name, "leerer Suchquery")
        return {"source_url": None, "events": []}

    params = urllib.parse.urlencode({"q": q, "hl": "de-CH", "gl": "CH", "ceid": "CH:de"})
    url = f"https://news.google.com/rss/search?{params}"
    headers = {"User-Agent": client.user_agent, "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"}

    rss_cache_key = f"rss::{url}"
    cached = client._read_disk_cache(rss_cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("events"), list):
        cached_events = list(cached.get("events") or [])[: max(0, limit)]
        sources.note_success(source_name, url, records=len(cached_events), optional=True)
        client._emit_upstream_event(
            event="api.upstream.response.summary",
            level="info",
            source=source_name,
            url=url,
            direction="upstream->api",
            status="cache_hit",
            cache="disk",
            records=len(cached_events),
            payload_kind="rss",
            retry_count=0,
        )
        return {
            "source_url": url,
            "events": cached_events,
            "cache": "disk",
        }

    last_error: Optional[str] = None
    max_attempts = client.retries + 1
    for attempt in range(1, max_attempts + 1):
        attempt_started_at = time.perf_counter()
        client._emit_upstream_event(
            event="api.upstream.request.start",
            level="info",
            source=source_name,
            url=url,
            direction="api->upstream",
            status="sent",
            attempt=attempt,
            max_attempts=max_attempts,
            retry_count=max(0, attempt - 1),
            timeout_seconds=float(client.timeout),
        )
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=client.timeout) as resp:
                raw = resp.read()
                status_code = int(getattr(resp, "status", 200) or 200)

            root = ET.fromstring(raw)
            events: List[Dict[str, Any]] = []
            for item in root.findall("./channel/item")[: max(0, limit)]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                source_node = item.find("source")
                source_label = (source_node.text or "").strip() if source_node is not None else ""
                pub_date = parse_rss_datetime(item.findtext("pubDate"))
                description = (item.findtext("description") or "").strip()

                events.append(
                    {
                        "title": title,
                        "url": link,
                        "source": source_label or "Google News",
                        "published_at": pub_date,
                        "description": strip_html(description) if description else None,
                    }
                )

            duration_ms = round((time.perf_counter() - attempt_started_at) * 1000.0, 3)
            client._emit_upstream_event(
                event="api.upstream.request.end",
                level="info",
                source=source_name,
                url=url,
                direction="upstream->api",
                status="ok",
                status_code=status_code,
                duration_ms=duration_ms,
                attempt=attempt,
                max_attempts=max_attempts,
                retry_count=max(0, attempt - 1),
            )
            client._emit_upstream_event(
                event="api.upstream.response.summary",
                level="info",
                source=source_name,
                url=url,
                direction="upstream->api",
                status="ok",
                cache="miss",
                status_code=status_code,
                records=len(events),
                payload_kind="rss",
                attempt=attempt,
                max_attempts=max_attempts,
                retry_count=max(0, attempt - 1),
            )

            sources.note_success(source_name, url, records=len(events), optional=True)
            client._write_disk_cache(rss_cache_key, {"source_url": url, "events": events})
            return {"source_url": url, "events": events}
        except urllib.error.HTTPError as exc:
            duration_ms = round((time.perf_counter() - attempt_started_at) * 1000.0, 3)
            retryable = exc.code in RETRYABLE_HTTP_CODES
            last_error = f"HTTP {exc.code}"
            sources.note_error(source_name, url, last_error, optional=True)
            will_retry = retryable and attempt <= client.retries
            client._emit_upstream_event(
                event="api.upstream.request.end",
                level="warn" if will_retry else "error",
                source=source_name,
                url=url,
                direction="upstream->api",
                status="retrying" if will_retry else "error",
                status_code=int(exc.code),
                duration_ms=duration_ms,
                attempt=attempt,
                max_attempts=max_attempts,
                retry_count=max(0, attempt - 1),
                retryable=retryable,
                error_class="http_error",
                error_message=last_error,
            )
            if not will_retry:
                break
            client._sleep_backoff(attempt)
        except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
            duration_ms = round((time.perf_counter() - attempt_started_at) * 1000.0, 3)
            last_error = str(exc)
            sources.note_error(source_name, url, last_error, optional=True)
            will_retry = attempt <= client.retries
            client._emit_upstream_event(
                event="api.upstream.request.end",
                level="warn" if will_retry else "error",
                source=source_name,
                url=url,
                direction="upstream->api",
                status="retrying" if will_retry else "error",
                duration_ms=duration_ms,
                attempt=attempt,
                max_attempts=max_attempts,
                retry_count=max(0, attempt - 1),
                retryable=not isinstance(exc, ET.ParseError),
                error_class="decode_error" if isinstance(exc, ET.ParseError) else "network_error",
                error_message=last_error,
            )
            if not will_retry or isinstance(exc, ET.ParseError):
                break
            client._sleep_backoff(attempt)

    if last_error:
        return {"source_url": url, "events": [], "error": last_error}
    return {"source_url": url, "events": []}


def fetch_city_anchor(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    city: str,
) -> Dict[str, Any]:
    city_q = (city or "").strip()
    if not city_q:
        raise ValueError("--city darf nicht leer sein.")

    url = build_search_url(city_q, limit=12, origins=None)
    payload = tracked_get_json(client, sources, "geoadmin_city_search", url, optional=False) or {}
    results = payload.get("results") or []

    city_norm = normalize_text(city_q)
    best: Optional[Dict[str, Any]] = None

    for item in results:
        attrs = (item or {}).get("attrs") or {}
        if not isinstance(attrs, dict):
            continue

        lat_raw = attrs.get("lat")
        lon_raw = attrs.get("lon")
        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
        except (TypeError, ValueError):
            continue

        label = strip_html(attrs.get("label") or "") or ""
        detail = str(attrs.get("detail") or "")
        origin = str(attrs.get("origin") or "")
        rank = attrs.get("rank")

        score = 0.0
        if origin in {"gg25", "zipcode", "district"}:
            score += 20
        elif origin in {"gazetteer", "kantone"}:
            score += 10

        haystack = f"{normalize_text(label)} {normalize_text(detail)}"
        if city_norm and city_norm in haystack:
            score += 24
        elif city_norm and all(t in haystack for t in tokenize(city_norm)):
            score += 14

        if isinstance(rank, (int, float)):
            score += clamp(10 - float(rank), 0, 8)

        cand = {
            "score": round(score, 3),
            "label": label,
            "origin": origin,
            "lat": lat,
            "lon": lon,
            "detail": detail,
            "feature_id": attrs.get("featureId"),
            "raw": attrs,
        }
        if best is None or cand["score"] > best["score"]:
            best = cand

    if not best:
        raise NoAddressMatchError(f"Keine belastbare Stadtverortung gefunden: {city_q}")

    label = str(best.get("label") or city_q)
    canton = None
    m = re.search(r"\(([A-Z]{2})\)", label)
    if m:
        canton = m.group(1)

    return {
        "query": city_q,
        "label": label,
        "origin": best.get("origin"),
        "lat": best.get("lat"),
        "lon": best.get("lon"),
        "canton": canton,
        "feature_id": best.get("feature_id"),
        "score": best.get("score"),
        "source_url": url,
    }


def fetch_target_address_anchor(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    target_address: str,
    city_hint: Optional[str],
) -> Optional[Dict[str, Any]]:
    query = str(target_address or "").strip()
    if not query:
        return None

    city_norm = normalize_text(city_hint or "")
    if city_norm and city_norm not in normalize_text(query):
        query = f"{query}, {city_hint}"

    primary_url = build_search_url(query, limit=8, origins="address")
    active_url = primary_url
    payload = tracked_get_json(client, sources, "geoadmin_target_search", primary_url, optional=True) or {}
    results = payload.get("results") or []

    if not results:
        fallback_url = build_search_url(query, limit=10, origins=None)
        active_url = fallback_url
        payload = tracked_get_json(client, sources, "geoadmin_target_search", fallback_url, optional=True) or {}
        results = payload.get("results") or []

    best = None
    for row in results:
        attrs = row.get("attrs") if isinstance(row, dict) else None
        if not isinstance(attrs, dict):
            continue

        lat = attrs.get("lat")
        lon = attrs.get("lon")
        if lat is None or lon is None:
            continue
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            continue
        if abs(lat_f) > 90 or abs(lon_f) > 180:
            continue

        label = strip_html(attrs.get("label") or "") or ""
        detail = str(attrs.get("detail") or "")
        origin = str(attrs.get("origin") or "")
        rank = float(attrs.get("rank") or 99)
        city_bonus = 0.0
        if city_norm and city_norm in normalize_text(f"{label} {detail}"):
            city_bonus = 3.0

        score = 0.0
        if origin == "address":
            score += 8.0
        score += clamp(12.0 - rank, 0.0, 8.0)
        score += city_bonus

        cand = {
            "query": target_address,
            "resolved_query": query,
            "label": label,
            "lat": lat_f,
            "lon": lon_f,
            "origin": origin,
            "rank": rank,
            "feature_id": attrs.get("featureId"),
            "score": score,
            "source_url": active_url,
        }
        if best is None or float(cand.get("score") or 0.0) > float(best.get("score") or 0.0):
            best = cand

    return best


def fetch_zone_signals_overpass(
    client: HttpClient,
    sources: SourceRegistry,
    *,
    lat: float,
    lon: float,
    radius_m: int,
    max_items: int,
) -> Dict[str, Any]:
    lat_s = f"{float(lat):.6f}"
    lon_s = f"{float(lon):.6f}"
    query = (
        "[out:json][timeout:25];"
        "("
        f"node(around:{radius_m},{lat_s},{lon_s})[amenity];"
        f"node(around:{radius_m},{lat_s},{lon_s})[shop];"
        f"node(around:{radius_m},{lat_s},{lon_s})[leisure];"
        f"node(around:{radius_m},{lat_s},{lon_s})[public_transport];"
        f"node(around:{radius_m},{lat_s},{lon_s})[railway];"
        f"node(around:{radius_m},{lat_s},{lon_s})[highway~\"^(bus_stop|motorway|trunk|primary|secondary|tertiary)$\"];"
        f"node(around:{radius_m},{lat_s},{lon_s})[landuse~\"^(forest|grass|recreation_ground|meadow)$\"];"
        f"node(around:{radius_m},{lat_s},{lon_s})[natural~\"^(wood|grassland|scrub|tree_row)$\"];"
        f"way(around:{radius_m},{lat_s},{lon_s})[amenity];"
        f"way(around:{radius_m},{lat_s},{lon_s})[shop];"
        f"way(around:{radius_m},{lat_s},{lon_s})[leisure];"
        f"way(around:{radius_m},{lat_s},{lon_s})[public_transport];"
        f"way(around:{radius_m},{lat_s},{lon_s})[railway];"
        f"way(around:{radius_m},{lat_s},{lon_s})[highway~\"^(motorway|trunk|primary|secondary|tertiary)$\"];"
        f"way(around:{radius_m},{lat_s},{lon_s})[landuse~\"^(forest|grass|recreation_ground|meadow)$\"];"
        f"way(around:{radius_m},{lat_s},{lon_s})[natural~\"^(wood|grassland|scrub|tree_row)$\"];"
        f"relation(around:{radius_m},{lat_s},{lon_s})[amenity];"
        f"relation(around:{radius_m},{lat_s},{lon_s})[shop];"
        f"relation(around:{radius_m},{lat_s},{lon_s})[leisure];"
        ");"
        "out body center;"
    )

    source_url = "https://overpass-api.de/api/interpreter?" + urllib.parse.urlencode({"data": query})
    payload = tracked_get_json(client, sources, "osm_area_profile_overpass", source_url, optional=True) or {}
    raw_elements = payload.get("elements") or []

    elements: List[Dict[str, Any]] = []
    seen_ids = set()
    for element in raw_elements:
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue

        point_lat = element.get("lat")
        point_lon = element.get("lon")
        center = element.get("center") or {}
        if point_lat is None:
            point_lat = center.get("lat")
        if point_lon is None:
            point_lon = center.get("lon")
        if point_lat is None or point_lon is None:
            continue

        try:
            p_lat = float(point_lat)
            p_lon = float(point_lon)
        except (TypeError, ValueError):
            continue

        el_type = str(element.get("type") or "")
        el_id = str(element.get("id") or "")
        dedup_key = f"{el_type}:{el_id}"
        if dedup_key in seen_ids:
            continue
        seen_ids.add(dedup_key)

        distance = haversine_distance_m(lat, lon, p_lat, p_lon)
        if distance > max(radius_m * 1.15, radius_m + 120):
            continue

        tag_hint = None
        for key in ("amenity", "shop", "leisure", "public_transport", "railway", "highway", "landuse", "natural"):
            if tags.get(key):
                tag_hint = f"{key}:{tags.get(key)}"
                break

        elements.append(
            {
                "id": dedup_key,
                "name": tags.get("name") or tag_hint or dedup_key,
                "distance_m": round(distance, 1),
                "lat": p_lat,
                "lon": p_lon,
                "tags": tags,
            }
        )

    elements.sort(key=lambda x: x.get("distance_m") or 999999)
    return {"source_url": source_url, "elements": elements[: max(0, max_items)]}


def build_city_incident_signals(
    *,
    city_name: str,
    news_payload: Dict[str, Any],
    max_items: int,
    mode: str,
) -> Dict[str, Any]:
    events_in = list(news_payload.get("events") or [])[: max(0, max_items)]
    source_url = news_payload.get("source_url")

    if not events_in:
        msg = (
            "Keine belastbaren öffentlichen Vorfallhinweise im Feed gefunden. "
            "Das ist kein Sicherheitsnachweis; Bewertung bleibt konservativ."
        )
        return {
            "status": "no_data",
            "incident_risk_score": 48,
            "uncertainty": "unklar",
            "relevant_event_count": 0,
            "events": [],
            "statements": [
                statement(
                    msg,
                    confidence=0.35,
                    evidence=[
                        evidence_item(
                            source="google_news_rss_city",
                            confidence=0.35,
                            url=source_url,
                            snippet=news_payload.get("error") or "Leere Trefferliste",
                            field_path="city_safety.events",
                        )
                    ],
                    field_path="city_safety",
                )
            ],
        }

    risk_keywords = {
        "einbruch": 1.0,
        "ubergriff": 1.2,
        "gewalt": 1.2,
        "raub": 1.1,
        "polizei": 0.65,
        "brand": 0.55,
        "messer": 1.2,
        "kriminal": 1.1,
        "ueberfall": 1.1,
        "delikt": 0.9,
    }

    city_tokens = [t for t in tokenize(city_name) if len(t) >= 3]
    enriched: List[Dict[str, Any]] = []
    total_signal = 0.0

    for idx, raw in enumerate(events_in):
        title = str(raw.get("title") or "")
        title_norm = normalize_text(title)
        token_hits = sum(1 for t in city_tokens if t in title_norm)

        kw_weight = 0.0
        for kw, weight in risk_keywords.items():
            if kw in title_norm:
                kw_weight += weight

        pub_iso = raw.get("published_at")
        recency = 0.35
        if pub_iso:
            try:
                dt = datetime.fromisoformat(str(pub_iso).replace("Z", "+00:00"))
                days = max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400)
                if days <= 30:
                    recency = 1.0
                elif days <= 180:
                    recency = 0.72
                elif days <= 365:
                    recency = 0.5
                else:
                    recency = 0.32
            except Exception:
                recency = 0.35

        relevance = clamp((token_hits * 0.2) + (kw_weight * 0.22) + (recency * 0.3), 0.08, 1.0)
        confidence = clamp(0.28 + token_hits * 0.12 + min(kw_weight, 2.4) * 0.1 + recency * 0.16, 0.2, 0.84)

        ev = [
            evidence_item(
                source="google_news_rss_city",
                confidence=confidence,
                url=raw.get("url") or source_url,
                observed_at=pub_iso or utc_now_iso(),
                snippet=title,
                field_path=f"city_safety.events[{idx}]",
            )
        ]

        status = classify_statement_status(confidence, ev)
        enriched.append(
            {
                "title": title,
                "date": pub_iso,
                "source": raw.get("source"),
                "url": raw.get("url"),
                "description": raw.get("description"),
                "relevance": round(relevance, 3),
                "status": status,
                "confidence": round(confidence, 2),
                "evidence": ev,
            }
        )
        total_signal += relevance * 100.0 * confidence

    enriched.sort(key=lambda x: x.get("date") or "", reverse=True)
    relevant_events = [ev for ev in enriched if ev.get("relevance", 0) >= 0.42]
    avg_signal = (total_signal / max(1, len(enriched))) / 100.0
    risk_score = clamp(20 + avg_signal * 62 + len(relevant_events) * 4.8, 12, 88)
    if mode == "risk":
        risk_score = clamp(risk_score + 6, 0, 95)

    layer_conf = clamp(0.42 + min(0.28, len(relevant_events) * 0.03), 0.42, 0.76)
    headline = (
        f"{len(relevant_events)} öffentliche Vorfallhinweise für {city_name} im Beobachtungszeitraum gefunden (Web-Indizien)."
        if relevant_events
        else f"Nur schwache/unspezifische Vorfallhinweise für {city_name} gefunden (kein Entwarnungssignal)."
    )

    evidence = [
        evidence_item(
            source="google_news_rss_city",
            confidence=layer_conf,
            url=source_url,
            snippet=f"events={len(enriched)}, relevant={len(relevant_events)}",
            field_path="city_safety.incident_risk_score",
        )
    ]

    return {
        "status": "ok",
        "incident_risk_score": int(round(risk_score)),
        "uncertainty": classify_statement_status(layer_conf, evidence),
        "relevant_event_count": len(relevant_events),
        "events": enriched,
        "statements": [
            statement(
                headline,
                confidence=layer_conf,
                evidence=evidence,
                field_path="city_safety",
            )
        ],
    }


def compute_zone_scores_from_indices(
    *,
    indices: Dict[str, float],
    city_incident_risk: float,
    city_incident_status: str,
    mode: str,
    local_signal_count: Optional[int] = None,
) -> Dict[str, Any]:
    transit = clamp(float(indices.get("transit", 0.0)), 0.0, 100.0)
    shopping = clamp(float(indices.get("shopping", 0.0)), 0.0, 100.0)
    green = clamp(float(indices.get("green", 0.0)), 0.0, 100.0)
    nightlife = clamp(float(indices.get("nightlife", 0.0)), 0.0, 100.0)
    major_road = clamp(float(indices.get("major_road", 0.0)), 0.0, 100.0)
    police = clamp(float(indices.get("police", 0.0)), 0.0, 100.0)
    food = clamp(float(indices.get("food", 0.0)), 0.0, 100.0)

    oev = clamp(0.78 * transit + 0.22 * min(100.0, transit + major_road * 0.2), 0.0, 100.0)
    einkauf = clamp(0.72 * shopping + 0.28 * food, 0.0, 100.0)
    gruen = green
    nacht = nightlife

    quiet_pressure = clamp(0.68 * nightlife + 0.72 * major_road + 0.2 * food - 0.25 * green, 0.0, 100.0)
    ruhe = clamp(100.0 - quiet_pressure, 0.0, 100.0)

    risk_pressure = clamp(0.58 * nightlife + 0.66 * major_road, 0.0, 100.0)
    protective_capacity = clamp(0.52 * police + 0.08 * transit, 0.0, 100.0)
    local_safety_risk = clamp(risk_pressure - protective_capacity, 0.0, 100.0)

    # Widersprüchliche Signale (z. B. viele Ausgehspots + starke Polizeipräsenz)
    # erhöhen die Unsicherheit und ziehen das Ergebnis moderat Richtung Neutralzone.
    contradiction_index = clamp(min(risk_pressure, protective_capacity) / 70.0, 0.0, 1.0)

    city_weight = 0.52 if mode == "risk" else 0.44
    city_part = city_incident_risk if city_incident_status == "ok" else 50.0
    uncertainty_penalty = 8.5 if city_incident_status != "ok" else 0.0
    safety_risk = clamp((1.0 - city_weight) * local_safety_risk + city_weight * city_part + uncertainty_penalty, 0.0, 100.0)

    raw_sicherheit = clamp(100.0 - safety_risk, 0.0, 100.0)
    neutral_pull = 0.22 * contradiction_index
    sicherheit = clamp(raw_sicherheit * (1.0 - neutral_pull) + 50.0 * neutral_pull, 0.0, 100.0)

    signal_count = max(0, int(local_signal_count or 0))
    sparse_blend = 0.0
    if local_signal_count is not None:
        if signal_count <= 3:
            sparse_blend = 0.54
        elif signal_count < 8:
            sparse_blend = 0.42
        elif signal_count < 14:
            sparse_blend = 0.24
        if sparse_blend > 0:
            sicherheit = clamp(sicherheit * (1.0 - sparse_blend) + 50.0 * sparse_blend, 0.0, 100.0)

    if city_incident_status != "ok":
        safety_uncertainty = "unklar"
    elif contradiction_index >= 0.62:
        safety_uncertainty = "unklar"
    elif signal_count >= 28 and contradiction_index <= 0.16 and mode != "risk":
        safety_uncertainty = "gesichert"
    elif local_signal_count is not None and signal_count < 8:
        safety_uncertainty = "unklar"
    else:
        safety_uncertainty = "indiz"

    return {
        "metrics": {
            "ruhe": round(ruhe, 1),
            "oev": round(oev, 1),
            "einkauf": round(einkauf, 1),
            "gruen": round(gruen, 1),
            "sicherheit": round(sicherheit, 1),
            "nachtaktivitaet": round(nacht, 1),
        },
        "indices": {
            "transit": round(transit, 1),
            "shopping": round(shopping, 1),
            "green": round(green, 1),
            "nightlife": round(nightlife, 1),
            "major_road": round(major_road, 1),
            "police": round(police, 1),
            "food": round(food, 1),
            "risk_pressure": round(risk_pressure, 1),
            "protective_capacity": round(protective_capacity, 1),
            "contradiction_index": round(contradiction_index, 3),
            "local_safety_risk": round(local_safety_risk, 1),
            "city_incident_risk": round(city_part, 1),
            "sparse_blend": round(sparse_blend, 3),
        },
        "safety_uncertainty": safety_uncertainty,
    }



def derive_zone_uncertainty(
    *,
    zone_status: str,
    safety_uncertainty: str,
    contradiction_index: float,
    poi_signal_count: int,
) -> Dict[str, Any]:
    contradiction = clamp(float(contradiction_index), 0.0, 1.0)
    status = "indiz"
    reason = "Indikative Modelllage aus Community-/Web-Signalen."

    if zone_status in {"sparse_data", "no_data"}:
        status = "unklar"
        reason = "Sehr dünne Datengrundlage (POI-Signale fehlen weitgehend)."
    elif safety_uncertainty == "unklar":
        status = "unklar"
        reason = "Sicherheitsindikator ist unsicher (fehlende/widersprüchliche Signale)."
    elif contradiction >= 0.62:
        status = "unklar"
        reason = "Widersprüchliche Risiko- und Schutzsignale im Nahumfeld."
    elif safety_uncertainty == "gesichert" and zone_status == "ok" and poi_signal_count >= 28 and contradiction <= 0.16:
        status = "gesichert"
        reason = "Hohe Signaldichte mit stabilen, wenig widersprüchlichen Modelltreibern."

    return {
        "status": status,
        "reason": reason,
        "contradiction_index": round(contradiction, 3),
    }


def _sample_confidence(distance_m: float, *, base: float = 0.42) -> float:
    try:
        d = float(distance_m)
    except (TypeError, ValueError):
        d = 250.0
    proximity = clamp(1.0 - (d / 320.0), 0.0, 1.0)
    return clamp(base + proximity * 0.34, 0.35, 0.86)


def build_zone_weight_model(
    *,
    zone_index: int,
    zone_code: str,
    metrics: Dict[str, float],
    normalized_weights: Dict[str, float],
    samples: Dict[str, List[Dict[str, Any]]],
    fallback_url: Optional[str],
) -> Dict[str, Any]:
    bucket_map = {
        'ruhe': ['major_road', 'nightlife'],
        'oev': ['transit'],
        'einkauf': ['shopping', 'food'],
        'gruen': ['green'],
        'sicherheit': ['police', 'major_road', 'nightlife'],
        'nachtaktivitaet': ['nightlife'],
    }

    contributions: List[Dict[str, Any]] = []
    for metric_key in AREA_WEIGHT_KEYS:
        metric_score = clamp(float(metrics.get(metric_key, 0.0)), 0.0, 100.0)
        weight = clamp(float(normalized_weights.get(metric_key, 0.0)), 0.0, 1.0)
        weighted_points = metric_score * weight
        delta_vs_neutral = (metric_score - 50.0) * weight

        sample_entries: List[Dict[str, Any]] = []
        for bucket in bucket_map.get(metric_key, []):
            sample_entries.extend(samples.get(bucket) or [])

        sample = sample_entries[0] if sample_entries else None
        ev_conf = _sample_confidence((sample or {}).get('distance_m', 260.0), base=0.43)
        evidence = [
            evidence_item(
                source='osm_area_profile_overpass',
                confidence=ev_conf,
                url=(sample or {}).get('url') or fallback_url,
                observed_at=(sample or {}).get('observed_at') or utc_now_iso(),
                snippet=f"{zone_code}:{metric_key}={metric_score:.0f},w={weight:.3f},delta={delta_vs_neutral:+.2f}",
                field_path=f"zones[{zone_index}].weight_model.contributions.{metric_key}",
            )
        ]

        contributions.append(
            {
                'metric': metric_key,
                'metric_score': round(metric_score, 2),
                'weight': round(weight, 6),
                'weighted_points': round(weighted_points, 2),
                'delta_vs_neutral': round(delta_vs_neutral, 2),
                'status': classify_statement_status(ev_conf, evidence),
                'evidence': evidence,
            }
        )

    contributions.sort(key=lambda item: abs(float(item.get('delta_vs_neutral') or 0.0)), reverse=True)

    drivers: List[Dict[str, Any]] = []
    for row in contributions:
        delta = float(row.get('delta_vs_neutral') or 0.0)
        if abs(delta) < 0.9:
            continue
        metric = str(row.get('metric') or '')
        score = float(row.get('metric_score') or 0.0)
        weight_pct = float(row.get('weight') or 0.0) * 100.0
        direction = 'positive' if delta >= 0 else 'negative'
        text = (
            f"Gewichtstreiber {metric}: {score:.0f}/100 bei {weight_pct:.1f}% Gewicht "
            f"({delta:+.1f} ggü. Neutralzone)."
        )
        drivers.append(
            {
                'metric': metric,
                'direction': direction,
                'impact_points': round(delta, 2),
                'text': text,
                'confidence': row.get('evidence', [{}])[0].get('confidence', 0.44),
                'evidence': row.get('evidence') or [],
            }
        )
        if len(drivers) >= 4:
            break

    return {
        'baseline_score': 50,
        'normalized_weights': {k: round(float(normalized_weights.get(k, 0.0)), 6) for k in AREA_WEIGHT_KEYS},
        'contributions': contributions,
        'drivers': drivers,
        'formula': 'overall_score = Σ(metric_score * normalized_weight); delta_vs_neutral = (metric_score-50)*weight',
        'notes': [
            'Gewichte werden vor der Berechnung auf Summe=1 normalisiert.',
            'Starke negative/positive Treiber werden als drivers ausgewiesen.',
        ],
    }


def build_zone_security_signals(
    *,
    zone_index: int,
    zone_code: str,
    city_safety: Dict[str, Any],
    city_news_payload: Dict[str, Any],
    local_samples: Dict[str, List[Dict[str, Any]]],
    local_indices: Dict[str, float],
    local_signal_count: int,
    zone_status: str,
    fallback_url: Optional[str],
) -> Dict[str, Any]:
    signals: List[Dict[str, Any]] = []
    facts: List[Dict[str, Any]] = []

    def add_fact(*, kind: str, text: str, value: Any, source: str, url: Optional[str], confidence: float) -> None:
        ev = [
            evidence_item(
                source=source,
                confidence=confidence,
                url=url,
                snippet=f"{zone_code}:{kind}={value}",
                field_path=f"zones[{zone_index}].security_facts",
            )
        ]
        facts.append(
            {
                "kind": kind,
                "text": text,
                "value": value,
                "certainty": "hoch" if confidence >= 0.75 else "mittel",
                "source": source,
                "evidence": ev,
            }
        )

    def add_signal(
        *,
        kind: str,
        direction: str,
        text: str,
        confidence: float,
        source: str,
        url: Optional[str],
        observed_at: Optional[str],
        score_hint: Optional[float] = None,
        snippet: Optional[str] = None,
    ) -> None:
        ev = [
            evidence_item(
                source=source,
                confidence=confidence,
                url=url,
                observed_at=observed_at,
                snippet=snippet or text,
                field_path=f"zones[{zone_index}].security_signals",
            )
        ]
        signals.append(
            {
                "kind": kind,
                "direction": direction,
                "signal_class": "indicative",
                "text": text,
                "confidence": round(clamp(confidence, 0.0, 1.0), 2),
                "status": classify_statement_status(confidence, ev),
                "source": source,
                "url": url,
                "observed_at": observed_at or utc_now_iso(),
                "score_hint": None if score_hint is None else round(float(score_hint), 1),
                "evidence": ev,
            }
        )

    city_risk = float(city_safety.get("incident_risk_score") or 48.0)
    city_status = str(city_safety.get("status") or "no_data")
    city_url = city_news_payload.get("source_url")
    city_obs = utc_now_iso()
    thin_data_guard = str(zone_status) in {"sparse_data", "thin_data"} or int(local_signal_count or 0) < 10

    add_fact(
        kind="zone_status",
        text="Zonen-Datenstatus aus POI-Signalabdeckung",
        value=str(zone_status),
        source="osm_area_profile_overpass",
        url=fallback_url,
        confidence=0.86,
    )
    add_fact(
        kind="local_signal_count",
        text="Anzahl lokaler Umfeldsignale (POI) im Radius",
        value=int(local_signal_count or 0),
        source="osm_area_profile_overpass",
        url=fallback_url,
        confidence=0.86,
    )
    add_fact(
        kind="city_feed_status",
        text="Status des stadtweiten Incident-Feeds",
        value=city_status,
        source="google_news_rss_city",
        url=city_url,
        confidence=0.82 if city_status == "ok" else 0.72,
    )
    add_fact(
        kind="city_relevant_event_count",
        text="Anzahl relevanter stadtweiter Vorfallhinweise (Feed)",
        value=int(city_safety.get("relevant_event_count") or 0),
        source="google_news_rss_city",
        url=city_url,
        confidence=0.8 if city_status == "ok" else 0.68,
    )

    city_conf = 0.55 if city_status == "ok" else 0.4
    if thin_data_guard:
        city_conf = min(city_conf, 0.5)
    add_signal(
        kind="city_incident_baseline",
        direction="risk",
        text=(
            f"Stadtweiter Web-Incident-Index {city_risk:.0f}/100 (indikativ, kein amtlicher Kriminaldatensatz)."
            if city_status == "ok"
            else "Stadtweite Incident-Daten unvollständig; Sicherheitsbewertung bleibt konservativ."
        ),
        confidence=city_conf,
        source="google_news_rss_city",
        url=city_url,
        observed_at=city_obs,
        score_hint=city_risk,
        snippet=f"{zone_code}:city_incident_risk={city_risk:.0f}",
    )

    city_event_limit = 5
    if thin_data_guard:
        city_event_limit = 1

    for event in (city_safety.get("events") or [])[:city_event_limit]:
        relevance = float(event.get("relevance") or 0.0)
        if relevance < (0.62 if thin_data_guard else 0.42):
            continue
        ev_conf = clamp(float(event.get("confidence") or 0.35), 0.2, 0.85)
        if thin_data_guard:
            ev_conf = clamp(ev_conf * 0.78, 0.2, 0.74)
        add_signal(
            kind="city_incident_event",
            direction="risk",
            text=str(event.get("title") or "Öffentlicher Vorfallhinweis"),
            confidence=ev_conf,
            source="google_news_rss_city",
            url=event.get("url") or city_url,
            observed_at=event.get("date") or city_obs,
            score_hint=relevance * 100.0,
            snippet=f"{zone_code}:relevance={relevance:.2f}",
        )

    for bucket, direction, kind in [
        ("major_road", "risk", "local_major_road"),
        ("nightlife", "risk", "local_nightlife"),
        ("police", "protective", "local_protective_services"),
    ]:
        sample = (local_samples.get(bucket) or [None])[0]
        if not sample:
            continue
        distance = float(sample.get("distance_m") or 260.0)
        idx_hint = float(local_indices.get(bucket) or 0.0)
        if thin_data_guard and direction == "risk" and idx_hint < 18:
            continue

        conf = _sample_confidence(distance, base=0.46 if direction == "risk" else 0.5)
        if thin_data_guard:
            conf = clamp(conf * 0.86, 0.34, 0.78)
        text = (
            f"Nahes Umfeldsignal ({bucket}) in {distance:.0f}m Abstand."
            if direction == "risk"
            else f"Schutz-/Interventionssignal ({bucket}) in {distance:.0f}m Abstand."
        )
        add_signal(
            kind=kind,
            direction=direction,
            text=text,
            confidence=conf,
            source="osm_area_profile_overpass",
            url=sample.get("url") or fallback_url,
            observed_at=sample.get("observed_at") or utc_now_iso(),
            score_hint=idx_hint,
            snippet=f"{zone_code}:{bucket}={idx_hint:.1f}",
        )

    if thin_data_guard:
        add_signal(
            kind="thin_data_guard",
            direction="neutral",
            text="Dünne lokale Datenlage: Risikosignale werden bewusst zurückhaltend interpretiert.",
            confidence=0.52,
            source="osm_area_profile_overpass",
            url=fallback_url,
            observed_at=utc_now_iso(),
            score_hint=100.0 - min(100.0, float(local_signal_count) * 8.0),
            snippet=f"{zone_code}:thin_data_guard={local_signal_count}",
        )

    signals.sort(key=lambda row: (float(row.get("confidence") or 0.0), float(row.get("score_hint") or 0.0)), reverse=True)

    risk_n = sum(1 for row in signals if row.get("direction") == "risk")
    protective_n = sum(1 for row in signals if row.get("direction") == "protective")
    contradiction_ratio = clamp(min(risk_n, protective_n) / max(1.0, float(risk_n + protective_n)), 0.0, 1.0)

    if risk_n >= 2 and protective_n >= 1 and contradiction_ratio >= 0.28:
        add_signal(
            kind="mixed_signal_pattern",
            direction="neutral",
            text="Widersprüchliche Sicherheitsindikatoren: Risiko- und Schutzsignale treten parallel auf.",
            confidence=0.48,
            source="osm_area_profile_overpass",
            url=fallback_url,
            observed_at=utc_now_iso(),
            score_hint=contradiction_ratio * 100.0,
            snippet=f"{zone_code}:mixed={contradiction_ratio:.2f}",
        )

    signals.sort(key=lambda row: (float(row.get("confidence") or 0.0), float(row.get("score_hint") or 0.0)), reverse=True)
    avg_conf = sum(float(row.get("confidence") or 0.0) for row in signals) / max(1, len(signals))
    overview_conf = clamp(avg_conf if signals else 0.34, 0.3, 0.8)

    if signals:
        headline = f"{risk_n} Risikosignale / {protective_n} Schutzsignale (indikativ, evidenzbasiert)."
        if contradiction_ratio >= 0.35:
            headline += " Gemischtes Signalbild erhöht die Unsicherheit."
        if thin_data_guard:
            headline += " Dünne Datenlage -> konservative Fehlalarmbremse aktiv."
    else:
        headline = "Keine belastbaren Sicherheitssignale gefunden; konservative Unsicherheitsannahme aktiv."

    overview_ev = [
        evidence_item(
            source="google_news_rss_city" if city_status == "ok" else "osm_area_profile_overpass",
            confidence=overview_conf,
            url=city_url or fallback_url,
            observed_at=city_obs,
            snippet=f"risk={risk_n},protective={protective_n},mixed={contradiction_ratio:.2f},thin_guard={thin_data_guard}",
            field_path=f"zones[{zone_index}].security_overview",
        )
    ]

    return {
        "facts": facts[:8],
        "signals": signals[:10],
        "overview": {
            "risk_signals": risk_n,
            "protective_signals": protective_n,
            "mixed_signal_ratio": round(contradiction_ratio, 3),
            "thin_data_guard": bool(thin_data_guard),
            "headline": headline,
            "confidence": round(overview_conf, 2),
            "status": classify_statement_status(overview_conf, overview_ev),
            "evidence": overview_ev,
        },
        "evidence_split": {
            "hard_facts": len(facts),
            "indicative_signals": len(signals),
            "note": "Harte Fakten = beobachtete Zählwerte/Status. Signale = modellierte Indikatoren.",
        },
    }

def render_city_heatmap(zones: Sequence[Dict[str, Any]], grid_size: int) -> str:
    rows: List[str] = []
    half = grid_size // 2
    zone_lookup = {
        (int(z.get("row_offset", 0)), int(z.get("col_offset", 0))): z
        for z in zones
    }

    for row in range(-half, half + 1):
        label = "N" if row < 0 else ("S" if row > 0 else "C")
        if row < 0:
            label += str(abs(row))
        elif row > 0:
            label += str(row)
        cells: List[str] = []
        for col in range(-half, half + 1):
            zone = zone_lookup.get((row, col))
            if not zone:
                cells.append("  ..")
                continue
            tl = str(zone.get("traffic_light") or "yellow")
            emoji = "🟢" if tl == "green" else ("🟡" if tl == "yellow" else "🔴")
            score = int(round(float(zone.get("overall_score") or 0.0)))
            cells.append(f"{emoji}{score:02d}")
        rows.append(f"{label:>3} | " + " ".join(cells))

    cols = []
    for col in range(-half, half + 1):
        if col < 0:
            cols.append(f"W{abs(col)}")
        elif col > 0:
            cols.append(f"E{col}")
        else:
            cols.append("C")
    header = "    | " + " ".join(f"{c:>3}" for c in cols)
    return header + "\n" + "\n".join(rows)


def build_recommendation_explanation(
    *,
    recommended_zone: Optional[Dict[str, Any]],
    city_safety: Dict[str, Any],
    top_n: int,
    target_context: Optional[Dict[str, Any]] = None,
) -> str:
    if not recommended_zone:
        return "Keine Empfehlung ableitbar (fehlende Zonenbewertung)."

    tl = str(recommended_zone.get("traffic_light") or zone_traffic_light(float(recommended_zone.get("score") or 0.0)))
    zone_code = str(recommended_zone.get("zone") or recommended_zone.get("zone_code") or "?")
    score = float(recommended_zone.get("score") or recommended_zone.get("overall_score") or 0.0)

    if tl == "green":
        base = f"{zone_code} ist im bewerteten Raster eine robuste Grün-Zone ({score:.1f}/100)."
    else:
        base = (
            f"{zone_code} ist die beste verfügbare Zone innerhalb der Top-{max(1, int(top_n))}, "
            f"aber absolut nicht grün (Ampel {tl}, {score:.1f}/100)."
        )

    drivers = [
        str(d.get("text") or "")
        for d in ((recommended_zone.get("weight_model") or {}).get("drivers") or [])
        if str(d.get("direction") or "") == "negative"
    ]
    if drivers:
        base += f" Hauptbremse: {drivers[0]}"

    city_risk = int(city_safety.get("incident_risk_score") or 0)
    if city_risk >= 67:
        base += f" Stadtweit erhöhtes Incident-Signalniveau ({city_risk}/100) dämpft die Sicherheitsmetrik."

    if target_context and target_context.get("nearest_zone_code"):
        nearest_code = target_context.get("nearest_zone_code")
        dist = target_context.get("nearest_zone_distance_m")
        if nearest_code != zone_code:
            base += (
                f" Zieladresse liegt näher bei {nearest_code}"
                f" ({int(dist or 0)}m), Empfehlung bleibt jedoch {zone_code} wegen besserem Gesamtscore."
            )
        elif dist is not None:
            base += f" Zieladresse liegt innerhalb der empfohlenen Zone (≈{int(dist)}m zum Zonenzentrum)."

    return base


def slugify_filename(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "city"


def canonical_map_style(raw: Optional[str]) -> str:
    key = normalize_text(raw or DEFAULT_MAP_STYLE).replace("_", "-")
    canonical = MAP_STYLE_ALIASES.get(key)
    if canonical:
        return canonical
    if key in MAP_STYLE_CONFIG:
        return key
    raise ValueError(
        "Unbekannter --map-style. Erlaubt: " + ", ".join(sorted(MAP_STYLE_CONFIG.keys()))
    )


def latlon_to_world_px(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    lat = clamp(lat, -85.05112878, 85.05112878)
    lon = clamp(lon, -180.0, 180.0)
    scale = 256.0 * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * scale
    lat_rad = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_rad) + (1.0 / max(math.cos(lat_rad), 1e-9))) / math.pi) / 2.0 * scale
    return x, y


def meters_per_pixel(lat: float, zoom: int) -> float:
    return math.cos(math.radians(clamp(lat, -85.0, 85.0))) * 2 * math.pi * 6378137 / (256 * (2 ** zoom))


def pick_zoom_for_bbox(
    *,
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    width: int,
    height: int,
    padding: int,
    min_zoom: int = 10,
    max_zoom: int = 18,
) -> int:
    inner_w = max(120, width - 2 * padding)
    inner_h = max(120, height - 2 * padding)

    for zoom in range(max_zoom, min_zoom - 1, -1):
        x1, y1 = latlon_to_world_px(min_lat, min_lon, zoom)
        x2, y2 = latlon_to_world_px(max_lat, max_lon, zoom)
        bbox_w = abs(x2 - x1)
        bbox_h = abs(y2 - y1)
        if bbox_w <= inner_w and bbox_h <= inner_h:
            return zoom
    return min_zoom


def build_city_ranking_map_layers(
    *,
    zones: Sequence[Dict[str, Any]],
    city_anchor: Dict[str, Any],
    zone_radius_m: int,
    top_n: int,
    target_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    marker_kind_meta = {
        "traffic_axis": {
            "bucket": "major_road",
            "label": "Verkehrsachse",
            "color": "#D84315",
            "shape": "triangle",
            "glyph": "V",
            "priority": 2,
        },
        "night_activity": {
            "bucket": "nightlife",
            "label": "Nachtaktivität",
            "color": "#6A1B9A",
            "shape": "circle",
            "glyph": "N",
            "priority": 3,
        },
        "safety_service": {
            "bucket": "police",
            "label": "Schutz-/Interventionspunkt",
            "color": "#1565C0",
            "shape": "square",
            "glyph": "S",
            "priority": 1,
        },
        "transit_hub": {
            "bucket": "transit",
            "label": "ÖV-Knoten",
            "color": "#00897B",
            "shape": "diamond",
            "glyph": "Ö",
            "priority": 0,
        },
    }

    map_zones: List[Dict[str, Any]] = []
    map_markers: List[Dict[str, Any]] = []
    marker_seen = set()

    top_zone_codes = [str(z.get("zone_code") or "") for z in list(zones)[: max(1, top_n)]]
    top_zone_set = {z for z in top_zone_codes if z}
    target_nearest_zone = str((target_context or {}).get("nearest_zone_code") or "")

    min_lat = 999.0
    max_lat = -999.0
    min_lon = 999.0
    max_lon = -999.0

    for zone in zones:
        center = zone.get("center") or {}
        z_lat = center.get("lat")
        z_lon = center.get("lon")
        if z_lat is None or z_lon is None:
            continue
        try:
            lat = float(z_lat)
            lon = float(z_lon)
        except (TypeError, ValueError):
            continue

        radius_lat = float(zone_radius_m) / 111320.0
        radius_lon = float(zone_radius_m) / (111320.0 * max(math.cos(math.radians(lat)), 0.2))
        min_lat = min(min_lat, lat - radius_lat)
        max_lat = max(max_lat, lat + radius_lat)
        min_lon = min(min_lon, lon - radius_lon)
        max_lon = max(max_lon, lon + radius_lon)

        zone_code = str(zone.get("zone_code") or "")
        score = float(zone.get("overall_score") or 0.0)
        traffic = str(zone.get("traffic_light") or zone_traffic_light(score))
        band = zone_score_band(score)
        fill_color = zone_score_color(score)
        is_top_zone = zone_code in top_zone_set
        is_target_nearest = bool(target_nearest_zone and zone_code == target_nearest_zone)

        stroke_color = "#263238"
        stroke_width = 1.2
        if is_top_zone:
            stroke_color = "#1B5E20"
            stroke_width = 1.6
        if is_target_nearest:
            stroke_color = "#0D47A1"
            stroke_width = 2.4

        map_zones.append(
            {
                "zone_code": zone.get("zone_code"),
                "zone_name": zone.get("zone_name"),
                "rank": zone.get("rank"),
                "traffic_light": traffic,
                "overall_score": round(score, 2),
                "score_band": band,
                "is_top_zone": is_top_zone,
                "is_target_nearest": is_target_nearest,
                "center": {"lat": round(lat, 6), "lon": round(lon, 6)},
                "radius_m": int(zone_radius_m),
                "style": {
                    "fill": fill_color,
                    "opacity": 0.24 if traffic != "yellow" else 0.28,
                    "stroke": stroke_color,
                    "stroke_width": stroke_width,
                },
                "evidence": [
                    {
                        "source": "osm_area_profile_overpass",
                        "status": zone.get("status"),
                        "quality_note": zone.get("quality_note"),
                        "zone_uncertainty": (zone.get("zone_uncertainty") or {}).get("status"),
                        "security_overview": (zone.get("security_overview") or {}).get("headline"),
                    }
                ],
            }
        )

        sample_signals = zone.get("sample_signals") or {}
        reasons = [str(r.get("text") or "") for r in (zone.get("reasons") or [])[:3] if r.get("text")]
        security_headline = (zone.get("security_overview") or {}).get("headline")

        for marker_kind, marker_meta in marker_kind_meta.items():
            bucket = marker_meta["bucket"]
            sample = (sample_signals.get(bucket) or [None])[0]
            if not sample:
                continue
            lat_raw = sample.get("lat")
            lon_raw = sample.get("lon")
            if lat_raw is None or lon_raw is None:
                continue
            try:
                m_lat = float(lat_raw)
                m_lon = float(lon_raw)
            except (TypeError, ValueError):
                continue
            dedup = (marker_kind, round(m_lat, 5), round(m_lon, 5))
            if dedup in marker_seen:
                continue
            marker_seen.add(dedup)

            marker = {
                "kind": marker_kind,
                "label": marker_meta["label"],
                "shape": marker_meta["shape"],
                "glyph": marker_meta.get("glyph") or marker_meta["label"][:1],
                "priority": int(marker_meta.get("priority") or 0),
                "color": marker_meta["color"],
                "zone_code": zone_code,
                "lat": round(m_lat, 6),
                "lon": round(m_lon, 6),
                "distance_m": sample.get("distance_m"),
                "why": reasons[0] if reasons else security_headline,
                "evidence_refs": [
                    {
                        "source": "osm_area_profile_overpass",
                        "url": sample.get("url"),
                        "observed_at": sample.get("observed_at"),
                        "reason": reasons[0] if reasons else f"Marker aus Bucket {bucket}",
                    },
                    {
                        "source": "google_news_rss_city",
                        "reason": security_headline,
                    },
                ],
            }
            map_markers.append(marker)

    if target_context and (target_context.get("lat") is not None and target_context.get("lon") is not None):
        map_markers.append(
            {
                "kind": "target_address",
                "label": "Zieladresse",
                "shape": "circle",
                "glyph": "⌂",
                "priority": -1,
                "color": "#0D47A1",
                "zone_code": target_nearest_zone or None,
                "lat": round(float(target_context.get("lat")), 6),
                "lon": round(float(target_context.get("lon")), 6),
                "distance_m": 0,
                "why": f"Adressanker: {target_context.get('label') or target_context.get('query')}",
                "evidence_refs": [
                    {
                        "source": "geoadmin_target_search",
                        "url": target_context.get("source_url"),
                        "observed_at": utc_now_iso(),
                        "reason": "Zieladresse für Zonen-Nähevergleich",
                    }
                ],
            }
        )

    map_markers.sort(
        key=lambda m: (
            int(m.get("priority") or 0),
            float(m.get("distance_m") or 999999),
        )
    )
    map_markers = map_markers[:90]

    if min_lat > max_lat or min_lon > max_lon:
        c_lat = float(city_anchor.get("lat") or 47.3769)
        c_lon = float(city_anchor.get("lon") or 8.5417)
        spread = max(float(zone_radius_m) / 111320.0, 0.01)
        min_lat, max_lat = c_lat - spread, c_lat + spread
        min_lon, max_lon = c_lon - spread, c_lon + spread

    warnings = []
    sparse_n = sum(1 for z in zones if str(z.get("status")) in {"sparse_data", "thin_data"})
    uncertain_n = sum(
        1 for z in zones if str((z.get("zone_uncertainty") or {}).get("status") or "indiz") == "unklar"
    )
    if sparse_n:
        warnings.append(
            f"{sparse_n} Zone(n) mit dünner Datenlage; Marker und Farbbänder sind indikativ."
        )
    if uncertain_n:
        warnings.append(f"{uncertain_n} Zone(n) mit Unsicherheitsstatus 'unklar'.")
    if target_context and target_context.get("query") and not target_context.get("label"):
        warnings.append("Zieladresse konnte nicht robust georeferenziert werden; Nähewertung deaktiviert.")

    return {
        "zones": map_zones,
        "markers": map_markers,
        "target": target_context or None,
        "legend": {
            "traffic_light": {
                "green": "gute Gesamtlage im gewichteten Modell",
                "yellow": "mittlere Lage / gemischte Signale",
                "red": "kritische Lage im Modell",
            },
            "score_scale": [
                {"min": 0, "max": 37, "label": "kritisch", "color": zone_score_color(24)},
                {"min": 38, "max": 51, "label": "erhöht", "color": zone_score_color(45)},
                {"min": 52, "max": 61, "label": "watch", "color": zone_score_color(56)},
                {"min": 62, "max": 71, "label": "balanciert", "color": zone_score_color(66)},
                {"min": 72, "max": 83, "label": "stark", "color": zone_score_color(77)},
                {"min": 84, "max": 100, "label": "sehr stark", "color": zone_score_color(90)},
            ],
            "marker_kinds": {
                **{
                    k: {"label": v["label"], "shape": v["shape"], "glyph": v.get("glyph")}
                    for k, v in marker_kind_meta.items()
                },
                "target_address": {"label": "Zieladresse", "shape": "circle", "glyph": "⌂"},
            },
        },
        "viewport": {
            "min_lat": round(min_lat, 6),
            "min_lon": round(min_lon, 6),
            "max_lat": round(max_lat, 6),
            "max_lon": round(max_lon, 6),
        },
        "warnings": warnings,
        "note": "Marker/Farben zeigen evidenzbasierte Indizien, keine amtliche Gefahrenkarte.",
        "top_zone_codes": top_zone_codes,
    }


def _tile_cache_file(style: str, zoom: int, tile_x: int, tile_y: int) -> Path:
    return SKILL_DIR / ".cache" / "osm_tiles" / style / str(zoom) / str(tile_x) / f"{tile_y}.png"


def _tile_error_cache_file(style: str, zoom: int, tile_x: int, tile_y: int) -> Path:
    return SKILL_DIR / ".cache" / "osm_tiles" / style / str(zoom) / str(tile_x) / f"{tile_y}.err.json"


def _fetch_osm_tile_png(
    *,
    client: HttpClient,
    sources: SourceRegistry,
    style: str,
    zoom: int,
    tile_x: int,
    tile_y: int,
    min_delay_s: float,
    tile_ttl_s: float,
) -> Tuple[Optional[Path], bool, Optional[str]]:
    global _LAST_OSM_TILE_REQUEST_TS

    style_cfg = MAP_STYLE_CONFIG.get(style) or MAP_STYLE_CONFIG[DEFAULT_MAP_STYLE]
    server_url = style_cfg["tile_url"].format(z=zoom, x=tile_x, y=tile_y)
    cache_file = _tile_cache_file(style, zoom, tile_x, tile_y)

    now = time.time()
    if cache_file.exists():
        age = now - cache_file.stat().st_mtime
        if age <= max(1.0, tile_ttl_s):
            return cache_file, True, None

    error_cache_file = _tile_error_cache_file(style, zoom, tile_x, tile_y)
    if error_cache_file.exists():
        try:
            err_age = now - error_cache_file.stat().st_mtime
            if err_age <= min(max(90.0, tile_ttl_s * 0.25), TILE_ERROR_CACHE_MAX_AGE):
                payload = json.loads(error_cache_file.read_text(encoding="utf-8"))
                err_msg = str(payload.get("error") or "kürzlicher Tile-Fehler")
                return None, False, f"error-cache:{err_msg}"
        except Exception:
            pass

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": client.user_agent,
        "Accept": "image/png,image/*;q=0.9,*/*;q=0.5",
    }

    last_error = None
    for attempt in range(1, client.retries + 2):
        wait = (min_delay_s or 0.0) - (time.time() - _LAST_OSM_TILE_REQUEST_TS)
        if wait > 0:
            time.sleep(wait)

        try:
            req = urllib.request.Request(server_url, headers=headers)
            with urllib.request.urlopen(req, timeout=client.timeout) as resp:
                body = resp.read()

            if not body:
                raise ExternalRequestError("osm_tile_server", server_url, "Leere Tile-Antwort", retryable=True)

            tmp = cache_file.with_suffix(".tmp")
            tmp.write_bytes(body)
            tmp.replace(cache_file)
            if error_cache_file.exists():
                error_cache_file.unlink(missing_ok=True)
            _LAST_OSM_TILE_REQUEST_TS = time.time()
            sources.note_success("osm_tile_server", server_url, records=1, optional=True)
            return cache_file, False, None
        except urllib.error.HTTPError as exc:
            retryable = exc.code in RETRYABLE_HTTP_CODES
            last_error = f"HTTP {exc.code}"
            sources.note_error("osm_tile_server", server_url, last_error, optional=True)
            if not (retryable and attempt <= client.retries):
                break
            client._sleep_backoff(attempt)
        except (urllib.error.URLError, TimeoutError, ExternalRequestError) as exc:
            last_error = str(exc)
            sources.note_error("osm_tile_server", server_url, last_error, optional=True)
            if attempt > client.retries:
                break
            client._sleep_backoff(attempt)

    try:
        error_cache_file.parent.mkdir(parents=True, exist_ok=True)
        error_cache_file.write_text(
            json.dumps({"error": last_error or "Tile-Download fehlgeschlagen", "ts": utc_now_iso()}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass
    return None, False, last_error or "Tile-Download fehlgeschlagen"


def _draw_marker_symbol(
    ctx: Any,
    x: float,
    y: float,
    kind: str,
    color_hex: str,
    glyph: Optional[str] = None,
) -> None:
    color = color_hex.lstrip("#")
    if len(color) != 6:
        color = "444444"
    r = int(color[0:2], 16) / 255.0
    g = int(color[2:4], 16) / 255.0
    b = int(color[4:6], 16) / 255.0

    ctx.set_source_rgba(1, 1, 1, 0.98)
    ctx.arc(x, y, 7.6, 0, math.tau)
    ctx.fill_preserve()
    ctx.set_source_rgba(0.08, 0.08, 0.08, 0.62)
    ctx.set_line_width(1.05)
    ctx.stroke()

    ctx.set_source_rgba(r, g, b, 0.98)
    if kind == "triangle":
        ctx.move_to(x, y - 5.0)
        ctx.line_to(x - 5.0, y + 3.7)
        ctx.line_to(x + 5.0, y + 3.7)
        ctx.close_path()
        ctx.fill()
    elif kind == "square":
        ctx.rectangle(x - 4.1, y - 4.1, 8.2, 8.2)
        ctx.fill()
    elif kind == "diamond":
        ctx.move_to(x, y - 5.0)
        ctx.line_to(x - 5.0, y)
        ctx.line_to(x, y + 5.0)
        ctx.line_to(x + 5.0, y)
        ctx.close_path()
        ctx.fill()
    else:
        ctx.arc(x, y, 4.5, 0, math.tau)
        ctx.fill()

    if glyph:
        glyph_char = str(glyph).strip()[:1]
        if glyph_char:
            ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(7.2)
            ext = ctx.text_extents(glyph_char)
            ctx.set_source_rgba(1, 1, 1, 0.95)
            ctx.move_to(x - ext.width / 2.0 - ext.x_bearing, y + ext.height / 2.0)
            ctx.show_text(glyph_char)


def _rects_overlap(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float], pad: float = 2.0) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 + pad < bx0 or bx1 + pad < ax0 or ay1 + pad < by0 or by1 + pad < ay0)


def _pick_zone_label_box(
    *,
    sx: float,
    sy: float,
    radius_px: float,
    text_w: float,
    text_h: float,
    occupied_boxes: List[Tuple[float, float, float, float]],
    width: int,
    height: int,
) -> Tuple[float, float, Tuple[float, float, float, float]]:
    candidates = [
        (0.0, -(radius_px + 18.0)),
        (0.0, radius_px + 10.0),
        (radius_px + 12.0 + text_w / 2.0, -3.0),
        (-(radius_px + 12.0 + text_w / 2.0), -3.0),
        (radius_px * 0.72 + text_w / 2.0, -(radius_px * 0.66)),
        (-(radius_px * 0.72 + text_w / 2.0), -(radius_px * 0.66)),
        (radius_px * 0.72 + text_w / 2.0, radius_px * 0.66),
        (-(radius_px * 0.72 + text_w / 2.0), radius_px * 0.66),
    ]

    chosen = None
    for dx, dy in candidates:
        cx = sx + dx
        cy = sy + dy
        box = (
            cx - text_w / 2.0 - 4.0,
            cy - text_h - 3.0,
            cx + text_w / 2.0 + 4.0,
            cy + 4.0,
        )
        if box[0] < 4 or box[1] < 4 or box[2] > width - 4 or box[3] > height - 32:
            continue
        if any(_rects_overlap(box, other, pad=3.0) for other in occupied_boxes):
            continue
        chosen = (cx, cy, box)
        break

    if chosen is None:
        cx = sx
        cy = sy - radius_px - 17.0
        box = (
            cx - text_w / 2.0 - 4.0,
            cy - text_h - 3.0,
            cx + text_w / 2.0 + 4.0,
            cy + 4.0,
        )
        chosen = (cx, cy, box)

    occupied_boxes.append(chosen[2])
    return chosen


def resolve_marker_screen_positions(
    *,
    markers: Sequence[Dict[str, Any]],
    zoom: int,
    origin_x: float,
    origin_y: float,
    width: int,
    height: int,
    min_sep_px: float = 13.0,
    avoid_boxes: Optional[Sequence[Tuple[float, float, float, float]]] = None,
) -> List[Dict[str, Any]]:
    placed: List[Dict[str, Any]] = []
    used: List[Tuple[float, float]] = []
    blocked_boxes = list(avoid_boxes or [])

    offsets: List[Tuple[float, float]] = [(0.0, 0.0)]
    for radius in (10.0, 16.0, 23.0):
        for angle_deg in (0, 45, 90, 135, 180, 225, 270, 315):
            rad = math.radians(angle_deg)
            offsets.append((math.cos(rad) * radius, math.sin(rad) * radius))

    for marker in markers:
        m_lat = marker.get("lat")
        m_lon = marker.get("lon")
        if m_lat is None or m_lon is None:
            continue

        try:
            px, py = latlon_to_world_px(float(m_lat), float(m_lon), zoom)
        except (TypeError, ValueError):
            continue

        base_x = px - origin_x
        base_y = py - origin_y
        chosen_x = None
        chosen_y = None

        for dx, dy in offsets:
            tx = base_x + dx
            ty = base_y + dy
            if tx < 8 or ty < 8 or tx > width - 8 or ty > height - 34:
                continue

            marker_box = (tx - 9.0, ty - 9.0, tx + 9.0, ty + 9.0)
            if any(_rects_overlap(marker_box, box, pad=2.0) for box in blocked_boxes):
                continue

            clash = False
            for ux, uy in used:
                if math.hypot(tx - ux, ty - uy) < min_sep_px:
                    clash = True
                    break
            if clash:
                continue

            chosen_x = tx
            chosen_y = ty
            break

        if chosen_x is None or chosen_y is None:
            fallback_box = (base_x - 9.0, base_y - 9.0, base_x + 9.0, base_y + 9.0)
            fallback_blocked = any(_rects_overlap(fallback_box, box, pad=1.5) for box in blocked_boxes)
            marker_priority = int(marker.get("priority") or 0)
            if fallback_blocked and marker_priority >= 2:
                continue
            chosen_x = base_x
            chosen_y = base_y

        used.append((chosen_x, chosen_y))
        row = dict(marker)
        row["screen_x"] = round(chosen_x, 2)
        row["screen_y"] = round(chosen_y, 2)
        row["screen_offset"] = [round(chosen_x - base_x, 2), round(chosen_y - base_y, 2)]
        placed.append(row)

    return placed


def render_city_ranking_map_png(
    *,
    report: Dict[str, Any],
    map_layers: Dict[str, Any],
    map_out: str,
    map_style: str,
    map_zoom: Optional[int],
    zone_radius_m: int,
    client: HttpClient,
    sources: SourceRegistry,
    width: int = DEFAULT_MAP_WIDTH,
    height: int = DEFAULT_MAP_HEIGHT,
    map_legend: str = DEFAULT_MAP_LEGEND_MODE,
) -> Dict[str, Any]:
    legend_mode = normalize_text(map_legend or DEFAULT_MAP_LEGEND_MODE)
    if legend_mode not in {"auto", "on", "off"}:
        legend_mode = DEFAULT_MAP_LEGEND_MODE
    effective_legend_mode = legend_mode
    if legend_mode == "auto":
        effective_legend_mode = "on" if width >= 560 else "off"

    if not CAIRO_AVAILABLE:
        style = canonical_map_style(map_style)
        style_cfg = MAP_STYLE_CONFIG.get(style) or MAP_STYLE_CONFIG[DEFAULT_MAP_STYLE]
        return {
            "status": "failed",
            "map_png_path": None,
            "style": style,
            "requested_style": style,
            "fallback_applied": False,
            "fallback_reason": None,
            "zoom": map_zoom,
            "warnings": ["PNG-Rendering nicht verfügbar (pycairo fehlt)."],
            "tile_stats": {"requested": 0, "cache_hits": 0, "downloaded": 0, "failed": 0},
            "map_legend_mode": effective_legend_mode,
            "attribution": style_cfg.get("attribution"),
            "provider": style_cfg.get("provider"),
            "license_note": style_cfg.get("license_note"),
        }

    style = canonical_map_style(map_style)
    requested_style = style
    style_cfg = MAP_STYLE_CONFIG.get(style) or MAP_STYLE_CONFIG[DEFAULT_MAP_STYLE]

    out_path = Path(map_out).expanduser()
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    vp = map_layers.get("viewport") or {}
    min_lat = float(vp.get("min_lat") or 47.0)
    min_lon = float(vp.get("min_lon") or 8.0)
    max_lat = float(vp.get("max_lat") or (min_lat + 0.02))
    max_lon = float(vp.get("max_lon") or (min_lon + 0.02))

    warnings: List[str] = list(map_layers.get("warnings") or [])

    if map_zoom is None:
        zoom = pick_zoom_for_bbox(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            width=width,
            height=height,
            padding=DEFAULT_MAP_PADDING,
            min_zoom=10,
            max_zoom=18,
        )
    else:
        zoom = int(clamp(float(map_zoom), 9, 19))

    style_max_zoom = int(style_cfg.get("max_zoom") or 19)
    if zoom > style_max_zoom:
        warnings.append(
            f"Gewählter Kartenstil '{style}' unterstützt max. Zoom {style_max_zoom}; Zoom wurde angepasst."
        )
        zoom = style_max_zoom

    x_min, y_max = latlon_to_world_px(min_lat, min_lon, zoom)
    x_max, y_min = latlon_to_world_px(max_lat, max_lon, zoom)
    center_x = (x_min + x_max) / 2.0
    center_y = (y_min + y_max) / 2.0
    origin_x = center_x - (width / 2.0)
    origin_y = center_y - (height / 2.0)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    ctx.set_source_rgb(0.94, 0.95, 0.96)
    ctx.paint()

    tile_x0 = int(math.floor(origin_x / 256.0))
    tile_y0 = int(math.floor(origin_y / 256.0))
    tile_x1 = int(math.floor((origin_x + width) / 256.0))
    tile_y1 = int(math.floor((origin_y + height) / 256.0))

    world_n = 2 ** zoom
    tile_ttl_s = max(6 * 3600.0, float(client.cache_ttl_seconds) * 8)

    def _paint_tiles(active_style: str) -> Tuple[Dict[str, int], List[str], int]:
        local_stats = {"requested": 0, "cache_hits": 0, "downloaded": 0, "failed": 0}
        local_warnings: List[str] = []
        loaded = 0

        for tile_y in range(tile_y0, tile_y1 + 1):
            if tile_y < 0 or tile_y >= world_n:
                continue
            for raw_tile_x in range(tile_x0, tile_x1 + 1):
                tile_x = raw_tile_x % world_n
                local_stats["requested"] += 1
                tile_path, was_cached, err = _fetch_osm_tile_png(
                    client=client,
                    sources=sources,
                    style=active_style,
                    zoom=zoom,
                    tile_x=tile_x,
                    tile_y=tile_y,
                    min_delay_s=DEFAULT_TILE_MIN_DELAY,
                    tile_ttl_s=tile_ttl_s,
                )

                draw_x = raw_tile_x * 256.0 - origin_x
                draw_y = tile_y * 256.0 - origin_y
                if tile_path and tile_path.exists():
                    try:
                        tile_surface = cairo.ImageSurface.create_from_png(str(tile_path))
                        ctx.set_source_surface(tile_surface, draw_x, draw_y)
                        ctx.paint()
                        loaded += 1
                        if was_cached:
                            local_stats["cache_hits"] += 1
                        else:
                            local_stats["downloaded"] += 1
                    except Exception as ex:
                        local_stats["failed"] += 1
                        ctx.set_source_rgba(0.90, 0.90, 0.90, 0.85)
                        ctx.rectangle(draw_x, draw_y, 256, 256)
                        ctx.fill()
                        local_warnings.append(f"Tile-Dekodierung fehlgeschlagen ({active_style} {tile_x}/{tile_y}): {ex}")
                else:
                    local_stats["failed"] += 1
                    ctx.set_source_rgba(0.92, 0.92, 0.92, 0.9)
                    ctx.rectangle(draw_x, draw_y, 256, 256)
                    ctx.fill()
                    if err:
                        local_warnings.append(f"Tile fehlt ({active_style} {tile_x}/{tile_y}): {err}")

        return local_stats, local_warnings, loaded

    tile_stats, tile_warnings, loaded_tiles = _paint_tiles(style)
    warnings.extend(tile_warnings)

    fallback_applied = False
    fallback_reason = None
    effective_style = style

    if loaded_tiles == 0 and style != DEFAULT_MAP_STYLE:
        fallback_style = str(style_cfg.get("fallback_style") or DEFAULT_MAP_STYLE)
        if fallback_style != style and fallback_style in MAP_STYLE_CONFIG:
            fallback_applied = True
            fallback_reason = (
                f"Kein Tile für Stil '{style}' geladen; Fallback auf '{fallback_style}' aktiviert."
            )
            warnings.append(fallback_reason)

            ctx.set_source_rgb(0.94, 0.95, 0.96)
            ctx.paint()

            fb_stats, fb_warnings, fb_loaded = _paint_tiles(fallback_style)
            warnings.extend(fb_warnings)
            tile_stats = {
                key: int(tile_stats.get(key, 0)) + int(fb_stats.get(key, 0))
                for key in {"requested", "cache_hits", "downloaded", "failed"}
            }

            if fb_loaded > 0:
                effective_style = fallback_style
                style_cfg = MAP_STYLE_CONFIG.get(effective_style) or MAP_STYLE_CONFIG[DEFAULT_MAP_STYLE]
            else:
                warnings.append("Fallback-Kartenstil konnte ebenfalls keine Tiles laden.")

    degradation_reasons: List[str] = []
    if tile_stats["downloaded"] == 0 and tile_stats["cache_hits"] == 0:
        warnings.append("Basiskarte nicht geladen; Darstellung zeigt nur analytische Overlay-Layer.")
        degradation_reasons.append("no_base_tiles")
    if tile_stats.get("failed", 0) > 0:
        degradation_reasons.append("tile_failures")
    if fallback_applied:
        degradation_reasons.append("style_fallback")

    occupied_label_boxes: List[Tuple[float, float, float, float]] = []
    for zone in map_layers.get("zones") or []:
        center = zone.get("center") or {}
        z_lat = center.get("lat")
        z_lon = center.get("lon")
        if z_lat is None or z_lon is None:
            continue
        px, py = latlon_to_world_px(float(z_lat), float(z_lon), zoom)
        sx = px - origin_x
        sy = py - origin_y

        mpp = meters_per_pixel(float(z_lat), zoom)
        radius_px = clamp(float(zone_radius_m) / max(mpp, 0.4), 18, 150)
        style_meta = zone.get("style") or {}
        fill_rgb = _hex_to_rgb_tuple(str(style_meta.get("fill") or zone_score_color(float(zone.get("overall_score") or 0.0))))
        stroke_rgb = _hex_to_rgb_tuple(str(style_meta.get("stroke") or "#212121"))
        fill_alpha = clamp(float(style_meta.get("opacity") or 0.24), 0.12, 0.4)
        stroke_w = clamp(float(style_meta.get("stroke_width") or 1.2), 1.0, 3.0)

        ctx.set_source_rgba(fill_rgb[0], fill_rgb[1], fill_rgb[2], fill_alpha)
        ctx.arc(sx, sy, radius_px, 0, math.tau)
        ctx.fill_preserve()
        ctx.set_source_rgba(stroke_rgb[0], stroke_rgb[1], stroke_rgb[2], 0.86)
        ctx.set_line_width(stroke_w)
        ctx.stroke()

        if zone.get("is_target_nearest"):
            ctx.set_source_rgba(0.05, 0.28, 0.65, 0.55)
            ctx.set_line_width(1.5)
            ctx.arc(sx, sy, radius_px + 5.5, 0, math.tau)
            ctx.stroke()

        label = f"{zone.get('zone_code')} {int(round(float(zone.get('overall_score') or 0))):02d}"
        if zone.get("is_target_nearest"):
            label += " ★"
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(12)
        ext = ctx.text_extents(label)

        text_x, text_y, box = _pick_zone_label_box(
            sx=sx,
            sy=sy,
            radius_px=radius_px,
            text_w=ext.width,
            text_h=ext.height,
            occupied_boxes=occupied_label_boxes,
            width=width,
            height=height,
        )

        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.rectangle(box[0], box[1], box[2] - box[0], box[3] - box[1])
        ctx.fill()
        ctx.set_source_rgba(0.05, 0.05, 0.05, 0.95)
        ctx.move_to(text_x - ext.width / 2 - ext.x_bearing, text_y)
        ctx.show_text(label)

    markers_with_screen = resolve_marker_screen_positions(
        markers=map_layers.get("markers") or [],
        zoom=zoom,
        origin_x=origin_x,
        origin_y=origin_y,
        width=width,
        height=height,
        min_sep_px=14.0 if width < 760 else 12.0,
        avoid_boxes=occupied_label_boxes,
    )
    for marker in markers_with_screen:
        _draw_marker_symbol(
            ctx,
            float(marker.get("screen_x") or 0.0),
            float(marker.get("screen_y") or 0.0),
            str(marker.get("shape") or "circle"),
            str(marker.get("color") or "#424242"),
            str(marker.get("glyph") or "")[:1],
        )

    anchor = report.get("city") or {}
    if anchor.get("lat") is not None and anchor.get("lon") is not None:
        ax, ay = latlon_to_world_px(float(anchor.get("lat")), float(anchor.get("lon")), zoom)
        sx = ax - origin_x
        sy = ay - origin_y
        ctx.set_source_rgba(0.05, 0.2, 0.65, 0.95)
        ctx.arc(sx, sy, 5.2, 0, math.tau)
        ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.95)
        ctx.arc(sx, sy, 2.0, 0, math.tau)
        ctx.fill()

    header_h = 90 if width >= 760 else 108
    header_w = min(width - 28, 500 if width >= 760 else width - 28)
    ctx.set_source_rgba(1, 1, 1, 0.82)
    ctx.rectangle(14, 14, header_w, header_h)
    ctx.fill()
    ctx.set_source_rgba(0.06, 0.06, 0.06, 0.92)
    ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(15 if width >= 760 else 14)
    title = f"City-Ranking Karte: {anchor.get('query') or 'Stadt'}"
    ctx.move_to(24, 36)
    ctx.show_text(title)
    ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(11.5 if width >= 760 else 11)
    ctx.move_to(24, 55)
    ctx.show_text("Farbbänder zeigen Score-Zonen (insb. differenziert im Mittelbereich).")
    target_meta = map_layers.get("target") or {}
    if target_meta and target_meta.get("label"):
        ctx.move_to(24, 73)
        ctx.show_text(f"Zieladresse: {str(target_meta.get('label'))[:70]}")
        ctx.move_to(24, 89)
        ctx.show_text("Hinweis: Indikativ, evidenzbasiert; keine amtliche Gefahrenkarte")
    else:
        ctx.move_to(24, 73)
        ctx.show_text("Hinweis: Indikativ, evidenzbasiert; keine amtliche Gefahrenkarte")

    if effective_legend_mode == "on":
        legend = map_layers.get("legend") or {}
        compact_legend = width < 900
        panel_w = 270 if compact_legend else 330
        panel_x = max(12, width - panel_w - 14)
        panel_y = 14
        panel_h = 176 if compact_legend else 214
        ctx.set_source_rgba(1, 1, 1, 0.84)
        ctx.rectangle(panel_x, panel_y, panel_w, panel_h)
        ctx.fill()

        ctx.set_source_rgba(0.08, 0.08, 0.08, 0.95)
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(12)
        ctx.move_to(panel_x + 12, panel_y + 18)
        ctx.show_text("Legende")

        score_scale = list(legend.get("score_scale") or [])
        row_y = panel_y + 36
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(10.5)
        for row in score_scale[: (4 if compact_legend else 6)]:
            col = _hex_to_rgb_tuple(str(row.get("color") or "#999999"))
            ctx.set_source_rgba(col[0], col[1], col[2], 0.96)
            ctx.rectangle(panel_x + 12, row_y - 9, 12, 12)
            ctx.fill()
            ctx.set_source_rgba(0.08, 0.08, 0.08, 0.95)
            ctx.move_to(panel_x + 30, row_y)
            ctx.show_text(f"{row.get('min')}-{row.get('max')}: {row.get('label')}")
            row_y += 16

        marker_legend = legend.get("marker_kinds") or {}
        marker_items = [marker_legend.get(k) for k in ["target_address", "transit_hub", "safety_service", "traffic_axis"] if marker_legend.get(k)]
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(10.5)
        ctx.move_to(panel_x + 12, row_y + 4)
        ctx.show_text("Marker")
        row_y += 18
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(10)
        for item in marker_items[:4]:
            glyph = str(item.get("glyph") or "•")[:1]
            ctx.move_to(panel_x + 12, row_y)
            ctx.show_text(f"{glyph} {str(item.get('label') or '')[:28]}")
            row_y += 14

    if warnings:
        ctx.set_source_rgba(1, 1, 1, 0.84)
        warn_h = 76 if width >= 760 else 92
        ctx.rectangle(14, height - (warn_h + 44), min(width - 28, 720), warn_h)
        ctx.fill()
        ctx.set_source_rgba(0.35, 0.12, 0.12, 0.95)
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(12)
        ctx.move_to(24, height - (warn_h + 22))
        ctx.show_text("Unsicherheit / Datenlage:")
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(11)
        for idx, note in enumerate(warnings[:3 if width < 760 else 2]):
            ctx.move_to(24, height - (warn_h + 4) + idx * 16)
            ctx.show_text(f"- {str(note)[:112]}")

    attribution = (
        f"{style_cfg.get('attribution')} | Tiles: {style_cfg.get('provider')} | "
        f"Generiert: {utc_now_iso()} | Zoom {zoom}"
    )
    ctx.set_source_rgba(1, 1, 1, 0.85)
    ctx.rectangle(0, height - 28, width, 28)
    ctx.fill()
    ctx.set_source_rgba(0.05, 0.05, 0.05, 0.95)
    ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(10.3)
    ctx.move_to(10, height - 10)
    ctx.show_text(attribution)

    surface.write_to_png(str(out_path))

    status = "ok"
    if degradation_reasons or warnings:
        status = "degraded"

    return {
        "status": status,
        "map_png_path": str(out_path),
        "style": effective_style,
        "requested_style": requested_style,
        "fallback_applied": fallback_applied,
        "fallback_reason": fallback_reason,
        "zoom": zoom,
        "tile_stats": tile_stats,
        "warnings": warnings[:8],
        "degradation_reasons": sorted(set(degradation_reasons)),
        "map_legend_mode": effective_legend_mode,
        "render_context": {
            "width": width,
            "height": height,
            "tile_x_range": [tile_x0, tile_x1],
            "tile_y_range": [tile_y0, tile_y1],
            "legend_mode": effective_legend_mode,
        },
        "attribution": style_cfg.get("attribution"),
        "provider": style_cfg.get("provider"),
        "license_note": style_cfg.get("license_note"),
    }


def build_city_ranking_report(
    city: str,
    *,
    top_n: int,
    grid_size: int,
    zone_spacing_m: int,
    zone_radius_m: int,
    timeout: int,
    retries: int,
    backoff_seconds: float,
    min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL,
    cache_ttl_seconds: float,
    intelligence_mode: str,
    area_weights: Dict[str, float],
    map_png: bool = False,
    map_out: Optional[str] = None,
    map_style: str = DEFAULT_MAP_STYLE,
    map_zoom: Optional[int] = None,
    map_legend: str = DEFAULT_MAP_LEGEND_MODE,
    target_address: Optional[str] = None,
    client: Optional[HttpClient] = None,
) -> Dict[str, Any]:
    mode = intelligence_mode if intelligence_mode in INTELLIGENCE_MODES else "extended"
    grid_n = int(clamp(float(grid_size), 1, 7))
    if grid_n % 2 == 0:
        grid_n += 1

    top_n = max(1, min(int(top_n), grid_n * grid_n))
    spacing = int(clamp(float(zone_spacing_m), 180.0, 1600.0))
    radius = int(clamp(float(zone_radius_m), 120.0, 1400.0))

    client = client or HttpClient(
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff_seconds,
        min_request_interval_seconds=max(0.0, min_request_interval_seconds),
        cache_ttl_seconds=max(0.0, cache_ttl_seconds),
    )
    sources = SourceRegistry()

    city_anchor = fetch_city_anchor(client, sources, city=city)
    city_news_query = f'"{city_anchor.get("query")}" (Einbruch OR Übergriff OR Gewalt OR Raub OR Polizei OR Delikt)'
    city_news_payload = fetch_google_news_rss(
        client,
        sources,
        query=city_news_query,
        limit=14,
        source_name="google_news_rss_city",
    )
    city_safety = build_city_incident_signals(
        city_name=str(city_anchor.get("query") or city),
        news_payload=city_news_payload,
        max_items=12,
        mode=mode,
    )

    target_context: Optional[Dict[str, Any]] = None
    if target_address:
        target_anchor = fetch_target_address_anchor(
            client,
            sources,
            target_address=target_address,
            city_hint=str(city_anchor.get("query") or city),
        )
        if target_anchor:
            target_context = {
                "query": target_address,
                "label": target_anchor.get("label"),
                "lat": target_anchor.get("lat"),
                "lon": target_anchor.get("lon"),
                "score": target_anchor.get("score"),
                "feature_id": target_anchor.get("feature_id"),
                "source_url": target_anchor.get("source_url"),
                "nearest_zone_code": None,
                "nearest_zone_distance_m": None,
            }
        else:
            target_context = {
                "query": target_address,
                "label": None,
                "lat": None,
                "lon": None,
                "nearest_zone_code": None,
                "nearest_zone_distance_m": None,
            }

    norm_weights = normalize_weight_profile(area_weights)
    half = grid_n // 2
    lat0 = float(city_anchor["lat"])
    lon0 = float(city_anchor["lon"])

    zones: List[Dict[str, Any]] = []
    zone_payload_cache: Dict[Tuple[float, float, int], Dict[str, Any]] = {}
    overpass_max_items = 220 if grid_n <= 3 else 180
    if mode == "risk":
        overpass_max_items = min(260, overpass_max_items + 20)

    for row in range(-half, half + 1):
        for col in range(-half, half + 1):
            north_m = -row * spacing
            east_m = col * spacing
            lat = lat0 + (north_m / 111320.0)
            lon = lon0 + (east_m / (111320.0 * max(math.cos(math.radians(lat0)), 0.2)))

            zone_name = zone_compass_label(row, col)
            zone_code = f"Z{row + half + 1}{col + half + 1}"

            zone_cache_key = (round(lat, 5), round(lon, 5), int(radius))
            overpass = zone_payload_cache.get(zone_cache_key)
            if overpass is None:
                overpass = fetch_zone_signals_overpass(
                    client,
                    sources,
                    lat=lat,
                    lon=lon,
                    radius_m=radius,
                    max_items=overpass_max_items,
                )
                zone_payload_cache[zone_cache_key] = overpass
            elements = overpass.get("elements") or []
            source_url = overpass.get("source_url")

            points = {
                "transit": 0.0,
                "shopping": 0.0,
                "green": 0.0,
                "nightlife": 0.0,
                "major_road": 0.0,
                "police": 0.0,
                "food": 0.0,
            }
            samples: Dict[str, List[Dict[str, Any]]] = {k: [] for k in points.keys()}

            def add_sample(bucket: str, item: Dict[str, Any]) -> None:
                arr = samples.get(bucket)
                if arr is None:
                    return
                if len(arr) >= 4:
                    return
                arr.append(item)

            for element in elements:
                distance = float(element.get("distance_m") or radius)
                prox = clamp(1.0 - (distance / max(float(radius), 1.0)), 0.0, 1.0)
                if prox <= 0:
                    continue
                tags = element.get("tags") or {}
                if not isinstance(tags, dict):
                    continue

                amenity = str(tags.get("amenity") or "")
                shop = str(tags.get("shop") or "")
                leisure = str(tags.get("leisure") or "")
                ptransport = str(tags.get("public_transport") or "")
                railway = str(tags.get("railway") or "")
                highway = str(tags.get("highway") or "")
                landuse = str(tags.get("landuse") or "")
                natural = str(tags.get("natural") or "")

                item = {
                    "name": element.get("name"),
                    "distance_m": distance,
                    "lat": element.get("lat"),
                    "lon": element.get("lon"),
                    "tags": tags,
                    "url": source_url,
                    "observed_at": utc_now_iso(),
                }

                if amenity in {"bus_station"}:
                    points["transit"] += 11.0 * prox
                    add_sample("transit", item)
                if ptransport in {"platform", "station", "stop_position", "stop_area"}:
                    points["transit"] += 7.5 * prox
                    add_sample("transit", item)
                if railway in {"station", "halt", "tram_stop"}:
                    points["transit"] += 13.5 * prox
                    add_sample("transit", item)
                if highway in {"bus_stop"}:
                    points["transit"] += 6.2 * prox
                    add_sample("transit", item)

                if shop and shop not in {"vacant", "no"}:
                    points["shopping"] += (7.0 if shop in {"supermarket", "mall", "convenience"} else 4.8) * prox
                    add_sample("shopping", item)
                if amenity in {"pharmacy", "marketplace", "post_office", "bank"}:
                    points["shopping"] += 4.4 * prox
                    add_sample("shopping", item)

                if leisure in {"park", "garden", "nature_reserve", "playground"}:
                    points["green"] += 9.0 * prox
                    add_sample("green", item)
                if landuse in {"forest", "grass", "recreation_ground", "meadow"}:
                    points["green"] += 8.0 * prox
                    add_sample("green", item)
                if natural in {"wood", "grassland", "scrub", "tree_row"}:
                    points["green"] += 7.0 * prox
                    add_sample("green", item)

                if amenity in {"bar", "pub", "nightclub", "casino"}:
                    points["nightlife"] += 12.0 * prox
                    add_sample("nightlife", item)
                elif amenity in {"restaurant", "fast_food", "cafe", "cinema", "theatre"}:
                    points["nightlife"] += 5.8 * prox
                    points["food"] += 4.8 * prox
                    add_sample("nightlife", item)
                    add_sample("food", item)
                if leisure in {"stadium", "sports_centre"}:
                    points["nightlife"] += 7.5 * prox
                    add_sample("nightlife", item)

                if highway in {"motorway", "trunk", "primary"}:
                    points["major_road"] += 14.5 * prox
                    add_sample("major_road", item)
                elif highway in {"secondary"}:
                    points["major_road"] += 9.0 * prox
                    add_sample("major_road", item)
                elif highway in {"tertiary"}:
                    points["major_road"] += 5.2 * prox
                    add_sample("major_road", item)

                if amenity in {"police", "fire_station"}:
                    points["police"] += 9.0 * prox
                    add_sample("police", item)

            indices = {
                "transit": points_to_score(points["transit"], 24),
                "shopping": points_to_score(points["shopping"], 26),
                "green": points_to_score(points["green"], 24),
                "nightlife": points_to_score(points["nightlife"], 21),
                "major_road": points_to_score(points["major_road"], 17),
                "police": points_to_score(points["police"], 10),
                "food": points_to_score(points["food"], 20),
            }

            score_pack = compute_zone_scores_from_indices(
                indices=indices,
                city_incident_risk=float(city_safety.get("incident_risk_score") or 48),
                city_incident_status=str(city_safety.get("status") or "no_data"),
                mode=mode,
                local_signal_count=len(elements),
            )
            metrics = score_pack["metrics"]

            weight_model = build_zone_weight_model(
                zone_index=len(zones),
                zone_code=zone_code,
                metrics=metrics,
                normalized_weights=norm_weights,
                samples=samples,
                fallback_url=source_url,
            )
            overall = clamp(
                sum(float(c.get("weighted_points") or 0.0) for c in (weight_model.get("contributions") or [])),
                0.0,
                100.0,
            )

            traffic = zone_traffic_light(overall)

            if not elements:
                zone_status = "sparse_data"
                quality_note = "Keine POI-Signale aus Community-Quelle; Zone konservativ neutral bewertet."
            elif len(elements) < 10:
                zone_status = "thin_data"
                quality_note = "Wenige Signale; Interpretation mit Vorsicht."
            else:
                zone_status = "ok"
                quality_note = "Ausreichende Signaldichte für indikative Mikro-Lagenbewertung."

            reasons: List[Dict[str, Any]] = []

            def add_reason(metric_key: str, text: str, confidence: float, evidence: Sequence[Dict[str, Any]]) -> None:
                reasons.append(
                    {
                        "metric": metric_key,
                        "text": text,
                        "confidence": round(confidence, 2),
                        "status": classify_statement_status(confidence, evidence),
                        "evidence": list(evidence),
                    }
                )

            for metric_key, source_bucket in [
                ("oev", "transit"),
                ("einkauf", "shopping"),
                ("gruen", "green"),
                ("nachtaktivitaet", "nightlife"),
                ("ruhe", "major_road"),
            ]:
                metric_val = float(metrics.get(metric_key, 0.0))
                sample = samples.get(source_bucket) or []
                if metric_key == "ruhe":
                    sample = (samples.get("major_road") or []) + (samples.get("nightlife") or [])
                if metric_val >= 68:
                    conf = clamp(0.48 + min(0.24, len(sample) * 0.04), 0.42, 0.8)
                    ev = [
                        evidence_item(
                            source="osm_area_profile_overpass",
                            confidence=conf,
                            url=(sample[0].get("url") if sample else source_url),
                            observed_at=(sample[0].get("observed_at") if sample else utc_now_iso()),
                            snippet=f"{zone_code}:{metric_key}={metric_val:.0f}",
                            field_path=f"zones[{len(zones)}].metrics.{metric_key}",
                        )
                    ]
                    add_reason(metric_key, f"{metric_key} überdurchschnittlich ({metric_val:.0f}/100)", conf, ev)
                elif metric_val <= 38:
                    conf = clamp(0.44 + min(0.22, len(sample) * 0.03), 0.4, 0.74)
                    ev = [
                        evidence_item(
                            source="osm_area_profile_overpass",
                            confidence=conf,
                            url=(sample[0].get("url") if sample else source_url),
                            observed_at=(sample[0].get("observed_at") if sample else utc_now_iso()),
                            snippet=f"{zone_code}:{metric_key}={metric_val:.0f}",
                            field_path=f"zones[{len(zones)}].metrics.{metric_key}",
                        )
                    ]
                    add_reason(metric_key, f"{metric_key} unterdurchschnittlich ({metric_val:.0f}/100)", conf, ev)

            zone_security = build_zone_security_signals(
                zone_index=len(zones),
                zone_code=zone_code,
                city_safety=city_safety,
                city_news_payload=city_news_payload,
                local_samples=samples,
                local_indices=score_pack["indices"],
                local_signal_count=len(elements),
                zone_status=zone_status,
                fallback_url=source_url,
            )

            safety_conf = 0.62 if city_safety.get("status") == "ok" else 0.41
            safety_ev = [
                evidence_item(
                    source="google_news_rss_city",
                    confidence=safety_conf,
                    url=city_news_payload.get("source_url"),
                    snippet=f"city_risk={city_safety.get('incident_risk_score')}",
                    field_path=f"zones[{len(zones)}].metrics.sicherheit",
                ),
                evidence_item(
                    source="osm_area_profile_overpass",
                    confidence=min(0.74, safety_conf + 0.08),
                    url=source_url,
                    snippet=f"local_safety_risk={score_pack['indices'].get('local_safety_risk')}",
                    field_path=f"zones[{len(zones)}].indices.local_safety_risk",
                ),
            ]
            add_reason(
                "sicherheit",
                (
                    "Sicherheitsindikator konservativ (Web-Incident-Hinweise + lokale Umfeldsignale)."
                    if city_safety.get("status") == "ok"
                    else "Sicherheitsindikator mit hoher Unsicherheit (News-Signale unvollständig)."
                )
                + f" {zone_security['overview'].get('headline')}",
                safety_conf,
                safety_ev,
            )

            zone_uncertainty = derive_zone_uncertainty(
                zone_status=zone_status,
                safety_uncertainty=score_pack.get("safety_uncertainty") or "indiz",
                contradiction_index=float((score_pack.get("indices") or {}).get("contradiction_index") or 0.0),
                poi_signal_count=len(elements),
            )

            if zone_uncertainty["status"] == "unklar":
                add_reason(
                    "unsicherheit",
                    f"Unsicherheitsflag: {zone_uncertainty['reason']}",
                    0.43,
                    [
                        evidence_item(
                            source="osm_area_profile_overpass",
                            confidence=0.43,
                            url=source_url,
                            snippet=f"{zone_code}:uncertainty={zone_uncertainty['status']}",
                            field_path=f"zones[{len(zones)}].zone_uncertainty",
                        )
                    ],
                )

            for driver in (weight_model.get("drivers") or [])[:3]:
                add_reason(
                    str(driver.get("metric") or "gewichtung"),
                    str(driver.get("text") or "Gewichtstreiber aus Zonenmodell."),
                    float(driver.get("confidence") or 0.44),
                    driver.get("evidence") or [],
                )

            zones.append(
                {
                    "zone_code": zone_code,
                    "zone_name": zone_name,
                    "row_offset": row,
                    "col_offset": col,
                    "center": {"lat": round(lat, 6), "lon": round(lon, 6)},
                    "distance_to_target_m": None,
                    "is_target_nearest": False,
                    "overall_score": round(overall, 2),
                    "traffic_light": traffic,
                    "status": zone_status,
                    "quality_note": quality_note,
                    "metrics": metrics,
                    "indices": score_pack["indices"],
                    "risk_model": {
                        "city_weight": 0.52 if mode == "risk" else 0.44,
                        "risk_pressure": score_pack["indices"].get("risk_pressure"),
                        "protective_capacity": score_pack["indices"].get("protective_capacity"),
                        "contradiction_index": score_pack["indices"].get("contradiction_index"),
                        "local_safety_risk": score_pack["indices"].get("local_safety_risk"),
                        "city_incident_risk": score_pack["indices"].get("city_incident_risk"),
                        "formula": "safety = 100 - blend(local_risk, city_risk) mit Neutralitätszug bei Widerspruch",
                    },
                    "safety_uncertainty": score_pack["safety_uncertainty"],
                    "zone_uncertainty": zone_uncertainty,
                    "weights_applied": norm_weights,
                    "weight_model": weight_model,
                    "poi_signal_count": len(elements),
                    "sample_signals": {k: v[:3] for k, v in samples.items() if v},
                    "security_facts": zone_security.get("facts") or [],
                    "security_signals": zone_security.get("signals") or [],
                    "security_overview": zone_security.get("overview") or {},
                    "security_evidence_split": zone_security.get("evidence_split") or {},
                    "reasons": reasons[:10],
                    "sources": {
                        "osm_area_profile_overpass": {
                            "status": "ok" if elements else "no_data",
                            "url": source_url,
                            "records": len(elements),
                        },
                        "google_news_rss_city": {
                            "status": city_safety.get("status"),
                            "url": city_news_payload.get("source_url"),
                            "relevant_events": city_safety.get("relevant_event_count"),
                        },
                    },
                }
            )

    zones.sort(
        key=lambda z: (
            float(z.get("overall_score") or 0.0),
            float((z.get("metrics") or {}).get("sicherheit") or 0.0),
            float((z.get("metrics") or {}).get("ruhe") or 0.0),
        ),
        reverse=True,
    )

    for idx, zone in enumerate(zones, start=1):
        zone["rank"] = idx

    if target_context and target_context.get("lat") is not None and target_context.get("lon") is not None:
        t_lat = float(target_context.get("lat"))
        t_lon = float(target_context.get("lon"))
        nearest_zone = None
        nearest_dist = None
        for zone in zones:
            center = zone.get("center") or {}
            if center.get("lat") is None or center.get("lon") is None:
                continue
            dist_m = haversine_distance_m(t_lat, t_lon, float(center.get("lat")), float(center.get("lon")))
            zone["distance_to_target_m"] = round(dist_m, 1)
            if nearest_dist is None or dist_m < nearest_dist:
                nearest_dist = dist_m
                nearest_zone = zone

        if nearest_zone is not None:
            nearest_zone["is_target_nearest"] = True
            target_context["nearest_zone_code"] = nearest_zone.get("zone_code")
            target_context["nearest_zone_rank"] = nearest_zone.get("rank")
            target_context["nearest_zone_distance_m"] = round(float(nearest_dist or 0.0), 1)

    top = zones[:top_n]
    heatmap_text = render_city_heatmap(zones, grid_n)

    traffic_counts = {"green": 0, "yellow": 0, "red": 0}
    uncertainty_counts = {"gesichert": 0, "indiz": 0, "unklar": 0}
    for zone in zones:
        traffic_counts[str(zone.get("traffic_light") or "yellow")] = (
            traffic_counts.get(str(zone.get("traffic_light") or "yellow"), 0) + 1
        )
        uncertainty_key = str((zone.get("zone_uncertainty") or {}).get("status") or "indiz")
        if uncertainty_key not in uncertainty_counts:
            uncertainty_counts[uncertainty_key] = 0
        uncertainty_counts[uncertainty_key] += 1

    executive_top = []
    for zone in top[: min(5, len(top))]:
        reasons = zone.get("reasons") or []
        weight_drivers = (zone.get("weight_model") or {}).get("drivers") or []
        executive_top.append(
            {
                "zone": zone.get("zone_code"),
                "name": zone.get("zone_name"),
                "score": zone.get("overall_score"),
                "traffic_light": zone.get("traffic_light"),
                "safety_uncertainty": zone.get("safety_uncertainty"),
                "zone_uncertainty": (zone.get("zone_uncertainty") or {}).get("status"),
                "uncertainty_reason": (zone.get("zone_uncertainty") or {}).get("reason"),
                "contradiction_index": (zone.get("risk_model") or {}).get("contradiction_index"),
                "distance_to_target_m": zone.get("distance_to_target_m"),
                "is_target_nearest": bool(zone.get("is_target_nearest")),
                "reasons": [r.get("text") for r in reasons[:3]],
                "driver_reasons": [d.get("text") for d in weight_drivers[:2]],
                "security_signals": (zone.get("security_overview") or {}).get("headline"),
                "security_facts": [f.get("text") for f in (zone.get("security_facts") or [])[:2]],
                "security_evidence_split": zone.get("security_evidence_split") or {},
            }
        )

    avg_top_score = round(
        sum(float(z.get("overall_score") or 0.0) for z in top) / max(1, len(top)),
        2,
    )
    executive_traffic = zone_traffic_light(avg_top_score)

    recommended_zone_full = top[0] if top else None
    recommendation_explanation = build_recommendation_explanation(
        recommended_zone=recommended_zone_full,
        city_safety=city_safety,
        top_n=top_n,
        target_context=target_context,
    )

    map_layers = build_city_ranking_map_layers(
        zones=zones,
        city_anchor=city_anchor,
        zone_radius_m=radius,
        top_n=top_n,
        target_context=target_context,
    )

    map_result: Dict[str, Any] = {
        "status": "disabled",
        "map_png_path": None,
        "style": canonical_map_style(map_style),
        "requested_style": canonical_map_style(map_style),
        "fallback_applied": False,
        "fallback_reason": None,
        "zoom": map_zoom,
        "tile_stats": {"requested": 0, "cache_hits": 0, "downloaded": 0, "failed": 0},
        "warnings": [],
        "degradation_reasons": [],
        "map_legend_mode": "off",
        "render_context": {},
        "attribution": MAP_STYLE_CONFIG.get(canonical_map_style(map_style), {}).get("attribution"),
        "provider": MAP_STYLE_CONFIG.get(canonical_map_style(map_style), {}).get("provider"),
        "license_note": MAP_STYLE_CONFIG.get(canonical_map_style(map_style), {}).get("license_note"),
    }

    if map_png:
        if map_out:
            target_map_out = map_out
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            city_slug = slugify_filename(str(city_anchor.get("query") or city))
            target_map_out = str(SKILL_DIR / "output" / f"city_ranking_{city_slug}_{timestamp}.png")

        try:
            map_result = render_city_ranking_map_png(
                report={"city": city_anchor},
                map_layers=map_layers,
                map_out=target_map_out,
                map_style=map_style,
                map_zoom=map_zoom,
                zone_radius_m=radius,
                map_legend=map_legend,
                client=client,
                sources=sources,
            )
        except Exception as ex:
            map_result = {
                "status": "failed",
                "map_png_path": None,
                "style": canonical_map_style(map_style),
                "requested_style": canonical_map_style(map_style),
                "fallback_applied": False,
                "fallback_reason": None,
                "zoom": map_zoom,
                "tile_stats": {"requested": 0, "cache_hits": 0, "downloaded": 0, "failed": 0},
                "warnings": [f"Map-Rendering fehlgeschlagen: {ex}"],
                "degradation_reasons": ["render_exception"],
                "map_legend_mode": "off",
                "render_context": {},
                "attribution": MAP_STYLE_CONFIG.get(canonical_map_style(map_style), {}).get("attribution"),
                "provider": MAP_STYLE_CONFIG.get(canonical_map_style(map_style), {}).get("provider"),
                "license_note": MAP_STYLE_CONFIG.get(canonical_map_style(map_style), {}).get("license_note"),
            }

    summary_compact = {
        "mode": "city-ranking",
        "city": city_anchor.get("query"),
        "anchor": {
            "label": city_anchor.get("label"),
            "lat": city_anchor.get("lat"),
            "lon": city_anchor.get("lon"),
            "canton": city_anchor.get("canton"),
        },
        "weights": area_weights,
        "weights_normalized": norm_weights,
        "target": target_context,
        "top_zones": executive_top,
        "city_safety": {
            "status": city_safety.get("status"),
            "incident_risk_score": city_safety.get("incident_risk_score"),
            "uncertainty": city_safety.get("uncertainty"),
            "relevant_event_count": city_safety.get("relevant_event_count"),
        },
        "executive": {
            "traffic_light": executive_traffic,
            "avg_top_score": avg_top_score,
            "traffic_counts": traffic_counts,
            "uncertainty_counts": uncertainty_counts,
            "recommended_zone": (executive_top[0] if executive_top else None),
            "recommendation_explanation": recommendation_explanation,
            "fact_vs_signal_note": "Harte Fakten = beobachtete Zählwerte/Status; Signale = indikative Modelltreiber.",
            "note": "Ampel basiert auf gewichteten Zonen-Scores; Unsicherheit wird explizit als gesichert/indiz/unklar ausgewiesen.",
        },
        "heatmap": heatmap_text,
        "output": {
            "map_png_path": map_result.get("map_png_path"),
            "map_status": map_result.get("status"),
            "map_style": map_result.get("style"),
            "map_requested_style": map_result.get("requested_style"),
            "map_fallback_applied": bool(map_result.get("fallback_applied")),
            "map_fallback_reason": map_result.get("fallback_reason"),
            "map_zoom": map_result.get("zoom"),
            "map_legend_mode": map_result.get("map_legend_mode"),
            "map_degradation_reasons": map_result.get("degradation_reasons") or [],
            "map_warnings": map_result.get("warnings") or [],
        },
        "map_layers": {
            "zones": len(map_layers.get("zones") or []),
            "markers": len(map_layers.get("markers") or []),
            "uncertain_zones": uncertainty_counts.get("unklar", 0),
            "target_zone": (target_context or {}).get("nearest_zone_code"),
            "note": map_layers.get("note"),
            "warnings": map_layers.get("warnings") or [],
        },
    }

    headline = (
        f"Top {len(top)} Wohnzonen in {city_anchor.get('query')} (indikativ, konservative Sicherheitsbewertung)."
    )

    return {
        "mode": "city-ranking",
        "generated_at": utc_now_iso(),
        "city": city_anchor,
        "parameters": {
            "grid_size": grid_n,
            "zone_spacing_m": spacing,
            "zone_radius_m": radius,
            "top_n": top_n,
            "intelligence_mode": mode,
            "weights": area_weights,
            "weights_normalized": norm_weights,
            "map_png": bool(map_png),
            "map_style": map_result.get("style"),
            "map_requested_style": map_result.get("requested_style"),
            "map_zoom": map_result.get("zoom"),
            "map_legend": map_legend,
            "target_address": target_address,
        },
        "executive": {
            "headline": headline,
            "traffic_light": executive_traffic,
            "avg_top_score": avg_top_score,
            "traffic_counts": traffic_counts,
            "uncertainty_counts": uncertainty_counts,
            "recommended_zone": (executive_top[0] if executive_top else None),
            "recommendation_explanation": recommendation_explanation,
            "fact_vs_signal_note": "Harte Fakten = beobachtete Zählwerte/Status; Signale = indikative Modelltreiber.",
            "top_zones": executive_top,
            "city_safety": {
                "traffic_light": "green"
                if int(city_safety.get("incident_risk_score") or 50) < 34
                else ("yellow" if int(city_safety.get("incident_risk_score") or 50) < 67 else "red"),
                "risk_score": city_safety.get("incident_risk_score"),
                "uncertainty": city_safety.get("uncertainty"),
                "note": "Web-/Community-Signale sind indikativ, kein amtlicher Kriminalitätsdatensatz.",
            },
            "heatmap": heatmap_text,
        },
        "city_safety": city_safety,
        "target": target_context,
        "zones": zones,
        "top_zones": top,
        "heatmap_text": heatmap_text,
        "output": {
            "map_png_path": map_result.get("map_png_path"),
            "map_status": map_result.get("status"),
            "map_style": map_result.get("style"),
            "map_requested_style": map_result.get("requested_style"),
            "map_fallback_applied": bool(map_result.get("fallback_applied")),
            "map_fallback_reason": map_result.get("fallback_reason"),
            "map_zoom": map_result.get("zoom"),
            "map_legend_mode": map_result.get("map_legend_mode"),
            "map_degradation_reasons": map_result.get("degradation_reasons") or [],
        },
        "map": {
            "status": map_result.get("status"),
            "map_png_path": map_result.get("map_png_path"),
            "style": map_result.get("style"),
            "requested_style": map_result.get("requested_style"),
            "fallback_applied": bool(map_result.get("fallback_applied")),
            "fallback_reason": map_result.get("fallback_reason"),
            "zoom": map_result.get("zoom"),
            "tile_stats": map_result.get("tile_stats") or {},
            "warnings": map_result.get("warnings") or [],
            "degradation_reasons": map_result.get("degradation_reasons") or [],
            "map_legend_mode": map_result.get("map_legend_mode"),
            "render_context": map_result.get("render_context") or {},
            "attribution": map_result.get("attribution"),
            "provider": map_result.get("provider"),
            "license_note": map_result.get("license_note"),
        },
        "map_layers": map_layers,
        "sources": sources.as_dict(),
        "source_classification": source_catalog_view(sources.as_dict()),
        "summary_compact": summary_compact,
    }


def build_tenants_businesses_layer(
    *,
    pois: Sequence[Dict[str, Any]],
    source_url: Optional[str],
    tenant_limit: int,
) -> Dict[str, Any]:
    business_amenities = {
        "restaurant",
        "cafe",
        "bar",
        "pub",
        "bank",
        "pharmacy",
        "clinic",
        "dentist",
        "fast_food",
        "kindergarten",
        "school",
        "marketplace",
    }

    entities: List[Dict[str, Any]] = []
    for idx, poi in enumerate(pois):
        category = str(poi.get("category") or "")
        sub = str(poi.get("subcategory") or "")

        is_business = category in {"shop", "office", "craft"}
        if category == "amenity" and sub in business_amenities:
            is_business = True
        if not is_business:
            continue

        distance = float(poi.get("distance_m") or 999999)
        confidence = clamp(0.25 + max(0.0, (200.0 - distance) / 200.0) * 0.5, 0.2, 0.78)
        evidence = [
            evidence_item(
                source="osm_poi_overpass",
                confidence=confidence,
                url=source_url,
                snippet=f"{poi.get('name')} ({category}:{sub}) in {distance:.0f}m",
                field_path=f"intelligence.tenants_businesses.entities[{len(entities)}]",
            )
        ]
        entities.append(
            {
                "name": poi.get("name"),
                "category": category,
                "subcategory": sub,
                "distance_m": distance,
                "address_hint": poi.get("address_hint"),
                "status": classify_statement_status(confidence, evidence),
                "confidence": round(confidence, 2),
                "evidence": evidence,
            }
        )
        if len(entities) >= tenant_limit:
            break

    if not entities:
        msg = "Keine belastbaren Geschäfts-/Mieter-Signale aus zulässigen Community-POIs gefunden."
        return {
            "status": "no_data",
            "source_policy_class": "community",
            "registry_signals": {
                "status": "not_configured",
                "note": "Keine lizenzierte/amtliche Firmenregister-Quelle angebunden; daher konservativ nur POI-Indizien.",
            },
            "entities": [],
            "counts_by_category": {},
            "statements": [
                statement(
                    msg,
                    confidence=0.42,
                    evidence=[
                        evidence_item(
                            source="osm_poi_overpass",
                            confidence=0.42,
                            url=source_url,
                            snippet="Keine geeigneten POI-Datensätze",
                            field_path="intelligence.tenants_businesses.entities",
                        )
                    ],
                    field_path="intelligence.tenants_businesses",
                )
            ],
        }

    counts: Dict[str, int] = {}
    for entity in entities:
        key = f"{entity.get('category')}:{entity.get('subcategory')}"
        counts[key] = counts.get(key, 0) + 1

    avg_distance = sum(float(x.get("distance_m") or 0) for x in entities) / len(entities)
    conf = clamp(0.48 + max(0.0, (160.0 - avg_distance) / 260.0) * 0.25, 0.45, 0.76)

    summary_statement = statement(
        f"{len(entities)} potenzielle Geschäfts-/Mieter-Indizien im Nahbereich identifiziert (Community-Quelle).",
        confidence=conf,
        evidence=[
            evidence_item(
                source="osm_poi_overpass",
                confidence=conf,
                url=source_url,
                snippet="Aggregierte POI-Auswertung im Umkreis",
                field_path="intelligence.tenants_businesses.entities",
            )
        ],
        field_path="intelligence.tenants_businesses.entities",
    )

    return {
        "status": "ok",
        "source_policy_class": "community",
        "registry_signals": {
            "status": "not_configured",
            "note": "Kein direkter Handelsregister-Abzug ohne Lizenz/API-Key verwendet (Policy-konservativ).",
        },
        "entities": entities,
        "counts_by_category": counts,
        "statements": [summary_statement],
    }


def build_incidents_timeline_layer(
    *,
    news_payload: Dict[str, Any],
    address_query: str,
    max_items: int,
) -> Dict[str, Any]:
    events_in = list(news_payload.get("events") or [])[: max(0, max_items)]
    source_url = news_payload.get("source_url")

    if not events_in:
        return {
            "status": "no_data",
            "events": [],
            "statements": [
                statement(
                    "Keine aktuellen Web-/News-Hinweise zur Adresse gefunden.",
                    confidence=0.35,
                    evidence=[
                        evidence_item(
                            source="google_news_rss",
                            confidence=0.35,
                            url=source_url,
                            snippet=news_payload.get("error") or "Leere Trefferliste",
                            field_path="intelligence.incidents_timeline.events",
                        )
                    ],
                    field_path="intelligence.incidents_timeline",
                )
            ],
        }

    query_tokens = [t for t in tokenize(address_query) if len(t) >= 3]
    incident_keywords = {"brand", "feuer", "einbruch", "polizei", "unfall", "delikt", "evaku"}

    events: List[Dict[str, Any]] = []
    for idx, raw in enumerate(events_in):
        title = str(raw.get("title") or "")
        title_norm = normalize_text(title)
        token_hits = sum(1 for t in query_tokens if t in title_norm)
        keyword_hits = sum(1 for kw in incident_keywords if kw in title_norm)

        recency_bonus = 0.0
        published = raw.get("published_at")
        if published:
            try:
                dt = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
                days = max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 86400)
                recency_bonus = 0.16 if days < 30 else (0.08 if days < 180 else 0.0)
            except Exception:
                recency_bonus = 0.0

        confidence = clamp(0.25 + token_hits * 0.1 + keyword_hits * 0.08 + recency_bonus, 0.2, 0.8)
        ev = [
            evidence_item(
                source="google_news_rss",
                confidence=confidence,
                url=raw.get("url") or source_url,
                observed_at=raw.get("published_at") or utc_now_iso(),
                snippet=title,
                field_path=f"intelligence.incidents_timeline.events[{idx}]",
            )
        ]

        events.append(
            {
                "title": title,
                "date": raw.get("published_at"),
                "source": raw.get("source"),
                "url": raw.get("url"),
                "description": raw.get("description"),
                "status": classify_statement_status(confidence, ev),
                "confidence": round(confidence, 2),
                "evidence": ev,
            }
        )

    events.sort(key=lambda x: x.get("date") or "", reverse=True)
    relevant_count = sum(1 for ev in events if ev.get("confidence", 0) >= 0.55)
    layer_conf = clamp(0.4 + relevant_count * 0.08, 0.38, 0.79)

    headline = (
        f"{relevant_count} zeitnahe Incident-Indizien gefunden (Web-Hinweise, nicht amtlich verifiziert)."
        if relevant_count
        else "Nur schwache oder indirekte Web-Hinweise gefunden."
    )

    return {
        "status": "ok",
        "events": events,
        "relevant_event_count": relevant_count,
        "statements": [
            statement(
                headline,
                confidence=layer_conf,
                evidence=[
                    evidence_item(
                        source="google_news_rss",
                        confidence=layer_conf,
                        url=source_url,
                        snippet="Aggregierte News-RSS-Auswertung",
                        field_path="intelligence.incidents_timeline.events",
                    )
                ],
                field_path="intelligence.incidents_timeline",
            )
        ],
    }


def build_environment_profile_layer(
    *,
    pois: Sequence[Dict[str, Any]],
    source_url: Optional[str],
    radius_m: int,
    mode: str,
) -> Dict[str, Any]:
    """Berechnet ein robustes Umfeldprofil auf Basis eines radialen POI-Modells."""
    radius = int(clamp(float(radius_m or 0), 120.0, 900.0))
    ring_1 = max(70, int(round(radius * 0.33)))
    ring_2 = max(ring_1 + 45, int(round(radius * 0.66)))
    ring_3 = radius

    ring_defs = [
        {"id": "inner", "max_distance_m": ring_1, "weight": 1.0},
        {"id": "mid", "max_distance_m": ring_2, "weight": 0.7},
        {"id": "outer", "max_distance_m": ring_3, "weight": 0.45},
    ]
    ring_weights = {entry["id"]: float(entry["weight"]) for entry in ring_defs}

    core_domains = (
        "transit",
        "daily_needs",
        "education_family",
        "health_care",
        "leisure_green",
        "nightlife",
    )

    def classify_domain(category: str, subcategory: str) -> str:
        cat = str(category or "").strip().lower()
        sub = str(subcategory or "").strip().lower()

        if cat == "amenity":
            if sub in {"bus_station", "ferry_terminal", "taxi", "parking", "parking_entrance", "charging_station"}:
                return "transit"
            if sub in {"school", "kindergarten", "childcare", "college", "university", "library"}:
                return "education_family"
            if sub in {"hospital", "clinic", "doctors", "pharmacy", "dentist", "social_facility", "nursing_home"}:
                return "health_care"
            if sub in {"bar", "pub", "nightclub", "casino"}:
                return "nightlife"
            if sub in {
                "restaurant",
                "cafe",
                "fast_food",
                "marketplace",
                "bank",
                "post_office",
                "atm",
                "fuel",
                "car_rental",
            }:
                return "daily_needs"

        if cat == "shop":
            return "daily_needs"

        if cat == "leisure":
            if sub in {"park", "garden", "nature_reserve", "playground", "dog_park", "recreation_ground"}:
                return "leisure_green"
            if sub in {"nightclub", "adult_gaming_centre", "dance"}:
                return "nightlife"
            return "leisure_green"

        if cat == "tourism":
            return "nightlife"

        if cat in {"office", "craft"}:
            return "daily_needs"

        return "other"

    def assign_ring(distance_m: float) -> str:
        if distance_m <= ring_1:
            return "inner"
        if distance_m <= ring_2:
            return "mid"
        return "outer"

    counts_by_ring = {entry["id"]: 0 for entry in ring_defs}
    counts_by_domain = {domain: 0 for domain in (*core_domains, "other")}
    weighted_domain_signals = {domain: 0.0 for domain in (*core_domains, "other")}
    weighted_samples: List[Dict[str, Any]] = []

    for poi in pois:
        distance_raw = poi.get("distance_m")
        try:
            distance = float(distance_raw)
        except (TypeError, ValueError):
            distance = float(radius)

        domain = classify_domain(str(poi.get("category") or ""), str(poi.get("subcategory") or ""))
        ring_id = assign_ring(distance)

        counts_by_ring[ring_id] += 1
        counts_by_domain[domain] += 1

        proximity = clamp(1.0 - (distance / max(float(radius), 1.0)), 0.0, 1.0)
        weighted_signal = float(ring_weights.get(ring_id, 0.45)) * (0.4 + 0.6 * proximity)
        weighted_domain_signals[domain] += weighted_signal

        weighted_samples.append(
            {
                "name": poi.get("name"),
                "domain": domain,
                "ring": ring_id,
                "distance_m": round(distance, 1),
                "weight": round(weighted_signal, 4),
            }
        )

    def norm_domain(domain: str, scale: float = 3.0) -> float:
        return clamp(float(weighted_domain_signals.get(domain) or 0.0) / scale, 0.0, 1.0)

    area_km2 = math.pi * ((float(radius) / 1000.0) ** 2)
    poi_total = sum(counts_by_domain.values())
    density_per_km2 = float(poi_total) / max(area_km2, 1e-6)

    density_score = clamp((density_per_km2 / 220.0) * 100.0, 0.0, 100.0)
    diversity_score = (
        sum(1 for domain in core_domains if int(counts_by_domain.get(domain) or 0) > 0)
        / float(len(core_domains))
        * 100.0
    )

    transit_n = norm_domain("transit")
    daily_n = norm_domain("daily_needs")
    edu_n = norm_domain("education_family")
    health_n = norm_domain("health_care")
    green_n = norm_domain("leisure_green")
    nightlife_n = norm_domain("nightlife")

    accessibility_score = clamp((transit_n * 0.4 + daily_n * 0.3 + health_n * 0.2 + edu_n * 0.1) * 100.0, 0.0, 100.0)
    family_support_score = clamp((edu_n * 0.4 + health_n * 0.25 + green_n * 0.35) * 100.0, 0.0, 100.0)
    vitality_score = clamp((daily_n * 0.5 + nightlife_n * 0.3 + transit_n * 0.2) * 100.0, 0.0, 100.0)
    quietness_score = clamp(((1.0 - nightlife_n) * 0.55 + green_n * 0.45) * 100.0, 0.0, 100.0)

    overall_score = clamp(
        (
            accessibility_score
            + family_support_score
            + vitality_score
            + quietness_score
            + diversity_score
            + density_score
        )
        / 6.0,
        0.0,
        100.0,
    )

    score_factor_order = (
        "density_score",
        "diversity_score",
        "accessibility_score",
        "family_support_score",
        "vitality_score",
        "quietness_score",
    )
    score_factor_values = {
        "density_score": density_score,
        "diversity_score": diversity_score,
        "accessibility_score": accessibility_score,
        "family_support_score": family_support_score,
        "vitality_score": vitality_score,
        "quietness_score": quietness_score,
    }
    factor_weight = 1.0 / float(len(score_factor_order))
    score_factors: List[Dict[str, Any]] = []
    for factor_key in score_factor_order:
        raw_score = clamp(float(score_factor_values.get(factor_key, 0.0)), 0.0, 100.0)
        score_factors.append(
            {
                "key": factor_key,
                "score": round(raw_score, 2),
                "weight": round(factor_weight, 6),
                "weighted_points": round(raw_score * factor_weight, 2),
            }
        )

    score_model = {
        "id": "environment-profile-scoring-v1",
        "formula": "overall_score = Σ(factor_score * factor_weight), factor_weight = 1/6",
        "factors": score_factors,
        "overall_score_raw": round(sum(float(row.get("weighted_points") or 0.0) for row in score_factors), 2),
        "calibration_reference": "docs/api/environment-profile-scoring-v1.md",
    }

    weighted_samples.sort(key=lambda row: float(row.get("weight") or 0.0), reverse=True)
    top_signals = weighted_samples[:8]
    layer_conf = clamp(0.44 + min(float(poi_total), 36.0) / 120.0, 0.42, 0.82)

    if poi_total <= 0:
        return {
            "status": "no_data",
            "model": {
                "id": "radius-v1",
                "mode": mode,
                "radius_m": radius,
                "rings": ring_defs,
                "distance_weighting": "ring_weight * (0.4 + 0.6 * proximity)",
            },
            "counts": {
                "poi_total": 0,
                "by_domain": counts_by_domain,
                "by_ring": counts_by_ring,
            },
            "metrics": {
                "density_score": 0,
                "diversity_score": 0,
                "accessibility_score": 0,
                "family_support_score": 0,
                "vitality_score": 0,
                "quietness_score": 0,
                "overall_score": 0,
            },
            "score_model": score_model,
            "signals": [],
            "statements": [
                statement(
                    "Keine POI-Signale im Radiusmodell verfügbar; Umfeldprofil bleibt unbestimmt.",
                    confidence=0.4,
                    evidence=[
                        evidence_item(
                            source="osm_poi_overpass",
                            confidence=0.4,
                            url=source_url,
                            snippet="environment_profile:no_data",
                            field_path="intelligence.environment_profile",
                        )
                    ],
                    field_path="intelligence.environment_profile",
                )
            ],
        }

    return {
        "status": "ok",
        "model": {
            "id": "radius-v1",
            "mode": mode,
            "radius_m": radius,
            "rings": ring_defs,
            "distance_weighting": "ring_weight * (0.4 + 0.6 * proximity)",
        },
        "counts": {
            "poi_total": poi_total,
            "by_domain": counts_by_domain,
            "by_ring": counts_by_ring,
            "density_per_km2": round(density_per_km2, 2),
        },
        "metrics": {
            "density_score": int(round(density_score)),
            "diversity_score": int(round(diversity_score)),
            "accessibility_score": int(round(accessibility_score)),
            "family_support_score": int(round(family_support_score)),
            "vitality_score": int(round(vitality_score)),
            "quietness_score": int(round(quietness_score)),
            "overall_score": int(round(overall_score)),
        },
        "score_model": score_model,
        "signals": top_signals,
        "statements": [
            statement(
                "Umfeldprofil aus radialem 3-Ring-POI-Modell berechnet (Kernkennzahlen + Explainability).",
                confidence=layer_conf,
                evidence=[
                    evidence_item(
                        source="osm_poi_overpass",
                        confidence=layer_conf,
                        url=source_url,
                        snippet=f"environment_profile:poi={poi_total},overall={overall_score:.1f}",
                        field_path="intelligence.environment_profile.metrics.overall_score",
                    )
                ],
                field_path="intelligence.environment_profile",
            )
        ],
    }


def build_environment_noise_risk_layer(
    *,
    pois: Sequence[Dict[str, Any]],
    source_url: Optional[str],
    radius_m: int,
    mode: str,
) -> Dict[str, Any]:
    noisy_weights = {
        ("amenity", "nightclub"): 28,
        ("amenity", "bar"): 22,
        ("amenity", "pub"): 20,
        ("amenity", "casino"): 20,
        ("amenity", "restaurant"): 10,
        ("amenity", "fast_food"): 12,
        ("leisure", "stadium"): 25,
        ("leisure", "sports_centre"): 13,
        ("tourism", "hotel"): 8,
        ("amenity", "bus_station"): 15,
        ("railway", "station"): 17,
    }

    indicators: List[Dict[str, Any]] = []
    total = 0.0

    for idx, poi in enumerate(pois):
        category = str(poi.get("category") or "")
        sub = str(poi.get("subcategory") or "")
        weight = noisy_weights.get((category, sub))
        if weight is None and category == "amenity" and sub in {"school", "kindergarten"}:
            weight = 6
        if weight is None:
            continue

        distance = float(poi.get("distance_m") or radius_m)
        distance_factor = clamp(1.0 - (distance / max(float(radius_m), 1.0)), 0.0, 1.0)
        impact = weight * distance_factor
        if impact <= 0:
            continue

        conf = clamp(0.35 + distance_factor * 0.35, 0.3, 0.75)
        ev = [
            evidence_item(
                source="osm_poi_overpass",
                confidence=conf,
                url=source_url,
                snippet=f"{poi.get('name')} ({category}:{sub})",
                field_path=f"intelligence.environment_noise_risk.indicators[{len(indicators)}]",
            )
        ]
        indicators.append(
            {
                "name": poi.get("name"),
                "category": category,
                "subcategory": sub,
                "distance_m": distance,
                "impact": round(impact, 2),
                "status": classify_statement_status(conf, ev),
                "confidence": round(conf, 2),
                "evidence": ev,
            }
        )
        total += impact

    score = int(round(clamp(total, 0.0, 100.0)))
    indicators.sort(key=lambda x: x.get("impact", 0), reverse=True)
    top = indicators[:8]

    if mode == "risk":
        high_thr, med_thr = 55, 28
    else:
        high_thr, med_thr = 65, 34

    if score >= high_thr:
        level = "high"
        traffic_light = "red"
    elif score >= med_thr:
        level = "medium"
        traffic_light = "yellow"
    else:
        level = "low"
        traffic_light = "green"

    msg = (
        "Erhöhtes Aktivitäts-/Lärmrisiko durch umliegende POI-Indikatoren."
        if level != "low"
        else "Keine starken Lärm-/Aktivitätsindikatoren im unmittelbaren Umfeld."
    )

    layer_conf = clamp(0.44 + (len(top) / 16.0), 0.42, 0.78)
    return {
        "status": "ok" if pois else "no_data",
        "score": score,
        "level": level,
        "traffic_light": traffic_light,
        "indicators": top,
        "reasons": [f"{i.get('name')} ({i.get('category')}:{i.get('subcategory')}, {int(i.get('distance_m') or 0)}m)" for i in top[:4]],
        "statements": [
            statement(
                msg,
                confidence=layer_conf,
                evidence=[
                    evidence_item(
                        source="osm_poi_overpass",
                        confidence=layer_conf,
                        url=source_url,
                        snippet=f"noise_score={score}",
                        field_path="intelligence.environment_noise_risk.score",
                    )
                ],
                field_path="intelligence.environment_noise_risk",
            )
        ],
    }


def build_consistency_checks_layer(
    *,
    query: QueryParts,
    selected: CandidateEval,
    incidents_timeline: Dict[str, Any],
    plz_layer: Dict[str, Any],
    admin_boundary: Dict[str, Any],
) -> Dict[str, Any]:
    gwr = selected.gwr_attrs
    addr = selected.address_attrs
    checks: List[Dict[str, Any]] = []

    def add_check(
        check_id: str,
        result: str,
        severity: str,
        message: str,
        confidence: float,
        evidence: Sequence[Dict[str, Any]],
    ) -> None:
        checks.append(
            {
                "id": check_id,
                "result": result,
                "severity": severity,
                "message": message,
                "status": classify_statement_status(confidence, evidence),
                "confidence": round(confidence, 2),
                "evidence": list(evidence),
            }
        )

    is_official = addr.get("adr_official") is True
    add_check(
        "address_registry_official",
        "pass" if is_official else "warn",
        "medium" if is_official else "high",
        "Adresse ist im amtlichen Register als offiziell markiert." if is_official else "Adresse nicht als offiziell markiert.",
        0.95 if is_official else 0.7,
        [
            evidence_item(
                source="geoadmin_address",
                confidence=0.95 if is_official else 0.7,
                field_path="address_registry.adr_official",
            )
        ],
    )

    gwr_plz = str(gwr.get("plz_plz6") or "")[:4]
    query_plz = str(query.postal_code or "")
    if query_plz and gwr_plz:
        same = query_plz == gwr_plz
        add_check(
            "postal_code_query_vs_gwr",
            "pass" if same else "fail",
            "low" if same else "high",
            f"PLZ Query ({query_plz}) {'stimmt mit' if same else 'weicht von'} GWR ({gwr_plz}) {'überein' if same else 'ab' }.",
            0.94 if same else 0.88,
            [
                evidence_item(source="geoadmin_gwr", confidence=0.92, field_path="administrative.plz_plz6"),
                evidence_item(source="geoadmin_search", confidence=0.78, field_path="match.query_parts.postal_code"),
            ],
        )

    query_city = normalize_text(query.city or "")
    gwr_city = normalize_text(gwr.get("dplzname") or gwr.get("ggdename") or "")
    if query_city and gwr_city:
        match = query_city in gwr_city or gwr_city in query_city
        add_check(
            "city_query_vs_gwr",
            "pass" if match else "warn",
            "low" if match else "medium",
            "Ortsbezeichnung Query/GWR konsistent." if match else "Ortsbezeichnung Query/GWR nicht eindeutig konsistent.",
            0.87 if match else 0.62,
            [
                evidence_item(source="geoadmin_gwr", confidence=0.86, field_path="administrative.ort"),
                evidence_item(source="geoadmin_search", confidence=0.72, field_path="match.query_parts.city"),
            ],
        )

    b_year_raw = gwr.get("gbauj")
    b_year = None
    if b_year_raw is not None:
        try:
            b_year = int(str(b_year_raw)[:4])
        except Exception:
            b_year = None

    current_year = datetime.now().year
    if b_year is None:
        add_check(
            "baujahr_plausibility",
            "unknown",
            "medium",
            "Baujahr fehlt oder ist nicht interpretierbar.",
            0.45,
            [evidence_item(source="geoadmin_gwr", confidence=0.45, field_path="building.baujahr")],
        )
    else:
        plausible = 1000 <= b_year <= current_year + 1
        add_check(
            "baujahr_plausibility",
            "pass" if plausible else "fail",
            "low" if plausible else "high",
            f"Baujahr {b_year} ist {'plausibel' if plausible else 'unplausibel'}.",
            0.94 if plausible else 0.9,
            [evidence_item(source="geoadmin_gwr", confidence=0.94 if plausible else 0.9, field_path="building.baujahr")],
        )

    boundary_city = normalize_text(admin_boundary.get("gemname") or "")
    if boundary_city and gwr_city:
        same = boundary_city in gwr_city or gwr_city in boundary_city
        add_check(
            "gwr_vs_boundary_city",
            "pass" if same else "warn",
            "low" if same else "medium",
            "GWR-Gemeinde passt zu SwissBoundaries." if same else "GWR-Gemeinde weicht von SwissBoundaries ab.",
            0.88 if same else 0.63,
            [
                evidence_item(source="geoadmin_gwr", confidence=0.84, field_path="administrative.gemeinde"),
                evidence_item(source="swissboundaries_identify", confidence=0.82, field_path="cross_source.admin_boundary.gemeinde"),
            ],
        )

    incident_warnings = 0
    if b_year is not None:
        for event in incidents_timeline.get("events") or []:
            date = event.get("date")
            if not date:
                continue
            try:
                year = datetime.fromisoformat(str(date).replace("Z", "+00:00")).year
            except Exception:
                continue
            if year < b_year - 1:
                incident_warnings += 1

    if incident_warnings:
        add_check(
            "incident_vs_baujahr",
            "warn",
            "medium",
            f"{incident_warnings} Web-Hinweise liegen deutlich vor dem Baujahr und könnten auf Adress-Homonyme hindeuten.",
            0.58,
            [
                evidence_item(
                    source="google_news_rss",
                    confidence=0.58,
                    field_path="intelligence.incidents_timeline.events",
                    snippet="Eventjahr vor Baujahr",
                )
            ],
        )
    else:
        add_check(
            "incident_vs_baujahr",
            "pass",
            "low",
            "Keine offensichtliche Zeitachsen-Inkonsistenz zwischen Baujahr und Incident-Hinweisen.",
            0.62,
            [
                evidence_item(
                    source="geoadmin_gwr",
                    confidence=0.75,
                    field_path="building.baujahr",
                ),
                evidence_item(
                    source="google_news_rss",
                    confidence=0.55,
                    field_path="intelligence.incidents_timeline.events",
                ),
            ],
        )

    fail_count = sum(1 for c in checks if c.get("result") == "fail")
    warn_count = sum(1 for c in checks if c.get("result") == "warn")
    unknown_count = sum(1 for c in checks if c.get("result") == "unknown")
    risk_score = int(round(clamp(fail_count * 28 + warn_count * 11 + unknown_count * 5, 0, 100)))

    overall = "critical" if fail_count > 0 else ("attention" if warn_count >= 2 else "stable")
    return {
        "status": "ok",
        "overall": overall,
        "risk_score": risk_score,
        "counts": {
            "pass": sum(1 for c in checks if c.get("result") == "pass"),
            "warn": warn_count,
            "fail": fail_count,
            "unknown": unknown_count,
        },
        "checks": checks,
        "statements": [
            statement(
                (
                    "Konsistenzprüfung zeigt kritische Widersprüche."
                    if overall == "critical"
                    else "Konsistenzprüfung mit einzelnen Warnsignalen."
                    if overall == "attention"
                    else "Konsistenzprüfung ohne harte Widersprüche."
                ),
                confidence=0.9 if overall == "stable" else (0.72 if overall == "attention" else 0.83),
                evidence=[
                    evidence_item(
                        source="geoadmin_gwr",
                        confidence=0.85,
                        field_path="intelligence.consistency_checks",
                    )
                ],
                field_path="intelligence.consistency_checks",
            )
        ],
    }


def build_executive_risk_summary(
    *,
    mode: str,
    confidence: Dict[str, Any],
    ambiguity: Dict[str, Any],
    tenants_businesses: Dict[str, Any],
    incidents_timeline: Dict[str, Any],
    environment_noise_risk: Dict[str, Any],
    consistency_checks: Dict[str, Any],
) -> Dict[str, Any]:
    reasons: List[str] = []
    risk_points = 0.0

    conf_level = confidence.get("level")
    if conf_level == "low":
        risk_points += 34
        reasons.append("Niedrige Match-Confidence")
    elif conf_level == "medium":
        risk_points += 15
        reasons.append("Mittlere Match-Confidence")

    amb_level = ambiguity.get("level")
    if amb_level == "high":
        risk_points += 24
        reasons.append("Hohe Kandidaten-Ambiguität")
    elif amb_level == "medium":
        risk_points += 10
        reasons.append("Mehrdeutigkeit im Kandidatenfeld")

    consistency_risk = float(consistency_checks.get("risk_score") or 0)
    risk_points += consistency_risk * 0.45
    if consistency_risk >= 45:
        reasons.append("Konsistenzchecks mit erhöhtem Risiko")

    incident_relevant = int(incidents_timeline.get("relevant_event_count") or 0)
    if incident_relevant:
        risk_points += min(24, incident_relevant * 6)
        reasons.append(f"{incident_relevant} relevante Incident-Hinweise im Web")

    noise_score = float(environment_noise_risk.get("score") or 0)
    if mode in {"extended", "risk"}:
        risk_points += noise_score * (0.25 if mode == "risk" else 0.18)
        if noise_score >= 35:
            reasons.append("Umfeld zeigt Aktivitäts-/Lärmindikatoren")

    if mode == "risk":
        risk_points += 6
        reasons.append("Risk-Modus: konservativere Schwellen")

    risk_score = int(round(clamp(risk_points, 0, 100)))
    traffic_light = "green" if risk_score < 34 else ("yellow" if risk_score < 67 else "red")
    traffic_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[traffic_light]

    if not reasons:
        reasons.append("Keine auffälligen Risikoindikatoren")

    evidence = [
        evidence_item(source="geoadmin_gwr", confidence=0.9, field_path="confidence.level"),
        evidence_item(source="osm_poi_overpass", confidence=0.55, field_path="intelligence.environment_noise_risk.score"),
        evidence_item(source="google_news_rss", confidence=0.52, field_path="intelligence.incidents_timeline.relevant_event_count"),
    ]

    return {
        "mode": mode,
        "risk_score": risk_score,
        "traffic_light": traffic_light,
        "traffic_emoji": traffic_emoji,
        "summary": f"{traffic_emoji} Risikoampel: {traffic_light.upper()} (Score {risk_score}/100)",
        "reasons": reasons[:6],
        "status": classify_statement_status(0.72, evidence),
        "evidence": evidence,
        "field_provenance": {
            "field": "intelligence.executive_risk_summary",
            "primary_source": "geoadmin_gwr",
            "observed_at": utc_now_iso(),
        },
    }


def build_intelligence_layers(
    *,
    mode: str,
    client: HttpClient,
    sources: SourceRegistry,
    query: QueryParts,
    selected: CandidateEval,
    confidence: Dict[str, Any],
    plz_layer: Dict[str, Any],
    admin_boundary: Dict[str, Any],
) -> Dict[str, Any]:
    mode = mode if mode in INTELLIGENCE_MODES else "basic"
    settings = intelligence_mode_settings(mode)

    tenants_businesses: Dict[str, Any]
    incidents_timeline: Dict[str, Any]
    environment_noise_risk: Dict[str, Any]
    environment_profile: Dict[str, Any]

    poi_payload = {"source_url": None, "pois": []}
    if settings.get("enable_external"):
        try:
            poi_payload = fetch_osm_poi_overpass(
                client,
                sources,
                lat=selected.lat,
                lon=selected.lon,
                radius_m=int(settings.get("poi_radius_m") or 180),
                max_items=int(settings.get("poi_limit") or 80),
            )
        except Exception as ex:
            sources.note_error("osm_poi_overpass", "https://overpass-api.de", str(ex), optional=True)
            poi_payload = {"source_url": "https://overpass-api.de/api/interpreter", "pois": [], "error": str(ex)}

        pois = poi_payload.get("pois") or []
        source_url = poi_payload.get("source_url")

        try:
            tenants_businesses = build_tenants_businesses_layer(
                pois=pois,
                source_url=source_url,
                tenant_limit=int(settings.get("tenant_limit") or 10),
            )
        except Exception as ex:
            tenants_businesses = {
                "status": "error",
                "error": str(ex),
                "entities": [],
                "statements": [
                    statement(
                        "Mieter-/Geschäftsindizien konnten nicht ausgewertet werden.",
                        confidence=0.3,
                        evidence=[
                            evidence_item(
                                source="osm_poi_overpass",
                                confidence=0.3,
                                url=source_url,
                                snippet=str(ex),
                                field_path="intelligence.tenants_businesses",
                            )
                        ],
                        field_path="intelligence.tenants_businesses",
                    )
                ],
            }

        try:
            environment_noise_risk = build_environment_noise_risk_layer(
                pois=pois,
                source_url=source_url,
                radius_m=int(settings.get("poi_radius_m") or 180),
                mode=mode,
            )
        except Exception as ex:
            environment_noise_risk = {
                "status": "error",
                "score": 0,
                "level": "unknown",
                "traffic_light": "yellow",
                "reasons": [f"Noise-Layer Fehler: {ex}"],
                "indicators": [],
                "statements": [
                    statement(
                        "Umfeld-Lärmrisiko konnte nicht berechnet werden.",
                        confidence=0.3,
                        evidence=[
                            evidence_item(
                                source="osm_poi_overpass",
                                confidence=0.3,
                                url=source_url,
                                snippet=str(ex),
                                field_path="intelligence.environment_noise_risk",
                            )
                        ],
                        field_path="intelligence.environment_noise_risk",
                    )
                ],
            }

        try:
            environment_profile = build_environment_profile_layer(
                pois=pois,
                source_url=source_url,
                radius_m=int(settings.get("poi_radius_m") or 180),
                mode=mode,
            )
        except Exception as ex:
            environment_profile = {
                "status": "error",
                "model": {
                    "id": "radius-v1",
                    "mode": mode,
                    "radius_m": int(settings.get("poi_radius_m") or 180),
                    "rings": [],
                    "distance_weighting": "ring_weight * (0.4 + 0.6 * proximity)",
                },
                "counts": {
                    "poi_total": 0,
                    "by_domain": {},
                    "by_ring": {},
                },
                "metrics": {
                    "density_score": 0,
                    "diversity_score": 0,
                    "accessibility_score": 0,
                    "family_support_score": 0,
                    "vitality_score": 0,
                    "quietness_score": 0,
                    "overall_score": 0,
                },
                "signals": [],
                "statements": [
                    statement(
                        "Umfeldprofil konnte nicht berechnet werden.",
                        confidence=0.3,
                        evidence=[
                            evidence_item(
                                source="osm_poi_overpass",
                                confidence=0.3,
                                url=source_url,
                                snippet=str(ex),
                                field_path="intelligence.environment_profile",
                            )
                        ],
                        field_path="intelligence.environment_profile",
                    )
                ],
            }

        try:
            incident_query = f'"{selected.label}" OR "{query.raw}"'
            if settings.get("news_focus") == "address_and_incident":
                incident_query += " (Brand OR Feuer OR Polizei OR Unfall OR Einbruch)"
            news_payload = fetch_google_news_rss(
                client,
                sources,
                query=incident_query,
                limit=int(settings.get("incident_limit") or 6),
            )
            incidents_timeline = build_incidents_timeline_layer(
                news_payload=news_payload,
                address_query=query.raw,
                max_items=int(settings.get("incident_limit") or 6),
            )
        except Exception as ex:
            incidents_timeline = {
                "status": "error",
                "events": [],
                "relevant_event_count": 0,
                "statements": [
                    statement(
                        "Incident-Timeline konnte nicht geladen werden.",
                        confidence=0.3,
                        evidence=[
                            evidence_item(
                                source="google_news_rss",
                                confidence=0.3,
                                snippet=str(ex),
                                field_path="intelligence.incidents_timeline",
                            )
                        ],
                        field_path="intelligence.incidents_timeline",
                    )
                ],
            }
    else:
        sources.disable("osm_poi_overpass", "im basic-Modus deaktiviert")
        sources.disable("google_news_rss", "im basic-Modus deaktiviert")
        tenants_businesses = {
            "status": "disabled_by_mode",
            "entities": [],
            "counts_by_category": {},
            "statements": [
                statement(
                    "Mieter-/Geschäftsindizien sind im basic-Modus deaktiviert.",
                    confidence=0.6,
                    evidence=[
                        evidence_item(
                            source="osm_poi_overpass",
                            confidence=0.6,
                            snippet="Mode basic",
                            field_path="intelligence.tenants_businesses",
                        )
                    ],
                    field_path="intelligence.tenants_businesses",
                )
            ],
        }
        incidents_timeline = {
            "status": "disabled_by_mode",
            "events": [],
            "relevant_event_count": 0,
            "statements": [
                statement(
                    "Incident-Timeline ist im basic-Modus deaktiviert.",
                    confidence=0.6,
                    evidence=[
                        evidence_item(
                            source="google_news_rss",
                            confidence=0.6,
                            snippet="Mode basic",
                            field_path="intelligence.incidents_timeline",
                        )
                    ],
                    field_path="intelligence.incidents_timeline",
                )
            ],
        }
        environment_noise_risk = {
            "status": "disabled_by_mode",
            "score": 0,
            "level": "unknown",
            "traffic_light": "green",
            "reasons": ["Noise-Risk-Layer im basic-Modus deaktiviert"],
            "indicators": [],
            "statements": [
                statement(
                    "Umfeld-Lärmrisiko ist im basic-Modus deaktiviert.",
                    confidence=0.6,
                    evidence=[
                        evidence_item(
                            source="osm_poi_overpass",
                            confidence=0.6,
                            snippet="Mode basic",
                            field_path="intelligence.environment_noise_risk",
                        )
                    ],
                    field_path="intelligence.environment_noise_risk",
                )
            ],
        }
        environment_profile = {
            "status": "disabled_by_mode",
            "model": {
                "id": "radius-v1",
                "mode": mode,
                "radius_m": int(settings.get("poi_radius_m") or 180),
                "rings": [],
                "distance_weighting": "ring_weight * (0.4 + 0.6 * proximity)",
            },
            "counts": {
                "poi_total": 0,
                "by_domain": {},
                "by_ring": {},
            },
            "metrics": {
                "density_score": 0,
                "diversity_score": 0,
                "accessibility_score": 0,
                "family_support_score": 0,
                "vitality_score": 0,
                "quietness_score": 0,
                "overall_score": 0,
            },
            "signals": [],
            "statements": [
                statement(
                    "Umfeldprofil ist im basic-Modus deaktiviert.",
                    confidence=0.6,
                    evidence=[
                        evidence_item(
                            source="osm_poi_overpass",
                            confidence=0.6,
                            snippet="Mode basic",
                            field_path="intelligence.environment_profile",
                        )
                    ],
                    field_path="intelligence.environment_profile",
                )
            ],
        }

    consistency_checks = build_consistency_checks_layer(
        query=query,
        selected=selected,
        incidents_timeline=incidents_timeline,
        plz_layer=plz_layer,
        admin_boundary=admin_boundary,
    )

    executive_risk_summary = build_executive_risk_summary(
        mode=mode,
        confidence=confidence,
        ambiguity=confidence.get("ambiguity") or {},
        tenants_businesses=tenants_businesses,
        incidents_timeline=incidents_timeline,
        environment_noise_risk=environment_noise_risk,
        consistency_checks=consistency_checks,
    )

    return {
        "mode": mode,
        "source_policy": {
            "priority": SOURCE_POLICY_ORDER,
            "description": "official > licensed > community > web",
        },
        "tenants_businesses": tenants_businesses,
        "incidents_timeline": incidents_timeline,
        "environment_profile": environment_profile,
        "environment_noise_risk": environment_noise_risk,
        "consistency_checks": consistency_checks,
        "executive_risk_summary": executive_risk_summary,
    }


def hydrate_candidates(
    client: HttpClient,
    sources: SourceRegistry,
    query: QueryParts,
    candidates: List[CandidateEval],
    *,
    max_hydrated: int,
) -> CandidateEval:
    if not candidates:
        raise NoAddressMatchError(f"Keine Adresse gefunden für: {query.raw}")

    hydrated: List[CandidateEval] = []
    best_pre = sorted(candidates, key=lambda c: c.pre_score, reverse=True)

    for cand in best_pre[: max(1, max_hydrated)]:
        try:
            addr = fetch_feature_attributes(
                client,
                sources,
                layer="ch.swisstopo.amtliches-gebaeudeadressverzeichnis",
                feature_id=cand.feature_id,
                source_name="geoadmin_address",
                optional=True,
            )
            gwr = fetch_feature_attributes(
                client,
                sources,
                layer="ch.bfs.gebaeude_wohnungs_register",
                feature_id=cand.feature_id,
                source_name="geoadmin_gwr",
                optional=False,
            )

            detail_score, detail_reasons = score_candidate_detail(query, addr, gwr)
            cand.address_attrs = addr
            cand.gwr_attrs = gwr
            cand.detail_score = detail_score
            cand.detail_reasons = detail_reasons
            cand.total_score = cand.pre_score + cand.detail_score
            hydrated.append(cand)
        except Exception:
            # Kandidat unbrauchbar => nächster
            continue

    if not hydrated:
        top = best_pre[0]
        raise NoAddressMatchError(
            f"Keine verwertbaren Gebäudedaten für Adresse gefunden. Bester Suchtreffer: {top.label} ({top.feature_id})"
        )

    hydrated.sort(
        key=lambda c: (
            c.total_score,
            1 if c.address_attrs.get("adr_official") else 0,
            1 if c.gwr_attrs.get("egid") else 0,
        ),
        reverse=True,
    )
    return hydrated[0]


def build_candidate_list(raw_results: List[Dict[str, Any]], query: QueryParts) -> List[CandidateEval]:
    out: List[CandidateEval] = []
    for attrs in raw_results:
        feature_id = str(attrs.get("featureId") or "").strip()
        if not feature_id:
            continue

        pre_score, pre_reasons = score_candidate_pre(attrs, query)
        out.append(
            CandidateEval(
                feature_id=feature_id,
                label=strip_html(attrs.get("label") or "") or "",
                detail=str(attrs.get("detail") or ""),
                origin=attrs.get("origin"),
                rank=int(attrs.get("rank")) if isinstance(attrs.get("rank"), (int, float)) else None,
                lat=float(attrs.get("lat")) if isinstance(attrs.get("lat"), (int, float)) else None,
                lon=float(attrs.get("lon")) if isinstance(attrs.get("lon"), (int, float)) else None,
                pre_score=pre_score,
                pre_reasons=pre_reasons,
                attrs=attrs,
            )
        )
    out.sort(key=lambda c: c.pre_score, reverse=True)
    return out


def assess_ambiguity(selected: CandidateEval, candidates: Sequence[CandidateEval]) -> Dict[str, Any]:
    warnings: List[str] = []
    level = "none"
    score_gap = None

    if len(candidates) > 1:
        others = [c for c in candidates if c.feature_id != selected.feature_id]
        if others:
            best_other = max(others, key=lambda c: c.total_score if c.total_score else c.pre_score)
            best_other_score = best_other.total_score if best_other.total_score else best_other.pre_score
            score_gap = round((selected.total_score or selected.pre_score) - best_other_score, 2)
            if score_gap < 5:
                level = "high"
                warnings.append("Sehr geringe Distanz zum nächstbesten Kandidaten")
            elif score_gap < 12:
                level = "medium"
                warnings.append("Mehrere Kandidaten mit ähnlichem Score")

    mismatch_hits = 0
    for reason in selected.pre_reasons + selected.detail_reasons:
        if "weicht ab" in reason.lower() or "nicht" in reason.lower() or "fehlt" in reason.lower():
            mismatch_hits += 1

    if mismatch_hits >= 3:
        if level == "none":
            level = "medium"
        warnings.append("Mehrere Matching-Indizien sind inkonsistent")

    return {
        "level": level,
        "score_gap_to_next": score_gap,
        "warnings": warnings,
    }


def compute_confidence(
    *,
    selected: CandidateEval,
    candidates: Sequence[CandidateEval],
    sources: SourceRegistry,
    heating_layer: Dict[str, Any],
    plz_layer: Dict[str, Any],
    admin_boundary: Dict[str, Any],
    osm: Dict[str, Any],
) -> Dict[str, Any]:
    gwr = selected.gwr_attrs
    addr = selected.address_attrs

    notes: List[str] = []
    explanations: List[Dict[str, Any]] = []

    # 1) Match-Qualität (0-40)
    match_component = clamp(selected.total_score or selected.pre_score, 0, 120) / 120 * 40
    notes.append(f"Match-Komponente: {match_component:.1f}/40")
    explanations.append({"factor": "match_quality", "impact": round(match_component, 1), "text": "Adress-Matching aus Such- und Detailscore"})

    # 2) Datenvollständigkeit (0-30)
    completeness = 0.0
    if selected.feature_id:
        completeness += 4
    if gwr.get("egid"):
        completeness += 9
    if gwr.get("egrid"):
        completeness += 5
    if gwr.get("esid") or gwr.get("edid") or addr.get("adr_egaid"):
        completeness += 4
    if gwr.get("gstat"):
        completeness += 3
    if gwr.get("gbauj"):
        completeness += 2
    if gwr.get("garea"):
        completeness += 1.5
    if gwr.get("gastw"):
        completeness += 1.5
    if gwr.get("ganzwhg") is not None:
        completeness += 1.0
    completeness = clamp(completeness, 0, 30)
    notes.append(f"Vollständigkeit: {completeness:.1f}/30")
    explanations.append({"factor": "data_completeness", "impact": round(completeness, 1), "text": "Verfügbarkeit von IDs, Status und Basis-Gebäudeattributen"})

    # 3) Quellen-/Konsistenzscore (0-20)
    consistency = 0.0
    gwr_plz = str(gwr.get("plz_plz6") or "")[:4]
    gwr_city = normalize_text(gwr.get("dplzname") or gwr.get("ggdename") or "")

    plz_layer_plz = str(plz_layer.get("plz") or "")[:4]
    plz_layer_city = normalize_text(plz_layer.get("langtext") or "")

    if gwr_plz and plz_layer_plz:
        if gwr_plz == plz_layer_plz:
            consistency += 6
            notes.append("PLZ-Konsistenz: GWR ↔ PLZ-Layer passt")
        else:
            consistency -= 3
            notes.append("PLZ-Konsistenz: Abweichung GWR ↔ PLZ-Layer")

    if gwr_city and plz_layer_city:
        if gwr_city in plz_layer_city or plz_layer_city in gwr_city:
            consistency += 4
            notes.append("Ortskonsistenz: GWR ↔ PLZ-Layer passt")
        else:
            consistency -= 2
            notes.append("Ortskonsistenz: Abweichung GWR ↔ PLZ-Layer")

    boundary_city = normalize_text(admin_boundary.get("gemname") or "")
    boundary_kanton = normalize_text(admin_boundary.get("kanton") or "")
    gwr_kanton = normalize_text(gwr.get("gdekt") or "")
    if boundary_city and gwr_city:
        if boundary_city in gwr_city or gwr_city in boundary_city:
            consistency += 3
            notes.append("Ortskonsistenz: GWR ↔ SwissBoundaries passt")
        else:
            consistency -= 2
            notes.append("Ortskonsistenz: Abweichung GWR ↔ SwissBoundaries")
    if boundary_kanton and gwr_kanton:
        if boundary_kanton == gwr_kanton:
            consistency += 2
            notes.append("Kantonskonsistenz: GWR ↔ SwissBoundaries passt")
        else:
            consistency -= 2
            notes.append("Kantonskonsistenz: Abweichung GWR ↔ SwissBoundaries")

    osm_addr = (osm.get("address") or {}) if isinstance(osm, dict) else {}
    osm_postcode = str(osm_addr.get("postcode") or "")[:4]
    osm_city = normalize_text(osm_addr.get("city") or osm_addr.get("town") or osm_addr.get("village") or "")

    if gwr_plz and osm_postcode:
        if gwr_plz == osm_postcode:
            consistency += 2.5
            notes.append("PLZ-Konsistenz: GWR ↔ OSM passt")
        else:
            consistency -= 1.5
            notes.append("PLZ-Konsistenz: GWR ↔ OSM abweichend")

    if gwr_city and osm_city:
        if gwr_city in osm_city or osm_city in gwr_city:
            consistency += 1.5
            notes.append("Ortskonsistenz: GWR ↔ OSM passt")
        else:
            consistency -= 1
            notes.append("Ortskonsistenz: GWR ↔ OSM abweichend")

    if heating_layer.get("genh1_de"):
        consistency += 1.5
        notes.append("Energie-Layer liefert Klartextwerte")

    consistency = clamp(consistency, 0, 20)
    explanations.append({"factor": "cross_source_consistency", "impact": round(consistency, 1), "text": "Übereinstimmung zwischen GWR, PLZ-Layer, SwissBoundaries und optional OSM"})

    # 4) Verfügbarkeit Pflichtquellen (0-10)
    source_ratio = sources.required_success_ratio(_REQUIRED_SOURCES)
    source_component = source_ratio * 10
    explanations.append({"factor": "required_source_health", "impact": round(source_component, 1), "text": "Verfügbarkeit der Pflichtquellen (Search, GWR, Adressregister)"})

    mismatch_penalty = 0.0
    if any("Strasse nicht ausreichend enthalten" in r for r in selected.pre_reasons):
        mismatch_penalty += 8.0
    if any("GWR-Strasse weicht ab" in r for r in selected.detail_reasons):
        mismatch_penalty += 14.0
    if any("Hausnummer abweichend" in r for r in selected.detail_reasons):
        mismatch_penalty += 4.0

    ambiguity = assess_ambiguity(selected, candidates)
    ambiguity_penalty = 0.0
    if ambiguity["level"] == "high":
        ambiguity_penalty = 10.0
    elif ambiguity["level"] == "medium":
        ambiguity_penalty = 4.0

    if mismatch_penalty:
        notes.append(f"Mismatch-Penalty: -{mismatch_penalty:.1f} (Adressabweichung)")
    if ambiguity_penalty:
        notes.append(f"Ambiguitäts-Penalty: -{ambiguity_penalty:.1f}")

    score_raw = match_component + completeness + consistency + source_component - mismatch_penalty - ambiguity_penalty
    score = int(round(clamp(score_raw, 0, 100)))
    level = "high" if score >= 82 else ("medium" if score >= 62 else "low")

    warnings = list(ambiguity.get("warnings") or [])
    if score < 60:
        warnings.append("Niedrige Gesamt-Confidence: manuelle Prüfung empfohlen")

    return {
        "score": score,
        "max": 100,
        "level": level,
        "components": {
            "match_quality": round(match_component, 1),
            "data_completeness": round(completeness, 1),
            "cross_source_consistency": round(consistency, 1),
            "required_source_health": round(source_component, 1),
            "mismatch_penalty": round(mismatch_penalty, 1),
            "ambiguity_penalty": round(ambiguity_penalty, 1),
        },
        "notes": notes,
        "explanations": explanations,
        "ambiguity": ambiguity,
        "warnings": warnings,
    }


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


def _to_optional_int(value: Any) -> Optional[int]:
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


def _to_optional_float(value: Any) -> Optional[float]:
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
    gwr: Dict[str, Any],
    decoded: Dict[str, Any],
    address_registry: Dict[str, Any],
) -> Dict[str, Any]:
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


def compact_energy_summary(decoded: Dict[str, Any]) -> Dict[str, str]:
    hz = decoded.get("heizung") or []
    ww = decoded.get("warmwasser") or []
    return {
        "heizung": ", ".join(hz) if hz else "keine Angabe",
        "warmwasser": ", ".join(ww) if ww else "keine Angabe",
    }


def source_catalog_view(source_status: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for name, meta in SOURCE_CATALOG.items():
        state = source_status.get(name, {})
        authority = str(meta.get("authority") or "unknown")
        out[name] = {
            "tier": meta.get("tier"),
            "authority": authority,
            "policy_rank": SOURCE_POLICY_RANK.get(authority, SOURCE_POLICY_RANK["unknown"]),
            "purpose": meta.get("purpose"),
            "status": state.get("status", "not_used"),
            "optional": state.get("optional", meta.get("tier") != "core"),
        }
    return out


def get_nested(data: Dict[str, Any], dotted_path: str) -> Any:
    cur: Any = data
    for part in dotted_path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def build_field_provenance(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapping = {
        "ids.egid": ["geoadmin_gwr"],
        "ids.egrid": ["geoadmin_gwr"],
        "administrative.gemeinde": ["geoadmin_gwr", "swissboundaries_identify"],
        "administrative.kanton": ["geoadmin_gwr", "swissboundaries_identify"],
        "cross_source.plz_layer.plz": ["plz_layer_identify"],
        "cross_source.admin_boundary.gemeinde": ["swissboundaries_identify"],
        "cross_source.elevation.height_m": ["swisstopo_height"],
        "building.codes": ["geoadmin_gwr"],
        "building.decoded": ["geoadmin_gwr", "gwr_codes"],
        "energy.raw_codes": ["geoadmin_gwr"],
        "energy.heating_layer": ["bfs_heating_layer"],
        "cross_source.osm_reverse": ["osm_reverse"],
        "intelligence.tenants_businesses.entities": ["osm_poi_overpass"],
        "intelligence.incidents_timeline.events": ["google_news_rss"],
        "intelligence.environment_noise_risk.score": ["osm_poi_overpass"],
        "intelligence.consistency_checks": ["geoadmin_gwr", "geoadmin_address", "google_news_rss"],
        "intelligence.executive_risk_summary": ["geoadmin_gwr", "osm_poi_overpass", "google_news_rss"],
        "suitability_light.score": ["swisstopo_height", "plz_layer_identify", "swissboundaries_identify", "geoadmin_gwr", "osm_reverse"],
        "suitability_light.traffic_light": ["swisstopo_height", "plz_layer_identify", "swissboundaries_identify", "geoadmin_gwr", "osm_reverse"],
    }
    out: Dict[str, Dict[str, Any]] = {}
    for field_path, source_names in mapping.items():
        value = get_nested(report, field_path)
        out[field_path] = {
            "sources": source_names,
            "primary_source": source_names[0],
            "present": value is not None and value != "" and value != [],
            "authority": SOURCE_CATALOG.get(source_names[0], {}).get("authority"),
        }
    return out


def build_executive_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    conf = report.get("confidence") or {}
    ambiguity = conf.get("ambiguity") or {}
    warnings = list(conf.get("warnings") or [])
    needs_review = conf.get("level") == "low" or ambiguity.get("level") in {"medium", "high"}
    verdict = "review" if needs_review else "ok"

    return {
        "verdict": verdict,
        "needs_review": needs_review,
        "headline": (
            "Treffer wirkt stabil" if not needs_review else "Treffer prüfen (Ambiguität oder geringe Confidence)"
        ),
        "ambiguity_level": ambiguity.get("level", "none"),
        "ambiguity_gap": ambiguity.get("score_gap_to_next"),
        "warnings": warnings,
    }


def build_report(
    address_query: str,
    *,
    include_osm: bool = True,
    candidate_limit: int = 8,
    candidate_preview: int = 3,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF,
    min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL,
    osm_min_delay: float = 1.0,
    cache_ttl_seconds: float = DEFAULT_CACHE_TTL,
    intelligence_mode: str = "basic",
    client: Optional[HttpClient] = None,
    upstream_log_emitter: Optional[Callable[..., None]] = None,
    trace_id: str = "",
    request_id: str = "",
    session_id: str = "",
) -> Dict[str, Any]:
    query = parse_query_parts(address_query)
    intelligence_mode = intelligence_mode if intelligence_mode in INTELLIGENCE_MODES else "basic"

    client = client or HttpClient(
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff_seconds,
        min_request_interval_seconds=max(0.0, min_request_interval_seconds),
        cache_ttl_seconds=max(0.0, cache_ttl_seconds),
        upstream_log_emitter=upstream_log_emitter,
        upstream_trace_id=str(trace_id or request_id or ""),
        upstream_request_id=str(request_id or trace_id or ""),
        upstream_session_id=str(session_id or ""),
    )
    if upstream_log_emitter is not None:
        client.upstream_log_emitter = upstream_log_emitter
    if trace_id or request_id:
        trace_value = str(trace_id or request_id or "")
        request_value = str(request_id or trace_id or "")
        client.upstream_trace_id = trace_value
        client.upstream_request_id = request_value
    if session_id:
        client.upstream_session_id = str(session_id)

    sources = SourceRegistry()

    raw_candidates = search_candidates(client, sources, address_query, limit=candidate_limit)
    candidates = build_candidate_list(raw_candidates, query)

    selected = hydrate_candidates(
        client,
        sources,
        query,
        candidates,
        max_hydrated=max(1, min(candidate_limit, 6)),
    )

    gwr = selected.gwr_attrs
    addr = selected.address_attrs

    egid = str(gwr.get("egid") or gwr.get("bdg_egid") or "")
    heating = fetch_heating_layer(client, sources, egid=egid) if egid else {}
    if not egid:
        sources.disable("bfs_heating_layer", "kein EGID vorhanden")

    lv95_e = gwr.get("gkode")
    lv95_n = gwr.get("gkodn")
    plz_layer = fetch_plz_layer_at_lv95(client, sources, lv95_e=lv95_e, lv95_n=lv95_n)
    admin_boundary = fetch_swissboundaries_at_lv95(client, sources, lv95_e=lv95_e, lv95_n=lv95_n)
    elevation = fetch_swisstopo_height(client, sources, lv95_e=lv95_e, lv95_n=lv95_n)

    osm = {}
    if include_osm:
        osm = fetch_osm_reverse(client, sources, lat=selected.lat, lon=selected.lon, min_delay_s=osm_min_delay)
    else:
        sources.disable("osm_reverse", "per Flag deaktiviert")

    mod = load_gwr_codes(GWR_CODES_PATH)
    decoded = mod.summarize_building(gwr)
    sources.note_success("gwr_codes", "local://gwr_codes", records=1, optional=False)

    heating_layer_text = None
    if heating:
        heating_layer_text = {
            "waermeerzeuger_heizung_1": heating.get("gwaerzh1_de"),
            "energiequelle_heizung_1": heating.get("genh1_de"),
            "informationsquelle_heizung_1": heating.get("gwaersceh1_de"),
            "aktualisiert_heizung_1": heating.get("gwaerdath1"),
            "datenstand_layer": heating.get("gexpdat"),
        }

    confidence = compute_confidence(
        selected=selected,
        candidates=candidates,
        sources=sources,
        heating_layer=heating,
        plz_layer=plz_layer,
        admin_boundary=admin_boundary,
        osm=osm,
    )

    suitability_light = evaluate_suitability_light(
        elevation_m=elevation.get("height_m"),
        has_road_access=bool((osm.get("address") or {}).get("road") or gwr.get("strname_deinr")),
        confidence_score=confidence.get("score"),
        building_status=decoded.get("status"),
        has_plz=bool(plz_layer.get("plz") or gwr.get("plz_plz6")),
        has_admin_boundary=bool(admin_boundary.get("gemname") or gwr.get("ggdename")),
    )

    candidate_preview_count = max(1, min(candidate_preview, len(candidates))) if candidates else 0
    candidate_preview_data = [c.to_preview() for c in candidates[:candidate_preview_count]]
    candidate_preview_data.sort(key=lambda x: x.get("score", 0), reverse=True)

    intelligence = build_intelligence_layers(
        mode=intelligence_mode,
        client=client,
        sources=sources,
        query=query,
        selected=selected,
        confidence=confidence,
        plz_layer=plz_layer,
        admin_boundary=admin_boundary,
    )
    executive_risk = intelligence.get("executive_risk_summary") or {}
    building_profile = build_building_core_profile(
        gwr=gwr,
        decoded=decoded,
        address_registry=addr,
    )

    compact_summary = {
        "query": address_query,
        "matched_address": selected.label,
        "confidence": confidence,
        "egid": gwr.get("egid"),
        "egrid": gwr.get("egrid"),
        "gemeinde": gwr.get("ggdename"),
        "kanton": gwr.get("gdekt"),
        "baujahr": building_profile.get("baujahr"),
        "elevation_m": elevation.get("height_m"),
        "energie": compact_energy_summary(decoded),
        "sources": {k: v["status"] for k, v in sources.as_dict().items()},
        "executive": {
            "needs_review": False,
            "verdict": "ok",
            "ambiguity_level": confidence.get("ambiguity", {}).get("level", "none"),
            "ambiguity_gap": confidence.get("ambiguity", {}).get("score_gap_to_next"),
            "warnings": confidence.get("warnings") or [],
        },
        "intelligence": {
            "mode": intelligence_mode,
            "tenants_businesses": {
                "status": (intelligence.get("tenants_businesses") or {}).get("status"),
                "count": len((intelligence.get("tenants_businesses") or {}).get("entities") or []),
            },
            "incidents_timeline": {
                "status": (intelligence.get("incidents_timeline") or {}).get("status"),
                "events": len((intelligence.get("incidents_timeline") or {}).get("events") or []),
                "relevant_events": (intelligence.get("incidents_timeline") or {}).get("relevant_event_count", 0),
            },
            "environment_profile": {
                "status": (intelligence.get("environment_profile") or {}).get("status"),
                "overall_score": ((intelligence.get("environment_profile") or {}).get("metrics") or {}).get("overall_score"),
                "poi_total": ((intelligence.get("environment_profile") or {}).get("counts") or {}).get("poi_total"),
            },
            "environment_noise_risk": {
                "status": (intelligence.get("environment_noise_risk") or {}).get("status"),
                "level": (intelligence.get("environment_noise_risk") or {}).get("level"),
                "score": (intelligence.get("environment_noise_risk") or {}).get("score"),
            },
            "consistency_checks": {
                "status": (intelligence.get("consistency_checks") or {}).get("status"),
                "overall": (intelligence.get("consistency_checks") or {}).get("overall"),
                "risk_score": (intelligence.get("consistency_checks") or {}).get("risk_score"),
            },
            "executive_risk": {
                "traffic_light": executive_risk.get("traffic_light"),
                "risk_score": executive_risk.get("risk_score"),
                "summary": executive_risk.get("summary"),
            },
        },
        "suitability_light": {
            "status": suitability_light.get("status"),
            "score": suitability_light.get("score"),
            "traffic_light": suitability_light.get("traffic_light"),
            "classification": suitability_light.get("classification"),
        },
        "map": f"https://map.geo.admin.ch/?lang=de&topic=ech&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.bfs.gebaeude_wohnungs_register&E={gwr.get('gkode')}&N={gwr.get('gkodn')}&zoom=10",
    }

    resolution_ids = derive_resolution_identifiers(
        feature_id=selected.feature_id,
        gwr_attrs=gwr,
        lat=selected.lat,
        lon=selected.lon,
    )

    report = {
        "query": address_query,
        "matched_address": selected.label,
        "match": {
            "selected_feature_id": selected.feature_id,
            "selected_score": round(selected.total_score, 2),
            "candidate_count": len(candidates),
            "candidates_preview": candidate_preview_data,
            "query_parts": {
                "street": query.street,
                "house_number": query.house_number,
                "postal_code": query.postal_code,
                "city": query.city,
            },
            "resolution": {
                "pipeline_version": "v1",
                "strategy": "provider_neutral_address_resolution",
                "provider_path": [
                    "candidate_search",
                    "candidate_hydration",
                    "cross_source_enrichment",
                ],
                "selected_origin": selected.origin,
                "selected_feature_id": selected.feature_id,
            },
        },
        "confidence": confidence,
        "coordinates": {
            "lat": selected.lat,
            "lon": selected.lon,
            "lv95_e": gwr.get("gkode"),
            "lv95_n": gwr.get("gkodn"),
        },
        "ids": {
            "feature_id": selected.feature_id,
            "egid": gwr.get("egid"),
            "egaid": gwr.get("egaid"),
            "egrid": gwr.get("egrid"),
            "esid": gwr.get("esid"),
            "edid": gwr.get("edid"),
            "entity_id": resolution_ids.get("entity_id"),
            "location_id": resolution_ids.get("location_id"),
            "resolution_id": resolution_ids.get("resolution_id"),
        },
        "administrative": {
            "strasse_nummer": gwr.get("strname_deinr"),
            "plz_plz6": gwr.get("plz_plz6"),
            "ort": gwr.get("dplzname"),
            "gemeinde": gwr.get("ggdename"),
            "gemeinde_bfs": gwr.get("ggdenr"),
            "kanton": gwr.get("gdekt"),
        },
        "building": building_profile,
        "energy": {
            "raw_codes": {
                "gwaerzh1": gwr.get("gwaerzh1"),
                "genh1": gwr.get("genh1"),
                "gwaerzh2": gwr.get("gwaerzh2"),
                "genh2": gwr.get("genh2"),
                "gwaerzw1": gwr.get("gwaerzw1"),
                "genw1": gwr.get("genw1"),
                "gwaerzw2": gwr.get("gwaerzw2"),
                "genw2": gwr.get("genw2"),
            },
            "decoded_summary": {
                "heizung": decoded.get("heizung"),
                "warmwasser": decoded.get("warmwasser"),
            },
            "heating_layer": heating_layer_text,
        },
        "address_registry": {
            "adr_egaid": addr.get("adr_egaid"),
            "adr_status": addr.get("adr_status"),
            "adr_official": addr.get("adr_official"),
            "adr_modified": addr.get("adr_modified"),
            "bdg_category": addr.get("bdg_category"),
        },
        "cross_source": {
            "plz_layer": {
                "plz": plz_layer.get("plz"),
                "zusatz": plz_layer.get("zusziff"),
                "ortschaft": plz_layer.get("langtext"),
                "status": plz_layer.get("status"),
                "modified": plz_layer.get("modified"),
            },
            "admin_boundary": {
                "gemeinde": admin_boundary.get("gemname"),
                "gemeinde_bfs": admin_boundary.get("gde_nr"),
                "kanton": admin_boundary.get("kanton"),
                "stand_jahr": admin_boundary.get("jahr"),
                "is_current": admin_boundary.get("is_current_jahr"),
            },
            "elevation": elevation,
            "osm_reverse": osm,
        },
        "sources": sources.as_dict(),
        "source_classification": source_catalog_view(sources.as_dict()),
        "source_attribution": {
            "match": ["geoadmin_search", "geoadmin_address", "geoadmin_gwr"],
            "building_energy": ["geoadmin_gwr", "bfs_heating_layer", "gwr_codes"],
            "postal_consistency": ["plz_layer_identify", "swissboundaries_identify", "osm_reverse"],
            "elevation_context": ["swisstopo_height"],
            "intelligence": ["osm_poi_overpass", "google_news_rss"],
        },
        "intelligence": intelligence,
        "suitability_light": suitability_light,
        "summary_compact": compact_summary,
        "links": {
            "map_geo_admin": compact_summary["map"],
            "gwr_api_object": mapserver_feature_url("ch.bfs.gebaeude_wohnungs_register", selected.feature_id),
            "address_api_object": mapserver_feature_url("ch.swisstopo.amtliches-gebaeudeadressverzeichnis", selected.feature_id),
        },
    }

    report["field_provenance"] = build_field_provenance(report)
    report["executive_summary"] = build_executive_summary(report)
    report["summary_compact"]["executive"] = report["executive_summary"]
    report["summary_compact"]["intelligence"]["executive_risk"] = (
        (report.get("intelligence") or {}).get("executive_risk_summary") or {}
    )

    return report


def summarize_sources(sources: Dict[str, Dict[str, Any]]) -> str:
    chunks = []
    for name, info in sources.items():
        status = info.get("status")
        if status == "ok":
            emoji = "✅"
        elif status == "partial":
            emoji = "🟨"
        elif status == "disabled":
            emoji = "⏸️"
        elif status == "error":
            emoji = "❌"
        else:
            emoji = "•"
        chunks.append(f"{emoji} {name}:{status}")
    return " | ".join(chunks)


def print_human_city_ranking(report: Dict[str, Any]) -> None:
    executive = report.get("executive") or {}
    city = report.get("city") or {}
    params = report.get("parameters") or {}
    top = report.get("top_zones") or []

    print(executive.get("headline") or f"City-Ranking für {city.get('query')}")
    print(
        f"Anker: {city.get('label')} | Grid {params.get('grid_size')}x{params.get('grid_size')} | "
        f"Radius {params.get('zone_radius_m')}m | Spacing {params.get('zone_spacing_m')}m"
    )

    city_safety = report.get("city_safety") or {}
    print(
        "Executive: "
        f"Ampel {executive.get('traffic_light')} | "
        f"Ø Top-Score {executive.get('avg_top_score')} | "
        f"Verteilung {executive.get('traffic_counts')}"
    )
    print(
        "Stadtweite Sicherheit: "
        f"Risk {city_safety.get('incident_risk_score')} "
        f"({city_safety.get('uncertainty')}, status={city_safety.get('status')}, "
        f"events={city_safety.get('relevant_event_count')})"
    )
    if executive.get("recommendation_explanation"):
        print(f"Empfehlung: {executive.get('recommendation_explanation')}")

    target = report.get("target") or {}
    if target.get("query"):
        if target.get("label"):
            print(
                "Zieladresse: "
                f"{target.get('label')} -> nächste Zone {target.get('nearest_zone_code')} "
                f"(Rank {target.get('nearest_zone_rank')}, {int(target.get('nearest_zone_distance_m') or 0)}m)"
            )
        else:
            print("Zieladresse: keine robuste Georeferenz möglich (Nähebewertung deaktiviert).")

    print("\nHeatmap (Nord oben):")
    print(report.get("heatmap_text") or "-")

    map_info = report.get("map") or {}
    output = report.get("output") or {}
    if map_info.get("map_png_path"):
        print(
            "\nKarte (PNG): "
            f"{map_info.get('map_png_path')} "
            f"[status={map_info.get('status')}, style={map_info.get('style')}, zoom={map_info.get('zoom')}, "
            f"legend={map_info.get('map_legend_mode')}]"
        )
    elif output.get("map_status") in {"failed", "degraded"}:
        print(f"\nKarte (PNG): nicht verfügbar (status={output.get('map_status')})")

    print("\nTop-Zonen:")
    for zone in top:
        m = zone.get("metrics") or {}
        reasons = [r.get("text") for r in (zone.get("reasons") or [])[:3] if r.get("text")]
        print(
            f"- #{zone.get('rank')} {zone.get('zone_code')} ({zone.get('zone_name')}): "
            f"{zone.get('overall_score')}/100 | Ampel {zone.get('traffic_light')} | "
            f"Ruhe {m.get('ruhe')}, ÖV {m.get('oev')}, Einkauf {m.get('einkauf')}, "
            f"Grün {m.get('gruen')}, Sicherheit {m.get('sicherheit')}, Nacht {m.get('nachtaktivitaet')}"
        )
        if reasons:
            for reason in reasons:
                print(f"  • {reason}")
        for driver in ((zone.get("weight_model") or {}).get("drivers") or [])[:2]:
            if driver.get("text"):
                print(f"  • Gewicht: {driver.get('text')}")
        sec = zone.get("security_overview") or {}
        if sec.get("headline"):
            print(f"  • Sicherheitssignale: {sec.get('headline')} (status={sec.get('status')})")
        split = zone.get("security_evidence_split") or {}
        if split:
            print(
                f"  • Evidenztrennung: Fakten={split.get('hard_facts')} | "
                f"Signale={split.get('indicative_signals')}"
            )
        facts = zone.get("security_facts") or []
        if facts:
            print(f"  • Fakt: {(facts[0] or {}).get('text')} -> {(facts[0] or {}).get('value')}")
        if zone.get("is_target_nearest"):
            print(f"  • Zielbezug: nächstgelegene Zone zur Zieladresse ({int(zone.get('distance_to_target_m') or 0)}m)")
        if zone.get("quality_note"):
            print(f"  • Datenlage: {zone.get('quality_note')}")

    if map_info.get("warnings"):
        print("\nKarten-Hinweise:")
        for note in (map_info.get("warnings") or [])[:3]:
            print(f"- {note}")
    if map_info.get("degradation_reasons"):
        print("- Degradation-Codes: " + ", ".join(map_info.get("degradation_reasons") or []))

    print("\nQuelle-Hinweis: Sicherheitsaussagen sind konservative Indikatoren aus öffentlichen Web-/Community-Daten.")


def print_human_full(report: Dict[str, Any]) -> None:
    b = report["building"]
    e = report["energy"]
    ids = report["ids"]
    adm = report["administrative"]
    conf = report["confidence"]

    print(f"Adresse: {report['matched_address']}")
    print(f"Confidence: {conf['score']}/{conf['max']} ({conf['level']})")
    print(
        "Komponenten: "
        f"Match {conf['components']['match_quality']}, "
        f"Vollst. {conf['components']['data_completeness']}, "
        f"Konsistenz {conf['components']['cross_source_consistency']}, "
        f"Quellen {conf['components']['required_source_health']}"
    )
    exec_sum = report.get("executive_summary") or {}
    if exec_sum.get("needs_review"):
        print(f"⚠️ Review: {exec_sum.get('headline')}")
    for warning in exec_sum.get("warnings") or []:
        print(f"  - Warnung: {warning}")
    print(f"Koordinaten: {report['coordinates']['lat']}, {report['coordinates']['lon']}")
    print(f"EGID/EGRID: {ids.get('egid')} / {ids.get('egrid')}")
    print(f"Gemeinde/Kanton: {adm.get('gemeinde')} ({adm.get('gemeinde_bfs')}), {adm.get('kanton')}")
    elevation = ((report.get("cross_source") or {}).get("elevation") or {}).get("height_m")
    if elevation is not None:
        print(f"Höhe (swisstopo): {elevation} m ü. M.")

    print("\nGebäude:")
    print(f"- Name/Nutzung: {b.get('name')}")
    print(f"- Baujahr: {b.get('baujahr')}, Geschosse: {b.get('geschosse')}, Wohnungen: {b.get('wohnungen')}")
    print(f"- Fläche: {b.get('flaeche_m2')} m²")

    print("\nEnergie:")
    hz = e.get("decoded_summary", {}).get("heizung") or []
    ww = e.get("decoded_summary", {}).get("warmwasser") or []
    print("- Heizung:")
    for item in hz or ["(keine Angabe)"]:
        print(f"  • {item}")
    print("- Warmwasser:")
    for item in ww or ["(keine Angabe)"]:
        print(f"  • {item}")

    hl = e.get("heating_layer")
    if hl:
        print("\nHeiz-Layer (Klartext):")
        print(f"- Wärmeerzeuger: {hl.get('waermeerzeuger_heizung_1')}")
        print(f"- Energiequelle: {hl.get('energiequelle_heizung_1')}")
        print(f"- Quelle: {hl.get('informationsquelle_heizung_1')}")
        print(f"- Aktualisiert: {hl.get('aktualisiert_heizung_1')} (Layerstand {hl.get('datenstand_layer')})")

    cands = report.get("match", {}).get("candidates_preview", [])
    if cands:
        print("\nTop-Kandidaten:")
        for c in cands:
            print(f"- {c['label']} | Score {c['score']}")

    plz = report.get("cross_source", {}).get("plz_layer", {})
    if plz:
        print("\nPLZ-Ortschafts-Layer:")
        print(f"- PLZ: {plz.get('plz')} | Ortschaft: {plz.get('ortschaft')} | Status: {plz.get('status')}")

    print("\nQuellenstatus:")
    print(summarize_sources(report.get("sources", {})))

    intel = report.get("intelligence") or {}
    risk = intel.get("executive_risk_summary") or {}
    print("\nExecutive Risk:")
    if risk:
        print(f"- {risk.get('summary')} | Gründe: {', '.join(risk.get('reasons') or ['-'])}")
    else:
        print("- (keine Risk-Summary)")

    tenants = intel.get("tenants_businesses") or {}
    incidents = intel.get("incidents_timeline") or {}
    env = intel.get("environment_noise_risk") or {}
    consistency = intel.get("consistency_checks") or {}

    print("\nIntelligence-Layer:")
    print(
        f"- tenants_businesses: {tenants.get('status')}"
        f" ({len(tenants.get('entities') or [])} Signale)"
    )
    for item in (tenants.get("entities") or [])[:5]:
        print(f"  • {item.get('name')} [{item.get('category')}:{item.get('subcategory')}] {int(item.get('distance_m') or 0)}m ({item.get('status')})")

    print(
        f"- incidents_timeline: {incidents.get('status')}"
        f" ({len(incidents.get('events') or [])} Hinweise, relevant={incidents.get('relevant_event_count', 0)})"
    )
    for event in (incidents.get("events") or [])[:4]:
        print(f"  • {event.get('date') or '?'} | {event.get('title')} ({event.get('status')})")

    print(
        f"- environment_noise_risk: {env.get('status')} | "
        f"Level {env.get('level')} | Score {env.get('score')} | Ampel {env.get('traffic_light')}"
    )
    for reason in env.get("reasons") or []:
        print(f"  • {reason}")

    print(
        f"- consistency_checks: {consistency.get('status')} | "
        f"overall={consistency.get('overall')} | risk={consistency.get('risk_score')}"
    )
    for check in (consistency.get("checks") or [])[:5]:
        print(f"  • {check.get('id')}: {check.get('result')} ({check.get('status')}) – {check.get('message')}")

    print("\nLinks:")
    print(f"- map.geo.admin.ch: {report['links']['map_geo_admin']}")


def print_human_compact(report: Dict[str, Any]) -> None:
    s = report["summary_compact"]
    energy = s["energie"]
    conf = s["confidence"]
    executive = s.get("executive") or {}
    intel = s.get("intelligence") or {}
    risk = intel.get("executive_risk") or {}

    print(f"{s['matched_address']} | Confidence {conf['score']}/{conf['max']} ({conf['level']})")
    print(
        f"EGID {s.get('egid')} | EGRID {s.get('egrid')} | "
        f"{s.get('gemeinde')} ({s.get('kanton')}) | Baujahr {s.get('baujahr')} | Höhe {s.get('elevation_m')} m"
    )
    print(f"Heizung: {energy['heizung']}")
    print(f"Warmwasser: {energy['warmwasser']}")
    if executive.get("needs_review"):
        print(f"Review: {executive.get('headline')}")
        for warning in executive.get("warnings") or []:
            print(f"- {warning}")

    if risk:
        print(f"Risk: {risk.get('summary')} (Score {risk.get('risk_score')}, Ampel {risk.get('traffic_light')})")

    print(
        "Intelligence: "
        f"mode={intel.get('mode')} | tenants={((intel.get('tenants_businesses') or {}).get('count'))} | "
        f"incidents={((intel.get('incidents_timeline') or {}).get('events'))} | "
        f"noise={((intel.get('environment_noise_risk') or {}).get('level'))}"
    )
    print(f"Quellen: {', '.join(f'{k}:{v}' for k, v in s.get('sources', {}).items())}")
    print(f"Karte: {s['map']}")


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " | ".join(str(v) for v in value if v not in (None, ""))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def flatten_report_for_csv(report: Dict[str, Any]) -> Dict[str, Any]:
    summary = report.get("summary_compact") or {}
    conf = summary.get("confidence") or {}
    executive = summary.get("executive") or {}
    intel = summary.get("intelligence") or {}
    risk = intel.get("executive_risk") or {}

    row = {
        "row": report.get("batch_meta", {}).get("row"),
        "query": report.get("query"),
        "status": report.get("batch_meta", {}).get("status", "ok"),
        "error_code": report.get("batch_meta", {}).get("error_code"),
        "error_type": report.get("batch_meta", {}).get("error_type"),
        "error": report.get("batch_meta", {}).get("error"),
        "matched_address": summary.get("matched_address"),
        "confidence_score": conf.get("score"),
        "confidence_level": conf.get("level"),
        "needs_review": executive.get("needs_review"),
        "ambiguity_level": executive.get("ambiguity_level"),
        "ambiguity_gap": executive.get("ambiguity_gap"),
        "intelligence_mode": intel.get("mode"),
        "risk_traffic_light": risk.get("traffic_light"),
        "risk_score": risk.get("risk_score"),
        "egid": summary.get("egid"),
        "egrid": summary.get("egrid"),
        "gemeinde": summary.get("gemeinde"),
        "kanton": summary.get("kanton"),
        "baujahr": summary.get("baujahr"),
        "elevation_m": summary.get("elevation_m"),
        "heizung": (summary.get("energie") or {}).get("heizung"),
        "warmwasser": (summary.get("energie") or {}).get("warmwasser"),
        "warnings": executive.get("warnings"),
        "risk_reasons": risk.get("reasons"),
        "map_link": summary.get("map"),
        "sources_ok": "; ".join(f"{k}:{v}" for k, v in (summary.get("sources") or {}).items()),
    }
    return {k: _csv_value(row.get(k)) for k in CSV_EXPORT_FIELDS}


def write_csv(path: str, rows: List[Dict[str, Any]], *, fieldnames: List[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _emit_export_log(
    *,
    path: str,
    channel: str,
    export_kind: str,
    row_count: int,
    error_count: int = 0,
    status: str = "ok",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort compliance export logging (must never block exports)."""

    try:
        record_export_log_entry(
            channel=channel,
            artifact_path=path,
            export_kind=export_kind,
            row_count=row_count,
            error_count=error_count,
            status=status,
            details=details or {},
        )
    except Exception:
        # Compliance logging is additive and must not break primary export workflows.
        return


def classify_error(ex: Exception) -> str:
    if isinstance(ex, NoAddressMatchError):
        return "NO_MATCH"
    if isinstance(ex, ExternalRequestError):
        return "EXTERNAL_REQUEST"
    if isinstance(ex, ValueError):
        return "INPUT"
    if isinstance(ex, AddressIntelError):
        return "DOMAIN"
    return "UNEXPECTED"


def normalize_error_row(query: str, row_number: int, ex: Exception) -> Dict[str, Any]:
    return {
        "query": query,
        "batch_meta": {
            "row": row_number,
            "status": "error",
            "error_code": classify_error(ex),
            "error_type": ex.__class__.__name__,
            "error": str(ex),
        },
        "summary_compact": {
            "query": query,
            "matched_address": None,
            "confidence": {"score": None, "max": 100, "level": "low"},
            "egid": None,
            "egrid": None,
            "gemeinde": None,
            "kanton": None,
            "baujahr": None,
            "elevation_m": None,
            "energie": {"heizung": None, "warmwasser": None},
            "sources": {},
            "executive": {
                "verdict": "review",
                "needs_review": True,
                "ambiguity_level": "none",
                "ambiguity_gap": None,
                "warnings": [str(ex)],
            },
            "intelligence": {
                "mode": "basic",
                "tenants_businesses": {"status": "error", "count": 0},
                "incidents_timeline": {"status": "error", "events": 0, "relevant_events": 0},
                "environment_noise_risk": {"status": "error", "level": "unknown", "score": 0},
                "consistency_checks": {"status": "error", "overall": "unknown", "risk_score": 100},
                "executive_risk": {
                    "traffic_light": "red",
                    "risk_score": 100,
                    "summary": "🔴 Risikoampel: RED (Fehlerfall)",
                    "reasons": [str(ex)],
                },
            },
            "map": None,
        },
    }


def run_batch(
    csv_path: str,
    address_column: str,
    *,
    include_osm: bool,
    candidate_limit: int,
    candidate_preview: int,
    timeout: int,
    retries: int,
    backoff_seconds: float,
    min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL,
    osm_min_delay: float,
    cache_ttl_seconds: float,
    intelligence_mode: str,
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    stats = {
        "processed": 0,
        "ok": 0,
        "error": 0,
        "skipped_empty": 0,
    }

    shared_client = HttpClient(
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff_seconds,
        min_request_interval_seconds=max(0.0, min_request_interval_seconds),
        cache_ttl_seconds=max(0.0, cache_ttl_seconds),
    )

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        available = reader.fieldnames or []
        if address_column not in available:
            raise ValueError(f"CSV-Spalte '{address_column}' nicht gefunden. Vorhanden: {available}")

        for row_number, row in enumerate(reader, start=2):
            address = (row.get(address_column) or "").strip()
            # Robustheit: unquotierte CSV-Zeilen mit Kommata landen in row[None]
            extras = row.get(None) or []
            if extras:
                combined = ",".join([address] + [str(x) for x in extras if str(x).strip()])
                address = combined.strip(" ,")

            if not address:
                stats["skipped_empty"] += 1
                continue

            stats["processed"] += 1
            try:
                rep = build_report(
                    address,
                    include_osm=include_osm,
                    candidate_limit=candidate_limit,
                    candidate_preview=candidate_preview,
                    timeout=timeout,
                    retries=retries,
                    backoff_seconds=backoff_seconds,
                    osm_min_delay=osm_min_delay,
                    cache_ttl_seconds=cache_ttl_seconds,
                    intelligence_mode=intelligence_mode,
                    client=shared_client,
                )
                rep["batch_meta"] = {"row": row_number, "status": "ok"}
                stats["ok"] += 1
            except Exception as ex:
                rep = normalize_error_row(address, row_number, ex)
                stats["error"] += 1
            results.append(rep)

    return {"rows": results, "stats": stats}


def write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_self_check(verbose: bool = False) -> Dict[str, Any]:
    """Leichter Offline-Self-Check (ohne externe Requests)."""
    checks: List[Tuple[str, bool, str]] = []

    qp = parse_query_parts("Wassergasse 24, 9000 St. Gallen")
    checks.append(("parse_street", qp.street == "wassergasse", f"street={qp.street}"))
    checks.append(("parse_house", qp.house_number == "24", f"house={qp.house_number}"))
    checks.append(("parse_postal", qp.postal_code == "9000", f"postal={qp.postal_code}"))

    exact = {
        "featureId": "111_0",
        "label": "Wassergasse 24 <b>9000 St. Gallen</b>",
        "detail": "wassergasse 24 9000 st. gallen",
        "origin": "address",
        "rank": 7,
    }
    fuzzy = {
        "featureId": "222_0",
        "label": "Burgstrasse 24 <b>9000 St. Gallen</b>",
        "detail": "burgstrasse 24 9000 st. gallen",
        "origin": "address",
        "rank": 7,
    }
    s1, _ = score_candidate_pre(exact, qp)
    s2, _ = score_candidate_pre(fuzzy, qp)
    checks.append(("candidate_scoring", s1 > s2, f"exact={s1:.1f}, fuzzy={s2:.1f}"))

    dummy_sources = SourceRegistry()
    dummy_sources.note_success("geoadmin_search", "https://example.test")
    dummy_sources.note_success("geoadmin_gwr", "https://example.test")
    dummy_sources.note_success("geoadmin_address", "https://example.test")

    selected = CandidateEval(
        feature_id="111_0",
        label="Wassergasse 24 9000 St. Gallen",
        detail="",
        origin="address",
        rank=1,
        lat=47.4,
        lon=9.3,
        pre_score=60,
        total_score=95,
        address_attrs={"adr_official": True},
        gwr_attrs={
            "egid": 123,
            "egrid": "CH123",
            "esid": 1,
            "gstat": 1004,
            "gbauj": 1990,
            "garea": 100,
            "gastw": 4,
            "ganzwhg": 8,
            "plz_plz6": 9000,
            "dplzname": "St. Gallen",
        },
    )
    conf = compute_confidence(
        selected=selected,
        candidates=[selected],
        sources=dummy_sources,
        heating_layer={"genh1_de": "Fernwärme"},
        plz_layer={"plz": 9000, "langtext": "St. Gallen"},
        admin_boundary={"gemname": "St. Gallen", "kanton": "SG"},
        osm={"address": {"postcode": "9000", "city": "St. Gallen"}},
    )
    checks.append(("confidence_high", conf["score"] >= 75, f"score={conf['score']}"))

    weights = parse_area_weights("ruhe=1.3,ov=0.9,safety=1.6,nightlife=0.2")
    checks.append(("area_weights_parse", weights["oev"] == 0.9 and weights["sicherheit"] == 1.6, f"weights={weights}"))

    map_style = canonical_map_style("standard")
    hot_style = canonical_map_style("hot")
    topo_style = canonical_map_style("topo")
    checks.append(("map_style_alias", map_style == "osm-standard", f"style={map_style}"))
    checks.append(("map_style_hot", hot_style == "osm-hot", f"style={hot_style}"))
    checks.append(("map_style_topo", topo_style == "opentopomap", f"style={topo_style}"))

    zone_scores = compute_zone_scores_from_indices(
        indices={
            "transit": 75,
            "shopping": 52,
            "green": 68,
            "nightlife": 20,
            "major_road": 15,
            "police": 35,
            "food": 40,
        },
        city_incident_risk=44,
        city_incident_status="ok",
        mode="extended",
    )
    checks.append(("zone_scoring", zone_scores["metrics"]["sicherheit"] >= 45, f"zone={zone_scores['metrics']}"))

    ok = all(item[1] for item in checks)
    if verbose:
        for name, passed, detail in checks:
            state = "OK" if passed else "FAIL"
            print(f"[{state}] {name}: {detail}")

    return {
        "ok": ok,
        "checks": [
            {"name": name, "ok": passed, "detail": detail}
            for name, passed, detail in checks
        ],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    description = "Adress- und Area-Report via swisstopo/GWR + freie Quellen (robust, mit Matching-Heuristik)"
    epilog = """
Beispiele:
  # Einzeladresse (menschlich lesbar)
  python address_intel.py "Wassergasse 24, 9000 St. Gallen"

  # JSON full / compact
  python address_intel.py "Bahnhofstrasse 1, Zürich" --json
  python address_intel.py "Bahnhofstrasse 1, Zürich" --json --summary-mode compact

  # Intelligence-Modi
  python address_intel.py "Bahnhofstrasse 1, Zürich" --intelligence-mode basic
  python address_intel.py "Bahnhofstrasse 1, Zürich" --intelligence-mode extended --json
  python address_intel.py "Bahnhofstrasse 1, Zürich" --intelligence-mode risk --summary-mode compact

  # Batch inkl. JSONL + CSV + Fehlerreport
  python address_intel.py --batch-csv input.csv --address-column address \
    --out-jsonl out.jsonl --out-csv out.csv --out-error-csv out.errors.csv

  # City/Area-Ranking (Reverse-Use-Case Wohngegend)
  python address_intel.py --area-mode city-ranking --city "St. Gallen" --top-n 6

  # City-Ranking mit personalisierten Gewichten
  python address_intel.py --area-mode city-ranking --city "Zürich" \
    --area-weights "ruhe=1.4,oev=1.2,einkauf=0.8,gruen=1.0,sicherheit=1.6,nachtaktivitaet=0.4" --json --summary-mode compact

  # City-Ranking inkl. OSM-Karte als PNG (Standard)
  python address_intel.py --area-mode city-ranking --city "St. Gallen" \
    --map-png --map-out ./output/stgallen_map.png --map-style osm-standard --map-zoom 14

  # Zieladresse im Ranking referenzieren (nächstgelegene Zone hervorheben)
  python address_intel.py --area-mode city-ranking --city "Zürich" \
    --target-address "Bahnhofstrasse 1, 8001 Zürich" --map-png --map-legend on --json --summary-mode compact

  # Alternative Kartenstile (lizenzkonform mit Attribution im PNG)
  python address_intel.py --area-mode city-ranking --city "Zürich" \
    --map-png --map-style osm-hot --map-out ./output/zuerich_hot.png
  python address_intel.py --area-mode city-ranking --city "Chur" \
    --map-png --map-style opentopomap --map-out ./output/chur_topo.png

  # City-Ranking Preset "ruhig & sicher" (Gewichte + Risiko-Modus)
  python address_intel.py --area-mode city-ranking --city "Winterthur" --grid-size 3 --top-n 6 \
    --weights "ruhe=1.5,oev=0.9,einkauf=0.8,gruen=1.2,sicherheit=1.8,nachtaktivitaet=0.3" \
    --intelligence-mode risk --json --summary-mode compact

  # Self-check (ohne Netz)
  python address_intel.py --self-check
"""
    ap = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )

    ap.add_argument("address", nargs="?", help="Adresse in der Schweiz (Einzelmodus)")
    ap.add_argument(
        "--area-mode",
        choices=list(AREA_MODES),
        default="address-report",
        help="Modus: address-report (Default) oder city-ranking",
    )
    ap.add_argument("--city", help="Stadtname für --area-mode city-ranking")
    ap.add_argument("--target-address", help="Optionale Zieladresse für city-ranking (nächstgelegene Zone markieren/erklären)")
    ap.add_argument("--top-n", type=int, default=6, help="Top-N Zonen für City-Ranking (default: 6)")
    ap.add_argument("--grid-size", type=int, default=3, help="Rastergröße (ungerade Zahl, default: 3)")
    ap.add_argument("--zone-spacing", type=int, default=450, help="Abstand der Zonenzentren in Metern (default: 450)")
    ap.add_argument("--zone-radius", type=int, default=320, help="Analyse-Radius pro Zone in Metern (default: 320)")
    ap.add_argument(
        "--weights",
        "--area-weights",
        dest="area_weights",
        help=(
            "Gewichte für City-Ranking als key=value-Liste, z.B. "
            "ruhe=1.2,oev=1.1,einkauf=0.8,gruen=1.0,sicherheit=1.5,nachtaktivitaet=0.4"
        ),
    )
    ap.add_argument("--map-png", action="store_true", help="Im city-ranking-Modus zusätzlich eine OSM-Karte als PNG rendern")
    ap.add_argument("--map-out", help="Ausgabepfad für --map-png (default: skills/swisstopo/output/city_ranking_<city>_<ts>.png)")
    ap.add_argument(
        "--map-style",
        default=DEFAULT_MAP_STYLE,
        help=f"Kartenstil für PNG (default: {DEFAULT_MAP_STYLE}; aktuell unterstützt: {', '.join(sorted(MAP_STYLE_CONFIG.keys()))})",
    )
    ap.add_argument("--map-zoom", type=int, help="Optionaler fixer Kartenzoom (9-19). Ohne Angabe wird Auto-Zoom verwendet")
    ap.add_argument(
        "--map-legend",
        choices=["auto", "on", "off"],
        default=DEFAULT_MAP_LEGEND_MODE,
        help="Legendenmodus für PNG-Karte (auto|on|off, default: auto)",
    )

    ap.add_argument("--json", action="store_true", help="JSON ausgeben")
    ap.add_argument(
        "--summary-mode",
        choices=["full", "compact"],
        default="full",
        help="Ausgabemodus (default: full)",
    )
    ap.add_argument(
        "--intelligence-mode",
        choices=list(INTELLIGENCE_MODES),
        default="basic",
        help="Intelligence-Tiefe: basic (nur Kernchecks), extended (POI+News), risk (konservatives Risikoscoring)",
    )

    ap.add_argument("--no-osm", action="store_true", help="OSM-Reverse-Geocoding deaktivieren")
    ap.add_argument("--osm-min-delay", type=float, default=1.0, help="Mindestabstand zwischen OSM-Requests in Sekunden (default: 1.0)")

    ap.add_argument("--candidates", type=int, default=8, help="Anzahl Suchkandidaten aus SearchServer (default: 8)")
    ap.add_argument("--candidate-preview", type=int, default=3, help="Anzahl Top-Kandidaten im Report (default: 3)")

    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"HTTP-Timeout in Sekunden (default: {DEFAULT_TIMEOUT})")
    ap.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help=f"Anzahl Retries pro Request (default: {DEFAULT_RETRIES})")
    ap.add_argument("--backoff", type=float, default=DEFAULT_BACKOFF, help=f"Backoff-Basis in Sekunden (default: {DEFAULT_BACKOFF})")
    ap.add_argument(
        "--min-request-interval",
        type=float,
        default=DEFAULT_MIN_REQUEST_INTERVAL,
        help=f"Mindestabstand zwischen API-Requests in Sekunden (default: {DEFAULT_MIN_REQUEST_INTERVAL})",
    )
    ap.add_argument("--cache-ttl", type=float, default=DEFAULT_CACHE_TTL, help=f"Kurzlebiger HTTP-Cache in Sekunden (default: {DEFAULT_CACHE_TTL})")

    ap.add_argument("--batch-csv", help="Batchmodus: CSV-Datei mit Adressen")
    ap.add_argument("--address-column", default="address", help="Spaltenname in der CSV (default: address)")
    ap.add_argument("--out-jsonl", help="Batchausgabe als JSONL-Datei")
    ap.add_argument("--out-csv", help="Batchausgabe als flache CSV-Datei")
    ap.add_argument("--out-error-csv", help="Batch-Fehlerreport als CSV")

    ap.add_argument("--self-check", action="store_true", help="Offline-Kernchecks ausführen und beenden")
    ap.add_argument("--self-check-verbose", action="store_true", help="Details zum Self-Check ausgeben")

    return ap


def main() -> int:
    ap = build_arg_parser()
    args = ap.parse_args()

    if args.self_check:
        result = run_self_check(verbose=args.self_check_verbose)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("SELF-CHECK OK" if result["ok"] else "SELF-CHECK FAILED")
            if args.self_check_verbose:
                for check in result["checks"]:
                    print(
                        f"- {'OK' if check['ok'] else 'FAIL'} {check['name']}: {check['detail']}"
                    )
        return EXIT_OK if result["ok"] else EXIT_USAGE

    include_osm = not args.no_osm

    try:
        if args.area_mode == "city-ranking":
            if args.batch_csv:
                raise ValueError("--batch-csv ist nur im Modus address-report erlaubt.")
            if args.address:
                raise ValueError("Im city-ranking-Modus keine Einzeladresse angeben; nutze --city.")
            if not args.city:
                raise ValueError("Für --area-mode city-ranking ist --city erforderlich.")

            area_weights = parse_area_weights(args.area_weights)
            map_style = canonical_map_style(args.map_style)
            if not args.map_png and (
                args.map_out
                or args.map_zoom is not None
                or args.map_style != DEFAULT_MAP_STYLE
                or args.map_legend != DEFAULT_MAP_LEGEND_MODE
            ):
                raise ValueError("--map-out/--map-style/--map-zoom/--map-legend benötigen --map-png.")
            if args.map_zoom is not None and not (9 <= int(args.map_zoom) <= 19):
                raise ValueError("--map-zoom muss zwischen 9 und 19 liegen.")

            report = build_city_ranking_report(
                args.city,
                top_n=args.top_n,
                grid_size=args.grid_size,
                zone_spacing_m=args.zone_spacing,
                zone_radius_m=args.zone_radius,
                timeout=args.timeout,
                retries=args.retries,
                backoff_seconds=args.backoff,
                min_request_interval_seconds=max(0.0, args.min_request_interval),
                cache_ttl_seconds=max(0.0, args.cache_ttl),
                intelligence_mode=args.intelligence_mode,
                area_weights=area_weights,
                map_png=bool(args.map_png),
                map_out=args.map_out,
                map_style=map_style,
                map_zoom=args.map_zoom,
                map_legend=args.map_legend,
                target_address=args.target_address,
            )
        else:
            if (
                args.map_png
                or args.map_out
                or args.map_zoom is not None
                or args.map_style != DEFAULT_MAP_STYLE
                or args.map_legend != DEFAULT_MAP_LEGEND_MODE
                or args.target_address
            ):
                raise ValueError("Map-/Target-Flags (--map-* / --target-address) sind nur mit --area-mode city-ranking verfügbar.")
            if args.batch_csv:
                batch = run_batch(
                    args.batch_csv,
                    args.address_column,
                    include_osm=include_osm,
                    candidate_limit=args.candidates,
                    candidate_preview=args.candidate_preview,
                    timeout=args.timeout,
                    retries=args.retries,
                    backoff_seconds=args.backoff,
                    min_request_interval_seconds=max(0.0, args.min_request_interval),
                    osm_min_delay=max(0.0, args.osm_min_delay),
                    cache_ttl_seconds=max(0.0, args.cache_ttl),
                    intelligence_mode=args.intelligence_mode,
                )
                rows = batch["rows"]
                stats = batch["stats"]

                if args.out_jsonl:
                    write_jsonl(args.out_jsonl, rows)
                    _emit_export_log(
                        path=args.out_jsonl,
                        channel="file:jsonl",
                        export_kind="address-intel-batch-jsonl",
                        row_count=len(rows),
                        error_count=int(stats.get("error", 0)),
                        status="partial" if stats.get("error") else "ok",
                        details={
                            "scope": "batch-export",
                            "source": "src.api.address_intel",
                        },
                    )
                if args.out_csv:
                    flat_rows = [flatten_report_for_csv(r) for r in rows]
                    write_csv(args.out_csv, flat_rows, fieldnames=CSV_EXPORT_FIELDS)
                    _emit_export_log(
                        path=args.out_csv,
                        channel="file:csv",
                        export_kind="address-intel-batch-csv",
                        row_count=len(flat_rows),
                        error_count=int(stats.get("error", 0)),
                        status="partial" if stats.get("error") else "ok",
                        details={
                            "scope": "batch-export",
                            "field_count": len(CSV_EXPORT_FIELDS),
                            "source": "src.api.address_intel",
                        },
                    )
                if args.out_error_csv:
                    errors = [flatten_report_for_csv(r) for r in rows if r.get("batch_meta", {}).get("status") == "error"]
                    write_csv(
                        args.out_error_csv,
                        errors,
                        fieldnames=["row", "query", "status", "error_code", "error_type", "error"],
                    )
                    _emit_export_log(
                        path=args.out_error_csv,
                        channel="file:error-csv",
                        export_kind="address-intel-batch-error-csv",
                        row_count=len(errors),
                        error_count=len(errors),
                        status="ok",
                        details={
                            "scope": "batch-export",
                            "source": "src.api.address_intel",
                        },
                    )

                if args.json and not args.out_jsonl and not args.out_csv:
                    print(json.dumps(batch, ensure_ascii=False, indent=2))
                else:
                    print(
                        "Batch fertig: "
                        f"processed={stats['processed']}, ok={stats['ok']}, error={stats['error']}, skipped_empty={stats['skipped_empty']}"
                    )
                    if args.out_jsonl:
                        print(f"- JSONL: {args.out_jsonl}")
                    if args.out_csv:
                        print(f"- CSV: {args.out_csv}")
                    if args.out_error_csv:
                        print(f"- Fehlerreport: {args.out_error_csv}")
                return EXIT_BATCH_PARTIAL if stats.get("error") else EXIT_OK

            if not args.address:
                raise ValueError("Adresse fehlt. Entweder <address> angeben oder --batch-csv nutzen.")

            report = build_report(
                args.address,
                include_osm=include_osm,
                candidate_limit=args.candidates,
                candidate_preview=args.candidate_preview,
                timeout=args.timeout,
                retries=args.retries,
                backoff_seconds=args.backoff,
                min_request_interval_seconds=max(0.0, args.min_request_interval),
                osm_min_delay=max(0.0, args.osm_min_delay),
                cache_ttl_seconds=max(0.0, args.cache_ttl),
                intelligence_mode=args.intelligence_mode,
            )

    except NoAddressMatchError as ex:
        print(f"Kein belastbarer Adresstreffer: {ex}", file=sys.stderr)
        print("Hinweis: --candidate-preview erhöhen und Treffer manuell prüfen.", file=sys.stderr)
        return EXIT_NO_MATCH
    except ExternalRequestError as ex:
        print(f"Externe Quelle fehlgeschlagen: {ex.short()}", file=sys.stderr)
        return EXIT_EXTERNAL
    except ValueError as ex:
        print(f"Eingabefehler: {ex}", file=sys.stderr)
        return EXIT_USAGE
    except AddressIntelError as ex:
        print(f"Domänenfehler: {ex}", file=sys.stderr)
        return EXIT_RUNTIME
    except Exception as ex:
        print(f"Unerwarteter Fehler: {ex}", file=sys.stderr)
        return 1

    if args.json:
        if args.summary_mode == "compact":
            print(json.dumps(report.get("summary_compact", {}), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if args.area_mode == "city-ranking":
            print_human_city_ranking(report)
        elif args.summary_mode == "compact":
            print_human_compact(report)
        else:
            print_human_full(report)

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
