#!/usr/bin/env bash
# Bring up the real-AWS demo env (infra/terraform/envs/aws). COSTS MONEY while it runs.
#
#   1. checks you are logged into the account named in terraform.tfvars
#   2. creates the ECR repos, builds + pushes images tagged with the git SHA
#   3. applies the rest, runs DB migrations as a one-off Fargate task
#   4. prints the API URL
#
# Tear down with `make aws-down` as soon as the demo is over.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_DIR="$ROOT/infra/terraform/envs/aws"
TFVARS="$ENV_DIR/terraform.tfvars"
ARCH="${ARCH:-arm64}" # must match var.cpu_architecture (ARM64 default)

die() { echo "error: $*" >&2; exit 1; }
for bin in aws docker terraform git; do command -v "$bin" >/dev/null || die "$bin is required"; done
[[ -f "$TFVARS" ]] || die "missing $TFVARS (cp terraform.tfvars.example terraform.tfvars)"

expected="$(sed -nE 's/^aws_account_id *= *"([0-9]{12})".*/\1/p' "$TFVARS")"
actual="$(aws sts get-caller-identity --query Account --output text)" || die "not logged in (aws sso login / aws configure)"
[[ "$expected" == "$actual" ]] || die "logged into $actual but terraform.tfvars says $expected"
region="$(sed -nE 's/^region *= *"([a-z0-9-]+)".*/\1/p' "$TFVARS")"; region="${region:-eu-central-1}"

cat <<EOF
About to create billable resources in AWS account $actual ($region):
  RDS db.t4g.micro, Fargate tasks (API always on, workers scale 0..N), public IPv4s,
  SQS, S3, ECR, CloudWatch Logs.  Expected: ~\$0.05-0.10 per hour while up.
  Run 'make aws-down' when the demo is over.
EOF
if [[ "${AUTO_APPROVE:-}" != "1" ]]; then
  read -r -p "Type 'yes' to continue: " answer
  [[ "$answer" == "yes" ]] || die "aborted"
fi

cd "$ENV_DIR"
terraform init -input=false >/dev/null

tag="$(git -C "$ROOT" rev-parse --short=12 HEAD)"
[[ -z "$(git -C "$ROOT" status --porcelain)" ]] || tag="${tag}-dirty-$(date +%s)"

echo "==> ECR repositories"
terraform apply -input=false -auto-approve -target=module.ecr

registry="$actual.dkr.ecr.$region.amazonaws.com"
aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin "$registry"

echo "==> Building and pushing images ($tag, linux/$ARCH)"
for svc in api scanner fixer verifier; do
  docker buildx build --platform "linux/$ARCH" -f "$ROOT/docker/Dockerfile" \
    --target "$svc" --build-arg SERVICE="$svc" \
    -t "$registry/patchloop/$svc:$tag" --push "$ROOT"
done

echo "==> Applying the environment"
terraform apply -input=false -auto-approve -var "image_tag=$tag"

cluster="$(terraform output -raw cluster_name)"
taskdef="$(terraform output -raw api_task_definition_arn)"
subnets="$(terraform output -json subnet_ids | tr -d '[]" ')"
sg="$(terraform output -raw api_security_group_id)"

echo "==> Running migrations (one-off task)"
task_arn="$(aws ecs run-task --region "$region" --cluster "$cluster" --launch-type FARGATE \
  --task-definition "$taskdef" \
  --network-configuration "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$sg],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"patchloop-api","command":["patchloop-migrate"]}]}' \
  --query 'tasks[0].taskArn' --output text)"
aws ecs wait tasks-stopped --region "$region" --cluster "$cluster" --tasks "$task_arn"
code="$(aws ecs describe-tasks --region "$region" --cluster "$cluster" --tasks "$task_arn" \
  --query 'tasks[0].containers[0].exitCode' --output text)"
[[ "$code" == "0" ]] || die "migration task exited with $code (see CloudWatch log group /ecs/patchloop-api)"

echo "==> Waiting for the API service to become stable"
aws ecs wait services-stable --region "$region" --cluster "$cluster" --services patchloop-api
api_task="$(aws ecs list-tasks --region "$region" --cluster "$cluster" --service-name patchloop-api \
  --query 'taskArns[0]' --output text)"
eni="$(aws ecs describe-tasks --region "$region" --cluster "$cluster" --tasks "$api_task" \
  --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text)"
ip="$(aws ec2 describe-network-interfaces --region "$region" --network-interface-ids "$eni" \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text)"

cat <<EOF

patchloop is up:  http://$ip:8000/docs   (health: http://$ip:8000/readyz)
Workers scale from 0 when their queue has messages (cold start ~1-3 min).

REMEMBER: make aws-down   when you're done.
EOF
