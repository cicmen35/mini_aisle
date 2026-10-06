output "queues" {
  value = module.pipeline.queues
}

output "bucket_name" {
  value = module.pipeline.bucket_name
}

output "service_role_arns" {
  value = module.pipeline.service_role_arns
}
