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
