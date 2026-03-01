"""Runtime data model for compliance policy metadata (v1).

The model enforces the minimum metadata fields introduced in
`docs/compliance/POLICY_STANDARD_V1.md` so policy artifacts can be validated
consistently before downstream processing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Mapping


_REQUIRED_FIELDS = (
    "policy_id",
    "version",
    "begruendung",
    "wirksam_ab",
    "impact_referenz",
)

_VERSION_RE = re.compile(r"^v\d+\.\d+$")


def _require_non_empty(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class PolicyMetadataV1:
    """Validated policy metadata envelope.

    Required fields:
    - policy_id
    - version
    - begruendung
    - wirksam_ab
    - impact_referenz
    """

    policy_id: str
    version: str
    begruendung: str
    wirksam_ab: date
    impact_referenz: str

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PolicyMetadataV1":
        """Create a validated model from a mapping payload."""
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")

        for field_name in _REQUIRED_FIELDS:
            if field_name not in payload:
                raise ValueError(f"missing required field: {field_name}")

        policy_id = _require_non_empty(payload, "policy_id")
        if not policy_id.startswith("POL-"):
            raise ValueError("policy_id must start with 'POL-'")

        version = _require_non_empty(payload, "version")
        if _VERSION_RE.fullmatch(version) is None:
            raise ValueError("version must match v<major>.<minor>")

        begruendung = _require_non_empty(payload, "begruendung")

        wirksam_ab_raw = _require_non_empty(payload, "wirksam_ab")
        try:
            wirksam_ab = date.fromisoformat(wirksam_ab_raw)
        except ValueError as exc:
            raise ValueError("wirksam_ab must be an ISO date (YYYY-MM-DD)") from exc

        impact_referenz = _require_non_empty(payload, "impact_referenz")
        if not (
            impact_referenz.startswith("http://")
            or impact_referenz.startswith("https://")
            or impact_referenz.startswith("issue:")
            or impact_referenz.startswith("#")
        ):
            raise ValueError("impact_referenz must be a URL or issue reference")

        return cls(
            policy_id=policy_id,
            version=version,
            begruendung=begruendung,
            wirksam_ab=wirksam_ab,
            impact_referenz=impact_referenz,
        )

    def to_dict(self) -> dict[str, str]:
        """Serialize the model to stable string values."""
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "begruendung": self.begruendung,
            "wirksam_ab": self.wirksam_ab.isoformat(),
            "impact_referenz": self.impact_referenz,
        }


def validate_policy_metadata(payload: Mapping[str, Any]) -> dict[str, str]:
    """Validate and normalize an untrusted policy metadata payload."""
    return PolicyMetadataV1.from_dict(payload).to_dict()
