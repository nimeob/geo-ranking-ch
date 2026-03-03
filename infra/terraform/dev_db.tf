locals {
  manage_dev_db_effective = var.environment == "dev" && var.manage_dev_db && var.manage_dev_network

  # Safe indirections (avoid invalid index errors when resources are not created)
  dev_vpc_id_effective             = try(aws_vpc.dev[0].id, null)
  dev_private_subnet_ids_effective = [for s in aws_subnet.dev_private : s.id]

  # Ingress sources for DB: optional list + (if managed) dev ECS service SG.
  dev_db_ingress_source_security_group_ids_effective = compact(concat(
    [try(aws_security_group.dev_ecs_service[0].id, null)],
    var.dev_db_ingress_source_security_group_ids
  ))

  # VPC peering: dev DB VPC ↔ original ECS VPC (172.31.0.0/16).
  # Used when ECS tasks run in a different VPC than the dev DB.
  # Ref: Issue #867 (DEV-WIRE-0), VPC peering pcx-0ec189e6248290214 created 2026-03-03.
  manage_dev_vpc_peering_effective = var.environment == "dev" && var.manage_dev_vpc_peering
}

# ---------------------------------------------------------------------------
# Dev DB (INFRA-NET-0-dev)
#
# Safety rules:
# - Everything is behind manage flags (default: false).
# - Additionally guarded by var.environment == "dev" to avoid accidental creates in staging.
# - Depends on dev network skeleton (manage_dev_network=true) to provide VPC/Subnets.
# - prevent_destroy + deletion_protection to avoid accidental deletes.
#
# Secret handling:
# - We use AWS-managed master user password (Secrets Manager) to avoid storing a password in TF state.
# - Only the secret ARN is exposed via output.
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "dev" {
  count = local.manage_dev_db_effective ? 1 : 0

  name        = "${var.project_name}-dev-db-subnet-group"
  description = "dev DB subnet group (managed by Terraform)"
  subnet_ids  = local.dev_private_subnet_ids_effective

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-db-subnet-group"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_security_group" "dev_db" {
  count = local.manage_dev_db_effective ? 1 : 0

  name        = "${var.project_name}-dev-db-sg"
  description = "dev DB security group (managed by Terraform)"
  vpc_id      = local.dev_vpc_id_effective

  # Default: no ingress. Explicit rules are added below.

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-db-sg"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_security_group_rule" "dev_db_ingress_from_sgs" {
  for_each = local.manage_dev_db_effective ? {
    for sg_id in local.dev_db_ingress_source_security_group_ids_effective : sg_id => sg_id
  } : {}

  type                     = "ingress"
  description              = "Postgres from allowed security group"
  from_port                = var.dev_db_port
  to_port                  = var.dev_db_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.dev_db[0].id
  source_security_group_id = each.value
}

resource "aws_db_instance" "dev_postgres" {
  count = local.manage_dev_db_effective ? 1 : 0

  identifier = var.dev_db_instance_identifier

  engine         = "postgres"
  engine_version = trimspace(var.dev_db_engine_version) != "" ? var.dev_db_engine_version : null

  instance_class    = var.dev_db_instance_class
  allocated_storage = var.dev_db_allocated_storage_gb
  storage_type      = var.dev_db_storage_type
  storage_encrypted = true

  db_name = var.dev_db_name
  port    = var.dev_db_port

  username                    = var.dev_db_master_username
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.dev[0].name
  vpc_security_group_ids = [aws_security_group.dev_db[0].id]

  publicly_accessible     = false
  multi_az                = false
  deletion_protection     = true
  backup_retention_period = var.dev_db_backup_retention_days

  # Guardrail: prevent Terraform destroy; deletion_protection adds a second layer.
  skip_final_snapshot = true

  apply_immediately = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-postgres"
  })

  lifecycle {
    prevent_destroy = true
  }
}

