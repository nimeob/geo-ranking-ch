from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_UI_ENV_FLAGS = (
    "UI_API_BASE_URL",
    "UI_AUTH_PROXY_TRUSTED_HOSTS",
    "UI_CANONICAL_HOSTS",
    "UI_CANONICAL_ORIGIN",
)


def test_operations_doc_has_environment_reference_section() -> None:
    content = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    assert "## Environment Variables Reference" in content


def test_operations_doc_references_ui_runtime_env_flags() -> None:
    content = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")

    for flag in REQUIRED_UI_ENV_FLAGS:
        assert f"`{flag}`" in content, (
            f"docs/OPERATIONS.md: fehlender Eintrag für {flag} in der "
            "Environment-Variables-Referenz"
        )
