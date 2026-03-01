"""
Test: Go-Live-Testlauf Evidence Archive (Issue #528)

Verifies that the acceptance run evidence archive ACC-MCS-2026-03-01-001
is present and contains all mandatory artefacts as specified in
docs/compliance/ACCEPTANCE_TEST_CATALOG_V1.md §Nachweisablage.
"""

from __future__ import annotations

import os
import yaml
import unittest

EVIDENCE_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "reports",
    "compliance",
    "acceptance",
    "2026",
    "03",
    "ACC-MCS-2026-03-01-001",
)
REQUIRED_FILES = [
    "summary.md",
    "automated-test-output.txt",
    "findings.md",
    "signoff.yaml",
]


class TestGoLiveTestlaufEvidence(unittest.TestCase):
    """Evidence archive for BL-342 Go-Live-Testlauf must be present and valid."""

    def _path(self, filename: str) -> str:
        return os.path.join(EVIDENCE_DIR, filename)

    def test_evidence_dir_exists(self) -> None:
        self.assertTrue(
            os.path.isdir(EVIDENCE_DIR),
            f"Evidence directory missing: {EVIDENCE_DIR}",
        )

    def test_all_mandatory_files_present(self) -> None:
        for fname in REQUIRED_FILES:
            with self.subTest(file=fname):
                self.assertTrue(
                    os.path.isfile(self._path(fname)),
                    f"Mandatory evidence file missing: {fname}",
                )

    def test_summary_contains_pass_result(self) -> None:
        with open(self._path("summary.md"), encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("PASS", content, "summary.md must contain result PASS")
        self.assertIn("31", content, "summary.md must reference 31 tests")

    def test_automated_output_is_non_empty(self) -> None:
        stat = os.stat(self._path("automated-test-output.txt"))
        self.assertGreater(stat.st_size, 100, "automated-test-output.txt must be non-empty")

    def test_signoff_yaml_is_valid(self) -> None:
        with open(self._path("signoff.yaml"), encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        self.assertEqual(data.get("result"), "pass", "signoff result must be 'pass'")
        self.assertEqual(data.get("finding_count"), 0, "finding_count must be 0")
        self.assertEqual(data.get("tests_passed"), 31, "tests_passed must be 31")
        self.assertEqual(data.get("tests_failed"), 0, "tests_failed must be 0")
        self.assertIn("528", data.get("issue_ref", ""), "issue_ref must reference #528")

    def test_findings_md_states_no_findings(self) -> None:
        with open(self._path("findings.md"), encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("finding-frei", content, "findings.md must declare finding-frei result")

    def test_backlog_tracks_issue_528_completion(self) -> None:
        backlog_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "BACKLOG.md"
        )
        with open(backlog_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn(
            "528",
            content,
            "BACKLOG.md must reference issue #528",
        )


if __name__ == "__main__":
    unittest.main()
