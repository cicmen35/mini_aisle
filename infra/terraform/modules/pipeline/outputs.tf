output "queues" {
  description = "Per queue key (scan/fix/verify): name, url, arn and the DLQ equivalents."
  value = {
    for k, q in module.queue : k => {
      name     = q.name
      url      = q.url
      arn      = q.arn
      dlq_name = q.dlq_name
      dlq_url  = q.dlq_url
      dlq_arn  = q.dlq_arn
    }
  }
}

output "bucket_name" {
  value = module.artifacts.name
}

output "bucket_arn" {
  value = module.artifacts.arn
}

output "service_role_arns" {
  value = { for k, r in module.service_iam : k => r.role_arn }
}
