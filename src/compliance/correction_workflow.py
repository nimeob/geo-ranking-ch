"""Runtime implementation of the Korrektur-Workflow (BL-342 / Issue #520).

Enforces the Korrektur-Richtlinie v1 (docs/compliance/KORREKTUR_RICHTLINIE_V1.md):
  - Originals are immutable — existing versions can never be overwritten.
  - Every correction creates a new version with a mandatory ``korrekturgrund``.
  - All six Pflichtfelder must be non-empty and structurally valid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Mapping, Any, Dict, List, Optional, Tuple


_VERSION_RE = re.compile(r"^v\d+\.\d+$")

_PLACEHOLDER_PATTERNS = (
    re.compile(r"^todo$", re.IGNORECASE),
    re.compile(r"^tbd$", re.IGNORECASE),
    re.compile(r"^n/?a$", re.IGNORECASE),
    re.compile(r"^-$"),
    re.compile(r"^\s*$"),
)

_EVIDENCE_PREFIXES = ("http://", "https://", "issue:", "#")


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    val = payload.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"{key!r} must be a non-empty string")
    return val.strip()


def _check_placeholder(value: str, key: str) -> None:
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.fullmatch(value):
            raise ValueError(
                f"{key!r} contains a placeholder or empty value: {value!r}"
            )


@dataclass(frozen=True, slots=True)
class CorrectionMetadataV1:
    """Validated correction metadata envelope.

    Required fields (all Pflichtfelder from Korrektur-Richtlinie v1):
    - version           — new version string (v<major>.<minor>)
    - supersedes_version — version of the record being corrected
    - korrekturgrund    — non-empty, human-readable reason (no placeholders)
    - wirksam_ab        — effective date (ISO-8601)
    - approved_by_role  — role that approved the correction
    - evidence_ref      — issue URL or reference
    """

    version: str
    supersedes_version: str
    korrekturgrund: str
    wirksam_ab: date
    approved_by_role: str
    evidence_ref: str

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CorrectionMetadataV1":
        required_keys = (
            "version",
            "supersedes_version",
            "korrekturgrund",
            "wirksam_ab",
            "approved_by_role",
            "evidence_ref",
        )
        for key in required_keys:
            if key not in payload:
                raise ValueError(f"missing required field: {key!r}")

        version = _require_str(payload, "version")
        if _VERSION_RE.fullmatch(version) is None:
            raise ValueError("version must match v<major>.<minor>")

        supersedes_version = _require_str(payload, "supersedes_version")
        if _VERSION_RE.fullmatch(supersedes_version) is None:
            raise ValueError("supersedes_version must match v<major>.<minor>")
        if supersedes_version == version:
            raise ValueError(
                "version and supersedes_version must differ"
            )

        korrekturgrund = _require_str(payload, "korrekturgrund")
        _check_placeholder(korrekturgrund, "korrekturgrund")
        if len(korrekturgrund) < 10:
            raise ValueError(
                "korrekturgrund must be at least 10 characters (substantive reason required)"
            )

        wirksam_ab_raw = _require_str(payload, "wirksam_ab")
        try:
            wirksam_ab = date.fromisoformat(wirksam_ab_raw)
        except ValueError as exc:
            raise ValueError("wirksam_ab must be an ISO date (YYYY-MM-DD)") from exc

        approved_by_role = _require_str(payload, "approved_by_role")
        _check_placeholder(approved_by_role, "approved_by_role")

        evidence_ref = _require_str(payload, "evidence_ref")
        if not any(evidence_ref.startswith(p) for p in _EVIDENCE_PREFIXES):
            raise ValueError(
                "evidence_ref must start with http://, https://, issue:, or #"
            )

        return cls(
            version=version,
            supersedes_version=supersedes_version,
            korrekturgrund=korrekturgrund,
            wirksam_ab=wirksam_ab,
            approved_by_role=approved_by_role,
            evidence_ref=evidence_ref,
        )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "supersedes_version": self.supersedes_version,
            "korrekturgrund": self.korrekturgrund,
            "wirksam_ab": self.wirksam_ab.isoformat(),
            "approved_by_role": self.approved_by_role,
            "evidence_ref": self.evidence_ref,
        }


@dataclass
class VersionedDocument:
    """A document with an immutable original and a linear correction history."""

    document_id: str
    content: Any  # original payload / content
    version: str  # initial version, e.g. "v1.0"

    # Ordered list of (CorrectionMetadataV1, corrected_content) pairs.
    # The first entry is always the original; subsequent entries are corrections.
    _history: List[Tuple[str, Any]] = field(default_factory=list, repr=False, compare=False)

    def __post_init__(self) -> None:
        if _VERSION_RE.fullmatch(self.version) is None:
            raise ValueError("version must match v<major>.<minor>")
        # Seed history with original
        self._history = [(self.version, self.content)]

    @property
    def current_version(self) -> str:
        return self._history[-1][0]

    @property
    def current_content(self) -> Any:
        return self._history[-1][1]

    def get_version(self, version: str) -> Any:
        for ver, content in self._history:
            if ver == version:
                return content
        raise KeyError(f"version {version!r} not found in document {self.document_id!r}")

    def all_versions(self) -> List[str]:
        return [ver for ver, _ in self._history]

    def apply_correction(
        self,
        correction: CorrectionMetadataV1,
        new_content: Any,
    ) -> None:
        """Add a correction as a new version.  Original is never modified.

        Raises:
            ValueError — if correction metadata is inconsistent with current state.
        """
        if correction.supersedes_version != self.current_version:
            raise ValueError(
                f"supersedes_version {correction.supersedes_version!r} does not match "
                f"current version {self.current_version!r}"
            )
        if correction.version in [ver for ver, _ in self._history]:
            raise ValueError(
                f"version {correction.version!r} already exists in document "
                f"{self.document_id!r} — overwriting is not allowed"
            )
        # Append new version; original entry at index 0 is never touched.
        self._history.append((correction.version, new_content))


class CorrectionStore:
    """In-memory store enforcing immutability of originals.

    In production this would delegate to a persistent backend.  The interface
    is kept side-effect-free (no external I/O) so it is fully unit-testable.
    """

    def __init__(self) -> None:
        self._docs: Dict[str, VersionedDocument] = {}

    def register(
        self,
        document_id: str,
        content: Any,
        version: str = "v1.0",
    ) -> VersionedDocument:
        """Register a new original document.  Raises if id already exists."""
        if document_id in self._docs:
            raise ValueError(
                f"document {document_id!r} already registered — "
                "use apply_correction() to create a new version"
            )
        doc = VersionedDocument(document_id=document_id, content=content, version=version)
        self._docs[document_id] = doc
        return doc

    def apply_correction(
        self,
        document_id: str,
        correction_payload: Mapping[str, Any],
        new_content: Any,
    ) -> VersionedDocument:
        """Validate the correction metadata and append as a new version."""
        doc = self._get(document_id)
        correction = CorrectionMetadataV1.from_dict(correction_payload)
        doc.apply_correction(correction, new_content)
        return doc

    def get_document(self, document_id: str) -> VersionedDocument:
        return self._get(document_id)

    def original_content(self, document_id: str) -> Any:
        """Return the original (v1.0) content — always the first history entry."""
        doc = self._get(document_id)
        return doc._history[0][1]

    def current_content(self, document_id: str) -> Any:
        return self._get(document_id).current_content

    def _get(self, document_id: str) -> VersionedDocument:
        try:
            return self._docs[document_id]
        except KeyError:
            raise KeyError(f"document {document_id!r} not found in store")
