locals {
  manage_staging_ecs_compute_effective = var.environment == "staging" && var.manage_staging_ecs_compute && var.manage_staging_network

  # Safe indirections (avoid invalid index errors when resources are not created)
  staging_vpc_id           = try(aws_vpc.staging[0].id, null)
  staging_public_subnet_ids = [for s in aws_subnet.staging_public : s.id]

  ecs_cluster_arn_effective = try(aws_ecs_cluster.dev[0].arn, data.aws_ecs_cluster.existing[0].arn, null)
  ecr_repository_url_effective = try(aws_ecr_repository.api[0].repository_url, data.aws_ecr_repository.existing[0].repository_url, null)

  staging_task_execution_role_arn_effective = trim(var.staging_task_execution_role_arn) != "" ? var.staging_task_execution_role_arn : null
  staging_task_role_arn_effective           = trim(var.staging_task_role_arn) != "" ? var.staging_task_role_arn : null

  staging_container_image_effective = trim(var.staging_container_image) != "" ? var.staging_container_image : (
    local.ecr_repository_url_effective != null ? "${local.ecr_repository_url_effective}:latest" : "public.ecr.aws/docker/library/nginx:latest"
  )

  staging_cloudwatch_log_group_name_effective = local.cloudwatch_log_group_effective != null ? local.cloudwatch_log_group_effective : var.cloudwatch_log_group_name
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

      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        }
      ]

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
