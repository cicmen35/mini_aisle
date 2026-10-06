variable "aws_account_id" {
  type        = string
  description = "12-digit account id. The provider refuses to touch any other account."
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be 12 digits."
  }
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "owner" {
  type        = string
  description = "Value of the Owner cost-allocation tag."
  default     = "simon"
}

variable "alert_email" {
  type        = string
  description = "Where DLQ alarms are sent (SNS e-mail, confirm once)."
}

variable "api_allowed_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to reach the API on port 8000, e.g. [\"203.0.113.7/32\"] (your IP)."
  validation {
    condition     = length(var.api_allowed_cidrs) > 0 && alltrue([for c in var.api_allowed_cidrs : c != "0.0.0.0/0"])
    error_message = "Allow-list at least one CIDR, and not 0.0.0.0/0."
  }
}

variable "image_tag" {
  type        = string
  description = "Image tag pushed to ECR by scripts/aws-up.sh (the git SHA)."
  default     = "bootstrap"
}

variable "cpu_architecture" {
  type    = string
  default = "ARM64"
}

variable "api_desired_count" {
  type        = number
  default     = 1
  description = "0 stops the API (and its public IP) while keeping everything else."
}

variable "worker_max_tasks" {
  type    = number
  default = 2
}

variable "llm_provider" {
  type        = string
  default     = "mock"
  description = "mock | openai. Never a GPU instance. For openai, put the key in SSM (see README)."
  validation {
    condition     = contains(["mock", "openai"], var.llm_provider)
    error_message = "llm_provider must be mock or openai on AWS."
  }
}

variable "openai_base_url" {
  type    = string
  default = "https://api.openai.com/v1"
}

variable "openai_model" {
  type    = string
  default = "gpt-4o-mini"
}

variable "log_retention_days" {
  type    = number
  default = 1
}
