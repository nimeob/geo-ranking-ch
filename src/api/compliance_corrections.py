"""HTTP-level enforcement of the Korrektur-Workflow (Issue #521).

Provides ``handle_correction_request()`` which is called by ``web_service.py``
for ``POST /compliance/corrections/<document_id>`` requests.

Contract
--------
- Missing or empty ``korrekturgrund`` → HTTP 422 Unprocessable Entity
  (error_code: ``korrekturgrund_required``)
- Any other missing/invalid Pflichtfeld → HTTP 422
  (error_code: ``invalid_correction_payload``)
- Document not found in store → HTTP 404
- Success → HTTP 201 Created with ``{ok: True, document_id, version, supersedes_version}``
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from src.compliance.correction_workflow import CorrectionStore

# Module-level singleton store (in production: inject / per-tenant store)
_GLOBAL_CORRECTION_STORE = CorrectionStore()


def get_global_correction_store() -> CorrectionStore:
    """Return the module-level CorrectionStore (testable via reset helper)."""
    return _GLOBAL_CORRECTION_STORE


def reset_global_correction_store() -> None:
    """Replace the global store with a fresh instance (for test isolation)."""
    global _GLOBAL_CORRECTION_STORE  # noqa: PLW0603
    _GLOBAL_CORRECTION_STORE = CorrectionStore()


def _error_body(
    *,
    error_code: str,
    message: str,
    request_id: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error_code,
        "message": message,
        "request_id": request_id,
    }


def handle_correction_request(
    document_id: str,
    payload: dict[str, Any],
    request_id: str,
    *,
    store: CorrectionStore | None = None,
    new_content: Any = None,
) -> tuple[dict[str, Any], HTTPStatus]:
    """Validate and apply a correction.  Returns (response_body, http_status).

    ``store`` defaults to the module-level singleton when None.
    ``new_content`` is the corrected document content (may be None for
    metadata-only corrections in tests).
    """
    _store = store if store is not None else _GLOBAL_CORRECTION_STORE

    if not isinstance(payload, dict):
        return (
            _error_body(
                error_code="invalid_correction_payload",
                message="Request body must be a JSON object.",
                request_id=request_id,
            ),
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    # Early guard: korrekturgrund missing or empty — most common API mistake
    korrekturgrund = payload.get("korrekturgrund")
    if korrekturgrund is None:
        return (
            _error_body(
                error_code="korrekturgrund_required",
                message="Field 'korrekturgrund' is required and must be a non-empty string.",
                request_id=request_id,
            ),
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    if not isinstance(korrekturgrund, str) or not korrekturgrund.strip():
        return (
            _error_body(
                error_code="korrekturgrund_required",
                message="Field 'korrekturgrund' must be a non-empty string.",
                request_id=request_id,
            ),
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    # Delegate full validation + store mutation to CorrectionStore
    try:
        doc = _store.apply_correction(
            document_id=document_id,
            correction_payload=payload,
            new_content=new_content,
        )
    except KeyError:
        return (
            _error_body(
                error_code="document_not_found",
                message=f"Document '{document_id}' not found.",
                request_id=request_id,
            ),
            HTTPStatus.NOT_FOUND,
        )
    except ValueError as exc:
        exc_msg = str(exc)
        # Surface korrekturgrund-specific errors with a dedicated code
        if "korrekturgrund" in exc_msg:
            return (
                _error_body(
                    error_code="korrekturgrund_required",
                    message=exc_msg,
                    request_id=request_id,
                ),
                HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        return (
            _error_body(
                error_code="invalid_correction_payload",
                message=exc_msg,
                request_id=request_id,
            ),
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    return (
        {
            "ok": True,
            "document_id": document_id,
            "version": doc.current_version,
            "supersedes_version": payload.get("supersedes_version"),
            "request_id": request_id,
        },
        HTTPStatus.CREATED,
    )
