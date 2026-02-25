# =============================================================================
# Telegram Alerting via Lambda (BL-08 Erweiterung)
#
# Architektur:  CloudWatch Alarm → SNS Topic → Lambda → Telegram Bot API
# Secret:       Bot-Token in SSM Parameter Store (SecureString, NICHT im State)
#               Anlegen vor Apply:
#                 aws ssm put-parameter \
#                   --region eu-central-1 \
#                   --name /swisstopo/dev/telegram-bot-token \
#                   --type SecureString \
#                   --value "<BOT_TOKEN>" \
#                   --description "Telegram Bot Token für swisstopo-dev Alerting"
#
# Aktivierung:  manage_telegram_alerting = true in terraform.tfvars
# =============================================================================

# --------------------------------------------------------------------------
# Packaging: Lambda-Quellcode automatisch zippen
# --------------------------------------------------------------------------
data "archive_file" "sns_to_telegram_zip" {
  count = var.manage_telegram_alerting ? 1 : 0

  type        = "zip"
  source_file = "${path.module}/../lambda/sns_to_telegram/lambda_function.py"
  output_path = "${path.module}/../lambda/sns_to_telegram/sns_to_telegram.zip"
}

# --------------------------------------------------------------------------
# IAM Role für Lambda (minimal-privilege)
# --------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume_role" {
  count = var.manage_telegram_alerting ? 1 : 0

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

resource "aws_iam_role" "sns_to_telegram" {
  count = var.manage_telegram_alerting ? 1 : 0

  name               = "swisstopo-${var.environment}-sns-to-telegram-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role[0].json
  tags               = local.common_tags

  lifecycle {
    prevent_destroy = false
  }
}

data "aws_iam_policy_document" "sns_to_telegram_inline" {
  count = var.manage_telegram_alerting ? 1 : 0

  # CloudWatch Logs (Lambda braucht das immer)
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/lambda/swisstopo-${var.environment}-sns-to-telegram:*",
    ]
  }

  # SSM Parameter Store: nur exakt diesen einen Parameter lesen
  statement {
    sid    = "AllowSSMGetBotToken"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
    ]
    resources = [
      "arn:aws:ssm:${var.aws_region}:${var.aws_account_id}:parameter/swisstopo/${var.environment}/telegram-bot-token",
    ]
  }

  # KMS: entschlüsseln des SSM SecureString (AWS-managed key)
  statement {
    sid    = "AllowKMSDecryptSSMKey"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
    ]
    resources = [
      "arn:aws:kms:${var.aws_region}:${var.aws_account_id}:key/aws/ssm",
    ]
  }
}

resource "aws_iam_role_policy" "sns_to_telegram_inline" {
  count = var.manage_telegram_alerting ? 1 : 0

  name   = "sns-to-telegram-inline"
  role   = aws_iam_role.sns_to_telegram[0].id
  policy = data.aws_iam_policy_document.sns_to_telegram_inline[0].json
}

# --------------------------------------------------------------------------
# Lambda-Funktion
# --------------------------------------------------------------------------
resource "aws_lambda_function" "sns_to_telegram" {
  count = var.manage_telegram_alerting ? 1 : 0

  function_name = "swisstopo-${var.environment}-sns-to-telegram"
  description   = "Forwardiert CloudWatch-Alarme via SNS als Telegram-Nachricht"
  role          = aws_iam_role.sns_to_telegram[0].arn

  filename         = data.archive_file.sns_to_telegram_zip[0].output_path
  source_code_hash = data.archive_file.sns_to_telegram_zip[0].output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      TELEGRAM_CHAT_ID       = var.telegram_chat_id
      TELEGRAM_BOT_TOKEN_SSM = "/swisstopo/${var.environment}/telegram-bot-token"
    }
  }

  tags = local.common_tags

  lifecycle {
    prevent_destroy = false
  }

  depends_on = [data.archive_file.sns_to_telegram_zip]
}

# Erlaubnis für SNS, die Lambda-Funktion aufzurufen
resource "aws_lambda_permission" "sns_invoke" {
  count = var.manage_telegram_alerting ? 1 : 0

  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sns_to_telegram[0].function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.sns_topic_arn
}

# --------------------------------------------------------------------------
# SNS → Lambda Subscription
# --------------------------------------------------------------------------
resource "aws_sns_topic_subscription" "lambda_telegram" {
  count = var.manage_telegram_alerting ? 1 : 0

  topic_arn = var.sns_topic_arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.sns_to_telegram[0].arn

  depends_on = [aws_lambda_permission.sns_invoke]
}
