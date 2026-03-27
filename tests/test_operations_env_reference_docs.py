from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_UI_ENV_FLAGS = (
    "UI_API_BASE_URL",
    "UI_AUTH_PROXY_TRUSTED_HOSTS",
    "UI_CANONICAL_HOSTS",
    "UI_CANONICAL_ORIGIN",
)

REQUIRED_OIDC_ENV_FLAGS = (
    "OIDC_JWKS_URL",
    "OIDC_JWT_ISSUER",
    "OIDC_JWT_AUDIENCE",
    "OIDC_JWKS_TTL_SECONDS",
    "OIDC_JWKS_TIMEOUT_SECONDS",
    "OIDC_CLOCK_SKEW_SECONDS",
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


def test_operations_doc_references_oidc_runtime_env_flags() -> None:
    content = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")

    for flag in REQUIRED_OIDC_ENV_FLAGS:
        assert f"`{flag}`" in content, (
            f"docs/OPERATIONS.md: fehlender OIDC-Eintrag für {flag} in der "
            "Environment-Variables-Referenz"
        )
