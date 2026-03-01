variable "project_name" {
  description = "Interner AWS-Projektname (z. B. swisstopo)."
  type        = string
  default     = "swisstopo"
}

variable "environment" {
  description = "Deployment-Umgebung (aktuell dev)."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS Region für Provider und Ressourcen."
  type        = string
  default     = "eu-central-1"
}

variable "owner" {
  description = "Owner-Tag für Ressourcen."
  type        = string
  default     = "nico"
}

variable "managed_by" {
  description = "ManagedBy-Tag für Ressourcen."
  type        = string
  default     = "openclaw"
}

variable "lookup_existing_resources" {
  description = "Wenn true, werden bestehende Ressourcen via Data Sources gelesen (Read-Only)."
  type        = bool
  default     = false
}

variable "manage_ecs_cluster" {
  description = "Wenn true, verwaltet Terraform den ECS Cluster (Import vor Apply empfohlen)."
  type        = bool
  default     = false
}

variable "manage_ecr_repository" {
  description = "Wenn true, verwaltet Terraform das ECR Repository (Import vor Apply empfohlen)."
  type        = bool
  default     = false
}

variable "manage_cloudwatch_log_group" {
  description = "Wenn true, verwaltet Terraform die CloudWatch Log Group (Import vor Apply empfohlen)."
  type        = bool
  default     = false
}

variable "manage_s3_bucket" {
  description = "Wenn true, verwaltet Terraform den dev-S3-Bucket (Import vor Apply empfohlen)."
  type        = bool
  default     = false
}

variable "ecs_cluster_name" {
  description = "Zielname des ECS Clusters im dev-Setup."
  type        = string
  default     = "swisstopo-dev"
}

variable "ecs_container_insights_enabled" {
  description = "Container Insights Setting für den ECS Cluster (nur relevant bei manage_ecs_cluster=true)."
  type        = bool
  default     = false
}

variable "ecr_repository_name" {
  description = "Zielname des ECR Repositories im dev-Setup."
  type        = string
  default     = "swisstopo-dev-api"
}

variable "cloudwatch_log_group_name" {
  description = "Zielname der CloudWatch Log Group für den API-Service."
  type        = string
  default     = "/swisstopo/dev/ecs/api"
}

variable "cloudwatch_log_retention_days" {
  description = "Retention für neue CloudWatch Log Group (nur relevant bei manage_cloudwatch_log_group=true)."
  type        = number
  default     = 30
}

variable "s3_bucket_name" {
  description = "Name des dev-S3-Buckets."
  type        = string
  default     = "swisstopo-dev-523234426229"
}

variable "existing_ecs_cluster_name" {
  description = "Name eines bereits existierenden ECS Clusters (Read-Only Lookup)."
  type        = string
  default     = "swisstopo-dev"
}

variable "existing_ecr_repository_name" {
  description = "Name eines bereits existierenden ECR Repositories (Read-Only Lookup)."
  type        = string
  default     = "swisstopo-dev-api"
}

variable "existing_cloudwatch_log_group_name" {
  description = "Name einer bereits existierenden CloudWatch Log Group (Read-Only Lookup)."
  type        = string
  default     = "/swisstopo/dev/ecs/api"
}

variable "existing_s3_bucket_name" {
  description = "Name eines bereits existierenden dev-S3-Buckets (Read-Only Lookup)."
  type        = string
  default     = "swisstopo-dev-523234426229"
}

# ---------------------------------------------------------------------------
# Telegram Alerting (BL-08)
# ---------------------------------------------------------------------------

