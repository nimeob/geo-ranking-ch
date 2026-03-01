"""Leichtgewichtiger Async-Worker für Analyze-Jobs.

Queue-/Dispatcher-light: ein Hintergrundthread verarbeitet Jobs seriell und
schreibt deterministische Partial-/Final-Snapshots in den AsyncJobStore.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from copy import deepcopy
from typing import Any

from src.api.address_intel import AddressIntelError
from src.api.async_jobs import AsyncJobStore


def _read_stage_delay_seconds() -> float:
    raw_value = str(os.getenv("ASYNC_WORKER_STAGE_DELAY_MS", "150")).strip()
    try:
        parsed_ms = int(raw_value)
    except ValueError:
        parsed_ms = 150
    parsed_ms = max(0, parsed_ms)
    return float(parsed_ms) / 1000.0


def _fault_injection_enabled() -> bool:
    return str(os.getenv("ENABLE_E2E_FAULT_INJECTION", "0")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _build_async_partial_result_stub(
    *,
    query: str,
    intelligence_mode: str,
    stage_index: int,
    total_stages: int,
) -> dict[str, Any]:
    progress_percent = max(1, min(99, int(round((stage_index / max(total_stages, 1)) * 100.0))))
    return {
        "ok": True,
        "result": {
            "status": {
                "confidence": {
                    "score": None,
                    "max": 100,
                    "level": "pending_implementation",
                },
                "sources": {
                    "async_runtime": {
                        "status": "partial",
                    }
                },
                "source_attribution": {
                    "match": ["async_runtime"],
                },
            },
            "data": {
                "entity": {
                    "query": query,
                },
                "modules": {
                    "runtime": {
                        "status": "partial",
                        "intelligence_mode": intelligence_mode,
                        "stage_index": stage_index,
                        "total_stages": total_stages,
                        "progress_percent": progress_percent,
                        "message": "Async worker partial snapshot",
                    }
                },
                "by_source": {
                    "async_runtime": {
                        "module_refs": ["runtime"],
                    }
                },
            },
        },
    }


def _build_async_final_result_stub(*, query: str, intelligence_mode: str) -> dict[str, Any]:
    return {
        "ok": True,
        "result": {
            "status": {
                "confidence": {
                    "score": None,
                    "max": 100,
                    "level": "pending_implementation",
                },
                "sources": {
                    "async_runtime": {
                        "status": "ok",
                    }
                },
                "source_attribution": {
                    "match": ["async_runtime"],
                },
            },
            "data": {
                "entity": {
                    "query": query,
                },
                "modules": {
                    "runtime": {
                        "status": "completed",
                        "intelligence_mode": intelligence_mode,
                        "message": "Async worker final result",
                    }
                },
                "by_source": {
                    "async_runtime": {
                        "module_refs": ["runtime"],
                    }
                },
            },
        },
    }


def _classify_failure(exc: Exception) -> tuple[str, bool, str]:
    if isinstance(exc, TimeoutError):
        return "timeout", True, "retry_with_backoff"
    if isinstance(exc, AddressIntelError):
        return "address_intel", False, "check_input_and_retry"
    return "internal", True, "retry_with_backoff"


class AsyncJobRuntime:
    """Single-worker Runtime für asynchrone Analyze-Jobs."""

    def __init__(self, *, store: AsyncJobStore, stage_delay_seconds: float | None = None):
        self._store = store
        self._stage_delay_seconds = (
            _read_stage_delay_seconds()
            if stage_delay_seconds is None
            else max(0.0, float(stage_delay_seconds))
        )
        self._queue: deque[str] = deque()
        self._queued_ids: set[str] = set()
        self._condition = threading.Condition()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with self._condition:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="async-job-worker",
                daemon=True,
            )
            self._thread.start()

    def stop(self, *, timeout: float = 2.0) -> None:
        self._stop_event.set()
        with self._condition:
            self._condition.notify_all()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=max(0.0, timeout))

    def enqueue(self, job_id: str) -> None:
        normalized_job_id = str(job_id or "").strip()
        if not normalized_job_id:
            return
        with self._condition:
            if normalized_job_id in self._queued_ids:
                return
            self._queue.append(normalized_job_id)
            self._queued_ids.add(normalized_job_id)
            self._condition.notify_all()

    def enqueue_pending_jobs(self) -> None:
        pending_ids = self._store.list_job_ids(statuses={"queued", "running", "partial"})
        for job_id in pending_ids:
            self.enqueue(job_id)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            with self._condition:
                if not self._queue:
                    self._condition.wait(timeout=0.5)
                    continue
                job_id = self._queue.popleft()
                self._queued_ids.discard(job_id)

            try:
                self._process_one(job_id)
            except Exception:
                # Worker darf den Prozess nicht crashen; Fehlerpfad wird pro Job persistiert.
                continue

    def _process_one(self, job_id: str) -> None:
        job = self._store.get_job(job_id)
        if job is None:
            return

        status = str(job.get("status") or "queued")
        if status in {"completed", "failed", "canceled"}:
            return

        canceled_job = self._store.consume_cancel_request(job_id=job_id, actor_type="worker")
        if canceled_job is not None and str(canceled_job.get("status")) == "canceled":
            return

        try:
            if status == "queued":
                self._store.transition_job(
                    job_id=job_id,
                    to_status="running",
                    progress_percent=max(5, int(job.get("progress_percent", 0) or 0)),
                    actor_type="worker",
                )

            job = self._store.get_job(job_id) or {}
            status = str(job.get("status") or "queued")
            if status not in {"running", "partial"}:
                return

            query = str(job.get("query") or "")
            intelligence_mode = str(job.get("intelligence_mode") or "basic")

            self._maybe_raise_fault_injection(query)

            total_stages = 2
            for stage_index in range(1, total_stages + 1):
                canceled_job = self._store.consume_cancel_request(job_id=job_id, actor_type="worker")
                if canceled_job is not None and str(canceled_job.get("status")) == "canceled":
                    return

                if self._stage_delay_seconds > 0:
                    time.sleep(self._stage_delay_seconds)

                partial_payload = _build_async_partial_result_stub(
                    query=query,
                    intelligence_mode=intelligence_mode,
                    stage_index=stage_index,
                    total_stages=total_stages,
                )
                partial_result = self._store.create_result(
                    job_id=job_id,
                    result_payload=partial_payload,
                    result_kind="partial",
                )

                progress_percent = 35 if stage_index == 1 else 70
                self._store.transition_job(
                    job_id=job_id,
                    to_status="partial",
                    progress_percent=progress_percent,
                    result_id=str(partial_result.get("result_id") or ""),
                    actor_type="worker",
                )

            canceled_job = self._store.consume_cancel_request(job_id=job_id, actor_type="worker")
            if canceled_job is not None and str(canceled_job.get("status")) == "canceled":
                return

            final_payload = _build_async_final_result_stub(
                query=query,
                intelligence_mode=intelligence_mode,
            )
            final_result = self._store.create_result(
                job_id=job_id,
                result_payload=final_payload,
                result_kind="final",
            )
            self._store.transition_job(
                job_id=job_id,
                to_status="completed",
                progress_percent=100,
                result_id=str(final_result.get("result_id") or ""),
                actor_type="worker",
            )
        except Exception as exc:
            current = self._store.get_job(job_id)
            if current is None:
                return
            current_status = str(current.get("status") or "queued")
            if current_status in {"completed", "failed", "canceled"}:
                return

            error_code, retryable, retry_hint = _classify_failure(exc)
            progress_percent = int(current.get("progress_percent", 0) or 0)
            try:
                self._store.transition_job(
                    job_id=job_id,
                    to_status="failed",
                    progress_percent=progress_percent,
                    error_code=error_code,
                    error_message=str(exc) or "async job failed",
                    retryable=retryable,
                    retry_hint=retry_hint,
                    actor_type="worker",
                )
            except ValueError:
                # Race mit Cancel/Terminal-Übergang: nichts weiter tun.
                return

    @staticmethod
    def _maybe_raise_fault_injection(query: str) -> None:
        if not _fault_injection_enabled():
            return

        normalized = str(query or "").strip()
        if normalized == "__timeout__":
            raise TimeoutError("forced timeout for async e2e")
        if normalized == "__internal__":
            raise RuntimeError("forced internal error for async e2e")
        if normalized == "__address_intel__":
            raise AddressIntelError("forced address intel error for async e2e")


__all__ = [
    "AsyncJobRuntime",
    "_build_async_partial_result_stub",
    "_build_async_final_result_stub",
]
