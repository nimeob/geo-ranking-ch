"""
Test: Go-Live-Entscheidungsprotokoll Docs (Issue #530)

Verifies that the Go/No-Go decision protocol document exists
with required markers and records a valid GO decision.
"""

from __future__ import annotations

import os
import unittest

DECISION_DOC = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docs",
    "compliance",
    "GOLIVE_DECISION_PROTOCOL_V1.md",
)

REQUIRED_MARKERS = [
    "GOLIVE-BL342-2026-03-01-001",
    "decision: GO",
    "ACC-MCS-2026-03-01-001",
    "READINESS-BL342-2026-03-01-001",
    "gates_passed: 10",
    "blocking_items_count: 0",
    "#530",
    "#532",
]


class TestGoLiveDecisionProtocolDocs(unittest.TestCase):
    """Go-Live-Entscheidungsprotokoll document must exist and contain required markers."""

    def test_decision_doc_exists(self) -> None:
        self.assertTrue(
            os.path.isfile(DECISION_DOC),
            f"Decision protocol doc missing: {DECISION_DOC}",
        )

    def test_decision_doc_has_required_markers(self) -> None:
        with open(DECISION_DOC, encoding="utf-8") as fh:
            content = fh.read()
        for marker in REQUIRED_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(
                    marker,
                    content,
                    f"Required marker missing in decision protocol: {marker!r}",
                )

    def test_decision_doc_records_go_decision(self) -> None:
        with open(DECISION_DOC, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            "decision: GO",
            content,
            "Decision protocol must record GO decision",
        )

    def test_decision_doc_all_gates_passed(self) -> None:
        with open(DECISION_DOC, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            "10/10 Gates erfüllt",
            content,
            "Decision doc must show 10/10 gates passed",
        )

    def test_backlog_tracks_issue_530_completion(self) -> None:
        backlog_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "BACKLOG.md"
        )
        with open(backlog_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            "530",
            content,
            "BACKLOG.md must reference issue #530",
        )


if __name__ == "__main__":
    unittest.main()
