# Real-AWS demo environment. Short-lived: `make aws-up`, demo, `make aws-down`.
# Same pipeline module as LocalStack, plus the compute and data layers LocalStack doesn't need.
#
#   Fargate (ARM64, public subnets, no NAT) -> SQS + DLQ, S3, RDS db.t4g.micro, CloudWatch Logs

locals {
  name = "patchloop"
  tags = {
    Project     = "patchloop"
    Environment = "aws-demo"
    Owner       = var.owner
    ManagedBy   = "terraform"
  }
  services = ["api", "scanner", "fixer", "verifier"]
}

module "pipeline" {
  source = "../../modules/pipeline"

  prefix                  = local.name
  bucket_name             = "${local.name}-artifacts-${var.aws_account_id}-${var.region}"
  force_destroy_bucket    = true # demo env: destroy must not fail on leftover artifacts
  artifact_retention_days = 3
}

module "network" {
  source = "../../modules/network"
  name   = local.name
}

module "ecr" {
  source       = "../../modules/ecr"
  prefix       = local.name
  repositories = local.services
}

module "database" {
  source                    = "../../modules/rds_postgres"
  name                      = local.name
  vpc_id                    = module.network.vpc_id
  subnet_ids                = module.network.public_subnet_ids
  client_security_group_ids = [aws_security_group.api.id, aws_security_group.workers.id]
}

# The budget lives in envs/aws-account (applied once, never destroyed) so alerts keep working
# even if something survives `make aws-down`.

resource "aws_ecs_cluster" "this" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "disabled" # costs extra; plain CloudWatch Logs are enough for a demo
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE"]
}
