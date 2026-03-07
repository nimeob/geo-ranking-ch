"""Guard tests for staging Terraform apply runbook (Issue #1331).

Verifies:
- docs/STAGING_TERRAFORM_APPLY_RUNBOOK.md exists
- Runbook contains the required apply sequence (ECR → ECS cluster → ECS compute → DB → ALB)
- Runbook references manage flags and key Terraform targets
- Links/refs are present for staging environment setup and terraform README
"""

import pathlib

RUNBOOK = pathlib.Path(__file__).parent.parent / "docs" / "STAGING_TERRAFORM_APPLY_RUNBOOK.md"


class TestStagingTerraformApplyRunbook:
    def _content(self) -> str:
        assert RUNBOOK.exists(), (
            "Missing docs/STAGING_TERRAFORM_APPLY_RUNBOOK.md (Issue #1331)"
        )
        return RUNBOOK.read_text()

    def test_mentions_issue(self):
        assert "#1331" in self._content()

    def test_references_staging_environment_setup(self):
        content = self._content()
        assert "staging-environment-setup.md" in content

    def test_references_terraform_readme(self):
        content = self._content()
        assert "infra/terraform/README.md" in content

    def test_contains_required_sequence(self):
        content = self._content()
        # Ordered list markers
        assert "1. **ECR**" in content
        assert "2. **ECS Cluster**" in content
        assert "3. **ECS Compute**" in content
        assert "4. **DB**" in content
        assert "5. **ALB / Ingress**" in content

    def test_mentions_manage_flags(self):
        content = self._content()
        required = [
            "manage_staging_network",
            "manage_staging_ingress",
            "manage_staging_ecs_cluster",
            "manage_staging_ecs_compute",
            "manage_staging_db",
            "manage_ecr_repository",
            "manage_ecr_repository_ui",
        ]
        missing = [k for k in required if k not in content]
        assert not missing, f"Runbook missing manage flags: {missing}"

    def test_mentions_key_terraform_targets(self):
        content = self._content()
        targets = [
            "-target=aws_ecr_repository.api",
            "-target=aws_ecr_repository.ui",
            "-target=aws_ecs_cluster.staging",
            "-target=aws_ecs_service.staging_api",
            "-target=aws_ecs_service.staging_ui",
            "-target=aws_db_instance.staging_postgres",
        ]
        missing = [t for t in targets if t not in content]
        assert not missing, f"Runbook missing terraform target examples: {missing}"
