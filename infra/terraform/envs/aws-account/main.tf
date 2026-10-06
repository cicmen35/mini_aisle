# Account-level guard rails, applied ONCE and kept (cost: $0, the first two budgets are free).
#   make aws-budget
# Kept separate from envs/aws so `make aws-down` never removes the alerts that would tell you
# something was left running.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "aws" {
  region              = "us-east-1" # Budgets and Cost Explorer are global, served from us-east-1
  allowed_account_ids = [var.aws_account_id]
  default_tags {
    tags = {
      Project     = "patchloop"
      Environment = "aws-account"
      Owner       = var.owner
      ManagedBy   = "terraform"
    }
  }
}

variable "aws_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be 12 digits."
  }
}

variable "owner" {
  type    = string
  default = "simon"
}

variable "alert_email" {
  type = string
}

variable "budget_thresholds_usd" {
  type    = list(number)
  default = [10, 25, 50]
}

variable "activate_cost_allocation_tags" {
  type        = bool
  default     = false
  description = "Set true >= 24h after the first `make aws-up` (AWS must have seen the tags)."
}

module "budget" {
  source                        = "../../modules/budget"
  name                          = "patchloop-monthly"
  alert_email                   = var.alert_email
  alert_thresholds_usd          = var.budget_thresholds_usd
  activate_cost_allocation_tags = var.activate_cost_allocation_tags
}
