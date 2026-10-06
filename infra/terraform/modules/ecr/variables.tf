variable "prefix" {
  type = string
}

variable "repositories" {
  type = list(string)
}

variable "keep_images" {
  type    = number
  default = 5
}

variable "force_delete" {
  type        = bool
  default     = true
  description = "Let `terraform destroy` remove repositories that still contain images."
}

variable "tags" {
  type    = map(string)
  default = {}
}
