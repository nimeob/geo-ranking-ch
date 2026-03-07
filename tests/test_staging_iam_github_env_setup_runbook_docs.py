"""Guard tests for staging IAM + GitHub Environment setup runbook (Issue #1332).

Verifies:
- docs/STAGING_IAM_GITHUB_ENV_SETUP_RUNBOOK.md exists
- Runbook references the staging IAM artefacts from #1326
- Runbook includes the expected AWS CLI command sequence
- Runbook includes the required GitHub Environment variable checklist
"""

import pathlib

RUNBOOK = pathlib.Path(__file__).parent.parent / "docs" / "STAGING_IAM_GITHUB_ENV_SETUP_RUNBOOK.md"


class TestStagingIamGithubEnvSetupRunbook:
    def _content(self) -> str:
        assert RUNBOOK.exists(), (
            "Missing docs/STAGING_IAM_GITHUB_ENV_SETUP_RUNBOOK.md (Issue #1332)"
        )
        return RUNBOOK.read_text()

    def test_mentions_issue(self):
        assert "#1332" in self._content()

    def test_references_staging_iam_json_templates(self):
        content = self._content()
        assert "infra/iam/staging-trust-policy.json" in content
        assert "infra/iam/staging-deploy-policy.json" in content

    def test_contains_role_name(self):
        assert "swisstopo-staging-github-deploy-role" in self._content()

    def test_contains_required_aws_cli_steps(self):
        content = self._content()
        assert "aws iam create-role" in content
        assert "aws iam update-assume-role-policy" in content
        assert "aws iam put-role-policy" in content
        assert "aws iam tag-role" in content

    def test_contains_rollback_commands(self):
        content = self._content()
        assert "aws iam delete-role-policy" in content
        assert "aws iam delete-role" in content

    def test_references_staging_environment_setup_doc(self):
        content = self._content()
        assert "docs/staging-environment-setup.md" in content or "staging-environment-setup.md" in content

    def test_contains_required_github_environment_variables(self):
        """These are hard-required by deploy-staging.yml preflight."""
        content = self._content()
        required = [
            "AWS_ROLE_TO_ASSUME",
            "ECS_CLUSTER",
            "ECS_API_SERVICE",
            "ECS_UI_SERVICE",
            "ECS_API_CONTAINER_NAME",
            "ECS_UI_CONTAINER_NAME",
            "ECR_API_REPOSITORY",
            "ECR_UI_REPOSITORY",
        ]
        missing = [k for k in required if k not in content]
        assert not missing, f"Runbook missing required vars: {missing}"

    def test_mentions_optional_smoketest_secret(self):
        assert "SERVICE_API_AUTH_TOKEN" in self._content(), (
            "Runbook must mention SERVICE_API_AUTH_TOKEN secret (smoketest recommended)"
        )
