variable "name" {
  type = string
}

variable "force_destroy" {
  type        = bool
  default     = false
  description = "Allow `terraform destroy` to delete a non-empty bucket (true for demo envs)."
}

variable "expire_after_days" {
  type    = number
  default = 30
}

variable "enforce_tls" {
  type        = bool
  default     = true
  description = "Attach a deny-non-TLS bucket policy. Off for LocalStack, which serves plain HTTP."
}

variable "tags" {
  type    = map(string)
  default = {}
}
