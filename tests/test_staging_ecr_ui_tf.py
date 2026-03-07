"""
Guard tests for staging ECR UI repository Terraform (Issue #1328).

Verifies:
- variables.tf declares manage_ecr_repository_ui, ecr_ui_repository_name,
  existing_ecr_ui_repository_name with correct defaults
- main.tf contains aws_ecr_repository.ui resource + data.aws_ecr_repository.existing_ui
- main.tf locals contains ecr_ui_repository_name_effective
- outputs.tf contains ecr_ui_repository_url output
- terraform.staging.tfvars sets manage_ecr_repository_ui=true + ecr_ui_repository_name
"""

import pathlib
import re
import pytest

TERRAFORM_DIR = pathlib.Path(__file__).parent.parent / "infra" / "terraform"
VARIABLES_TF = TERRAFORM_DIR / "variables.tf"
MAIN_TF = TERRAFORM_DIR / "main.tf"
OUTPUTS_TF = TERRAFORM_DIR / "outputs.tf"
STAGING_TFVARS = TERRAFORM_DIR / "terraform.staging.tfvars"
STAGING_TFVARS_EXAMPLE = TERRAFORM_DIR / "terraform.staging.tfvars.example"


# ---------------------------------------------------------------------------
# variables.tf checks
# ---------------------------------------------------------------------------

class TestVariablesTf:
    def _content(self) -> str:
        return VARIABLES_TF.read_text()

    def test_manage_ecr_repository_ui_variable_exists(self):
        assert 'variable "manage_ecr_repository_ui"' in self._content(), (
            "variables.tf must declare manage_ecr_repository_ui"
        )

    def test_manage_ecr_repository_ui_default_false(self):
        content = self._content()
        # Find the block and check default = false
        match = re.search(
            r'variable\s+"manage_ecr_repository_ui"\s*\{[^}]+default\s*=\s*(false)',
            content,
        )
        assert match, (
            "manage_ecr_repository_ui must have default = false"
        )

    def test_ecr_ui_repository_name_variable_exists(self):
        assert 'variable "ecr_ui_repository_name"' in self._content(), (
            "variables.tf must declare ecr_ui_repository_name"
        )

    def test_ecr_ui_repository_name_default_dev_ui(self):
        content = self._content()
        match = re.search(
            r'variable\s+"ecr_ui_repository_name"\s*\{[^}]+"(swisstopo-dev-ui)"',
            content,
        )
        assert match, (
            'ecr_ui_repository_name must have default = "swisstopo-dev-ui"'
        )

    def test_existing_ecr_ui_repository_name_variable_exists(self):
        assert 'variable "existing_ecr_ui_repository_name"' in self._content(), (
            "variables.tf must declare existing_ecr_ui_repository_name"
        )

    def test_existing_ecr_ui_repository_name_default_dev_ui(self):
        content = self._content()
        match = re.search(
            r'variable\s+"existing_ecr_ui_repository_name"\s*\{[^}]+"(swisstopo-dev-ui)"',
            content,
        )
        assert match, (
            'existing_ecr_ui_repository_name must have default = "swisstopo-dev-ui"'
        )


# ---------------------------------------------------------------------------
# main.tf checks
# ---------------------------------------------------------------------------

class TestMainTf:
    def _content(self) -> str:
        return MAIN_TF.read_text()

    def test_data_aws_ecr_repository_existing_ui_exists(self):
        assert 'data "aws_ecr_repository" "existing_ui"' in self._content(), (
            "main.tf must contain data aws_ecr_repository.existing_ui"
        )

    def test_data_existing_ui_uses_correct_variable(self):
        content = self._content()
        assert "existing_ecr_ui_repository_name" in content, (
            "data.aws_ecr_repository.existing_ui must reference var.existing_ecr_ui_repository_name"
        )

    def test_resource_aws_ecr_repository_ui_exists(self):
        assert 'resource "aws_ecr_repository" "ui"' in self._content(), (
            "main.tf must contain resource aws_ecr_repository.ui"
        )

    def test_ecr_ui_resource_uses_manage_flag(self):
        content = self._content()
        # Check manage_ecr_repository_ui is referenced in the resource count
        assert "manage_ecr_repository_ui" in content, (
            "aws_ecr_repository.ui must be guarded by var.manage_ecr_repository_ui"
        )

    def test_ecr_ui_resource_has_prevent_destroy(self):
        content = self._content()
        # Find the ui resource block and verify prevent_destroy
        ui_block_start = content.find('resource "aws_ecr_repository" "ui"')
        assert ui_block_start != -1
        # Take a slice after the start to find prevent_destroy within the block
        block_excerpt = content[ui_block_start:ui_block_start + 600]
        assert "prevent_destroy = true" in block_excerpt, (
            "aws_ecr_repository.ui must have lifecycle.prevent_destroy = true"
        )

    def test_ecr_ui_resource_scan_on_push(self):
        content = self._content()
        ui_block_start = content.find('resource "aws_ecr_repository" "ui"')
        assert ui_block_start != -1
        block_excerpt = content[ui_block_start:ui_block_start + 600]
        assert "scan_on_push = true" in block_excerpt, (
            "aws_ecr_repository.ui must have scan_on_push = true"
        )

    def test_ecr_ui_resource_force_delete_false(self):
        content = self._content()
        ui_block_start = content.find('resource "aws_ecr_repository" "ui"')
        assert ui_block_start != -1
        block_excerpt = content[ui_block_start:ui_block_start + 600]
        assert "force_delete         = false" in block_excerpt, (
            "aws_ecr_repository.ui must have force_delete = false"
        )

    def test_locals_ecr_ui_repository_name_effective(self):
        assert "ecr_ui_repository_name_effective" in self._content(), (
            "main.tf locals must define ecr_ui_repository_name_effective"
        )


