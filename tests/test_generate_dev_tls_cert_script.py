import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "generate_dev_tls_cert.sh"


@unittest.skipUnless(shutil.which("openssl"), "openssl nicht verfügbar")
class TestGenerateDevTlsCertScript(unittest.TestCase):
    def test_generates_cert_and_key_with_secure_key_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env.update(
                {
                    "DEV_TLS_CERT_DIR": tmpdir,
                    "DEV_TLS_CERT_BASENAME": "ci-dev",
                    "DEV_TLS_CERT_DAYS": "2",
                }
            )

            cp = subprocess.run(
                [str(SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)

            cert = Path(tmpdir) / "ci-dev.crt"
            key = Path(tmpdir) / "ci-dev.key"
            self.assertTrue(cert.is_file())
            self.assertTrue(key.is_file())

            mode = stat.S_IMODE(key.stat().st_mode)
            self.assertEqual(mode, 0o600)
            self.assertIn(str(cert), cp.stdout)
            self.assertIn(str(key), cp.stdout)

    def test_rejects_non_numeric_or_non_positive_days(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env.update(
                {
                    "DEV_TLS_CERT_DIR": tmpdir,
                    "DEV_TLS_CERT_DAYS": "0",
                }
            )

            cp = subprocess.run(
                [str(SCRIPT)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(cp.returncode, 2, msg=cp.stdout + "\n" + cp.stderr)
            self.assertIn("DEV_TLS_CERT_DAYS muss eine Ganzzahl > 0 sein", cp.stderr)


if __name__ == "__main__":
    unittest.main()
