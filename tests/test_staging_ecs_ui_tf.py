"""
Guard tests for staging UI ECS Service Terraform (Issue #1329).

Verifies:
- variables.tf declares staging_ui_service_name, staging_ui_task_family,
  staging_ui_container_name, staging_ui_container_image, staging_ui_container_port
- staging_ecs_compute.tf contains:
  - ecr_ui_repository_url_effective local
  - staging_cloudwatch_log_group_ui_name_effective local
  - staging_ui_container_image_effective local
  - aws_ecs_task_definition.staging_ui resource (guarded)
  - aws_ecs_service.staging_ui resource (guarded)
- infra/ecs/taskdef.swisstopo-staging-ui.json exists + is valid JSON
- outputs.tf declares staging_ui_service_name output
- terraform.staging.tfvars sets staging_ui_service_name/task_family/container_name
- terraform.staging.tfvars.example documents the same values
"""

import json
import pathlib
import re

import pytest

TERRAFORM_DIR = pathlib.Path(__file__).parent.parent / "infra" / "terraform"
ECS_DIR = pathlib.Path(__file__).parent.parent / "infra" / "ecs"
VARIABLES_TF = TERRAFORM_DIR / "variables.tf"
STAGING_ECS_COMPUTE_TF = TERRAFORM_DIR / "staging_ecs_compute.tf"
OUTPUTS_TF = TERRAFORM_DIR / "outputs.tf"
STAGING_TFVARS = TERRAFORM_DIR / "terraform.staging.tfvars"
STAGING_TFVARS_EXAMPLE = TERRAFORM_DIR / "terraform.staging.tfvars.example"
TASKDEF_JSON = ECS_DIR / "taskdef.swisstopo-staging-ui.json"


# ---------------------------------------------------------------------------
# variables.tf checks
# ---------------------------------------------------------------------------

class TestVariablesTf:
    def _content(self) -> str:
        return VARIABLES_TF.read_text()

    def test_staging_ui_service_name_variable_exists(self):
        assert 'variable "staging_ui_service_name"' in self._content(), (
            "variables.tf must declare staging_ui_service_name"
        )

    def test_staging_ui_service_name_default(self):
        content = self._content()
        match = re.search(
            r'variable\s+"staging_ui_service_name"\s*\{[^}]+"(swisstopo-staging-ui)"',
            content,
        )
        assert match, (
            'staging_ui_service_name must have default = "swisstopo-staging-ui"'
        )

    def test_staging_ui_task_family_variable_exists(self):
        assert 'variable "staging_ui_task_family"' in self._content(), (
            "variables.tf must declare staging_ui_task_family"
        )

    def test_staging_ui_task_family_default(self):
        content = self._content()
        match = re.search(
            r'variable\s+"staging_ui_task_family"\s*\{[^}]+"(swisstopo-staging-ui)"',
            content,
        )
        assert match, (
            'staging_ui_task_family must have default = "swisstopo-staging-ui"'
        )

    def test_staging_ui_container_name_variable_exists(self):
        assert 'variable "staging_ui_container_name"' in self._content(), (
            "variables.tf must declare staging_ui_container_name"
        )

    def test_staging_ui_container_name_default(self):
        content = self._content()
        match = re.search(
            r'variable\s+"staging_ui_container_name"\s*\{[^}]+"(ui)"',
            content,
        )
        assert match, (
            'staging_ui_container_name must have default = "ui"'
        )

    def test_staging_ui_container_image_variable_exists(self):
        assert 'variable "staging_ui_container_image"' in self._content(), (
            "variables.tf must declare staging_ui_container_image"
        )

    def test_staging_ui_container_port_variable_exists(self):
        assert 'variable "staging_ui_container_port"' in self._content(), (
            "variables.tf must declare staging_ui_container_port"
        )

    def test_staging_ui_container_port_default_8080(self):
        content = self._content()
        idx = content.find('variable "staging_ui_container_port"')
        assert idx != -1
        block = content[idx:idx + 200]
        assert "8080" in block, (
            "staging_ui_container_port must have default = 8080"
        )


# ---------------------------------------------------------------------------
# staging_ecs_compute.tf checks
# ---------------------------------------------------------------------------

