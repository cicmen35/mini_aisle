variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "client_security_group_ids" {
  type        = list(string)
  description = "Security groups allowed to connect on 5432."
}

variable "instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "engine_version" {
  type    = string
  default = "16"
}

variable "db_name" {
  type    = string
  default = "patchloop"
}

variable "username" {
  type    = string
  default = "patchloop"
}

variable "tags" {
  type    = map(string)
  default = {}
}
