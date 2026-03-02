"""POI coverage regression guard (reference points).

Local run:

    ./.venv/bin/python -m pytest -q tests/test_poi_coverage_reference_points.py

Design:
- Deterministic/offline: no network calls to Overpass/Google News.
- We patch `fetch_osm_poi_overpass` to return fixture-based POIs per radius.
- We validate that `build_intelligence_layers(mode=extended)` produces a non-empty
  environment profile OR (if intentionally thin) emits the expected low_confidence
  signal with a stable fallback metadata shape.

This guards against regressions in:
- adaptive fallback radius sequence / attempt behaviour
- `low_confidence` wiring into the environment_profile layer
- accidental “empty POI section” outputs without explanation

Reference: WP #691 (parent #646).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import patch

from src.api import address_intel


_FIXTURE_PATH = Path(__file__).resolve().parent / "data" / "poi_reference_points_v1.json"


def _load_fixture() -> dict[str, Any]:
    payload = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _poi_catalog() -> list[Tuple[str, str]]:
    # keep it stable + representative across the domains used by the scoring.
    return [
        ("amenity", "bus_station"),
        ("amenity", "school"),
        ("amenity", "pharmacy"),
        ("amenity", "restaurant"),
        ("amenity", "bar"),
        ("shop", "supermarket"),
        ("shop", "convenience"),
        ("leisure", "park"),
        ("leisure", "playground"),
        ("office", "company"),
    ]


def _build_dummy_pois(*, count: int, radius_m: int) -> list[dict[str, Any]]:
    catalog = _poi_catalog()
    out: list[dict[str, Any]] = []
    for idx in range(max(0, int(count))):
        cat, sub = catalog[idx % len(catalog)]
        # Spread over the radius so ring logic is exercised.
        distance = min(max(15.0, 20.0 + (idx * 11.0)), float(max(radius_m, 1)))
        out.append(
            {
                "name": f"fixture-poi-{idx:03d}",
                "category": cat,
                "subcategory": sub,
                "distance_m": round(distance, 1),
                "lat": 0.0,
                "lon": 0.0,
                "address_hint": None,
                "tags": {"name": f"fixture-poi-{idx:03d}"},
            }
        )
    return out


class TestPoiCoverageReferencePoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = _load_fixture()
        cls.settings = cls.fixture.get("adaptive_settings") or {}
        cls.points = list(cls.fixture.get("points") or [])

        # Basic shape validation (fail early with a nice message).
        assert cls.fixture.get("mode") == "extended"
        assert isinstance(cls.settings.get("expected_radii_m"), list)
        assert cls.points, "poi_reference_points_v1.json must contain at least 1 point"

    def test_reference_points_guard_environment_profile(self):
        points_by_key: Dict[Tuple[str, str], dict[str, Any]] = {}
        for point in self.points:
            key = (f"{float(point['lat']):.6f}", f"{float(point['lon']):.6f}")
            points_by_key[key] = point

        def fake_fetch_osm_poi_overpass(
            client: address_intel.HttpClient,
            sources: address_intel.SourceRegistry,
            *,
            lat: float | None,
            lon: float | None,
            radius_m: int,
            max_items: int,
        ) -> dict[str, Any]:
            if lat is None or lon is None:
                return {"source_url": None, "pois": []}

            key = (f"{float(lat):.6f}", f"{float(lon):.6f}")
            point = points_by_key.get(key)
            if point is None:
                raise AssertionError(f"unexpected reference point: {key}")

            counts_by_radius = point.get("poi_counts_by_radius") or {}
            desired = int(counts_by_radius.get(str(int(radius_m)), 0) or 0)

            pois = _build_dummy_pois(count=min(desired, int(max_items)), radius_m=int(radius_m))
            return {
                "source_url": f"https://overpass-api.de/api/interpreter?fixture=1&lat={key[0]}&lon={key[1]}&r={int(radius_m)}",
                "pois": pois,
            }

        def fake_fetch_google_news_rss(
            client: address_intel.HttpClient,
            sources: address_intel.SourceRegistry,
            *,
            query: str,
            limit: int,
            source_name: str = "google_news_rss",
        ) -> dict[str, Any]:
            # fully offline: return empty events.
            sources.note_success(source_name, "fixture://google-news", records=0, optional=True)
            return {"source_url": "fixture://google-news", "events": [], "cache": "fixture"}

        with patch.object(address_intel, "fetch_osm_poi_overpass", new=fake_fetch_osm_poi_overpass), patch.object(
            address_intel, "fetch_google_news_rss", new=fake_fetch_google_news_rss
        ):
            for point in self.points:
                with self.subTest(point=point.get("id")):
                    query = address_intel.parse_query_parts(point.get("address_hint") or point.get("label") or "")
                    selected = address_intel.CandidateEval(
                        feature_id=f"fixture::{point['id']}",
                        label=str(point.get("label") or point["id"]),
                        detail=str(point.get("address_hint") or ""),
                        origin="fixture",
                        rank=1,
                        lat=float(point["lat"]),
                        lon=float(point["lon"]),
                        pre_score=90.0,
                        total_score=95.0,
                        address_attrs={"adr_official": True},
                        gwr_attrs={"plz_plz6": 0, "dplzname": "", "gbauj": 1970},
                    )

                    intel = address_intel.build_intelligence_layers(
                        mode="extended",
                        client=address_intel.HttpClient(timeout=1, retries=0, enable_disk_cache=False),
                        sources=address_intel.SourceRegistry(),
                        query=query,
                        selected=selected,
                        confidence={"level": "high", "ambiguity": {"level": "none"}},
                        plz_layer={"plz": None},
                        admin_boundary={"gemname": None},
                    )

                    env = intel.get("environment_profile") or {}
                    expected = point.get("expected") or {}

                    expected_always = expected.get("always") or {}
                    self.assertEqual(env.get("status"), expected_always.get("status"))
                    self.assertGreaterEqual(
                        int((env.get("counts") or {}).get("poi_total") or 0),
                        int(expected_always.get("min_poi_total") or 0),
                    )

                    mode_settings = address_intel.intelligence_mode_settings("extended")
                    fallback_supported = any(
                        str(key).startswith("poi_fallback_") for key in (mode_settings or {}).keys()
                    )
                    if not fallback_supported:
                        # WP #690 (adaptive POI fallback) is not merged yet in this branch.
                        # Keep this guard CI-safe while still providing value once fallback
                        # settings/wiring land.
                        continue

                    expected_fb = expected.get("when_fallback_supported") or {}
                    self.assertEqual(env.get("status"), expected_fb.get("status"))
                    self.assertGreaterEqual(
                        int((env.get("counts") or {}).get("poi_total") or 0),
                        int(expected_fb.get("min_poi_total") or 0),
                    )

                    exp_low_conf = bool(expected_fb.get("low_confidence"))
                    got_low_conf = bool(env.get("low_confidence"))
                    self.assertEqual(got_low_conf, exp_low_conf)

                    if exp_low_conf:
                        self.assertTrue(str(env.get("low_confidence_reason") or ""))
                        fb = env.get("fallback") or {}
                        attempts = list(fb.get("attempts") or [])
                        self.assertEqual(len(attempts), int(expected_fb.get("expected_attempt_count") or 0))

                        # Guard the radius progression (stable behavioural contract).
                        radii = [int(a.get("radius_m") or 0) for a in attempts]
                        allowed = list(self.settings.get("expected_radii_m") or [])
                        self.assertTrue(all(r in allowed for r in radii))
                        self.assertEqual(radii[0], int(self.settings.get("base_radius_m") or 0))

                        # When fallback is active, the environment profile must reflect the
                        # last attempt payload (so we don't silently ignore the fallback).
                        counts_by_radius = point.get("poi_counts_by_radius") or {}
                        last_radius = str(radii[-1]) if radii else ""
                        expected_count = int(counts_by_radius.get(last_radius, 0) or 0)
                        self.assertEqual(
                            int((env.get("counts") or {}).get("poi_total") or 0),
                            min(expected_count, int(mode_settings.get("poi_limit") or 90)),
                        )
                    else:
                        self.assertFalse(env.get("fallback"))
                        self.assertFalse(env.get("low_confidence_reason"))
