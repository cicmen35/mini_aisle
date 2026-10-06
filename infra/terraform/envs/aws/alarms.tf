# Anything landing in a DLQ is a bug or a poison message: e-mail about it.
# SNS e-mail subscriptions must be confirmed once from the inbox.

resource "aws_sns_topic" "alerts" {
  name              = "${local.name}-alerts"
  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  for_each            = module.pipeline.queues
  alarm_name          = "${each.value.dlq_name}-not-empty"
  alarm_description   = "Messages in ${each.value.dlq_name}: inspect, fix, then redrive."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = each.value.dlq_name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
