# =============================================================================
# HTTP Health Probe via Lambda (BL-14)
#
# Architektur: EventBridge (rate) -> Lambda -> ECS/EC2 Lookup -> GET /health
#              -> CloudWatch Metric HealthProbeSuccess -> Alarm -> SNS
#
# Hinweis:
# - manage_health_probe ist standardmäßig false (safe default).
# - In dev existieren diese Ressourcen bereits häufig aus Script-Setup.
#   Daher: Import-first vor erstem Apply (siehe infra/terraform/README.md).
# =============================================================================

data "archive_file" "health_probe_zip" {
  count = var.manage_health_probe ? 1 : 0

  type        = "zip"
  source_file = "${path.module}/../lambda/health_probe/lambda_function.py"
  output_path = "${path.module}/../lambda/health_probe/health_probe.zip"
}

data "aws_iam_policy_document" "health_probe_assume_role" {
  count = var.manage_health_probe ? 1 : 0

  statement {
    sid     = "LambdaAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "health_probe" {
  count = var.manage_health_probe ? 1 : 0

  name               = var.health_probe_role_name
  description        = "Health Probe Lambda: ECS task IP lookup + HTTP probe + CW metric"
  assume_role_policy = data.aws_iam_policy_document.health_probe_assume_role[0].json
  tags               = local.common_tags

  lifecycle {
    prevent_destroy = false
  }
}

resource "aws_iam_role_policy_attachment" "health_probe_basic_execution" {
  count = var.manage_health_probe ? 1 : 0

  role       = aws_iam_role.health_probe[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "health_probe_inline" {
  count = var.manage_health_probe ? 1 : 0

  statement {
    sid    = "ECSTaskLookup"
    effect = "Allow"
    actions = [
      "ecs:ListTasks",
      "ecs:DescribeTasks",
    ]
    resources = ["*"]

    condition {
      test     = "ArnLike"
      variable = "ecs:cluster"
      values = [
        "arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:cluster/${var.health_probe_ecs_cluster}",
      ]
    }
  }

  statement {
    sid    = "ENIPublicIPLookup"
    effect = "Allow"
    actions = [
      "ec2:DescribeNetworkInterfaces",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "PutHealthMetric"
    effect = "Allow"
    actions = [
      "cloudwatch:PutMetricData",
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = [var.health_probe_metric_namespace]
    }
  }
}

resource "aws_iam_role_policy" "health_probe_inline" {
  count = var.manage_health_probe ? 1 : 0

  name   = "health-probe-inline"
  role   = aws_iam_role.health_probe[0].id
  policy = data.aws_iam_policy_document.health_probe_inline[0].json
}

resource "aws_lambda_function" "health_probe" {
  count = var.manage_health_probe ? 1 : 0

  function_name = var.health_probe_lambda_name
  description   = "HTTP Uptime Probe: ${var.project_name}-${var.environment} GET /health (dynamische ECS-IP)"
  role          = aws_iam_role.health_probe[0].arn

  filename         = data.archive_file.health_probe_zip[0].output_path
  source_code_hash = data.archive_file.health_probe_zip[0].output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      ECS_CLUSTER = var.health_probe_ecs_cluster
      ECS_SERVICE = var.health_probe_ecs_service
      HEALTH_PORT = tostring(var.health_probe_port)
      HEALTH_PATH = var.health_probe_path
      METRIC_NS   = var.health_probe_metric_namespace
    }
  }

  tags = local.common_tags

  lifecycle {
    prevent_destroy = false
  }

  depends_on = [
    data.archive_file.health_probe_zip,
    aws_iam_role_policy_attachment.health_probe_basic_execution,
    aws_iam_role_policy.health_probe_inline,
  ]
}

resource "aws_cloudwatch_event_rule" "health_probe_schedule" {
  count = var.manage_health_probe ? 1 : 0

  name                = var.health_probe_rule_name
  description         = "Trigger HTTP health probe Lambda alle 5 Minuten"
  schedule_expression = var.health_probe_schedule_expression
  state               = "ENABLED"

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "health_probe_lambda" {
  count = var.manage_health_probe ? 1 : 0

  rule      = aws_cloudwatch_event_rule.health_probe_schedule[0].name
  arn       = aws_lambda_function.health_probe[0].arn
  target_id = "health-probe-lambda"
}

resource "aws_lambda_permission" "health_probe_eventbridge_invoke" {
  count = var.manage_health_probe ? 1 : 0

  statement_id  = "allow-eventbridge-health-probe"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health_probe[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.health_probe_schedule[0].arn
}

resource "aws_cloudwatch_metric_alarm" "health_probe_fail" {
  count = var.manage_health_probe ? 1 : 0

  alarm_name          = var.health_probe_alarm_name
  alarm_description   = "HTTP /health probe failed (ECS task not reachable or unhealthy)"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 3
  threshold           = 1
  period              = 300
  statistic           = "Minimum"
  namespace           = var.health_probe_metric_namespace
  metric_name         = "HealthProbeSuccess"
  treat_missing_data  = "breaching"

  dimensions = {
    Service     = var.health_probe_ecs_service
    Environment = var.environment
  }

  alarm_actions = [var.sns_topic_arn]
  ok_actions    = [var.sns_topic_arn]

  tags = local.common_tags
}
