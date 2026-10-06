# Task *execution* role: what ECS itself needs to start a task (pull from ECR, write logs, read
# the secrets it injects). The per-service *task* roles (what the code may do) come from the
# pipeline module.

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid       = "EcrAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"] # this API has no resource-level permissions
  }
  statement {
    sid       = "EcrPull"
    actions   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
    resources = module.ecr.repository_arns
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [for s in module.service : "arn:aws:logs:${var.region}:${var.aws_account_id}:log-group:${s.log_group_name}:*"]
  }
  statement {
    sid     = "InjectSecrets"
    actions = ["ssm:GetParameters"]
    resources = compact([
      module.database.database_url_parameter_arn,
      var.llm_provider == "openai" ? aws_ssm_parameter.openai_api_key[0].arn : "",
    ])
  }
}

resource "aws_iam_role_policy" "execution" {
  name   = "${local.name}-ecs-execution"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution.json
}

# The key itself is never in Terraform: apply creates a placeholder, then
#   aws ssm put-parameter --name /patchloop/openai_api_key --type SecureString --overwrite --value sk-...
resource "aws_ssm_parameter" "openai_api_key" {
  count       = var.llm_provider == "openai" ? 1 : 0
  name        = "/${local.name}/openai_api_key"
  description = "Hosted LLM API key for the fixer (set out of band)"
  type        = "SecureString"
  value       = "set-me-with-aws-ssm-put-parameter"
  lifecycle {
    ignore_changes = [value]
  }
}
