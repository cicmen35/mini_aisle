# The messaging + storage backbone shared by every environment:
# 3 work queues (each with a DLQ), the artifacts bucket and one least-privilege role per service.

locals {
  queues = {
    scan   = { visibility = var.scan_visibility_timeout_seconds }
    fix    = { visibility = var.fix_visibility_timeout_seconds }
    verify = { visibility = var.verify_visibility_timeout_seconds }
  }
}

module "queue" {
  source   = "../queue"
  for_each = local.queues

  name                       = "${var.prefix}-${each.key}-requests"
  visibility_timeout_seconds = each.value.visibility
  max_receive_count          = var.max_receive_count
  tags                       = var.tags
}

module "artifacts" {
  source = "../bucket"

  name              = var.bucket_name
  force_destroy     = var.force_destroy_bucket
  expire_after_days = var.artifact_retention_days
  tags              = var.tags
}

locals {
  services = {
    api = {
      consume = []
      publish = [module.queue["scan"].arn]
      read    = ["patches/", "reports/"]
      write   = ["uploads/"]
    }
    scanner = {
      consume = [module.queue["scan"].arn]
      publish = [module.queue["fix"].arn]
      read    = ["uploads/"]
      write   = ["snapshots/", "reports/"]
    }
    fixer = {
      consume = [module.queue["fix"].arn]
      publish = [module.queue["verify"].arn]
      read    = ["snapshots/"]
      write   = ["patches/"]
    }
    verifier = {
      consume = [module.queue["verify"].arn]
      publish = []
      read    = ["snapshots/", "patches/"]
      write   = ["verifications/"]
    }
  }
}

module "service_iam" {
  source   = "../service_iam"
  for_each = local.services

  name                 = "${var.prefix}-${each.key}"
  assume_role_services = var.assume_role_services
  consume_queue_arns   = each.value.consume
  publish_queue_arns   = each.value.publish
  bucket_arn           = module.artifacts.arn
  read_prefixes        = each.value.read
  write_prefixes       = each.value.write
  tags                 = var.tags
}
