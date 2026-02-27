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


if __name__ == "__main__":
    unittest.main()
