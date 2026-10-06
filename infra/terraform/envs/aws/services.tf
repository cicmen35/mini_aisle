locals {
  common_env = {
    PATCHLOOP_ENV               = "aws"
    PATCHLOOP_AWS_REGION        = var.region
    PATCHLOOP_SCAN_QUEUE_NAME   = module.pipeline.queues["scan"].name
    PATCHLOOP_FIX_QUEUE_NAME    = module.pipeline.queues["fix"].name
    PATCHLOOP_VERIFY_QUEUE_NAME = module.pipeline.queues["verify"].name
    PATCHLOOP_ARTIFACTS_BUCKET  = module.pipeline.bucket_name
    PATCHLOOP_LOG_JSON          = "true"
  }
  common_secrets = {
    PATCHLOOP_DATABASE_URL = module.database.database_url_parameter_arn
  }

  service_config = {
    api = {
      cpu = 256, memory = 512, desired = var.api_desired_count, port = 8000
      sg  = aws_security_group.api.id, queue = null, env = {}, secrets = {}
    }
    scanner = {
      cpu = 512, memory = 1024, desired = 0, port = null
      sg  = aws_security_group.workers.id, queue = "scan", env = {}, secrets = {}
    }
    fixer = {
      cpu = 256, memory = 512, desired = 0, port = null
      sg  = aws_security_group.workers.id, queue = "fix"
      env = {
        PATCHLOOP_LLM_PROVIDER    = var.llm_provider
        PATCHLOOP_OPENAI_BASE_URL = var.openai_base_url
        PATCHLOOP_OPENAI_MODEL    = var.openai_model
      }
      secrets = var.llm_provider == "openai" ? { PATCHLOOP_OPENAI_API_KEY = aws_ssm_parameter.openai_api_key[0].arn } : {}
    }
    verifier = {
      cpu = 512, memory = 1024, desired = 0, port = null
      sg  = aws_security_group.workers.id, queue = "verify", env = {}, secrets = {}
    }
  }
}

module "service" {
  source   = "../../modules/ecs_service"
  for_each = local.service_config

  name               = "${local.name}-${each.key}"
  cluster_arn        = aws_ecs_cluster.this.arn
  cluster_name       = aws_ecs_cluster.this.name
  image              = "${module.ecr.repository_urls[each.key]}:${var.image_tag}"
  cpu                = each.value.cpu
  memory             = each.value.memory
  cpu_architecture   = var.cpu_architecture
  desired_count      = each.value.desired
  container_port     = each.value.port
  environment        = merge(local.common_env, each.value.env)
  secrets            = merge(local.common_secrets, each.value.secrets)
  task_role_arn      = module.pipeline.service_role_arns[each.key]
  execution_role_arn = aws_iam_role.execution.arn
  subnet_ids         = module.network.public_subnet_ids
  security_group_ids = [each.value.sg]
  assign_public_ip   = true
  log_retention_days = var.log_retention_days

  scale_on_queue = each.value.queue == null ? null : {
    queue_name = module.pipeline.queues[each.value.queue].name
    max_tasks  = var.worker_max_tasks
  }
}
