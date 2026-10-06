variable "prefix" {
  type        = string
  default     = "patchloop"
  description = "Name prefix for queues and roles."
}

variable "bucket_name" {
  type        = string
  description = "S3 bucket names are global on AWS; add a suffix there."
}

variable "max_receive_count" {
  type    = number
  default = 5
}

variable "scan_visibility_timeout_seconds" {
  type    = number
  default = 600
}

variable "fix_visibility_timeout_seconds" {
  type    = number
  default = 300
}

variable "verify_visibility_timeout_seconds" {
  type    = number
  default = 600
}

variable "force_destroy_bucket" {
  type    = bool
  default = false
}

variable "artifact_retention_days" {
  type    = number
  default = 30
}

variable "assume_role_services" {
  type    = list(string)
  default = ["ecs-tasks.amazonaws.com"]
}

variable "tags" {
  type    = map(string)
  default = {}
}
