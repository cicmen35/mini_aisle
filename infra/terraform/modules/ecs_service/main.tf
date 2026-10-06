# One Fargate service: log group, task definition, service and (optionally) scale-from-zero on
# SQS queue depth. Hardened container: non-root, read-only rootfs (+ ephemeral /tmp), no Linux
# capabilities, init process for signal forwarding (graceful SIGTERM shutdown).

data "aws_region" "current" {}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${var.name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

locals {
  container_base = {
    name                   = var.name
    image                  = var.image
    essential              = true
    user                   = "10001:10001"
    readonlyRootFilesystem = true
    environment            = [for k, v in var.environment : { name = k, value = v }]
    secrets                = [for k, arn in var.secrets : { name = k, valueFrom = arn }]
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
    linuxParameters = {
      initProcessEnabled = true
      capabilities       = { drop = ["ALL"] }
    }
    stopTimeout = 30
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.this.name
        awslogs-region        = data.aws_region.current.region
        awslogs-stream-prefix = var.name
      }
    }
  }

  # Optional parts as zero-or-one element lists (conditional objects must share a type).
  container_command = [for c in(var.command == null ? [] : [var.command]) : { command = c }]
  container_port = [for p in(var.container_port == null ? [] : [var.container_port]) : {
    portMappings = [{ containerPort = p, protocol = "tcp" }]
    healthCheck = {
      command     = ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:${p}/healthz', timeout=2).status == 200 else 1)"]
      interval    = 15
      timeout     = 5
      retries     = 3
      startPeriod = 20
    }
  }]

  container = merge(concat([local.container_base], local.container_command, local.container_port)...)
}

resource "aws_ecs_task_definition" "this" {
  family                   = var.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn
  container_definitions    = jsonencode([local.container])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = var.cpu_architecture
  }

  volume {
    name = "tmp"
  }

  ephemeral_storage {
    size_in_gib = 21
  }

  tags = var.tags
}

resource "aws_ecs_service" "this" {
  name                   = var.name
  cluster                = var.cluster_arn
  task_definition        = aws_ecs_task_definition.this.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = false
  propagate_tags         = "SERVICE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = var.assign_public_ip
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # Autoscaling owns desired_count once enabled.
  lifecycle {
    ignore_changes = [desired_count]
  }

  tags = var.tags
}

# ---------------------------------------------------------------- scale 0..N on queue depth
# CloudWatch publishes SQS metrics every minute (with some delay), so a cold start after an
# idle period takes ~1-3 minutes. That's the price of paying nothing while idle.

locals {
  autoscale = var.scale_on_queue != null
}

resource "aws_appautoscaling_target" "this" {
  count              = local.autoscale ? 1 : 0
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${var.cluster_name}/${aws_ecs_service.this.name}"
  min_capacity       = 0
  max_capacity       = var.scale_on_queue.max_tasks
}

resource "aws_appautoscaling_policy" "scale_out" {
  count              = local.autoscale ? 1 : 0
  name               = "${var.name}-scale-out"
  service_namespace  = aws_appautoscaling_target.this[0].service_namespace
  scalable_dimension = aws_appautoscaling_target.this[0].scalable_dimension
  resource_id        = aws_appautoscaling_target.this[0].resource_id
  policy_type        = "StepScaling"

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 60
    metric_aggregation_type = "Maximum"

    step_adjustment {
      metric_interval_lower_bound = 0
      metric_interval_upper_bound = var.scale_on_queue.messages_per_task
      scaling_adjustment          = 1
    }
    step_adjustment {
      metric_interval_lower_bound = var.scale_on_queue.messages_per_task
      scaling_adjustment          = var.scale_on_queue.max_tasks
    }
  }
}

resource "aws_appautoscaling_policy" "scale_in" {
  count              = local.autoscale ? 1 : 0
  name               = "${var.name}-scale-to-zero"
  service_namespace  = aws_appautoscaling_target.this[0].service_namespace
  scalable_dimension = aws_appautoscaling_target.this[0].scalable_dimension
  resource_id        = aws_appautoscaling_target.this[0].resource_id
  policy_type        = "StepScaling"

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 300
    metric_aggregation_type = "Maximum"

    step_adjustment {
      metric_interval_upper_bound = 0
      scaling_adjustment          = 0
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "backlog" {
  count               = local.autoscale ? 1 : 0
  alarm_name          = "${var.name}-backlog"
  alarm_description   = "Messages waiting in ${var.scale_on_queue.queue_name}: scale ${var.name} out"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = var.scale_on_queue.queue_name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_appautoscaling_policy.scale_out[0].arn]
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "idle" {
  count               = local.autoscale ? 1 : 0
  alarm_name          = "${var.name}-idle"
  alarm_description   = "Queue ${var.scale_on_queue.queue_name} empty (visible + in flight): scale ${var.name} to zero"
  evaluation_periods  = var.scale_on_queue.idle_minutes
  comparison_operator = "LessThanOrEqualToThreshold"
  threshold           = 0
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_appautoscaling_policy.scale_in[0].arn]

  metric_query {
    id          = "backlog"
    expression  = "visible + inflight"
    label       = "Total messages"
    return_data = true
  }
  metric_query {
    id = "visible"
    metric {
      namespace   = "AWS/SQS"
      metric_name = "ApproximateNumberOfMessagesVisible"
      dimensions  = { QueueName = var.scale_on_queue.queue_name }
      stat        = "Maximum"
      period      = 60
    }
  }
  metric_query {
    id = "inflight"
    metric {
      namespace   = "AWS/SQS"
      metric_name = "ApproximateNumberOfMessagesNotVisible"
      dimensions  = { QueueName = var.scale_on_queue.queue_name }
      stat        = "Maximum"
      period      = 60
    }
  }
  tags = var.tags
}
