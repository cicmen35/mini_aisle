terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Local state on purpose: this env lives for one demo and is destroyed afterwards.
  # For anything longer-lived, move to an S3 backend with locking (see README).
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "aws" {
  region = var.region

  # Hard guard: refuses to run against any account other than the one you put in tfvars.
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = local.tags
  }
}
