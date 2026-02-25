locals {
  common_tags = {
    Environment = var.environment
    ManagedBy   = var.managed_by
    Owner       = var.owner
    Project     = var.project_name
  }

  ecs_cluster_name_effective     = var.manage_ecs_cluster ? var.ecs_cluster_name : (var.lookup_existing_resources ? var.existing_ecs_cluster_name : null)
  ecr_repository_name_effective  = var.manage_ecr_repository ? var.ecr_repository_name : (var.lookup_existing_resources ? var.existing_ecr_repository_name : null)
  cloudwatch_log_group_effective = var.manage_cloudwatch_log_group ? var.cloudwatch_log_group_name : (var.lookup_existing_resources ? var.existing_cloudwatch_log_group_name : null)
  s3_bucket_name_effective       = var.manage_s3_bucket ? var.s3_bucket_name : (var.lookup_existing_resources ? var.existing_s3_bucket_name : null)
}

# --- Read-only Lookups (optional) -------------------------------------------
# Nur aktiv, wenn lookup_existing_resources=true und die jeweilige Ressource
# NICHT von Terraform gemanagt wird.

data "aws_ecs_cluster" "existing" {
  count = var.lookup_existing_resources && !var.manage_ecs_cluster ? 1 : 0

  cluster_name = var.existing_ecs_cluster_name
}

data "aws_ecr_repository" "existing" {
  count = var.lookup_existing_resources && !var.manage_ecr_repository ? 1 : 0

  name = var.existing_ecr_repository_name
}

data "aws_cloudwatch_log_group" "existing" {
  count = var.lookup_existing_resources && !var.manage_cloudwatch_log_group ? 1 : 0

  name = var.existing_cloudwatch_log_group_name
}

data "aws_s3_bucket" "existing" {
  count = var.lookup_existing_resources && !var.manage_s3_bucket ? 1 : 0

  bucket = var.existing_s3_bucket_name
}

# --- Managed Resources (Import-first empfohlen) -----------------------------
# Standardmässig sind alle manage_* Flags auf false, damit kein blindes Apply
# bestehende Ressourcen verändert oder neu erstellt.

resource "aws_ecs_cluster" "dev" {
  count = var.manage_ecs_cluster ? 1 : 0

  name = var.ecs_cluster_name

  setting {
    name  = "containerInsights"
    value = var.ecs_container_insights_enabled ? "enabled" : "disabled"
  }

  tags = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ecr_repository" "api" {
  count = var.manage_ecr_repository ? 1 : 0

  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_cloudwatch_log_group" "api" {
  count = var.manage_cloudwatch_log_group ? 1 : 0

  name              = var.cloudwatch_log_group_name
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}
resource "aws_s3_bucket" "dev" {
  count = var.manage_s3_bucket ? 1 : 0

  bucket        = var.s3_bucket_name
  force_destroy = false
  tags          = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}

