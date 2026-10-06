output "region" {
  value = var.region
}

output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}

output "service_names" {
  value = { for k, s in module.service : k => s.service_name }
}

output "api_task_definition_arn" {
  description = "Used by scripts/aws-up.sh to run the one-off migration task."
  value       = module.service["api"].task_definition_arn
}

output "subnet_ids" {
  value = module.network.public_subnet_ids
}

output "api_security_group_id" {
  value = aws_security_group.api.id
}

output "queues" {
  value = module.pipeline.queues
}

output "bucket_name" {
  value = module.pipeline.bucket_name
}
