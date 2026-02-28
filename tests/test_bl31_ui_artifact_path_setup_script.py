import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = REPO_ROOT / "scripts" / "setup_bl31_ui_artifact_path.sh"
BUILDSPEC = REPO_ROOT / "buildspec-openclaw.yml"


class TestBl31UiArtifactPathSetup(unittest.TestCase):
    def test_setup_script_is_syntax_valid(self):
        cp = subprocess.run(
            ["bash", "-n", str(SETUP_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)

    def test_buildspec_contains_ui_build_and_push_steps(self):
        text = BUILDSPEC.read_text(encoding="utf-8")
        self.assertIn("docker build -f \"${DOCKERFILE_PATH}\"", text)
        self.assertIn("--build-arg APP_VERSION=\"${APP_VERSION}\"", text)
        self.assertIn("docker push \"${REPO_URI}:${IMAGE_TAG}\"", text)


if __name__ == "__main__":
    unittest.main()
