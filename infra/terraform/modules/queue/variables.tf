variable "name" {
  type        = string
  description = "Queue name; the DLQ is named <name>-dlq."
}

variable "visibility_timeout_seconds" {
  type        = number
  default     = 120
  description = "Must exceed the worst-case processing time of one message."
}

variable "message_retention_seconds" {
  type    = number
  default = 345600 # 4 days
}

variable "max_receive_count" {
  type        = number
  default     = 5
  description = "Deliveries before a message is moved to the DLQ."
  validation {
    condition     = var.max_receive_count >= 1 && var.max_receive_count <= 1000
    error_message = "max_receive_count must be between 1 and 1000."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
