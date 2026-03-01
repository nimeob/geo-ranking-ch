"""
Test: Pre-Go-Live-Readiness-Review Docs (Issue #529)

Verifies that the readiness review document exists with required markers
and is consistent with the completed acceptance run.
"""

from __future__ import annotations

import os
import unittest

REVIEW_DOC = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docs",
    "compliance",
    "GOLIVE_READINESS_REVIEW_V1.md",
)

REQUIRED_MARKERS = [
    "ACC-MCS-2026-03-01-001",
    "freigegeben",
    "READINESS-BL342-2026-03-01-001",
    "deviation_count: 0",
    "result: freigegeben",
    "16/16",
    "#528",
    "#529",
]


class TestGoLiveReadinessReviewDocs(unittest.TestCase):
    """Pre-Go-Live-Readiness-Review document must exist and contain required markers."""

    def test_readiness_review_doc_exists(self) -> None:
        self.assertTrue(
            os.path.isfile(REVIEW_DOC),
            f"Readiness review doc missing: {REVIEW_DOC}",
        )

    def test_readiness_review_doc_has_required_markers(self) -> None:
        with open(REVIEW_DOC, encoding="utf-8") as fh:
            content = fh.read()
        for marker in REQUIRED_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(
                    marker,
                    content,
                    f"Required marker missing in readiness review doc: {marker!r}",
                )

    def test_readiness_review_doc_declares_freigabe(self) -> None:
        with open(REVIEW_DOC, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            "Freigabe",
            content,
            "Readiness review doc must contain a Freigabe section",
        )

    def test_backlog_tracks_issue_529_completion(self) -> None:
        backlog_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "BACKLOG.md"
        )
        with open(backlog_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            "529",
            content,
            "BACKLOG.md must reference issue #529",
        )


if __name__ == "__main__":
    unittest.main()
