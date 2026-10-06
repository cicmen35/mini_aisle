# Local dev environment: everything runs in LocalStack (community edition, zero cost).
#   make tf-apply      (runs this inside the `infra` compose service)

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  # State path is overridden with -backend-config in the container (see scripts/).
  backend "local" {}
}

locals {
  tags = {
    Project     = "patchloop"
    Environment = "localstack"
    ManagedBy   = "terraform"
  }
}

provider "aws" {
  region     = var.region
  access_key = "test"
  secret_key = "test"

  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    iam = var.localstack_endpoint
    s3  = var.localstack_endpoint
    sqs = var.localstack_endpoint
    sts = var.localstack_endpoint
  }

  default_tags {
    tags = local.tags
  }
}

module "pipeline" {
  source = "../../modules/pipeline"

  prefix               = "patchloop"
  bucket_name          = "patchloop-artifacts"
  max_receive_count    = var.max_receive_count
  force_destroy_bucket = true
}
