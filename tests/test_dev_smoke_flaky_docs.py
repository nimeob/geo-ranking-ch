from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_deploy_test_tiers_documents_flaky_in_dev_ci_policy() -> None:
    content = (REPO_ROOT / "docs" / "testing" / "DEPLOY_TEST_TIERS.md").read_text(encoding="utf-8")

    assert "### Flaky in Dev-CI" in content
    assert "DEV_SMOKE_MAX_RETRIES=1" in content
    assert "flaky_hint" in content
    assert "run_id" in content
    assert "dev_smoke_flaky_demo_runner.py" in content


def test_operations_documents_flaky_build_context_fields() -> None:
    content = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    assert "DEV_SMOKE_MAX_RETRIES=1" in content
    assert "run_id" in content
    assert "run_attempt" in content
    assert "run_url" in content
