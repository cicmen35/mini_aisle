# Account-wide monthly cost budget with e-mail alerts at fixed dollar amounts.
# Account-wide on purpose: it also catches spend from resources that escaped tagging.
# Budget e-mails need no subscription confirmation; the first 2 budgets per account are free.

resource "aws_budgets_budget" "monthly" {
  name         = var.name
  budget_type  = "COST"
  limit_amount = format("%.2f", max(var.alert_thresholds_usd...))
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = toset(var.alert_thresholds_usd)
    content {
      comparison_operator        = "GREATER_THAN"
      notification_type          = "ACTUAL"
      threshold                  = notification.value
      threshold_type             = "ABSOLUTE_VALUE"
      subscriber_email_addresses = [var.alert_email]
    }
  }

  # Early warning: the forecast says we'll cross the top threshold this month.
  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = max(var.alert_thresholds_usd...)
    threshold_type             = "ABSOLUTE_VALUE"
    subscriber_email_addresses = [var.alert_email]
  }

  tags = var.tags
}

# Cost-allocation tags only show up in Cost Explorer once activated. AWS can only activate a tag
# key after it has seen it on a billed resource (up to 24h after the first apply), so this is
# opt-in: apply once, wait a day, then set activate_cost_allocation_tags = true.
resource "aws_ce_cost_allocation_tag" "this" {
  for_each = var.activate_cost_allocation_tags ? toset(var.cost_allocation_tag_keys) : toset([])
  tag_key  = each.value
  status   = "Active"
}
