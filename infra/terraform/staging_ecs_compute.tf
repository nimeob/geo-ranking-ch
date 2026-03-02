locals {
  manage_staging_ecs_compute_effective = var.environment == "staging" && var.manage_staging_ecs_compute && var.manage_staging_network

  # Safe indirections (avoid invalid index errors when resources are not created)
  staging_vpc_id            = try(aws_vpc.staging[0].id, null)
  staging_public_subnet_ids = [for s in aws_subnet.staging_public : s.id]

  ecs_cluster_arn_effective    = try(aws_ecs_cluster.dev[0].arn, data.aws_ecs_cluster.existing[0].arn, null)
  ecr_repository_url_effective = try(aws_ecr_repository.api[0].repository_url, data.aws_ecr_repository.existing[0].repository_url, null)

  staging_task_execution_role_arn_effective = trimspace(var.staging_task_execution_role_arn) != "" ? var.staging_task_execution_role_arn : null
  staging_task_role_arn_effective           = trimspace(var.staging_task_role_arn) != "" ? var.staging_task_role_arn : null

  staging_container_image_effective = trimspace(var.staging_container_image) != "" ? var.staging_container_image : (
    local.ecr_repository_url_effective != null ? "${local.ecr_repository_url_effective}:latest" : "public.ecr.aws/docker/library/nginx:latest"
  )

  staging_cloudwatch_log_group_name_effective = local.cloudwatch_log_group_effective != null ? local.cloudwatch_log_group_effective : var.cloudwatch_log_group_name

  # ---------------------------------------------------------------------------
  # INFRA-DB-0.wp2: DB Secrets Wiring
  #
  # DB_HOST / DB_PORT / DB_NAME / DB_USERNAME → plain environment (non-secret)
  # DB_PASSWORD → secrets block via SecretsManager ARN (JSON key "password")
  #
  # Secret ARN resolution order:
  #   1) var.staging_db_master_user_secret_arn_override (explicit cross-workspace override)
  #   2) aws_db_instance.staging_postgres[0].master_user_secret[0].secret_arn
  #      (auto-managed by RDS via manage_master_user_password=true, available when manage_staging_db=true)
  # If neither is set, the secrets block is omitted (no DB_PASSWORD injected).
  # ---------------------------------------------------------------------------

  staging_db_host_effective = try(aws_db_instance.staging_postgres[0].address, null)

  staging_db_secret_arn_effective = trimspace(var.staging_db_master_user_secret_arn_override) != "" ? (
    var.staging_db_master_user_secret_arn_override
  ) : try(aws_db_instance.staging_postgres[0].master_user_secret[0].secret_arn, null)

  # Secrets list: only populated when ARN is known.
  # valueFrom format: "<SecretArn>:<JsonKey>::"
  staging_db_secrets = local.staging_db_secret_arn_effective != null ? [
    {
      name      = "DB_PASSWORD"
      valueFrom = "${local.staging_db_secret_arn_effective}:password::"
    }
  ] : []
}

# ---------------------------------------------------------------------------
# Staging ECS Compute Baseline (WP #661)
#
# Safety rules:
# - Everything is behind manage flags (default: false).
# - Additionally guarded by var.environment == "staging" to avoid accidental creates in dev.
# - prevent_destroy where sensible.
#
# Notes:
# - This is a skeleton. ALB Target Groups / Listener Rules wiring is handled in separate work.
# - Roles/Secrets/Logs are referenced via variables; creation/import is handled in other WPs.
# ---------------------------------------------------------------------------

resource "aws_security_group" "staging_ecs_service" {
  count = local.manage_staging_ecs_compute_effective ? 1 : 0

  name        = "${var.project_name}-staging-ecs-service-sg"
  description = "staging ECS service security group (managed by Terraform)"
  vpc_id      = local.staging_vpc_id

  # Default: no ingress. Traffic is wired when Target Groups/ALB routing is added.

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-ecs-service-sg"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ecs_task_definition" "staging_api" {
  count = local.manage_staging_ecs_compute_effective ? 1 : 0

  family                   = var.staging_task_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.staging_task_cpu
  memory                   = var.staging_task_memory

  execution_role_arn = local.staging_task_execution_role_arn_effective
  task_role_arn      = local.staging_task_role_arn_effective

  container_definitions = jsonencode([
    {
      name      = var.staging_container_name
      image     = local.staging_container_image_effective
      essential = true

      portMappings = [
        {
          containerPort = var.staging_container_port
          hostPort      = var.staging_container_port
          protocol      = "tcp"
        }
      ]

      environment = concat(
        [
          {
            name  = "ENVIRONMENT"
            value = var.environment
          }
        ],
        # DB connection info (non-secret). Only added when DB host is known.
        # DB_PORT and DB_NAME use the same variables as the RDS resource.
        local.staging_db_host_effective != null ? [
          {
            name  = "DB_HOST"
            value = local.staging_db_host_effective
          },
          {
            name  = "DB_PORT"
            value = tostring(var.staging_db_port)
          },
          {
            name  = "DB_NAME"
            value = var.staging_db_name
          },
          {
            name  = "DB_USERNAME"
            value = var.staging_db_master_username
          }
        ] : []
      )

      # DB_PASSWORD injected via Secrets Manager (no plaintext in task definition).
      # Requires: Execution Role must have secretsmanager:GetSecretValue on the secret ARN.
      # See: docs/STAGING_DB_ECS_SECRETS_RUNBOOK.md for full IAM requirements.
      secrets = local.staging_db_secrets

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = local.staging_cloudwatch_log_group_name_effective
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ecs_service" "staging_api" {
  count = local.manage_staging_ecs_compute_effective ? 1 : 0

  name            = var.staging_service_name
  cluster         = local.ecs_cluster_arn_effective
  task_definition = aws_ecs_task_definition.staging_api[0].arn
  desired_count   = var.staging_desired_count

  launch_type = "FARGATE"

  network_configuration {
    subnets          = local.staging_public_subnet_ids
    security_groups  = [aws_security_group.staging_ecs_service[0].id]
    assign_public_ip = true
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  tags = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}
