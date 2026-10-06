output "name" {
  value = aws_sqs_queue.this.name
}

output "url" {
  value = aws_sqs_queue.this.url
}

output "arn" {
  value = aws_sqs_queue.this.arn
}

output "dlq_name" {
  value = aws_sqs_queue.dlq.name
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}
