from __future__ import annotations

from dataclasses import dataclass

from src.api.async_worker_runtime import AsyncJobRuntime


@dataclass
class _LegacyBoolCancelStore:
    """Minimal store stub with legacy consume_cancel_request signature.

    Legacy behavior:
    - consume_cancel_request(job_id=...) exists
    - returns bool (False = no cancel request)
    - does NOT accept actor_type kwarg
    """

    def __post_init__(self):
        self.job = {
            "job_id": "job-1",
            "status": "queued",
            "progress_percent": 0,
            "query": "Bahnhofstrasse 1, 8001 Zürich",
            "intelligence_mode": "basic",
        }
        self.results: list[dict] = []

    def get_job(self, job_id: str):
        if job_id != self.job["job_id"]:
            return None
        return dict(self.job)

    def consume_cancel_request(self, *, job_id: str):
        if job_id != self.job["job_id"]:
            return False
        return False

    def transition_job(self, *, job_id: str, to_status: str, progress_percent: int | None = None, result_id: str | None = None, **_kwargs):
        assert job_id == self.job["job_id"]
        self.job["status"] = to_status
        if progress_percent is not None:
            self.job["progress_percent"] = progress_percent
        if result_id is not None:
            self.job["result_id"] = result_id
        return dict(self.job)

    def create_result(self, *, job_id: str, result_payload: dict, result_kind: str = "final", **_kwargs):
        assert job_id == self.job["job_id"]
        result_id = f"r-{len(self.results) + 1}"
        row = {
            "result_id": result_id,
            "job_id": job_id,
            "result_kind": result_kind,
            "payload": result_payload,
        }
        self.results.append(row)
        return dict(row)


def test_runtime_processes_job_with_legacy_bool_cancel_store() -> None:
    """Regression for DB legacy signature mismatch.

    Before fix, AsyncJobRuntime passed actor_type to a store method that did not
    accept it and jobs stayed permanently queued.
    """
    store = _LegacyBoolCancelStore()
    runtime = AsyncJobRuntime(store=store, stage_delay_seconds=0.0)

    runtime._process_one("job-1")

    assert store.job["status"] == "completed"
    assert int(store.job.get("progress_percent") or 0) == 100
    assert len(store.results) >= 1
    assert any(r.get("result_kind") == "final" for r in store.results)
