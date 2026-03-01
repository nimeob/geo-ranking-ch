locals {
  manage_staging_network_effective = var.environment == "staging" && var.manage_staging_network
  manage_staging_ingress_effective = var.environment == "staging" && var.manage_staging_network && var.manage_staging_ingress
}

# ---------------------------------------------------------------------------
# Staging Network Baseline + ALB/Ingress Skeleton (WP #660)
#
# Safety rules:
# - Everything is behind manage flags (default: false).
# - Additionally guarded by var.environment == "staging" to avoid accidental creates in dev.
# - prevent_destroy where sensible.
# ---------------------------------------------------------------------------

data "aws_availability_zones" "staging" {
  count = local.manage_staging_network_effective ? 1 : 0

  state = "available"
}

resource "aws_vpc" "staging" {
  count = local.manage_staging_network_effective ? 1 : 0

  cidr_block           = var.staging_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-vpc"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_internet_gateway" "staging" {
  count = local.manage_staging_network_effective ? 1 : 0

  vpc_id = aws_vpc.staging[0].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-igw"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_subnet" "staging_public" {
  count = local.manage_staging_network_effective ? length(var.staging_public_subnet_cidrs) : 0

  vpc_id                  = aws_vpc.staging[0].id
  cidr_block              = var.staging_public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.staging[0].names[count.index % length(data.aws_availability_zones.staging[0].names)]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-public-${count.index + 1}"
    Tier = "public"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_subnet" "staging_private" {
  count = local.manage_staging_network_effective ? length(var.staging_private_subnet_cidrs) : 0

  vpc_id            = aws_vpc.staging[0].id
  cidr_block        = var.staging_private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.staging[0].names[count.index % length(data.aws_availability_zones.staging[0].names)]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-private-${count.index + 1}"
    Tier = "private"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route_table" "staging_public" {
  count = local.manage_staging_network_effective ? 1 : 0

  vpc_id = aws_vpc.staging[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.staging[0].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-public-rt"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route_table_association" "staging_public" {
  count = local.manage_staging_network_effective ? length(aws_subnet.staging_public) : 0

  subnet_id      = aws_subnet.staging_public[count.index].id
  route_table_id = aws_route_table.staging_public[0].id
}

resource "aws_security_group" "staging_alb" {
  count = local.manage_staging_ingress_effective ? 1 : 0

  name        = "${var.project_name}-staging-alb-sg"
  description = "staging ALB ingress security group (managed by Terraform)"
  vpc_id      = aws_vpc.staging[0].id

  ingress {
    description = "HTTP from allowed CIDRs"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.staging_alb_ingress_cidr_blocks
  }

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-staging-alb-sg"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_lb" "staging" {
  count = local.manage_staging_ingress_effective ? 1 : 0

  name               = var.staging_alb_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.staging_alb[0].id]
  subnets            = aws_subnet.staging_public[*].id

  enable_deletion_protection = true

  tags = merge(local.common_tags, {
    Name = var.staging_alb_name
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_lb_listener" "staging_http" {
  count = local.manage_staging_ingress_effective ? 1 : 0

  load_balancer_arn = aws_lb.staging[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "staging ALB skeleton - no target attached"
      status_code  = "200"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
