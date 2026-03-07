"""
Guard tests for staging ECS Cluster Terraform wiring (Issue #1330).

Verifies:
- variables.tf declares manage_staging_ecs_cluster (default false)
- staging_ecs_compute.tf contains:
  - manage_staging_ecs_cluster_effective local
  - staging_ecs_cluster_arn_effective local
  - aws_ecs_cluster.staging resource (guarded)
  - aws_ecs_service.staging_api and aws_ecs_service.staging_ui use local.staging_ecs_cluster_arn_effective
- outputs.tf declares staging_ecs_cluster_arn output
- terraform.staging.tfvars sets manage_staging_ecs_cluster = true (skipped in CI if file missing)
- terraform.staging.tfvars.example documents manage_staging_ecs_cluster
"""

import pathlib
import re

import pytest

TERRAFORM_DIR = pathlib.Path(__file__).parent.parent / "infra" / "terraform"
VARIABLES_TF = TERRAFORM_DIR / "variables.tf"
STAGING_ECS_COMPUTE_TF = TERRAFORM_DIR / "staging_ecs_compute.tf"
OUTPUTS_TF = TERRAFORM_DIR / "outputs.tf"
STAGING_TFVARS = TERRAFORM_DIR / "terraform.staging.tfvars"
STAGING_TFVARS_EXAMPLE = TERRAFORM_DIR / "terraform.staging.tfvars.example"


class TestVariablesTf:
    def _content(self) -> str:
        return VARIABLES_TF.read_text()

    def test_manage_staging_ecs_cluster_variable_exists(self):
        assert 'variable "manage_staging_ecs_cluster"' in self._content(), (
            "variables.tf must declare manage_staging_ecs_cluster"
        )

    def test_manage_staging_ecs_cluster_default_false(self):
        content = self._content()
        match = re.search(
            r'variable\s+"manage_staging_ecs_cluster"\s*\{[^}]*?default\s*=\s*false',
            content,
            re.DOTALL,
        )
        assert match, "manage_staging_ecs_cluster must have default = false"


class TestStagingEcsComputeTf:
    def _content(self) -> str:
        return STAGING_ECS_COMPUTE_TF.read_text()

    def test_manage_staging_ecs_cluster_effective_local_exists(self):
        assert "manage_staging_ecs_cluster_effective" in self._content(), (
            "staging_ecs_compute.tf must define manage_staging_ecs_cluster_effective local"
        )

    def test_staging_ecs_cluster_arn_effective_local_exists(self):
        assert "staging_ecs_cluster_arn_effective" in self._content(), (
            "staging_ecs_compute.tf must define staging_ecs_cluster_arn_effective local"
        )

    def test_aws_ecs_cluster_staging_resource_exists(self):
        assert 'resource "aws_ecs_cluster" "staging"' in self._content(), (
            "staging_ecs_compute.tf must contain resource aws_ecs_cluster.staging"
        )

    def test_aws_ecs_cluster_staging_guarded(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_cluster" "staging"')
        assert idx != -1
        block = content[idx : idx + 200]
        assert "manage_staging_ecs_cluster_effective" in block, (
            "aws_ecs_cluster.staging must be guarded by manage_staging_ecs_cluster_effective"
        )

    def test_staging_services_use_staging_cluster_local(self):
        content = self._content()
        assert "cluster         = local.staging_ecs_cluster_arn_effective" in content, (
            "staging ECS services must use local.staging_ecs_cluster_arn_effective"
        )


class TestOutputsTf:
    def _content(self) -> str:
        return OUTPUTS_TF.read_text()

    def test_staging_ecs_cluster_arn_output_exists(self):
        assert 'output "staging_ecs_cluster_arn"' in self._content(), (
            "outputs.tf must define staging_ecs_cluster_arn output"
        )

    def test_staging_ecs_cluster_arn_output_references_local(self):
        content = self._content()
        idx = content.find('output "staging_ecs_cluster_arn"')
        assert idx != -1
        block = content[idx : idx + 240]
        assert "staging_ecs_cluster_arn_effective" in block, (
            "staging_ecs_cluster_arn output must reference local.staging_ecs_cluster_arn_effective"
        )


class TestStagingTfvars:
    def _content(self) -> str:
        if not STAGING_TFVARS.exists():
            pytest.skip("terraform.staging.tfvars not found (gitignored; run locally with operator file)")
        return STAGING_TFVARS.read_text()

    def test_manage_staging_ecs_cluster_true(self):
        content = self._content()
        assert re.search(r"manage_staging_ecs_cluster\s*=\s*true", content), (
            "terraform.staging.tfvars must set manage_staging_ecs_cluster = true"
        )


class TestStagingTfvarsExample:
    def _content(self) -> str:
        return STAGING_TFVARS_EXAMPLE.read_text()

    def test_manage_staging_ecs_cluster_documented(self):
        assert "manage_staging_ecs_cluster" in self._content(), (
            "terraform.staging.tfvars.example must document manage_staging_ecs_cluster"
        )
