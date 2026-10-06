output "address" {
  value = aws_db_instance.this.address
}

output "security_group_id" {
  value = aws_security_group.db.id
}

output "database_url_parameter_arn" {
  value = aws_ssm_parameter.database_url.arn
}