# ---------------------------------------------------------------------------
# VPC Peering: dev DB VPC (10.80.0.0/16) ↔ original ECS VPC (172.31.0.0/16)
#
# Required so ECS tasks (in the original/default VPC) can reach the RDS instance
# (in the Terraform-managed dev VPC).  Route table entries + DB SG CIDR rule added
# alongside the peering.
#
# Note: the peering connection + routes were initially applied manually (2026-03-03,
# issue #867). This block tracks them in Terraform state.
#
# Import commands (run once to bring existing resources into state):
#   terraform import -state=terraform.dev.tfstate aws_vpc_peering_connection.dev_ecs_to_db[0] pcx-0ec189e6248290214
#   terraform import -state=terraform.dev.tfstate aws_route.dev_ecs_vpc_to_db[0] rtb-08d33e4b98ae61177_10.80.0.0/16
#   terraform import -state=terraform.dev.tfstate aws_route.dev_db_vpc_to_ecs[0] rtb-0347b0c65f8622118_172.31.0.0/16
#   terraform import -state=terraform.dev.tfstate aws_route.dev_db_vpc_main_to_ecs[0] rtb-0a2f77efc467f2dc4_172.31.0.0/16
#   terraform import -state=terraform.dev.tfstate 'aws_security_group_rule.dev_db_ingress_from_ecs_cidr[0]' sg-08e775d778b9c551f_ingress_tcp_5432_5432_172.31.0.0/16
# ---------------------------------------------------------------------------

resource "aws_vpc_peering_connection" "dev_ecs_to_db" {
  count = local.manage_dev_vpc_peering_effective ? 1 : 0

  vpc_id      = var.dev_ecs_vpc_id   # original ECS VPC (requester)
  peer_vpc_id = aws_vpc.dev[0].id    # Terraform dev VPC (accepter)

  # Same-account/same-region peering: auto-accept via accepter block.
  accepter {
    allow_remote_vpc_dns_resolution = false
  }
  requester {
    allow_remote_vpc_dns_resolution = false
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-ecs-to-db"
  })

  lifecycle {
    prevent_destroy = true
  }
}

# Route in original ECS VPC: 10.80.0.0/16 → peering
resource "aws_route" "dev_ecs_vpc_to_db" {
  count = local.manage_dev_vpc_peering_effective ? 1 : 0

  route_table_id            = var.dev_ecs_vpc_route_table_id
  destination_cidr_block    = aws_vpc.dev[0].cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.dev_ecs_to_db[0].id
}

# Route in dev DB VPC public RT: 172.31.0.0/16 → peering
resource "aws_route" "dev_db_vpc_to_ecs" {
  count = local.manage_dev_vpc_peering_effective ? 1 : 0

  route_table_id            = var.dev_db_vpc_public_route_table_id
  destination_cidr_block    = var.dev_ecs_vpc_cidr
  vpc_peering_connection_id = aws_vpc_peering_connection.dev_ecs_to_db[0].id
}

# Route in dev DB VPC main RT: 172.31.0.0/16 → peering
resource "aws_route" "dev_db_vpc_main_to_ecs" {
  count = local.manage_dev_vpc_peering_effective ? 1 : 0

  route_table_id            = var.dev_db_vpc_main_route_table_id
  destination_cidr_block    = var.dev_ecs_vpc_cidr
  vpc_peering_connection_id = aws_vpc_peering_connection.dev_ecs_to_db[0].id
}

# DB SG ingress: allow port 5432 from original ECS VPC CIDR (peered)
resource "aws_security_group_rule" "dev_db_ingress_from_ecs_cidr" {
  count = local.manage_dev_vpc_peering_effective ? 1 : 0

  type              = "ingress"
  description       = "Postgres from original ECS VPC (via VPC peering)"
  from_port         = var.dev_db_port
  to_port           = var.dev_db_port
  protocol          = "tcp"
  cidr_blocks       = [var.dev_ecs_vpc_cidr]
  security_group_id = aws_security_group.dev_db[0].id
}
