provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = var.managed_by
      Owner       = var.owner
      Project     = var.project_name
    }
  }
}
