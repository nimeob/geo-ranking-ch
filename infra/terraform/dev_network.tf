locals {
  manage_dev_network_effective = var.environment == "dev" && var.manage_dev_network
  manage_dev_ingress_effective = var.environment == "dev" && var.manage_dev_network && var.manage_dev_ingress
  manage_dev_nat_effective     = var.environment == "dev" && var.manage_dev_network && var.manage_dev_nat_gateway
}

# ---------------------------------------------------------------------------
# Dev Network Baseline + ALB/Ingress Skeleton
#
# Safety rules:
# - Everything is behind manage flags (default: false).
# - Additionally guarded by var.environment == "dev" to avoid accidental creates in staging.
# - prevent_destroy where sensible.
# ---------------------------------------------------------------------------

data "aws_availability_zones" "dev" {
  count = local.manage_dev_network_effective ? 1 : 0

  state = "available"
}

resource "aws_vpc" "dev" {
  count = local.manage_dev_network_effective ? 1 : 0

  cidr_block           = var.dev_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-vpc"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_internet_gateway" "dev" {
  count = local.manage_dev_network_effective ? 1 : 0

  vpc_id = aws_vpc.dev[0].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-igw"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_subnet" "dev_public" {
  count = local.manage_dev_network_effective ? length(var.dev_public_subnet_cidrs) : 0

  vpc_id                  = aws_vpc.dev[0].id
  cidr_block              = var.dev_public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.dev[0].names[count.index % length(data.aws_availability_zones.dev[0].names)]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-public-${count.index + 1}"
    Tier = "public"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_subnet" "dev_private" {
  count = local.manage_dev_network_effective ? length(var.dev_private_subnet_cidrs) : 0

  vpc_id            = aws_vpc.dev[0].id
  cidr_block        = var.dev_private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.dev[0].names[count.index % length(data.aws_availability_zones.dev[0].names)]

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-private-${count.index + 1}"
    Tier = "private"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route_table" "dev_public" {
  count = local.manage_dev_network_effective ? 1 : 0

  vpc_id = aws_vpc.dev[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.dev[0].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-public-rt"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route_table_association" "dev_public" {
  count = local.manage_dev_network_effective ? length(var.dev_public_subnet_cidrs) : 0

  subnet_id      = aws_subnet.dev_public[count.index].id
  route_table_id = aws_route_table.dev_public[0].id
}

resource "aws_eip" "dev_nat" {
  count = local.manage_dev_nat_effective ? 1 : 0

  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-nat-eip"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_nat_gateway" "dev" {
  count = local.manage_dev_nat_effective ? 1 : 0

  allocation_id = aws_eip.dev_nat[0].id
  subnet_id     = aws_subnet.dev_public[0].id

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-nat"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route_table" "dev_private" {
  count = local.manage_dev_nat_effective ? 1 : 0

  vpc_id = aws_vpc.dev[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.dev[0].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-private-rt"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route_table_association" "dev_private" {
  count = local.manage_dev_nat_effective ? length(var.dev_private_subnet_cidrs) : 0

  subnet_id      = aws_subnet.dev_private[count.index].id
  route_table_id = aws_route_table.dev_private[0].id
}

resource "aws_security_group" "dev_alb" {
  count = local.manage_dev_ingress_effective ? 1 : 0

  name        = "${var.project_name}-dev-alb-sg"
  description = "dev ALB ingress security group (managed by Terraform)"
  vpc_id      = aws_vpc.dev[0].id

  ingress {
    description = "HTTP from allowed CIDRs"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.dev_alb_ingress_cidr_blocks
  }

  egress {
    description = "All egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dev-alb-sg"
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_lb" "dev" {
  count = local.manage_dev_ingress_effective ? 1 : 0

  name               = var.dev_alb_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.dev_alb[0].id]
  subnets            = aws_subnet.dev_public[*].id

  enable_deletion_protection = true

  tags = merge(local.common_tags, {
    Name = var.dev_alb_name
  })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_lb_listener" "dev_http" {
  count = local.manage_dev_ingress_effective ? 1 : 0

  load_balancer_arn = aws_lb.dev[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "dev ALB skeleton - no target attached"
      status_code  = "200"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
