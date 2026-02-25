output "environment" {
  description = "Aktive Umgebung für dieses Terraform-Setup."
  value       = var.environment
}

output "aws_region" {
  description = "Aktive AWS Region."
  value       = var.aws_region
}

output "ecs_cluster_name" {
  description = "Effektiver ECS-Clustername (managed oder read-only erkannt)."
  value       = local.ecs_cluster_name_effective
}

output "ecs_cluster_arn" {
  description = "ECS-Cluster-ARN (falls managed oder erfolgreich read-only aufgelöst)."
  value = coalesce(
    try(aws_ecs_cluster.dev[0].arn, null),
    try(data.aws_ecs_cluster.existing[0].arn, null)
  )
}

output "ecr_repository_name" {
  description = "Effektiver ECR-Repository-Name (managed oder read-only erkannt)."
  value       = local.ecr_repository_name_effective
}

output "ecr_repository_url" {
  description = "ECR Repository URL (falls managed oder erfolgreich read-only aufgelöst)."
  value = coalesce(
    try(aws_ecr_repository.api[0].repository_url, null),
    try(data.aws_ecr_repository.existing[0].repository_url, null)
  )
}

output "cloudwatch_log_group_name" {
  description = "Effektiver CloudWatch Log Group Name (managed oder read-only erkannt)."
  value       = local.cloudwatch_log_group_effective
}

output "cloudwatch_log_group_arn" {
  description = "CloudWatch Log Group ARN (falls managed oder erfolgreich read-only aufgelöst)."
  value = coalesce(
    try(aws_cloudwatch_log_group.api[0].arn, null),
    try(data.aws_cloudwatch_log_group.existing[0].arn, null)
  )
}

output "s3_bucket_name" {
  description = "Effektiver S3-Bucket-Name (managed oder read-only erkannt)."
  value       = local.s3_bucket_name_effective
}

output "s3_bucket_arn" {
  description = "S3 Bucket ARN (falls managed oder erfolgreich read-only aufgelöst)."
  value = coalesce(
    try(aws_s3_bucket.dev[0].arn, null),
    try(data.aws_s3_bucket.existing[0].arn, null)
  )
}

output "resource_management_flags" {
  description = "Transparenz: welche Ressourcen aktuell von Terraform gemanagt werden."
  value = {
    lookup_existing_resources   = var.lookup_existing_resources
    manage_ecs_cluster          = var.manage_ecs_cluster
    manage_ecr_repository       = var.manage_ecr_repository
    manage_cloudwatch_log_group = var.manage_cloudwatch_log_group
    manage_s3_bucket            = var.manage_s3_bucket
    manage_telegram_alerting    = var.manage_telegram_alerting
    manage_health_probe         = var.manage_health_probe
  }
}

output "telegram_lambda_arn" {
  description = "ARN der Telegram-Alerting Lambda-Funktion (leer wenn nicht gemanagt)."
  value       = try(aws_lambda_function.sns_to_telegram[0].arn, null)
}

output "telegram_lambda_function_name" {
  description = "Name der Telegram-Alerting Lambda-Funktion (leer wenn nicht gemanagt)."
  value       = try(aws_lambda_function.sns_to_telegram[0].function_name, null)
}

output "telegram_sns_subscription_arn" {
  description = "ARN der SNS → Lambda Subscription für Telegram-Alerting."
  value       = try(aws_sns_topic_subscription.lambda_telegram[0].arn, null)
}

output "health_probe_lambda_arn" {
  description = "ARN der Health-Probe-Lambda-Funktion (leer wenn nicht gemanagt)."
  value       = try(aws_lambda_function.health_probe[0].arn, null)
}

output "health_probe_lambda_function_name" {
  description = "Name der Health-Probe-Lambda-Funktion (leer wenn nicht gemanagt)."
  value       = try(aws_lambda_function.health_probe[0].function_name, null)
}

output "health_probe_alarm_name" {
  description = "Name des Health-Probe-Alarms (leer wenn nicht gemanagt)."
  value       = try(aws_cloudwatch_metric_alarm.health_probe_fail[0].alarm_name, null)
}

output "health_probe_schedule_rule_arn" {
  description = "ARN der EventBridge-Rule für die Health-Probe (leer wenn nicht gemanagt)."
  value       = try(aws_cloudwatch_event_rule.health_probe_schedule[0].arn, null)
}
