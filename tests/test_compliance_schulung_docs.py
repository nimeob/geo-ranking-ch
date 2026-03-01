"""
Test: Schulungsdokumentation BL-342 Docs (Issue #532)

Verifies that the training documentation exists with required markers
for all relevant roles and includes attendance + comprehension evidence.
"""

from __future__ import annotations

import os
import unittest

SCHULUNG_DOC = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docs",
    "compliance",
    "SCHULUNG_MINIMUM_COMPLIANCE_V1.md",
)

REQUIRED_MARKERS = [
    "SCHULUNG-BL342-2026-03-01-001",
    "roles_trained: 5",
    "roles_verified: 5",
    "completion_status: abgeschlossen",
    "GOLIVE-BL342-2026-03-01-001",
    "ACC-MCS-2026-03-01-001",
    "#532",
    "Compliance Lead",
    "IT Product Owner",
    "QA Lead",
]


class TestComplianceSchulungDocs(unittest.TestCase):
    """Training documentation must exist and contain required proof of attendance."""

    def test_schulung_doc_exists(self) -> None:
        self.assertTrue(
            os.path.isfile(SCHULUNG_DOC),
            f"Schulung doc missing: {SCHULUNG_DOC}",
        )

    def test_schulung_doc_has_required_markers(self) -> None:
        with open(SCHULUNG_DOC, encoding="utf-8") as fh:
            content = fh.read()
        for marker in REQUIRED_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(
                    marker,
                    content,
                    f"Required marker missing in Schulung doc: {marker!r}",
                )

    def test_schulung_doc_is_completed(self) -> None:
        with open(SCHULUNG_DOC, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            "completion_status: abgeschlossen",
            content,
            "Schulung must be marked as abgeschlossen",
        )

    def test_backlog_tracks_issue_532_completion(self) -> None:
        backlog_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "BACKLOG.md"
        )
        with open(backlog_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            "532",
            content,
            "BACKLOG.md must reference issue #532",
        )


if __name__ == "__main__":
    unittest.main()
