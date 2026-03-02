locals {
  manage_staging_db_effective = var.environment == "staging" && var.manage_staging_db && var.manage_staging_network

  # Safe indirections (avoid invalid index errors when resources are not created)
  staging_vpc_id_effective             = try(aws_vpc.staging[0].id, null)
  staging_private_subnet_ids_effective = [for s in aws_subnet.staging_private : s.id]

  # Ingress sources for DB: optional list + (if managed) staging ECS service SG.
  staging_db_ingress_source_security_group_ids_effective = compact(concat(
    [try(aws_security_group.staging_ecs_service[0].id, null)],
    var.staging_db_ingress_source_security_group_ids
  ))
}

# ---------------------------------------------------------------------------
# Staging DB (INFRA-DB-0.wp1)
#
# Safety rules:
# - Everything is behind manage flags (default: false).
# - Additionally guarded by var.environment == "staging" to avoid accidental creates in dev.
# - Depends on staging network skeleton (manage_staging_network=true) to provide VPC/Subnets.
# - prevent_destroy + deletion_protection to avoid accidental deletes.
#
# Secret handling:
# - We use AWS-managed master user password (Secrets Manager) to avoid storing a password in TF state.
# - Only the secret ARN is exposed via output.
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "staging" {
  count = local.manage_staging_db_effective ? 1 : 0

  name        = "${var.project_name}-staging-db-subnet-group"
  description = "staging DB subnet group (managed by Terraform)"
  subnet_ids  = local.staging_private_subnet_ids_effective

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-db-subnet-group"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_security_group" "staging_db" {
  count = local.manage_staging_db_effective ? 1 : 0

  name        = "${var.project_name}-staging-db-sg"
  description = "staging DB security group (managed by Terraform)"
  vpc_id      = local.staging_vpc_id_effective

  # Default: no ingress. Explicit rules are added below.

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-db-sg"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_security_group_rule" "staging_db_ingress_from_sgs" {
  for_each = local.manage_staging_db_effective ? {
    for sg_id in local.staging_db_ingress_source_security_group_ids_effective : sg_id => sg_id
  } : {}

  type                     = "ingress"
  description              = "Postgres from allowed security group"
  from_port                = var.staging_db_port
  to_port                  = var.staging_db_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.staging_db[0].id
  source_security_group_id = each.value
}

resource "aws_db_instance" "staging_postgres" {
  count = local.manage_staging_db_effective ? 1 : 0

  identifier = var.staging_db_instance_identifier

  engine         = "postgres"
  engine_version = trimspace(var.staging_db_engine_version) != "" ? var.staging_db_engine_version : null

  instance_class    = var.staging_db_instance_class
  allocated_storage = var.staging_db_allocated_storage_gb
  storage_type      = var.staging_db_storage_type
  storage_encrypted = true

  db_name = var.staging_db_name
  port    = var.staging_db_port

  username                    = var.staging_db_master_username
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.staging[0].name
  vpc_security_group_ids = [aws_security_group.staging_db[0].id]

  publicly_accessible     = false
  multi_az                = false
  deletion_protection     = true
  backup_retention_period = var.staging_db_backup_retention_days

  # Guardrail: prevent Terraform destroy; deletion_protection adds a second layer.
  skip_final_snapshot = true

  apply_immediately = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-postgres"
  })

  lifecycle {
    prevent_destroy = true
  }
}
