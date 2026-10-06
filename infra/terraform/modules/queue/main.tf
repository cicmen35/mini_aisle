# A work queue plus its dead-letter queue.
# After `max_receive_count` failed deliveries SQS moves a message to the DLQ (redrive policy),
# so one poison message can't block or crash-loop the consumers.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

locals {
  # Built by hand to avoid a queue <-> DLQ dependency cycle (and the separate
  # aws_sqs_queue_redrive_allow_policy resource, whose propagation waiter hangs on LocalStack).
  source_queue_arn = "arn:${data.aws_partition.current.partition}:sqs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:${var.name}"
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-dlq"
  message_retention_seconds = 1209600 # 14 days: time to inspect and redrive by hand
  sqs_managed_sse_enabled   = true

  # Only the work queue may use this DLQ as its dead-letter target.
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [local.source_queue_arn]
  })

  tags = var.tags
}

resource "aws_sqs_queue" "this" {
  name                       = var.name
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  receive_wait_time_seconds  = 20 # long polling: fewer empty receives, lower cost
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = var.tags
}
