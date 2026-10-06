variable "name" {
  type = string
}

variable "alert_email" {
  type = string
  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be an e-mail address."
  }
}

variable "alert_thresholds_usd" {
  type    = list(number)
  default = [10, 25, 50]
}

variable "activate_cost_allocation_tags" {
  type    = bool
  default = false
}

variable "cost_allocation_tag_keys" {
  type    = list(string)
  default = ["Project", "Environment", "Owner"]
}

variable "tags" {
  type    = map(string)
  default = {}
}
