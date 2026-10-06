variable "name" {
  type = string
}

variable "cluster_arn" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "image" {
  type = string
}

variable "command" {
  type    = list(string)
  default = null
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "cpu_architecture" {
  type        = string
  default     = "ARM64"
  description = "ARM64 (Graviton) Fargate is ~20% cheaper than X86_64."
  validation {
    condition     = contains(["ARM64", "X86_64"], var.cpu_architecture)
    error_message = "cpu_architecture must be ARM64 or X86_64."
  }
}

variable "environment" {
  type    = map(string)
  default = {}
}

variable "secrets" {
  type        = map(string)
  default     = {}
  description = "Env var name -> SSM parameter / Secrets Manager ARN."
}

variable "task_role_arn" {
  type = string
}

variable "execution_role_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "assign_public_ip" {
  type        = bool
  default     = true
  description = "Needed for egress without a NAT gateway."
}

variable "desired_count" {
  type    = number
  default = 0
}

variable "container_port" {
  type    = number
  default = null
}

variable "log_retention_days" {
  type    = number
  default = 1
}

variable "scale_on_queue" {
  type = object({
    queue_name        = string
    max_tasks         = number
    messages_per_task = optional(number, 10)
    idle_minutes      = optional(number, 10)
  })
  default     = null
  description = "Enable 0..max_tasks scaling on SQS depth. null = fixed desired_count."
}

variable "tags" {
  type    = map(string)
  default = {}
}
