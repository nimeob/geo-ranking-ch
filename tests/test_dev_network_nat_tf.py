from pathlib import Path


DEV_NETWORK_TF = Path("infra/terraform/dev_network.tf")
VARS_TF = Path("infra/terraform/variables.tf")
TFVARS_EXAMPLE = Path("infra/terraform/terraform.dev.tfvars.example")


def test_nat_resources_and_guard_present() -> None:
    text = DEV_NETWORK_TF.read_text(encoding="utf-8")
    required = [
        'manage_dev_nat_effective',
        'resource "aws_eip" "dev_nat"',
        'resource "aws_nat_gateway" "dev"',
        'resource "aws_route_table" "dev_private"',
        'resource "aws_route_table_association" "dev_private"',
    ]
    missing = [m for m in required if m not in text]
    assert not missing, f"NAT/private-route Ressourcen fehlen in dev_network.tf: {missing}"


def test_manage_dev_nat_variable_exposed() -> None:
    vars_text = VARS_TF.read_text(encoding="utf-8")
    tfvars_text = TFVARS_EXAMPLE.read_text(encoding="utf-8")

    assert 'variable "manage_dev_nat_gateway"' in vars_text
    assert 'manage_dev_nat_gateway' in tfvars_text
