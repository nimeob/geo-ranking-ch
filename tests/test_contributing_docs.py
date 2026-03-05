#!/usr/bin/env python3
"""Regression-Checks für CONTRIBUTING.md (dev-only Guide)."""

from __future__ import annotations

from pathlib import Path
import unittest


class TestContributingDocs(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path("CONTRIBUTING.md")
        self.assertTrue(self.path.exists(), "CONTRIBUTING.md fehlt")
        self.content = self.path.read_text(encoding="utf-8")

    def test_contains_core_dev_sections_and_commands(self) -> None:
        required_markers = [
            "## Setup (frischer Checkout)",
            "## Lokaler Dev-Start",
            "## Tests",
            "## Lint / Format",
            "python -m src.api.web_service",
            "python -m src.ui.service",
            "pytest -q",
            "pre-commit run --all-files",
            "npm ci",
        ]
        for marker in required_markers:
            self.assertIn(marker, self.content, msg=f"Marker fehlt in CONTRIBUTING.md: {marker}")

    def test_is_explicitly_dev_only_and_excludes_deploy_instructions(self) -> None:
        self.assertIn("dev-only", self.content.lower())
        self.assertIn("Out of scope", self.content)

        forbidden_markers = [
            "terraform apply",
            "openclaw gateway start",
            "kubectl apply",
            "aws ecs update-service",
        ]
        lowered = self.content.lower()
        for marker in forbidden_markers:
            self.assertNotIn(marker, lowered, msg=f"Deployment/Infra-Marker unerwartet gefunden: {marker}")


if __name__ == "__main__":
    unittest.main()
