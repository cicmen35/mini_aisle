variable "name" {
  type        = string
  description = "Role name, e.g. patchloop-scanner."
}

variable "assume_role_services" {
  type        = list(string)
  default     = ["ecs-tasks.amazonaws.com"]
  description = "AWS service principals allowed to assume the role."
}

variable "consume_queue_arns" {
  type    = list(string)
  default = []
}

variable "publish_queue_arns" {
  type    = list(string)
  default = []
}

variable "bucket_arn" {
  type = string
}

variable "read_prefixes" {
  type        = list(string)
  default     = []
  description = "S3 key prefixes (e.g. \"snapshots/\") the service may read."
}

variable "write_prefixes" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
