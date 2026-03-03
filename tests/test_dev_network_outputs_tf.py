from pathlib import Path


OUTPUTS_TF = Path("infra/terraform/outputs.tf")


def test_dev_network_outputs_present() -> None:
    text = OUTPUTS_TF.read_text(encoding="utf-8")
    required_outputs = [
        'output "dev_vpc_id"',
        'output "dev_public_subnet_ids"',
        'output "dev_private_subnet_ids"',
        'output "dev_nat_gateway_id"',
        'output "dev_nat_eip_allocation_id"',
        'output "dev_private_route_table_id"',
        'output "dev_alb_security_group_id"',
        'output "dev_db_security_group_id"',
        'output "dev_ecs_service_security_group_id"',
    ]
    missing = [marker for marker in required_outputs if marker not in text]
    assert not missing, f"Dev-network Outputs fehlen in outputs.tf: {missing}"
