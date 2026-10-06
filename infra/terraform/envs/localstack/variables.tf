variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "localstack_endpoint" {
  type        = string
  default     = "http://localhost:4566"
  description = "LocalStack edge endpoint. This env must never point at real AWS."
  validation {
    condition     = can(regex("^https?://(localhost|127\\.0\\.0\\.1|localstack|[a-z0-9-]+\\.localstack[a-z0-9.-]*|localstack\\.[a-z0-9.-]+)(:[0-9]+)?/?$", var.localstack_endpoint))
    error_message = "localstack_endpoint must be a LocalStack URL (localhost/localstack host), never a real AWS endpoint."
  }
}

variable "max_receive_count" {
  type    = number
  default = 3
}