# ---------------------------------------------------------------------------
# outputs.tf checks
# ---------------------------------------------------------------------------

class TestOutputsTf:
    def _content(self) -> str:
        return OUTPUTS_TF.read_text()

    def test_ecr_ui_repository_url_output_exists(self):
        assert 'output "ecr_ui_repository_url"' in self._content(), (
            "outputs.tf must define ecr_ui_repository_url"
        )

    def test_ecr_ui_output_references_ui_resource(self):
        content = self._content()
        # Find the output block
        idx = content.find('output "ecr_ui_repository_url"')
        assert idx != -1
        block = content[idx:idx + 400]
        assert "aws_ecr_repository.ui" in block, (
            "ecr_ui_repository_url must reference aws_ecr_repository.ui"
        )

    def test_ecr_ui_output_references_existing_ui_datasource(self):
        content = self._content()
        idx = content.find('output "ecr_ui_repository_url"')
        assert idx != -1
        block = content[idx:idx + 400]
        assert "aws_ecr_repository.existing_ui" in block, (
            "ecr_ui_repository_url must reference data.aws_ecr_repository.existing_ui as fallback"
        )


# ---------------------------------------------------------------------------
# terraform.staging.tfvars checks (skipped in CI — file is .gitignore'd)
# These tests run locally where the operator's tfvars is present.
# ---------------------------------------------------------------------------

class TestStagingTfvars:
    def _content(self) -> str:
        if not STAGING_TFVARS.exists():
            pytest.skip("terraform.staging.tfvars not found (gitignored; run locally with operator file)")
        return STAGING_TFVARS.read_text()

    def test_manage_ecr_repository_ui_true(self):
        content = self._content()
        assert re.search(r'manage_ecr_repository_ui\s*=\s*true', content), (
            "terraform.staging.tfvars must set manage_ecr_repository_ui = true"
        )

    def test_ecr_ui_repository_name_staging(self):
        content = self._content()
        assert re.search(r'ecr_ui_repository_name\s*=\s*"swisstopo-staging-ui"', content), (
            'terraform.staging.tfvars must set ecr_ui_repository_name = "swisstopo-staging-ui"'
        )

    def test_existing_ecr_ui_repository_name_staging(self):
        content = self._content()
        assert re.search(r'existing_ecr_ui_repository_name\s*=\s*"swisstopo-staging-ui"', content), (
            'terraform.staging.tfvars must set existing_ecr_ui_repository_name = "swisstopo-staging-ui"'
        )


# ---------------------------------------------------------------------------
# terraform.staging.tfvars.example checks (committed, CI-verifiable)
# ---------------------------------------------------------------------------

class TestStagingTfvarsExample:
    def _content(self) -> str:
        return STAGING_TFVARS_EXAMPLE.read_text()

    def test_manage_ecr_repository_ui_in_example(self):
        assert "manage_ecr_repository_ui" in self._content(), (
            "terraform.staging.tfvars.example must document manage_ecr_repository_ui"
        )

    def test_ecr_ui_repository_name_in_example(self):
        assert "ecr_ui_repository_name" in self._content(), (
            "terraform.staging.tfvars.example must document ecr_ui_repository_name"
        )

    def test_manage_ecr_repository_ui_true_in_example(self):
        content = self._content()
        assert re.search(r'manage_ecr_repository_ui\s*=\s*true', content), (
            "terraform.staging.tfvars.example must set manage_ecr_repository_ui = true"
        )

    def test_ecr_ui_repository_name_staging_in_example(self):
        content = self._content()
        assert re.search(r'ecr_ui_repository_name\s*=\s*"swisstopo-staging-ui"', content), (
            'terraform.staging.tfvars.example must show ecr_ui_repository_name = "swisstopo-staging-ui"'
        )