variable "manage_telegram_alerting" {
  description = "Wenn true, erstellt Terraform Lambda + IAM Role + SNS-Subscription für Telegram-Alerting. Voraussetzung: SSM-Parameter /swisstopo/<env>/telegram-bot-token muss manuell angelegt sein."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# HTTP Health Probe (BL-14)
# ---------------------------------------------------------------------------

variable "manage_health_probe" {
  description = "Wenn true, verwaltet Terraform die Lambda-basierte HTTP-Health-Probe (IAM, Lambda, EventBridge, Alarm). Import-first empfohlen, da Ressourcen in dev bereits existieren können."
  type        = bool
  default     = false
}

variable "health_probe_ecs_cluster" {
  description = "ECS Cluster Name für die Health-Probe-Lambda (ENV ECS_CLUSTER)."
  type        = string
  default     = "swisstopo-dev"
}

variable "health_probe_ecs_service" {
  description = "ECS Service Name für die Health-Probe-Lambda (ENV ECS_SERVICE)."
  type        = string
  default     = "swisstopo-dev-api"
}

variable "health_probe_port" {
  description = "HTTP-Port für den /health Probe-Aufruf (ENV HEALTH_PORT)."
  type        = number
  default     = 8080
}

variable "health_probe_path" {
  description = "HTTP-Pfad für die Probe (ENV HEALTH_PATH)."
  type        = string
  default     = "/health"
}

variable "health_probe_metric_namespace" {
  description = "CloudWatch Namespace für Probe-Metrik HealthProbeSuccess."
  type        = string
  default     = "swisstopo/dev-api"
}

variable "health_probe_lambda_name" {
  description = "Name der Health-Probe-Lambda-Funktion."
  type        = string
  default     = "swisstopo-dev-health-probe"
}

variable "health_probe_role_name" {
  description = "Name der IAM-Role für die Health-Probe-Lambda."
  type        = string
  default     = "swisstopo-dev-health-probe-role"
}

variable "health_probe_rule_name" {
  description = "Name der EventBridge Schedule Rule für die Health-Probe-Lambda."
  type        = string
  default     = "swisstopo-dev-health-probe-schedule"
}

variable "health_probe_alarm_name" {
  description = "Name des CloudWatch Alarms für fehlgeschlagene Health-Probe."
  type        = string
  default     = "swisstopo-dev-api-health-probe-fail"
}

variable "health_probe_schedule_expression" {
  description = "Schedule Expression für EventBridge (z. B. rate(5 minutes))."
  type        = string
  default     = "rate(5 minutes)"
}

variable "aws_account_id" {
  description = "AWS Account ID (für IAM-Policy-ARNs). Nicht sensitiv."
  type        = string
  default     = "523234426229"
}

variable "sns_topic_arn" {
  description = "ARN des SNS Topics, auf das CloudWatch-Alarme publishen."
  type        = string
  default     = "arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts"
}

variable "telegram_chat_id" {
  description = "Telegram Chat ID für Alarm-Empfang. Kein Secret (nur numerische ID)."
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Staging Network + Ingress Skeleton (WP #660)
# ---------------------------------------------------------------------------

variable "manage_staging_network" {
  description = "Wenn true, erstellt Terraform die staging Network-Baseline (VPC/Subnets/Route Tables/IGW). Guard: wirkt nur bei environment=staging."
  type        = bool
  default     = false
}

variable "manage_staging_ingress" {
  description = "Wenn true, erstellt Terraform ein staging ALB/Ingress-Skeleton (ALB + SG + HTTP listener fixed-response). Guard: wirkt nur bei environment=staging und nur wenn manage_staging_network=true."
  type        = bool
  default     = false
}

variable "staging_vpc_cidr" {
  description = "CIDR Block für die staging VPC."
  type        = string
  default     = "10.70.0.0/16"
}

variable "staging_public_subnet_cidrs" {
  description = "CIDR Blocks für staging Public Subnets (mind. 2 empfohlen, unterschiedliche AZs)."
  type        = list(string)
  default     = ["10.70.0.0/24", "10.70.1.0/24"]
}

variable "staging_private_subnet_cidrs" {
  description = "CIDR Blocks für staging Private Subnets (optional; NAT ist in diesem WP bewusst nicht enthalten)."
  type        = list(string)
  default     = ["10.70.10.0/24", "10.70.11.0/24"]
}

variable "staging_alb_name" {
  description = "Name des staging Application Load Balancers (<= 32 Zeichen)."
  type        = string
  default     = "swisstopo-staging-alb"
}

variable "staging_alb_ingress_cidr_blocks" {
  description = "CIDR Blocks, von denen HTTP (80) auf das staging ALB erlaubt ist (nur relevant bei manage_staging_ingress=true)."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# ---------------------------------------------------------------------------
# Service URLs / Endpoints (staging scaffold)
# ---------------------------------------------------------------------------

variable "api_base_url" {
  description = "Base-URL der API (z. B. https://api.example.com). Wird als Output gespiegelt; kann später aus ALB DNS abgeleitet werden."
  type        = string
  default     = ""
}

variable "api_health_path" {
  description = "Health-Path relativ zur api_base_url (Default: /health)."
  type        = string
  default     = "/health"
}

# ---------------------------------------------------------------------------
# Staging ECS Compute Baseline (WP #661)
# ---------------------------------------------------------------------------

variable "manage_staging_ecs_compute" {
  description = "Wenn true, erstellt Terraform ein staging ECS compute skeleton (SG + TaskDef + Service). Guard: wirkt nur bei environment=staging."
  type        = bool
  default     = false
}

variable "staging_service_name" {
  description = "Name des ECS Services in staging."
  type        = string
  default     = "swisstopo-staging-api"
}

variable "staging_task_family" {
  description = "Task Definition Family für staging."
  type        = string
  default     = "swisstopo-staging-api"
}

variable "staging_task_cpu" {
  description = "CPU für Fargate Task Definition (String; z. B. 256/512/1024)."
  type        = string
  default     = "256"
}

variable "staging_task_memory" {
  description = "Memory für Fargate Task Definition (String; z. B. 512/1024/2048)."
  type        = string
  default     = "512"
}

variable "staging_desired_count" {
  description = "Desired Count für den staging ECS Service."
  type        = number
  default     = 1
}

variable "staging_container_name" {
  description = "Container-Name im staging Task Definition Container Definitions JSON."
  type        = string
  default     = "api"
}

variable "staging_container_image" {
  description = "Container Image für staging. Leer => auto: <ecr_repository_url>:latest (wenn verfügbar), sonst nginx Placeholder."
  type        = string
  default     = ""
}

variable "staging_container_port" {
  description = "Container Port für staging (z. B. 8080)."
  type        = number
  default     = 8080
}

variable "staging_task_execution_role_arn" {
  description = "Optional: Execution Role ARN für die ECS Task Definition (leer => null)."
  type        = string
  default     = ""
}

variable "staging_task_role_arn" {
  description = "Optional: Task Role ARN für die ECS Task Definition (leer => null)."
  type        = string
  default     = ""
}
