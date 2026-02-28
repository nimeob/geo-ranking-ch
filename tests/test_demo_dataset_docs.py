import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDemoDatasetDocs(unittest.TestCase):
    def test_demo_dataset_doc_has_3_to_5_entries_and_expected_markers(self):
        doc_path = REPO_ROOT / "docs" / "DEMO_DATASET_CH.md"
        self.assertTrue(doc_path.is_file(), msg="docs/DEMO_DATASET_CH.md fehlt")

        content = doc_path.read_text(encoding="utf-8")
        self.assertIn("# BL-20.7.r2 — Reproduzierbares Demo-Datenset (CH)", content)
        self.assertIn("Erwartete Kernaussagen", content)
        self.assertIn("Confidence", content)
        self.assertIn("Unsicherheit", content)
        self.assertIn("## Demo-Skript (Kurz)", content)

        dataset_ids = sorted(set(re.findall(r"DS-CH-\d{2}", content)))
        self.assertGreaterEqual(
            len(dataset_ids),
            3,
            msg="Es müssen mindestens 3 Demo-Standorte dokumentiert sein",
        )
        self.assertLessEqual(
            len(dataset_ids),
            5,
            msg="Es dürfen maximal 5 Demo-Standorte dokumentiert sein",
        )


if __name__ == "__main__":
    unittest.main()
