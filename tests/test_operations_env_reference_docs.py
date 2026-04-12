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

REQUIRED_BFF_ENV_FLAGS = (
    "BFF_OIDC_ISSUER",
    "BFF_OIDC_CLIENT_ID",
    "BFF_OIDC_CLIENT_SECRET",
    "BFF_OIDC_REDIRECT_URI",
    "BFF_OIDC_TOKEN_ENDPOINT",
    "BFF_OIDC_LOGOUT_ENDPOINT",
    "BFF_OIDC_POST_LOGOUT_REDIRECT_URI",
    "BFF_OIDC_SCOPES",
    "BFF_OIDC_NEXT_PARAM_ALLOW_SAME_ORIGIN",
    "BFF_API_CALL_TIMEOUT_SECONDS",
    "BFF_ME_RENEW_WINDOW_SECONDS",
    "BFF_SESSION_COOKIE_NAME",
    "BFF_SESSION_SECURE_COOKIE",
    "BFF_SESSION_TTL_SECONDS",
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


def test_operations_doc_references_bff_runtime_env_flags() -> None:
    content = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")

    for flag in REQUIRED_BFF_ENV_FLAGS:
        assert f"`{flag}`" in content, (
            f"docs/OPERATIONS.md: fehlender BFF-Eintrag für {flag} in der "
            "Environment-Variables-Referenz"
        )
