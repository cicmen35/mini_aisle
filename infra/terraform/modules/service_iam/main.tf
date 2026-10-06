# Least-privilege role for one service: it can only consume/publish the queues it needs and
# touch the S3 prefixes it owns. On AWS the role is assumed by ECS tasks (or EKS pods via IRSA);
# on LocalStack the policies exist but community edition doesn't enforce IAM.

locals {
  consume_actions = [
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:ChangeMessageVisibility",
    "sqs:GetQueueAttributes",
    "sqs:GetQueueUrl",
  ]
  publish_actions = ["sqs:SendMessage", "sqs:GetQueueAttributes", "sqs:GetQueueUrl"]
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = var.assume_role_services
    }
  }
}

data "aws_iam_policy_document" "this" {
  dynamic "statement" {
    for_each = length(var.consume_queue_arns) > 0 ? [1] : []
    content {
      sid       = "ConsumeQueues"
      actions   = local.consume_actions
      resources = var.consume_queue_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.publish_queue_arns) > 0 ? [1] : []
    content {
      sid       = "PublishQueues"
      actions   = local.publish_actions
      resources = var.publish_queue_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.read_prefixes) > 0 ? [1] : []
    content {
      sid       = "ReadArtifacts"
      actions   = ["s3:GetObject"]
      resources = [for p in var.read_prefixes : "${var.bucket_arn}/${p}*"]
    }
  }

  dynamic "statement" {
    for_each = length(var.write_prefixes) > 0 ? [1] : []
    content {
      sid       = "WriteArtifacts"
      actions   = ["s3:PutObject"]
      resources = [for p in var.write_prefixes : "${var.bucket_arn}/${p}*"]
    }
  }

  statement {
    sid       = "BucketHealthCheck"
    actions   = ["s3:ListBucket"]
    resources = [var.bucket_arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = concat([""], [for p in concat(var.read_prefixes, var.write_prefixes) : "${p}*"])
    }
  }
}

resource "aws_iam_role" "this" {
  name                 = var.name
  assume_role_policy   = data.aws_iam_policy_document.assume.json
  max_session_duration = 3600
  tags                 = var.tags
}

resource "aws_iam_role_policy" "this" {
  name   = "${var.name}-least-privilege"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.this.json
}
