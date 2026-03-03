from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "bench_deploy_gate_runtime.py"
SPEC = importlib.util.spec_from_file_location("bench_deploy_gate_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_normalize_runs_filters_and_sorts() -> None:
    raw = [
        {
            "databaseId": 3,
            "startedAt": "2026-03-03T20:00:00Z",
            "updatedAt": "2026-03-03T20:10:00Z",
            "headSha": "ccc",
            "conclusion": "success",
            "event": "workflow_dispatch",
            "url": "https://example/3",
        },
        {
            "databaseId": 1,
            "startedAt": "2026-03-03T18:00:00Z",
            "updatedAt": "2026-03-03T18:12:00Z",
            "headSha": "aaa",
            "conclusion": "failure",
            "event": "schedule",
            "url": "https://example/1",
        },
        {
            "databaseId": 2,
            "startedAt": "2026-03-03T19:00:00Z",
            "updatedAt": "2026-03-03T19:09:00Z",
            "headSha": "bbb",
            "conclusion": "success",
            "event": "schedule",
            "url": "https://example/2",
        },
    ]

    filtered = MODULE._normalize_runs(raw, conclusion="success", event=None)

    assert [run.run_id for run in filtered] == [2, 3]
    assert filtered[0].duration_seconds == 9 * 60



def test_summarize_handles_empty_and_non_empty_samples() -> None:
    empty = MODULE._summarize([])
    assert empty["count"] == 0
    assert empty["median"] == 0.0

    values = [600.0, 660.0, 540.0]
    summary = MODULE._summarize(values)

    assert summary["count"] == 3.0
    assert summary["median"] == 600.0
    assert summary["min"] == 540.0
    assert summary["max"] == 660.0
