from __future__ import annotations

import subprocess
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "audit_legacy_aws_consumer_refs.sh"


def test_audit_legacy_consumer_refs_ignores_artifacts_directory() -> None:
    token = f"sentinel-{uuid.uuid4()}"
    artifact_dir = REPO_ROOT / "artifacts" / "_tmp_pytest"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_file = artifact_dir / "legacy_ref_probe.txt"
    artifact_file.write_text(f"AWS_ACCESS_KEY_ID={token}\n", encoding="utf-8")

    try:
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        artifact_file.unlink(missing_ok=True)

    combined_output = f"{result.stdout}\n{result.stderr}"
    assert result.returncode in {0, 10, 20, 30}
    assert str(artifact_file.relative_to(REPO_ROOT)) not in combined_output
    assert token not in combined_output
