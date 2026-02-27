import copy
import json
import unittest
from pathlib import Path

from src.web_service import _grouped_api_result


REPO_ROOT = Path(__file__).resolve().parents[1]
GROUPED_SUCCESS_EXAMPLE = (
    REPO_ROOT / "docs" / "api" / "examples" / "current" / "analyze.response.grouped.success.json"
)


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


def _legacy_minimal_projection(payload: dict) -> dict:
    result = payload.get("result") or {}
    status = result.get("status") or {}
    quality = status.get("quality") or {}
    confidence = quality.get("confidence") or {}
    data = result.get("data") or {}
    entity = data.get("entity") or {}

    return {
        "ok": payload.get("ok"),
        "request_id": payload.get("request_id"),
        "confidence_score": confidence.get("score"),
        "confidence_level": confidence.get("level"),
        "entity_query": entity.get("query"),
        "entity_id": (entity.get("ids") or {}).get("egid"),
    }


def _smoke_minimum_ok(payload: dict) -> bool:
    if payload.get("ok") is not True:
        return False
    result = payload.get("result")
    return isinstance(result, dict) and bool(result)


class TestContractCompatibilityRegression(unittest.TestCase):
    def test_legacy_minimal_projection_survives_additive_optional_fields(self):
        baseline = json.loads(GROUPED_SUCCESS_EXAMPLE.read_text(encoding="utf-8"))
        additive = copy.deepcopy(baseline)

        additive["contract_meta"] = {
            "compatibility": "additive",
            "since": "v1",
        }
        additive["result"]["status"]["capabilities"] = {
            "deep_mode": {"available": False, "state": "beta"}
        }
        additive["result"]["status"]["entitlements"] = {
            "plan": {"value": "starter", "state": "stable"}
        }
        additive["result"]["status"]["quality"]["confidence"]["confidence_band"] = "p95"
        additive["result"]["data"]["entity"]["normalization"] = {
            "strategy": "plus-code-v2"
        }
        additive["result"]["data"]["modules"]["future_context"] = {
            "walk_score": 71,
            "coverage": "beta",
        }
        additive["result"]["data"]["by_source"]["future_api"] = {
            "source": "future_api",
            "data": {"future_context": {"walk_score": 71}},
        }

        self.assertEqual(
            _legacy_minimal_projection(additive),
            _legacy_minimal_projection(baseline),
            msg="Additive Felder dürfen die Legacy-Minimalauswertung nicht verändern",
        )
        self.assertTrue(_smoke_minimum_ok(baseline))
        self.assertTrue(_smoke_minimum_ok(additive))

    def test_status_and_data_remain_semantically_separated_for_additive_payloads(self):
        report = {
            "query": "Bahnhofstrasse 1, 8001 Zürich",
            "matched_address": "Bahnhofstrasse 1, 8001 Zürich",
            "ids": {"egid": "123"},
            "coordinates": {"lat": 47.3769, "lon": 8.5417},
            "administrative": {"gemeinde": "Zürich"},
            "match": {
                "selected_score": 0.97,
                "status": "ok",
                "status_reason": "from_upstream",
            },
            "future_module": {
                "score": 0.42,
                "status": "experimental",
                "status_reason": "beta",
            },
            "confidence": {"score": 88, "max": 100, "level": "high"},
            "sources": {"geoadmin_search": {"status": "ok", "records": 1}},
            "source_attribution": {
                "match": ["geoadmin_search"],
                "future_module": ["geoadmin_search"],
            },
            "source_classification": {
                "future_module.score": {"primary_source": "geoadmin_search"}
            },
        }

        grouped = _grouped_api_result(report)
        self.assertIn("status", grouped)
        self.assertIn("data", grouped)

        data_block = grouped["data"]
        status_like_paths = _collect_status_like_paths(data_block)
        self.assertEqual(
            status_like_paths,
            [],
            msg=f"status-artige Felder dürfen nicht in result.data auftauchen: {status_like_paths}",
        )

        self.assertEqual(grouped["status"]["quality"]["confidence"]["score"], 88)
        self.assertIn("future_module", data_block["modules"])
        self.assertEqual(data_block["modules"]["future_module"], {"score": 0.42})


if __name__ == "__main__":
    unittest.main()
