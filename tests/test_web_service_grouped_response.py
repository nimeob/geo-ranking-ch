import json
import unittest

from src.web_service import _grouped_api_result


def _collect_status_like_paths(payload, prefix=""):
    paths = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_str = str(key)
            current = f"{prefix}.{key_str}" if prefix else key_str
            normalized = key_str.lower()
            if (
                normalized == "status"
                or normalized.startswith("status_")
                or normalized.endswith("_status")
            ):
                paths.append(current)
            paths.extend(_collect_status_like_paths(value, current))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            current = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            paths.extend(_collect_status_like_paths(item, current))
    return paths


class TestGroupedApiResult(unittest.TestCase):
    def test_separates_status_from_data_and_groups_by_source(self):
        report = {
            "query": "Bahnhofstrasse 1, 8001 Zürich",
            "matched_address": "Bahnhofstrasse 1, 8001 Zürich",
            "ids": {"egid": "123"},
            "coordinates": {"lat": 47.3769, "lon": 8.5417},
            "administrative": {"gemeinde": "Zürich"},
            "match": {
                "selected_score": 0.99,
                "candidate_count": 3,
                "status": "ok",
            },
            "building": {
                "baujahr": 1999,
                "decoded": {
                    "heizung": [{"label": "Wärmepumpe", "status": "ok"}],
                },
            },
            "energy": {
                "decoded_summary": {"heizung": ["Wärmepumpe"]},
                "map_status": "available",
            },
            "cross_source": {
                "plz_layer": {
                    "plz": 8001,
                    "status": "REAL",
                }
            },
            "intelligence": {
                "tenants_businesses": {
                    "entities": [{"name": "Muster AG"}],
                    "status": "ok",
                }
            },
            "confidence": {"score": 92, "max": 100, "level": "high"},
            "executive_summary": {"verdict": "ok"},
            "sources": {
                "geoadmin_search": {"status": "ok", "records": 1},
                "osm_reverse": {"status": "partial", "records": 1},
            },
            "source_classification": {
                "building.baujahr": {"primary_source": "geoadmin_search"}
            },
            "source_attribution": {
                "match": ["geoadmin_search"],
                "intelligence": ["osm_reverse"],
            },
            "field_provenance": {
                "building.baujahr": {
                    "primary_source": "geoadmin_search",
                    "present": True,
                }
            },
            "personalization_status": {
                "state": "active",
                "source": "personalized_reweighting",
                "fallback_applied": False,
                "signal_strength": 0.33,
            },
        }

        grouped = _grouped_api_result(report)

        self.assertIn("status", grouped)
        self.assertIn("data", grouped)

        status_block = grouped["status"]
        self.assertEqual(status_block["quality"]["confidence"]["score"], 92)
        self.assertEqual(status_block["source_health"]["geoadmin_search"]["status"], "ok")
        self.assertIn("source_attribution", status_block["source_meta"])
        self.assertEqual(status_block["personalization"]["state"], "active")
        self.assertEqual(status_block["personalization"]["source"], "personalized_reweighting")

        data_block = grouped["data"]
        self.assertEqual(data_block["entity"]["ids"]["egid"], "123")
        self.assertIn("match", data_block["modules"])
        self.assertIn("building", data_block["modules"])

        status_like_paths = _collect_status_like_paths(data_block)
        self.assertEqual(status_like_paths, [])

        by_source = data_block["by_source"]
        self.assertIn("geoadmin_search", by_source)
        self.assertIn("osm_reverse", by_source)
        self.assertEqual(by_source["geoadmin_search"]["source"], "geoadmin_search")
        self.assertIn("match", by_source["geoadmin_search"]["data"])
        self.assertIn("intelligence", by_source["osm_reverse"]["data"])
        self.assertEqual(
            by_source["geoadmin_search"]["data"]["match"]["module_ref"],
            "#/result/data/modules/match",
        )

    def test_compact_default_reduces_by_source_payload_vs_verbose_mode(self):
        report = {
            "query": "Bahnhofstrasse 1, 8001 Zürich",
            "matched_address": "Bahnhofstrasse 1, 8001 Zürich",
            "ids": {"egid": "123"},
            "coordinates": {"lat": 47.3769, "lon": 8.5417},
            "match": {
                "selected_score": 0.99,
                "candidate_count": 3,
                "candidates": [
                    {"id": "A", "score": 0.99, "meta": {"distance_m": 2.1, "quality": "high"}},
                    {"id": "B", "score": 0.82, "meta": {"distance_m": 12.4, "quality": "medium"}},
                    {"id": "C", "score": 0.71, "meta": {"distance_m": 27.2, "quality": "medium"}},
                ],
            },
            "building": {
                "baujahr": 1999,
                "decoded": {
                    "heizung": [{"label": "Wärmepumpe"}],
                },
            },
            "energy": {
                "decoded_summary": {"heizung": ["Wärmepumpe"]},
            },
            "intelligence": {
                "tenants_businesses": {
                    "entities": [{"name": "Muster AG"}],
                }
            },
            "sources": {
                "geoadmin_search": {"status": "ok", "records": 1},
                "osm_reverse": {"status": "partial", "records": 1},
            },
            "source_attribution": {
                "match": ["geoadmin_search"],
                "building_energy": ["geoadmin_search"],
                "intelligence": ["osm_reverse"],
            },
        }

        compact = _grouped_api_result(report)
        verbose = _grouped_api_result(report, response_mode="verbose")

        compact_match = compact["data"]["by_source"]["geoadmin_search"]["data"]["match"]
        self.assertEqual(compact_match["module_ref"], "#/result/data/modules/match")
        self.assertEqual(compact_match["selected_score"], 0.99)
        self.assertEqual(compact_match["candidate_count"], 3)

        verbose_match = verbose["data"]["by_source"]["geoadmin_search"]["data"]["match"]
        self.assertNotIn("module_ref", verbose_match)
        self.assertEqual(verbose_match["selected_score"], 0.99)

        compact_size = len(json.dumps(compact["data"]["by_source"], ensure_ascii=False))
        verbose_size = len(json.dumps(verbose["data"]["by_source"], ensure_ascii=False))
        self.assertLess(
            compact_size,
            verbose_size,
            msg="compact by_source muss kleiner als verbose by_source sein",
        )

    def test_code_first_projection_removes_decoded_labels_and_emits_dictionary_status(self):
        report = {
            "query": "Espenmoosstrasse 18, 9008 St. Gallen",
            "matched_address": "Espenmoosstrasse 18, 9008 St. Gallen",
            "building": {
                "codes": {"gstat": 1004, "gkat": 1020, "gklas": "1122"},
                "decoded": {
                    "status": "Bestehend",
                    "kategorie": "Gebäude mit Wohnnutzung und anderen Nutzungen",
                },
            },
            "energy": {
                "raw_codes": {"gwaerzh1": 7410, "genh1": 7501},
                "decoded_summary": {"heizung": ["Wärmepumpe (Luft)"]},
            },
            "sources": {"geoadmin_search": {"status": "ok"}},
        }

        grouped = _grouped_api_result(report)
        status = grouped["status"]
        modules = grouped["data"]["modules"]

        dictionary = status.get("dictionary")
        self.assertIsInstance(dictionary, dict)
        self.assertIn("version", dictionary)
        self.assertIn("etag", dictionary)
        self.assertIn("domains", dictionary)

        self.assertNotIn("decoded", modules["building"])
        self.assertEqual(modules["building"]["codes"]["gstat"], "1004")
        self.assertNotIn("decoded_summary", modules["energy"])
        self.assertEqual(modules["energy"]["codes"]["gwaerzh1"], "7410")

    def test_legacy_label_projection_keeps_decoded_fields_when_enabled(self):
        report = {
            "query": "Espenmoosstrasse 18, 9008 St. Gallen",
            "matched_address": "Espenmoosstrasse 18, 9008 St. Gallen",
            "building": {
                "codes": {"gstat": 1004},
                "decoded": {"status": "Bestehend"},
            },
            "energy": {
                "raw_codes": {"gwaerzh1": 7410},
                "decoded_summary": {"heizung": ["Wärmepumpe (Luft)"]},
            },
            "sources": {"geoadmin_search": {"status": "ok"}},
        }

        grouped = _grouped_api_result(report, include_legacy_labels=True)
        modules = grouped["data"]["modules"]

        self.assertIn("decoded", modules["building"])
        self.assertIn("decoded_summary", modules["energy"])
        self.assertIn("raw_codes", modules["energy"])

    def test_code_first_projection_reduces_payload_vs_legacy_label_projection(self):
        report = {
            "query": "Espenmoosstrasse 18, 9008 St. Gallen",
            "matched_address": "Espenmoosstrasse 18, 9008 St. Gallen",
            "building": {
                "codes": {"gstat": 1004, "gkat": 1020, "gklas": 1122},
                "decoded": {
                    "status": "Bestehend",
                    "kategorie": "Gebäude mit Wohnnutzung und anderen Nutzungen",
                    "klasse": "Gebäude mit drei oder mehr Wohnungen",
                    "heizung": [
                        {"label": "Wärmepumpe für ein Gebäude (Luft)", "status": "ok"},
                        {"label": "Wärmepumpe für ein Gebäude (Luft)", "status": "ok"},
                    ],
                },
            },
            "energy": {
                "raw_codes": {"gwaerzh1": 7410, "genh1": 7501, "gwaerzw1": 7610, "genw1": 7501},
                "decoded_summary": {
                    "heizung": ["Wärmepumpe für ein Gebäude (Luft)"] * 2,
                    "warmwasser": ["Wärmepumpe für ein Gebäude (Luft)"] * 2,
                },
            },
            "sources": {"geoadmin_search": {"status": "ok"}},
            "source_attribution": {
                "building_energy": ["geoadmin_search"],
            },
        }

        legacy_payload = _grouped_api_result(report, response_mode="verbose", include_legacy_labels=True)
        code_first_payload = _grouped_api_result(report, response_mode="verbose")

        legacy_size = len(json.dumps(legacy_payload, ensure_ascii=False))
        code_first_size = len(json.dumps(code_first_payload, ensure_ascii=False))

        self.assertLess(
            code_first_size,
            legacy_size,
            msg=(
                "Code-first Payload muss kleiner als Label-Projection sein "
                f"(legacy={legacy_size}, code_first={code_first_size})"
            ),
        )


if __name__ == "__main__":
    unittest.main()
