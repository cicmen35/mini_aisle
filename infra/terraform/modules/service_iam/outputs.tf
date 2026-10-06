output "role_arn" {
  value = aws_iam_role.this.arn
}

output "role_name" {
  value = aws_iam_role.this.name
}

output "policy_json" {
  value = data.aws_iam_policy_document.this.json
}