class TestStagingEcsComputeTf:
    def _content(self) -> str:
        return STAGING_ECS_COMPUTE_TF.read_text()

    def test_ecr_ui_repository_url_effective_local_exists(self):
        assert "ecr_ui_repository_url_effective" in self._content(), (
            "staging_ecs_compute.tf must define ecr_ui_repository_url_effective local"
        )

    def test_ecr_ui_url_effective_references_ui_resource(self):
        content = self._content()
        assert "aws_ecr_repository.ui" in content, (
            "ecr_ui_repository_url_effective must reference aws_ecr_repository.ui"
        )

    def test_ecr_ui_url_effective_references_existing_ui_datasource(self):
        content = self._content()
        assert "aws_ecr_repository.existing_ui" in content, (
            "ecr_ui_repository_url_effective must reference data.aws_ecr_repository.existing_ui as fallback"
        )

    def test_staging_ui_container_image_effective_local_exists(self):
        assert "staging_ui_container_image_effective" in self._content(), (
            "staging_ecs_compute.tf must define staging_ui_container_image_effective local"
        )

    def test_staging_cloudwatch_log_group_ui_name_effective_local_exists(self):
        assert "staging_cloudwatch_log_group_ui_name_effective" in self._content(), (
            "staging_ecs_compute.tf must define staging_cloudwatch_log_group_ui_name_effective local"
        )

    def test_aws_ecs_task_definition_staging_ui_exists(self):
        assert 'resource "aws_ecs_task_definition" "staging_ui"' in self._content(), (
            "staging_ecs_compute.tf must contain resource aws_ecs_task_definition.staging_ui"
        )

    def test_staging_ui_task_def_guarded(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_task_definition" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 200]
        assert "manage_staging_ecs_compute_effective" in block, (
            "staging_ui task definition must be guarded by manage_staging_ecs_compute_effective"
        )

    def test_staging_ui_task_def_uses_ui_family(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_task_definition" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 600]
        assert "staging_ui_task_family" in block, (
            "staging_ui task definition must use var.staging_ui_task_family"
        )

    def test_staging_ui_task_def_uses_ui_container_name(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_task_definition" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 1200]
        assert "staging_ui_container_name" in block, (
            "staging_ui task definition must use var.staging_ui_container_name"
        )

    def test_staging_ui_task_def_uses_ui_image_effective(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_task_definition" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 1200]
        assert "staging_ui_container_image_effective" in block, (
            "staging_ui task definition must use local.staging_ui_container_image_effective"
        )

    def test_staging_ui_task_def_uses_ui_log_group(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_task_definition" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 1800]
        assert "staging_cloudwatch_log_group_ui_name_effective" in block, (
            "staging_ui task definition must use local.staging_cloudwatch_log_group_ui_name_effective"
        )

    def test_staging_ui_task_def_has_prevent_destroy(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_task_definition" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 1800]
        assert "prevent_destroy = true" in block, (
            "staging_ui task definition must have lifecycle.prevent_destroy = true"
        )

    def test_aws_ecs_service_staging_ui_exists(self):
        assert 'resource "aws_ecs_service" "staging_ui"' in self._content(), (
            "staging_ecs_compute.tf must contain resource aws_ecs_service.staging_ui"
        )

    def test_staging_ui_service_guarded(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_service" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 300]
        assert "manage_staging_ecs_compute_effective" in block, (
            "staging_ui service must be guarded by manage_staging_ecs_compute_effective"
        )

    def test_staging_ui_service_uses_ui_service_name(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_service" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 600]
        assert "staging_ui_service_name" in block, (
            "staging_ui service must use var.staging_ui_service_name"
        )

    def test_staging_ui_service_references_ui_task_def(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_service" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 600]
        assert "aws_ecs_task_definition.staging_ui[0].arn" in block, (
            "staging_ui service must reference aws_ecs_task_definition.staging_ui[0].arn"
        )

    def test_staging_ui_service_has_prevent_destroy(self):
        content = self._content()
        idx = content.find('resource "aws_ecs_service" "staging_ui"')
        assert idx != -1
        block = content[idx:idx + 800]
        assert "prevent_destroy = true" in block, (
            "staging_ui service must have lifecycle.prevent_destroy = true"
        )


# ---------------------------------------------------------------------------
# Taskdef JSON template
# ---------------------------------------------------------------------------

class TestTaskdefJson:
    def _data(self) -> dict:
        assert TASKDEF_JSON.exists(), (
            f"infra/ecs/taskdef.swisstopo-staging-ui.json must exist"
        )
        return json.loads(TASKDEF_JSON.read_text())

    def test_taskdef_json_exists(self):
        assert TASKDEF_JSON.exists(), (
            "infra/ecs/taskdef.swisstopo-staging-ui.json must exist"
        )

    def test_taskdef_json_valid(self):
        data = self._data()
        assert isinstance(data, dict), "taskdef JSON must be a valid object"

    def test_taskdef_family(self):
        data = self._data()
        assert data.get("family") == "swisstopo-staging-ui", (
            "taskdef family must be swisstopo-staging-ui"
        )

    def test_taskdef_network_mode(self):
        data = self._data()
        assert data.get("networkMode") == "awsvpc", (
            "taskdef networkMode must be awsvpc"
        )

    def test_taskdef_requires_fargate(self):
        data = self._data()
        assert "FARGATE" in data.get("requiresCompatibilities", []), (
            "taskdef must require FARGATE"
        )

    def test_taskdef_has_container_definitions(self):
        data = self._data()
        containers = data.get("containerDefinitions", [])
        assert len(containers) >= 1, (
            "taskdef must have at least one containerDefinition"
        )

    def test_taskdef_container_name(self):
        data = self._data()
        containers = data.get("containerDefinitions", [])
        assert containers[0].get("name") == "ui", (
            "taskdef first container name must be 'ui'"
        )

    def test_taskdef_container_port_8080(self):
        data = self._data()
        containers = data.get("containerDefinitions", [])
        port_mappings = containers[0].get("portMappings", [])
        ports = [pm.get("containerPort") for pm in port_mappings]
        assert 8080 in ports, (
            "taskdef container must expose port 8080"
        )

    def test_taskdef_has_log_configuration(self):
        data = self._data()
        containers = data.get("containerDefinitions", [])
        log_conf = containers[0].get("logConfiguration", {})
        assert log_conf.get("logDriver") == "awslogs", (
            "taskdef container must use awslogs log driver"
        )

    def test_taskdef_log_group_staging_ui(self):
        data = self._data()
        containers = data.get("containerDefinitions", [])
        log_conf = containers[0].get("logConfiguration", {})
        log_group = log_conf.get("options", {}).get("awslogs-group", "")
        assert "staging" in log_group and "ui" in log_group, (
            "taskdef awslogs-group must reference staging UI log group"
        )


# ---------------------------------------------------------------------------
# outputs.tf checks
# ---------------------------------------------------------------------------

class TestOutputsTf:
    def _content(self) -> str:
        return OUTPUTS_TF.read_text()

    def test_staging_ui_service_name_output_exists(self):
        assert 'output "staging_ui_service_name"' in self._content(), (
            "outputs.tf must define staging_ui_service_name output"
        )

    def test_staging_ui_service_name_output_references_service(self):
        content = self._content()
        idx = content.find('output "staging_ui_service_name"')
        assert idx != -1
        block = content[idx:idx + 300]
        assert "aws_ecs_service.staging_ui" in block, (
            "staging_ui_service_name output must reference aws_ecs_service.staging_ui"
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

    def test_staging_ui_service_name_set(self):
        content = self._content()
        assert re.search(r'staging_ui_service_name\s*=\s*"swisstopo-staging-ui"', content), (
            'terraform.staging.tfvars must set staging_ui_service_name = "swisstopo-staging-ui"'
        )

    def test_staging_ui_task_family_set(self):
        content = self._content()
        assert re.search(r'staging_ui_task_family\s*=\s*"swisstopo-staging-ui"', content), (
            'terraform.staging.tfvars must set staging_ui_task_family = "swisstopo-staging-ui"'
        )

    def test_staging_ui_container_name_set(self):
        content = self._content()
        assert re.search(r'staging_ui_container_name\s*=\s*"ui"', content), (
            'terraform.staging.tfvars must set staging_ui_container_name = "ui"'
        )


# ---------------------------------------------------------------------------
# terraform.staging.tfvars.example checks (committed, CI-verifiable)
# ---------------------------------------------------------------------------

class TestStagingTfvarsExample:
    def _content(self) -> str:
        return STAGING_TFVARS_EXAMPLE.read_text()

    def test_staging_ui_service_name_in_example(self):
        assert "staging_ui_service_name" in self._content(), (
            "terraform.staging.tfvars.example must document staging_ui_service_name"
        )

    def test_staging_ui_task_family_in_example(self):
        assert "staging_ui_task_family" in self._content(), (
            "terraform.staging.tfvars.example must document staging_ui_task_family"
        )

    def test_staging_ui_container_name_in_example(self):
        assert "staging_ui_container_name" in self._content(), (
            "terraform.staging.tfvars.example must document staging_ui_container_name"
        )

    def test_staging_ui_service_name_value_in_example(self):
        content = self._content()
        assert re.search(r'staging_ui_service_name\s*=\s*"swisstopo-staging-ui"', content), (
            'terraform.staging.tfvars.example must show staging_ui_service_name = "swisstopo-staging-ui"'
        )

    def test_staging_ui_container_name_value_in_example(self):
        content = self._content()
        assert re.search(r'staging_ui_container_name\s*=\s*"ui"', content), (
            'terraform.staging.tfvars.example must show staging_ui_container_name = "ui"'
        )
