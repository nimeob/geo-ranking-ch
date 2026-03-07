"""
Guard tests for staging IAM policy artefacts (Issue #1326).

Verifies:
- infra/iam/staging-deploy-policy.json exists and is well-formed
- infra/iam/staging-trust-policy.json exists and is well-formed
- infra/iam/README.md contains staging documentation markers
"""

import json
import pathlib
import pytest

IAM_DIR = pathlib.Path(__file__).parent.parent / "infra" / "iam"
STAGING_DEPLOY_POLICY = IAM_DIR / "staging-deploy-policy.json"
STAGING_TRUST_POLICY = IAM_DIR / "staging-trust-policy.json"
IAM_README = IAM_DIR / "README.md"


# ---------------------------------------------------------------------------
# staging-deploy-policy.json
# ---------------------------------------------------------------------------

class TestStagingDeployPolicy:
    def test_file_exists(self):
        assert STAGING_DEPLOY_POLICY.exists(), (
            f"Missing: {STAGING_DEPLOY_POLICY} — run Issue #1326 implementation"
        )

    def test_valid_json(self):
        data = json.loads(STAGING_DEPLOY_POLICY.read_text())
        assert isinstance(data, dict)

    def test_version_field(self):
        data = json.loads(STAGING_DEPLOY_POLICY.read_text())
        assert data.get("Version") == "2012-10-17", "IAM policy Version must be 2012-10-17"

    def test_statement_is_list(self):
        data = json.loads(STAGING_DEPLOY_POLICY.read_text())
        assert isinstance(data.get("Statement"), list), "Statement must be a list"
        assert len(data["Statement"]) > 0, "Statement must not be empty"

    def test_all_statements_have_sid(self):
        data = json.loads(STAGING_DEPLOY_POLICY.read_text())
        missing = [s for s in data["Statement"] if not s.get("Sid")]
        assert not missing, f"Statements missing Sid: {missing}"

    def test_staging_ecr_repos_referenced(self):
        """ECR Push sid must reference staging repos, not dev."""
        data = json.loads(STAGING_DEPLOY_POLICY.read_text())
        ecr_stmt = next(
            (s for s in data["Statement"] if s.get("Sid") == "EcrPushOnlyToStagingRepositories"),
            None,
        )
        assert ecr_stmt is not None, "Missing Sid 'EcrPushOnlyToStagingRepositories'"
        resources = ecr_stmt.get("Resource", [])
        assert any("swisstopo-staging-api" in r for r in resources), (
            "ECR push must reference swisstopo-staging-api"
        )
        assert any("swisstopo-staging-ui" in r for r in resources), (
            "ECR push must reference swisstopo-staging-ui"
        )
        # Must NOT reference dev repos
        assert not any("swisstopo-dev-" in r for r in resources), (
            "Staging deploy policy must not reference dev ECR repos"
        )

    def test_staging_ecs_resources_referenced(self):
        """ECS update sid must reference staging cluster/services."""
        data = json.loads(STAGING_DEPLOY_POLICY.read_text())
        ecs_stmt = next(
            (s for s in data["Statement"] if s.get("Sid") == "EcsUpdateOnlyStagingServices"),
            None,
        )
        assert ecs_stmt is not None, "Missing Sid 'EcsUpdateOnlyStagingServices'"
        resources = ecs_stmt.get("Resource", [])
        assert any("swisstopo-staging" in r for r in resources), (
            "ECS update must reference staging cluster/services"
        )
        # Must NOT reference dev
        assert not any("/swisstopo-dev" in r for r in resources), (
            "Staging ECS update policy must not reference dev cluster/services"
        )

    def test_staging_iam_pass_role(self):
        """PassRole must reference staging ECS execution/task roles."""
        data = json.loads(STAGING_DEPLOY_POLICY.read_text())
        pass_stmt = next(
            (s for s in data["Statement"] if s.get("Sid") == "IamPassOnlyEcsStagingTaskRoles"),
            None,
        )
        assert pass_stmt is not None, "Missing Sid 'IamPassOnlyEcsStagingTaskRoles'"
        resources = pass_stmt.get("Resource", [])
        assert any("swisstopo-staging-ecs-execution-role" in r for r in resources), (
            "PassRole must include swisstopo-staging-ecs-execution-role"
        )
        assert any("swisstopo-staging-ecs-task-role" in r for r in resources), (
            "PassRole must include swisstopo-staging-ecs-task-role"
        )

    def test_secrets_manager_statement_present(self):
        """Staging policy must include SecretsManager access for staging secrets."""
        data = json.loads(STAGING_DEPLOY_POLICY.read_text())
        sm_stmt = next(
            (s for s in data["Statement"] if s.get("Sid") == "SecretsManagerReadStagingSecrets"),
            None,
        )
        assert sm_stmt is not None, "Missing Sid 'SecretsManagerReadStagingSecrets'"
        resources = sm_stmt.get("Resource", [])
        assert any("/swisstopo/staging/" in r for r in resources), (
            "SecretsManager must be scoped to /swisstopo/staging/* ARNs"
        )


