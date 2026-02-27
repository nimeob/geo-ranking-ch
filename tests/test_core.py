import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_DIR = Path(__file__).resolve().parents[1]  # repo root
SRC_DIR = SKILL_DIR / "src"
SCRIPT = SRC_DIR / "address_intel.py"

spec = importlib.util.spec_from_file_location("address_intel", str(SCRIPT))
address_intel = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = address_intel
spec.loader.exec_module(address_intel)


class TestCoreFunctions(unittest.TestCase):
    def test_parse_query_parts(self):
        qp = address_intel.parse_query_parts("Wassergasse 24, 9000 St. Gallen")
        self.assertEqual(qp.street, "wassergasse")
        self.assertEqual(qp.house_number, "24")
        self.assertEqual(qp.postal_code, "9000")
        self.assertIn("gallen", qp.city)

    def test_parse_query_parts_normalizes_separators_and_street_abbrev(self):
        qp = address_intel.parse_query_parts("  St. Leonhard-Str. 39 ; 9000 St. Gallen  ")
        self.assertEqual(qp.street, "st. leonhard-strasse")
        self.assertEqual(qp.house_number, "39")
        self.assertEqual(qp.postal_code, "9000")
        self.assertEqual(qp.city, "st. gallen")

    def test_parse_query_parts_supports_house_number_suffix_ranges(self):
        qp = address_intel.parse_query_parts("Seestrasse 10A/2, 8640 Rapperswil")
        self.assertEqual(qp.street, "seestrasse")
        self.assertEqual(qp.house_number, "10a/2")
        self.assertEqual(qp.postal_code, "8640")
        self.assertEqual(qp.city, "rapperswil")

    def test_derive_resolution_identifiers_prefers_egid_and_lv95(self):
        ids = address_intel.derive_resolution_identifiers(
            feature_id="123_0",
            gwr_attrs={"egid": 555, "gkode": 2745000.4, "gkodn": 1256000.6},
            lat=47.1,
            lon=8.5,
        )
        self.assertEqual(ids["entity_id"], "ch:egid:555")
        self.assertEqual(ids["location_id"], "ch:lv95:2745000:1256001")
        self.assertTrue(str(ids["resolution_id"]).startswith("ch:resolution:v1:"))

    def test_derive_resolution_identifiers_fallback_to_feature_and_wgs84(self):
        ids = address_intel.derive_resolution_identifiers(
            feature_id="abc_7",
            gwr_attrs={},
            lat=47.3769123,
            lon=8.5417234,
        )
        self.assertEqual(ids["entity_id"], "ch:feature:abc_7")
        self.assertEqual(ids["location_id"], "ch:wgs84:47.376912:8.541723")
        self.assertTrue(str(ids["resolution_id"]).startswith("ch:resolution:v1:"))

    def test_candidate_scoring_prefers_exact(self):
        qp = address_intel.parse_query_parts("Wassergasse 24, 9000 St. Gallen")

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

        s_exact, _ = address_intel.score_candidate_pre(exact, qp)
        s_fuzzy, _ = address_intel.score_candidate_pre(fuzzy, qp)
        self.assertGreater(s_exact, s_fuzzy)

    def test_confidence_levels(self):
        sources = address_intel.SourceRegistry()
        sources.note_success("geoadmin_search", "https://example")
        sources.note_success("geoadmin_gwr", "https://example")
        sources.note_success("geoadmin_address", "https://example")

        selected = address_intel.CandidateEval(
            feature_id="111_0",
            label="Test 1",
            detail="",
            origin="address",
            rank=1,
            lat=47.0,
            lon=8.0,
            pre_score=50,
            total_score=95,
            address_attrs={"adr_official": True},
            gwr_attrs={
                "egid": 1,
                "egrid": "CH1",
                "esid": 22,
                "gstat": 1004,
                "gbauj": 1999,
                "garea": 100,
                "gastw": 4,
                "ganzwhg": 8,
                "plz_plz6": 9000,
                "dplzname": "St. Gallen",
                "ggdename": "St. Gallen",
                "gdekt": "SG",
            },
        )

        conf = address_intel.compute_confidence(
            selected=selected,
            candidates=[selected],
            sources=sources,
            heating_layer={"genh1_de": "Fernwärme"},
            plz_layer={"plz": 9000, "langtext": "St. Gallen"},
            admin_boundary={"gemname": "St. Gallen", "kanton": "SG"},
            osm={"address": {"postcode": "9000", "city": "St. Gallen"}},
        )

        self.assertGreaterEqual(conf["score"], 75)
        self.assertEqual(conf["level"], "high")

    def test_ambiguity_detection_flags_warning(self):
        selected = address_intel.CandidateEval(
            feature_id="a",
            label="A",
            detail="",
            origin="address",
            rank=1,
            lat=None,
            lon=None,
            pre_score=40,
            total_score=62,
            pre_reasons=["Strasse exakt im Treffertext"],
            detail_reasons=["GWR-Strasse bestätigt"],
            gwr_attrs={"plz_plz6": 8001, "dplzname": "Zürich", "gdekt": "ZH"},
            address_attrs={},
        )
        close = address_intel.CandidateEval(
            feature_id="b",
            label="B",
            detail="",
            origin="address",
            rank=2,
            lat=None,
            lon=None,
            pre_score=59,
            total_score=59,
            gwr_attrs={},
            address_attrs={},
        )

        ambiguity = address_intel.assess_ambiguity(selected, [selected, close])
        self.assertIn(ambiguity["level"], {"medium", "high"})
        self.assertTrue(ambiguity["warnings"])

    def test_http_cache_avoids_duplicate_requests(self):
        payload = b'{"ok": true}'

        class DummyResp:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return payload

        call_count = {"n": 0}

        def fake_urlopen(req, timeout=0):
            call_count["n"] += 1
            return DummyResp()

        client = address_intel.HttpClient(cache_ttl_seconds=60, enable_disk_cache=False)
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            a = client.get_json("https://example.test/x", source="test")
            b = client.get_json("https://example.test/x", source="test")

        self.assertEqual(call_count["n"], 1)
        self.assertEqual(a, b)

    def test_batch_recovers_unquoted_commas(self):
        captured = []
        original_build_report = address_intel.build_report

        def fake_build_report(query, **kwargs):
            captured.append(query)
            return {
                "query": query,
                "summary_compact": {
                    "matched_address": query,
                    "confidence": {"score": 80, "level": "high"},
                    "executive": {"needs_review": False, "warnings": []},
                    "sources": {},
                    "energie": {},
                    "map": "",
                },
            }

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".csv", delete=False) as f:
            f.write("address\n")
            f.write("Wassergasse 24, 9000 St. Gallen\n")
            path = f.name

        try:
            address_intel.build_report = fake_build_report
            batch = address_intel.run_batch(
                path,
                "address",
                include_osm=False,
                candidate_limit=5,
                candidate_preview=2,
                timeout=10,
                retries=1,
                backoff_seconds=0.1,
                osm_min_delay=0.0,
                cache_ttl_seconds=0.0,
                intelligence_mode="basic",
            )
        finally:
            address_intel.build_report = original_build_report
            Path(path).unlink(missing_ok=True)

        self.assertEqual(batch["stats"]["ok"], 1)
        self.assertEqual(captured[0], "Wassergasse 24, 9000 St. Gallen")

    def test_csv_flatten_null_handling(self):
        err = address_intel.normalize_error_row("X", 7, ValueError("kaputt"))
        flat = address_intel.flatten_report_for_csv(err)
        self.assertEqual(set(flat.keys()), set(address_intel.CSV_EXPORT_FIELDS))
        self.assertEqual(flat["status"], "error")
        self.assertEqual(flat["error_code"], "INPUT")
        self.assertEqual(flat["matched_address"], "")

    def test_error_classification(self):
        self.assertEqual(address_intel.classify_error(ValueError("x")), "INPUT")
        self.assertEqual(address_intel.classify_error(address_intel.NoAddressMatchError("x")), "NO_MATCH")

    def test_statement_status_classification(self):
        ev_official = [address_intel.evidence_item(source="geoadmin_gwr", confidence=0.9)]
        ev_community = [address_intel.evidence_item(source="osm_poi_overpass", confidence=0.62)]

        self.assertEqual(address_intel.classify_statement_status(0.85, ev_official), "gesichert")
        self.assertEqual(address_intel.classify_statement_status(0.62, ev_community), "indiz")
        self.assertEqual(address_intel.classify_statement_status(0.32, ev_community), "unklar")

    def test_consistency_checks_detect_old_incident(self):
        query = address_intel.parse_query_parts("Wassergasse 24, 9000 St. Gallen")
        selected = address_intel.CandidateEval(
            feature_id="111",
            label="Wassergasse 24 9000 St. Gallen",
            detail="",
            origin="address",
            rank=1,
            lat=47.0,
            lon=9.0,
            pre_score=70,
            total_score=90,
            address_attrs={"adr_official": True},
            gwr_attrs={"plz_plz6": 9000, "dplzname": "St. Gallen", "gbauj": 2010},
        )
        incidents = {
            "events": [
                {
                    "title": "Brand in der Wassergasse",
                    "date": "2005-01-10T00:00:00+00:00",
                    "status": "indiz",
                    "confidence": 0.65,
                    "evidence": [],
                }
            ]
        }

        checks = address_intel.build_consistency_checks_layer(
            query=query,
            selected=selected,
            incidents_timeline=incidents,
            plz_layer={"plz": 9000, "langtext": "St. Gallen"},
            admin_boundary={"gemname": "St. Gallen"},
        )

        self.assertEqual(checks["status"], "ok")
        self.assertGreaterEqual(checks["counts"]["warn"], 1)
        self.assertTrue(any(c["id"] == "incident_vs_baujahr" for c in checks["checks"]))

    def test_executive_risk_summary_has_traffic_light(self):
        summary = address_intel.build_executive_risk_summary(
            mode="risk",
            confidence={"level": "low"},
            ambiguity={"level": "high"},
            tenants_businesses={"status": "ok", "entities": [{}, {}]},
            incidents_timeline={"relevant_event_count": 3},
            environment_noise_risk={"score": 70},
            consistency_checks={"risk_score": 60},
        )

        self.assertIn(summary["traffic_light"], {"green", "yellow", "red"})
        self.assertGreaterEqual(summary["risk_score"], 70)

    def test_intelligence_basic_mode_disables_external_layers(self):
        query = address_intel.parse_query_parts("Bahnhofstrasse 1, 8001 Zürich")
        selected = address_intel.CandidateEval(
            feature_id="x",
            label="Bahnhofstrasse 1 8001 Zürich",
            detail="",
            origin="address",
            rank=1,
            lat=47.37,
            lon=8.54,
            pre_score=80,
            total_score=95,
            address_attrs={"adr_official": True},
            gwr_attrs={"plz_plz6": 8001, "dplzname": "Zürich", "gbauj": 1970},
        )
        intel = address_intel.build_intelligence_layers(
            mode="basic",
            client=address_intel.HttpClient(timeout=1, retries=0),
            sources=address_intel.SourceRegistry(),
            query=query,
            selected=selected,
            confidence={"level": "high", "ambiguity": {"level": "none"}},
            plz_layer={"plz": 8001},
            admin_boundary={"gemname": "Zürich"},
        )

        self.assertEqual(intel["tenants_businesses"]["status"], "disabled_by_mode")
        self.assertEqual(intel["incidents_timeline"]["status"], "disabled_by_mode")
        self.assertEqual(intel["environment_noise_risk"]["status"], "disabled_by_mode")
        self.assertEqual(intel["mode"], "basic")

    def test_area_weight_parsing_with_aliases(self):
        weights = address_intel.parse_area_weights("ruhe=1.3,ov=0.9,shopping=0.8,green=1.1,safety=1.7,nightlife=0.4")
        self.assertEqual(weights["ruhe"], 1.3)
        self.assertEqual(weights["oev"], 0.9)
        self.assertEqual(weights["einkauf"], 0.8)
        self.assertEqual(weights["gruen"], 1.1)
        self.assertEqual(weights["sicherheit"], 1.7)
        self.assertEqual(weights["nachtaktivitaet"], 0.4)

    def test_zone_scoring_penalizes_high_city_incident_risk(self):
        low_risk = address_intel.compute_zone_scores_from_indices(
            indices={
                "transit": 65,
                "shopping": 60,
                "green": 60,
                "nightlife": 25,
                "major_road": 20,
                "police": 28,
                "food": 50,
            },
            city_incident_risk=25,
            city_incident_status="ok",
            mode="extended",
        )
        high_risk = address_intel.compute_zone_scores_from_indices(
            indices={
                "transit": 65,
                "shopping": 60,
                "green": 60,
                "nightlife": 25,
                "major_road": 20,
                "police": 28,
                "food": 50,
            },
            city_incident_risk=80,
            city_incident_status="ok",
            mode="extended",
        )
        self.assertGreater(low_risk["metrics"]["sicherheit"], high_risk["metrics"]["sicherheit"])

    def test_zone_scoring_marks_uncertain_when_city_data_missing(self):
        result = address_intel.compute_zone_scores_from_indices(
            indices={
                "transit": 50,
                "shopping": 50,
                "green": 55,
                "nightlife": 30,
                "major_road": 30,
                "police": 10,
                "food": 45,
            },
            city_incident_risk=0,
            city_incident_status="no_data",
            mode="extended",
        )
        self.assertEqual(result["safety_uncertainty"], "unklar")

    def test_city_ranking_weighted_overall_prefers_green_when_weighted(self):
        a = address_intel.compute_zone_scores_from_indices(
            indices={
                "transit": 75,
                "shopping": 72,
                "green": 85,
                "nightlife": 22,
                "major_road": 18,
                "police": 24,
                "food": 60,
            },
            city_incident_risk=40,
            city_incident_status="ok",
            mode="extended",
        )["metrics"]
        b = address_intel.compute_zone_scores_from_indices(
            indices={
                "transit": 84,
                "shopping": 82,
                "green": 25,
                "nightlife": 58,
                "major_road": 55,
                "police": 12,
                "food": 72,
            },
            city_incident_risk=40,
            city_incident_status="ok",
            mode="extended",
        )["metrics"]

        w = address_intel.normalize_weight_profile(
            address_intel.parse_area_weights("ruhe=1.4,oev=1.0,einkauf=0.6,gruen=1.8,sicherheit=1.7,nachtaktivitaet=0.2")
        )

        score_a = sum(a[k] * w[k] for k in w)
        score_b = sum(b[k] * w[k] for k in w)
        self.assertGreater(score_a, score_b)


    def test_zone_weight_model_contains_explainable_drivers(self):
        metrics = {
            "ruhe": 78.0,
            "oev": 42.0,
            "einkauf": 65.0,
            "gruen": 72.0,
            "sicherheit": 60.0,
            "nachtaktivitaet": 30.0,
        }
        norm = address_intel.normalize_weight_profile(
            address_intel.parse_area_weights("ruhe=1.2,oev=1.0,einkauf=0.8,gruen=1.1,sicherheit=1.7,nachtaktivitaet=0.5")
        )
        samples = {
            "major_road": [{"distance_m": 110, "url": "https://overpass.test", "observed_at": "2026-01-01T00:00:00+00:00"}],
            "nightlife": [{"distance_m": 220, "url": "https://overpass.test", "observed_at": "2026-01-01T00:00:00+00:00"}],
            "shopping": [{"distance_m": 90, "url": "https://overpass.test", "observed_at": "2026-01-01T00:00:00+00:00"}],
            "green": [{"distance_m": 75, "url": "https://overpass.test", "observed_at": "2026-01-01T00:00:00+00:00"}],
            "police": [{"distance_m": 140, "url": "https://overpass.test", "observed_at": "2026-01-01T00:00:00+00:00"}],
            "transit": [{"distance_m": 130, "url": "https://overpass.test", "observed_at": "2026-01-01T00:00:00+00:00"}],
            "food": [{"distance_m": 150, "url": "https://overpass.test", "observed_at": "2026-01-01T00:00:00+00:00"}],
        }

        model = address_intel.build_zone_weight_model(
            zone_index=0,
            zone_code="Z11",
            metrics=metrics,
            normalized_weights=norm,
            samples=samples,
            fallback_url="https://overpass.test",
        )

        self.assertIn("drivers", model)
        self.assertTrue(model["drivers"])
        self.assertEqual(len(model["contributions"]), len(address_intel.AREA_WEIGHT_KEYS))
        self.assertTrue(any(abs(float(row.get("delta_vs_neutral") or 0.0)) > 0 for row in model["contributions"]))

    def test_zone_security_signals_include_provenance_fields(self):
        city_safety = {
            "status": "ok",
            "incident_risk_score": 62,
            "events": [
                {
                    "title": "Einbruchserie in Teststadt",
                    "date": "2026-01-15T12:00:00+00:00",
                    "url": "https://news.example/e1",
                    "confidence": 0.71,
                    "relevance": 0.82,
                }
            ],
        }
        signals = address_intel.build_zone_security_signals(
            zone_index=0,
            zone_code="Z11",
            city_safety=city_safety,
            city_news_payload={"source_url": "https://news.example/rss"},
            local_samples={
                "major_road": [{"distance_m": 80, "url": "https://overpass.example", "observed_at": "2026-01-15T12:30:00+00:00"}],
                "nightlife": [{"distance_m": 140, "url": "https://overpass.example", "observed_at": "2026-01-15T12:30:00+00:00"}],
                "police": [{"distance_m": 210, "url": "https://overpass.example", "observed_at": "2026-01-15T12:30:00+00:00"}],
            },
            local_indices={"major_road": 45, "nightlife": 35, "police": 20},
            local_signal_count=22,
            zone_status="ok",
            fallback_url="https://overpass.example",
        )

        self.assertIn("signals", signals)
        self.assertIn("facts", signals)
        self.assertIn("evidence_split", signals)
        self.assertGreaterEqual(len(signals["signals"]), 2)
        self.assertGreaterEqual(len(signals["facts"]), 2)
        first = signals["signals"][0]
        for key in ("source", "url", "observed_at", "confidence", "evidence", "signal_class"):
            self.assertIn(key, first)

    def test_city_ranking_report_includes_security_and_executive_with_mocks(self):
        mock_city = {
            "query": "Teststadt",
            "label": "Teststadt (TG)",
            "lat": 47.5,
            "lon": 9.1,
            "canton": "TG",
            "origin": "gg25",
            "feature_id": "x",
            "score": 41,
            "source_url": "https://api3.geo.admin.ch",
        }
        mock_city_safety = {
            "status": "ok",
            "incident_risk_score": 58,
            "uncertainty": "indiz",
            "relevant_event_count": 2,
            "events": [
                {
                    "title": "Polizeimeldung Teststadt",
                    "date": "2026-01-20T10:00:00+00:00",
                    "url": "https://news.example/e2",
                    "confidence": 0.65,
                    "relevance": 0.72,
                }
            ],
            "statements": [],
        }
        mock_zone_payload = {
            "source_url": "https://overpass.example/query",
            "elements": [
                {"id": "node:1", "name": "Bahnhof", "distance_m": 60, "tags": {"railway": "station"}},
                {"id": "node:2", "name": "Laden", "distance_m": 90, "tags": {"shop": "supermarket"}},
                {"id": "node:3", "name": "Park", "distance_m": 120, "tags": {"leisure": "park"}},
                {"id": "node:4", "name": "Polizei", "distance_m": 180, "tags": {"amenity": "police"}},
                {"id": "node:5", "name": "Hauptstrasse", "distance_m": 110, "tags": {"highway": "primary"}},
            ],
        }

        with mock.patch.object(address_intel, "fetch_city_anchor", return_value=mock_city),             mock.patch.object(address_intel, "fetch_google_news_rss", return_value={"source_url": "https://news.example/rss", "events": []}),             mock.patch.object(address_intel, "build_city_incident_signals", return_value=mock_city_safety),             mock.patch.object(address_intel, "fetch_zone_signals_overpass", return_value=mock_zone_payload):
            report = address_intel.build_city_ranking_report(
                "Teststadt",
                top_n=1,
                grid_size=1,
                zone_spacing_m=300,
                zone_radius_m=220,
                timeout=5,
                retries=0,
                backoff_seconds=0.0,
                cache_ttl_seconds=0.0,
                intelligence_mode="risk",
                area_weights=address_intel.parse_area_weights("ruhe=1.3,oev=1.1,einkauf=0.8,gruen=1.0,sicherheit=1.6,nachtaktivitaet=0.5"),
            )

        self.assertEqual(report["mode"], "city-ranking")
        self.assertIn("executive", report)
        self.assertIn(report["executive"].get("traffic_light"), {"green", "yellow", "red"})
        zone = report["top_zones"][0]
        self.assertIn("weight_model", zone)
        self.assertIn("security_signals", zone)
        self.assertTrue(zone["security_signals"])
        self.assertIn("executive", report.get("summary_compact", {}))
        self.assertIn("output", report)
        self.assertEqual(report["output"].get("map_status"), "disabled")

    def test_map_style_aliases(self):
        self.assertEqual(address_intel.canonical_map_style("osm"), "osm-standard")
        self.assertEqual(address_intel.canonical_map_style("standard"), "osm-standard")
        self.assertEqual(address_intel.canonical_map_style("hot"), "osm-hot")
        self.assertEqual(address_intel.canonical_map_style("topo"), "opentopomap")
        with self.assertRaises(ValueError):
            address_intel.canonical_map_style("fantasy-style")

    def test_build_city_map_layers_contains_evidence_refs(self):
        zones = [
            {
                "zone_code": "Z11",
                "zone_name": "Nord",
                "rank": 1,
                "traffic_light": "green",
                "overall_score": 78.4,
                "center": {"lat": 47.423, "lon": 9.371},
                "status": "ok",
                "quality_note": "ausreichende Signale",
                "sample_signals": {
                    "major_road": [{"lat": 47.4235, "lon": 9.3721, "distance_m": 80, "url": "https://overpass.example", "observed_at": "2026-01-01T12:00:00+00:00"}],
                    "nightlife": [{"lat": 47.4228, "lon": 9.3708, "distance_m": 120, "url": "https://overpass.example", "observed_at": "2026-01-01T12:00:00+00:00"}],
                    "police": [{"lat": 47.4232, "lon": 9.3717, "distance_m": 190, "url": "https://overpass.example", "observed_at": "2026-01-01T12:00:00+00:00"}],
                    "transit": [{"lat": 47.4226, "lon": 9.3712, "distance_m": 70, "url": "https://overpass.example", "observed_at": "2026-01-01T12:00:00+00:00"}],
                },
                "reasons": [{"text": "ruhe überdurchschnittlich (74/100)"}],
                "security_overview": {"headline": "2 Risikosignale / 1 Schutzsignale"},
            }
        ]

        layers = address_intel.build_city_ranking_map_layers(
            zones=zones,
            city_anchor={"lat": 47.423, "lon": 9.371, "query": "St. Gallen"},
            zone_radius_m=320,
            top_n=1,
        )

        self.assertIn("zones", layers)
        self.assertIn("markers", layers)
        self.assertTrue(layers["zones"])
        self.assertTrue(layers["markers"])
        marker = layers["markers"][0]
        self.assertIn("evidence_refs", marker)
        self.assertTrue(marker["evidence_refs"])
        self.assertIn("why", marker)

    def test_city_ranking_map_png_export_with_offline_tiles(self):
        if not address_intel.CAIRO_AVAILABLE:
            self.skipTest("pycairo nicht verfügbar")

        mock_city = {
            "query": "Teststadt",
            "label": "Teststadt (TG)",
            "lat": 47.5,
            "lon": 9.1,
            "canton": "TG",
            "origin": "gg25",
            "feature_id": "x",
            "score": 41,
            "source_url": "https://api3.geo.admin.ch",
        }
        mock_city_safety = {
            "status": "ok",
            "incident_risk_score": 58,
            "uncertainty": "indiz",
            "relevant_event_count": 1,
            "events": [],
            "statements": [],
        }
        mock_zone_payload = {
            "source_url": "https://overpass.example/query",
            "elements": [
                {"id": "node:1", "name": "Bahnhof", "distance_m": 60, "lat": 47.5005, "lon": 9.101, "tags": {"railway": "station"}},
                {"id": "node:2", "name": "Laden", "distance_m": 90, "lat": 47.4999, "lon": 9.1004, "tags": {"shop": "supermarket"}},
                {"id": "node:3", "name": "Bar", "distance_m": 100, "lat": 47.4995, "lon": 9.1014, "tags": {"amenity": "bar"}},
                {"id": "node:4", "name": "Polizei", "distance_m": 170, "lat": 47.501, "lon": 9.0998, "tags": {"amenity": "police"}},
                {"id": "node:5", "name": "Hauptstrasse", "distance_m": 110, "lat": 47.5008, "lon": 9.102, "tags": {"highway": "primary"}},
            ],
        }

        with tempfile.TemporaryDirectory() as td, mock.patch.object(address_intel, "fetch_city_anchor", return_value=mock_city), mock.patch.object(address_intel, "fetch_google_news_rss", return_value={"source_url": "https://news.example/rss", "events": []}), mock.patch.object(address_intel, "build_city_incident_signals", return_value=mock_city_safety), mock.patch.object(address_intel, "fetch_zone_signals_overpass", return_value=mock_zone_payload), mock.patch.object(address_intel, "_fetch_osm_tile_png", return_value=(None, False, "offline")):
            map_out = Path(td) / "city_map.png"
            report = address_intel.build_city_ranking_report(
                "Teststadt",
                top_n=1,
                grid_size=1,
                zone_spacing_m=300,
                zone_radius_m=220,
                timeout=5,
                retries=0,
                backoff_seconds=0.0,
                cache_ttl_seconds=0.0,
                intelligence_mode="risk",
                area_weights=address_intel.parse_area_weights("ruhe=1.3,oev=1.1,einkauf=0.8,gruen=1.0,sicherheit=1.6,nachtaktivitaet=0.5"),
                map_png=True,
                map_out=str(map_out),
                map_style="osm-standard",
                map_zoom=13,
            )

            self.assertEqual(report.get("output", {}).get("map_png_path"), str(map_out))
            self.assertTrue(map_out.exists())
            self.assertIn(report.get("map", {}).get("status"), {"ok", "degraded"})
            self.assertIn("map_layers", report)
            self.assertGreaterEqual(len((report.get("map_layers") or {}).get("zones") or []), 1)

    def test_resolve_marker_screen_positions_separates_overlaps(self):
        markers = [
            {"lat": 47.0, "lon": 8.0, "shape": "circle", "color": "#111", "glyph": "A"},
            {"lat": 47.0, "lon": 8.0, "shape": "circle", "color": "#222", "glyph": "B"},
            {"lat": 47.0, "lon": 8.0, "shape": "circle", "color": "#333", "glyph": "C"},
        ]
        base_x, base_y = address_intel.latlon_to_world_px(47.0, 8.0, 13)
        placed = address_intel.resolve_marker_screen_positions(
            markers=markers,
            zoom=13,
            origin_x=base_x - 700,
            origin_y=base_y - 450,
            width=1400,
            height=900,
            min_sep_px=9.0,
        )
        self.assertEqual(len(placed), 3)
        offsets = {tuple(p.get("screen_offset") or []) for p in placed}
        self.assertGreater(len(offsets), 1)

    def test_derive_zone_uncertainty(self):
        unklar = address_intel.derive_zone_uncertainty(
            zone_status="sparse_data",
            safety_uncertainty="indiz",
            contradiction_index=0.1,
            poi_signal_count=3,
        )
        self.assertEqual(unklar["status"], "unklar")

        gesichert = address_intel.derive_zone_uncertainty(
            zone_status="ok",
            safety_uncertainty="gesichert",
            contradiction_index=0.05,
            poi_signal_count=40,
        )
        self.assertEqual(gesichert["status"], "gesichert")

    def test_map_style_fallback_applied_when_primary_unavailable(self):
        if not address_intel.CAIRO_AVAILABLE:
            self.skipTest("pycairo nicht verfügbar")

        with tempfile.TemporaryDirectory() as td:
            tile_path = Path(td) / "dummy_tile.png"
            surf = address_intel.cairo.ImageSurface(address_intel.cairo.FORMAT_ARGB32, 256, 256)
            ctx = address_intel.cairo.Context(surf)
            ctx.set_source_rgb(0.8, 0.85, 0.9)
            ctx.paint()
            surf.write_to_png(str(tile_path))

            def fake_tile_fetch(**kwargs):
                style = kwargs.get("style")
                if style == "osm-hot":
                    return None, False, "blocked"
                return tile_path, True, None

            map_layers = {
                "viewport": {"min_lat": 47.49, "min_lon": 9.09, "max_lat": 47.51, "max_lon": 9.11},
                "zones": [],
                "markers": [],
                "warnings": [],
            }
            out_path = Path(td) / "fallback_map.png"
            with mock.patch.object(address_intel, "_fetch_osm_tile_png", side_effect=fake_tile_fetch):
                result = address_intel.render_city_ranking_map_png(
                    report={"city": {"query": "Teststadt", "lat": 47.5, "lon": 9.1}},
                    map_layers=map_layers,
                    map_out=str(out_path),
                    map_style="osm-hot",
                    map_zoom=13,
                    zone_radius_m=220,
                    client=address_intel.HttpClient(timeout=2, retries=0, cache_ttl_seconds=0),
                    sources=address_intel.SourceRegistry(),
                )

            self.assertTrue(out_path.exists())
            self.assertTrue(result.get("fallback_applied"))
            self.assertEqual(result.get("requested_style"), "osm-hot")
            self.assertEqual(result.get("style"), "osm-standard")
            self.assertIn(result.get("status"), {"ok", "degraded"})

    def test_zone_score_color_scale_differentiates_mid_ranges(self):
        c1 = address_intel.zone_score_color(54)
        c2 = address_intel.zone_score_color(60)
        c3 = address_intel.zone_score_color(68)
        self.assertNotEqual(c1, c2)
        self.assertNotEqual(c2, c3)
        self.assertEqual(address_intel.zone_score_band(54), "watch")
        self.assertEqual(address_intel.zone_score_band(68), "balanced")

    def test_build_city_map_layers_highlights_target_zone(self):
        zones = [
            {
                "zone_code": "Z11",
                "zone_name": "Nord",
                "rank": 1,
                "traffic_light": "yellow",
                "overall_score": 64.0,
                "center": {"lat": 47.423, "lon": 9.371},
                "status": "ok",
                "quality_note": "ausreichende Signale",
                "sample_signals": {},
                "reasons": [{"text": "mixed"}],
                "security_overview": {"headline": "2 Risikosignale / 1 Schutzsignale"},
            },
            {
                "zone_code": "Z12",
                "zone_name": "Süd",
                "rank": 2,
                "traffic_light": "green",
                "overall_score": 73.5,
                "center": {"lat": 47.421, "lon": 9.373},
                "status": "ok",
                "quality_note": "gut",
                "sample_signals": {},
                "reasons": [{"text": "grün"}],
                "security_overview": {"headline": "1 Risikosignal / 2 Schutzsignale"},
                "is_target_nearest": True,
            },
        ]

        layers = address_intel.build_city_ranking_map_layers(
            zones=zones,
            city_anchor={"lat": 47.423, "lon": 9.371, "query": "St. Gallen"},
            zone_radius_m=320,
            top_n=2,
            target_context={
                "query": "Bahnhofstrasse 1",
                "label": "Bahnhofstrasse 1, 9000 St. Gallen",
                "lat": 47.421,
                "lon": 9.373,
                "nearest_zone_code": "Z12",
                "nearest_zone_distance_m": 62,
            },
        )

        self.assertTrue(any(z.get("is_target_nearest") for z in layers.get("zones") or []))
        self.assertTrue(any(m.get("kind") == "target_address" for m in layers.get("markers") or []))

    def test_security_signals_enable_thin_data_guard(self):
        city_safety = {
            "status": "ok",
            "incident_risk_score": 74,
            "relevant_event_count": 4,
            "events": [
                {"title": "Event A", "relevance": 0.9, "confidence": 0.75},
                {"title": "Event B", "relevance": 0.8, "confidence": 0.7},
                {"title": "Event C", "relevance": 0.7, "confidence": 0.68},
            ],
        }
        sig = address_intel.build_zone_security_signals(
            zone_index=0,
            zone_code="Z11",
            city_safety=city_safety,
            city_news_payload={"source_url": "https://news.example/rss"},
            local_samples={},
            local_indices={"major_road": 8, "nightlife": 4, "police": 0},
            local_signal_count=3,
            zone_status="thin_data",
            fallback_url="https://overpass.example",
        )

        self.assertTrue(sig.get("overview", {}).get("thin_data_guard"))
        city_events = [s for s in (sig.get("signals") or []) if s.get("kind") == "city_incident_event"]
        self.assertLessEqual(len(city_events), 1)

    def test_recommendation_explanation_mentions_relative_ranking(self):
        text = address_intel.build_recommendation_explanation(
            recommended_zone={
                "zone": "Z11",
                "score": 48.2,
                "traffic_light": "red",
                "weight_model": {"drivers": [{"direction": "negative", "text": "Sicherheit unterdurchschnittlich"}]},
            },
            city_safety={"incident_risk_score": 82},
            top_n=5,
            target_context={"nearest_zone_code": "Z12", "nearest_zone_distance_m": 130},
        )
        self.assertIn("beste verfügbare Zone", text)
        self.assertIn("nicht grün", text)

    def test_tile_error_cache_skips_immediate_retry(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            def fake_tile(style, zoom, x, y):
                return td_path / f"{style}-{zoom}-{x}-{y}.png"

            def fake_err(style, zoom, x, y):
                return td_path / f"{style}-{zoom}-{x}-{y}.err.json"

            call_count = {"n": 0}

            def failing_open(*args, **kwargs):
                call_count["n"] += 1
                raise address_intel.urllib.error.URLError("offline")

            client = address_intel.HttpClient(timeout=1, retries=0, cache_ttl_seconds=30)
            sources = address_intel.SourceRegistry()

            with mock.patch.object(address_intel, "_tile_cache_file", side_effect=fake_tile), \
                mock.patch.object(address_intel, "_tile_error_cache_file", side_effect=fake_err), \
                mock.patch("urllib.request.urlopen", side_effect=failing_open):
                first = address_intel._fetch_osm_tile_png(
                    client=client,
                    sources=sources,
                    style="osm-standard",
                    zoom=13,
                    tile_x=4321,
                    tile_y=2876,
                    min_delay_s=0.0,
                    tile_ttl_s=120,
                )
                second = address_intel._fetch_osm_tile_png(
                    client=client,
                    sources=sources,
                    style="osm-standard",
                    zoom=13,
                    tile_x=4321,
                    tile_y=2876,
                    min_delay_s=0.0,
                    tile_ttl_s=120,
                )

            self.assertIsNone(first[0])
            self.assertIn("error-cache", str(second[2]))
            self.assertEqual(call_count["n"], 1)


if __name__ == "__main__":
    unittest.main()
