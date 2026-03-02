locals {
  manage_dev_ecs_compute_effective = var.environment == "dev" && var.manage_dev_ecs_compute && var.manage_dev_network

  # Safe indirections (avoid invalid index errors when resources are not created)
  dev_vpc_id            = try(aws_vpc.dev[0].id, null)
  dev_public_subnet_ids = [for s in aws_subnet.dev_public : s.id]

  dev_task_execution_role_arn_effective = trimspace(var.dev_task_execution_role_arn) != "" ? var.dev_task_execution_role_arn : null
  dev_task_role_arn_effective           = trimspace(var.dev_task_role_arn) != "" ? var.dev_task_role_arn : null

  dev_container_image_effective = trimspace(var.dev_container_image) != "" ? var.dev_container_image : (
    local.ecr_repository_url_effective != null ? "${local.ecr_repository_url_effective}:latest" : "public.ecr.aws/docker/library/nginx:latest"
  )

  dev_cloudwatch_log_group_name_effective = local.cloudwatch_log_group_effective != null ? local.cloudwatch_log_group_effective : var.cloudwatch_log_group_name

  # ---------------------------------------------------------------------------
  # Dev DB Secrets Wiring
  #
  # DB_HOST / DB_PORT / DB_NAME / DB_USERNAME → plain environment (non-secret)
  # DB_PASSWORD → secrets block via SecretsManager ARN (JSON key "password")
  #
  # Secret ARN resolution order:
  #   1) var.dev_db_master_user_secret_arn_override (explicit cross-workspace override)
  #   2) aws_db_instance.dev_postgres[0].master_user_secret[0].secret_arn
  #      (auto-managed by RDS via manage_master_user_password=true, available when manage_dev_db=true)
  # If neither is set, the secrets block is omitted (no DB_PASSWORD injected).
  # ---------------------------------------------------------------------------

  dev_db_host_effective = try(aws_db_instance.dev_postgres[0].address, null)

  dev_db_secret_arn_effective = trimspace(var.dev_db_master_user_secret_arn_override) != "" ? (
    var.dev_db_master_user_secret_arn_override
  ) : try(aws_db_instance.dev_postgres[0].master_user_secret[0].secret_arn, null)

  # Secrets list: only populated when ARN is known.
  # valueFrom format: "<SecretArn>:<JsonKey>::"
  dev_db_secrets = local.dev_db_secret_arn_effective != null ? [
    {
      name      = "DB_PASSWORD"
      valueFrom = "${local.dev_db_secret_arn_effective}:password::"
    }
  ] : []
}

# ---------------------------------------------------------------------------
# Dev ECS Compute Baseline (INFRA-NET-0-dev)
#
# Safety rules:
# - Everything is behind manage flags (default: false).
# - Additionally guarded by var.environment == "dev" to avoid accidental creates in staging.
# - prevent_destroy where sensible.
#
# Notes:
# - This is a skeleton. ALB Target Groups / Listener Rules wiring is handled in separate work.
# - Roles/Secrets/Logs are referenced via variables; creation/import is handled in other WPs.
# ---------------------------------------------------------------------------

resource "aws_security_group" "dev_ecs_service" {
  count = local.manage_dev_ecs_compute_effective ? 1 : 0

  name        = "${var.project_name}-dev-ecs-service-sg"
  description = "dev ECS service security group (managed by Terraform)"
  vpc_id      = local.dev_vpc_id

  # Default: no ingress. Traffic is wired when Target Groups/ALB routing is added.

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-ecs-service-sg"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ecs_task_definition" "dev_api" {
  count = local.manage_dev_ecs_compute_effective ? 1 : 0

  family                   = var.dev_task_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.dev_task_cpu
  memory                   = var.dev_task_memory

  execution_role_arn = local.dev_task_execution_role_arn_effective
  task_role_arn      = local.dev_task_role_arn_effective

  container_definitions = jsonencode([
    {
      name      = var.dev_container_name
      image     = local.dev_container_image_effective
      essential = true

      portMappings = [
        {
          containerPort = var.dev_container_port
          hostPort      = var.dev_container_port
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
        local.dev_db_host_effective != null ? [
          {
            name  = "DB_HOST"
            value = local.dev_db_host_effective
          },
          {
            name  = "DB_PORT"
            value = tostring(var.dev_db_port)
          },
          {
            name  = "DB_NAME"
            value = var.dev_db_name
          },
          {
            name  = "DB_USERNAME"
            value = var.dev_db_master_username
          }
        ] : []
      )

      # DB_PASSWORD injected via Secrets Manager (no plaintext in task definition).
      # Requires: Execution Role must have secretsmanager:GetSecretValue on the secret ARN.
      # See: docs/DEV_DB_ECS_SECRETS_RUNBOOK.md for full IAM requirements.
      secrets = local.dev_db_secrets

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = local.dev_cloudwatch_log_group_name_effective
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

resource "aws_ecs_service" "dev_api" {
  count = local.manage_dev_ecs_compute_effective ? 1 : 0

  name            = var.dev_service_name
  cluster         = local.ecs_cluster_arn_effective
  task_definition = aws_ecs_task_definition.dev_api[0].arn
  desired_count   = var.dev_desired_count

  launch_type = "FARGATE"

  network_configuration {
    subnets          = local.dev_public_subnet_ids
    security_groups  = [aws_security_group.dev_ecs_service[0].id]
    assign_public_ip = true
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  tags = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}