# ---------------------------------------------------------------------------
# staging-trust-policy.json
# ---------------------------------------------------------------------------

class TestStagingTrustPolicy:
    def test_file_exists(self):
        assert STAGING_TRUST_POLICY.exists(), (
            f"Missing: {STAGING_TRUST_POLICY} — run Issue #1326 implementation"
        )

    def test_valid_json(self):
        data = json.loads(STAGING_TRUST_POLICY.read_text())
        assert isinstance(data, dict)

    def test_version_field(self):
        data = json.loads(STAGING_TRUST_POLICY.read_text())
        assert data.get("Version") == "2012-10-17"

    def test_statement_is_list(self):
        data = json.loads(STAGING_TRUST_POLICY.read_text())
        assert isinstance(data.get("Statement"), list)
        assert len(data["Statement"]) > 0

    def test_oidc_principal(self):
        """Trust policy must use GitHub OIDC provider as principal."""
        data = json.loads(STAGING_TRUST_POLICY.read_text())
        stmt = data["Statement"][0]
        federated = stmt.get("Principal", {}).get("Federated", "")
        assert "token.actions.githubusercontent.com" in federated, (
            "Trust policy must federate GitHub OIDC provider"
        )

    def test_environment_scoped_sub(self):
        """Staging trust must use environment:staging (not branch-only)."""
        data = json.loads(STAGING_TRUST_POLICY.read_text())
        stmt = data["Statement"][0]
        condition = stmt.get("Condition", {})
        # Accept StringEquals or StringLike for sub
        sub_value = (
            condition.get("StringEquals", {}).get("token.actions.githubusercontent.com:sub")
            or condition.get("StringLike", {}).get("token.actions.githubusercontent.com:sub", "")
        )
        assert "environment:staging" in sub_value, (
            f"Staging trust policy sub must contain 'environment:staging', got: {sub_value!r}"
        )

    def test_repo_scoped(self):
        """Trust must be scoped to the correct repo."""
        data = json.loads(STAGING_TRUST_POLICY.read_text())
        stmt = data["Statement"][0]
        condition = stmt.get("Condition", {})
        sub_value = (
            condition.get("StringEquals", {}).get("token.actions.githubusercontent.com:sub")
            or condition.get("StringLike", {}).get("token.actions.githubusercontent.com:sub", "")
        )
        assert "nimeob/geo-ranking-ch" in sub_value, (
            "Trust policy must be scoped to repo nimeob/geo-ranking-ch"
        )


# ---------------------------------------------------------------------------
# infra/iam/README.md — staging section markers
# ---------------------------------------------------------------------------

class TestIamReadmeStagingSection:
    def test_readme_exists(self):
        assert IAM_README.exists()

    def test_staging_deploy_policy_mentioned(self):
        content = IAM_README.read_text()
        assert "staging-deploy-policy.json" in content, (
            "README must reference staging-deploy-policy.json"
        )

    def test_staging_trust_policy_mentioned(self):
        content = IAM_README.read_text()
        assert "staging-trust-policy.json" in content, (
            "README must reference staging-trust-policy.json"
        )

    def test_staging_role_name_mentioned(self):
        content = IAM_README.read_text()
        assert "swisstopo-staging-github-deploy-role" in content, (
            "README must document the staging role name"
        )

    def test_staging_policy_name_mentioned(self):
        content = IAM_README.read_text()
        assert "swisstopo-staging-github-deploy-policy" in content, (
            "README must document the staging policy name"
        )

    def test_aws_runbook_commands_present(self):
        """README must contain the 3-step aws iam create-role/create-policy/attach runbook."""
        content = IAM_README.read_text()
        assert "aws iam create-policy" in content
        assert "aws iam create-role" in content
        assert "aws iam attach-role-policy" in content

    def test_staging_environment_setup_link(self):
        content = IAM_README.read_text()
        assert "staging-environment-setup.md" in content, (
            "README must link to docs/staging-environment-setup.md"
        )
