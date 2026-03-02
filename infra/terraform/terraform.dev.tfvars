# --- Basis ---
project_name = "swisstopo"
environment  = "dev"
aws_region   = "eu-central-1"
owner        = "nico"
managed_by   = "openclaw"

# --- Sicherheitsmodus ---
lookup_existing_resources      = true
manage_ecs_cluster             = false
manage_ecr_repository          = false
manage_cloudwatch_log_group    = false
manage_cloudwatch_log_group_ui = false
manage_s3_bucket               = false

# --- Dev Network + Ingress Skeleton (INFRA-NET-0-dev) ---
manage_dev_network = true
manage_dev_ingress = false

# --- Dev ECS Compute Skeleton ---
manage_dev_ecs_compute = false

# --- Dev DB (INFRA-NET-0-dev) ---
manage_dev_db = true

dev_vpc_cidr = "10.80.0.0/16"

# Public Subnets (mind. 2 empfohlen, unterschiedliche AZs)
dev_public_subnet_cidrs = ["10.80.0.0/24", "10.80.1.0/24"]

# Private Subnets (optional; NAT ist in diesem WP bewusst nicht enthalten)
dev_private_subnet_cidrs = ["10.80.10.0/24", "10.80.11.0/24"]

dev_alb_name = "swisstopo-dev-alb"

# HTTP 80 allowlist (nur relevant wenn manage_dev_ingress=true)
dev_alb_ingress_cidr_blocks = ["0.0.0.0/0"]

# --- Ziel-/Bestandsnamen (dev) ---
ecs_cluster_name               = "swisstopo-dev"
ecs_container_insights_enabled = false

ecr_repository_name          = "swisstopo-dev-api"
cloudwatch_log_group_name    = "/swisstopo/dev/ecs/api"
cloudwatch_log_group_ui_name = "/swisstopo/dev/ecs/ui"
cloudwatch_log_retention_days = 30

s3_bucket_name = "swisstopo-dev-523234426229"

existing_ecs_cluster_name             = "swisstopo-dev"
existing_ecr_repository_name         = "swisstopo-dev-api"
existing_cloudwatch_log_group_name    = "/swisstopo/dev/ecs/api"
existing_cloudwatch_log_group_ui_name = "/swisstopo/dev/ecs/ui"
existing_s3_bucket_name               = "swisstopo-dev-523234426229"

# --- Telegram Alerting ---
manage_telegram_alerting = false

# --- HTTP Health Probe ---
manage_health_probe = false

health_probe_ecs_cluster      = "swisstopo-dev"
health_probe_ecs_service      = "swisstopo-dev-api"
health_probe_port             = 8080
health_probe_path             = "/health"
health_probe_metric_namespace = "swisstopo/dev-api"

health_probe_lambda_name = "swisstopo-dev-health-probe"
health_probe_role_name   = "swisstopo-dev-health-probe-role"
health_probe_rule_name   = "swisstopo-dev-health-probe-schedule"
health_probe_alarm_name  = "swisstopo-dev-api-health-probe-fail"
health_probe_schedule_expression = "rate(5 minutes)"

aws_account_id   = "523234426229"
sns_topic_arn    = "arn:aws:sns:eu-central-1:523234426229:swisstopo-dev-alerts"
telegram_chat_id = ""

# --- Service URLs ---
api_base_url    = ""
api_health_path = "/health"
