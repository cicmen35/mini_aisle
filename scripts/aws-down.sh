#!/usr/bin/env bash
# Destroy the real-AWS demo env and check that nothing tagged Project=patchloop is left behind.
# The budget in envs/aws-account is intentionally NOT destroyed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_DIR="$ROOT/infra/terraform/envs/aws"
TFVARS="$ENV_DIR/terraform.tfvars"

die() { echo "error: $*" >&2; exit 1; }
[[ -f "$TFVARS" ]] || die "missing $TFVARS"
expected="$(sed -nE 's/^aws_account_id *= *"([0-9]{12})".*/\1/p' "$TFVARS")"
actual="$(aws sts get-caller-identity --query Account --output text)" || die "not logged in"
[[ "$expected" == "$actual" ]] || die "logged into $actual but terraform.tfvars says $expected"
region="$(sed -nE 's/^region *= *"([a-z0-9-]+)".*/\1/p' "$TFVARS")"; region="${region:-eu-central-1}"

cd "$ENV_DIR"
terraform init -input=false >/dev/null
terraform destroy -input=false -auto-approve

echo "==> Checking for leftovers tagged Project=patchloop, Environment=aws-demo"
left="$(aws resourcegroupstaggingapi get-resources --region "$region" \
  --tag-filters Key=Project,Values=patchloop Key=Environment,Values=aws-demo \
  --query 'ResourceTagMappingList[].ResourceARN' --output text | tr '\t' '\n' \
  | grep -v ':task-definition/' || true)" # INACTIVE task definitions linger but cost nothing
if [[ -n "$left" ]]; then
  echo "Still present (the tagging API can lag a few minutes; re-run to confirm):"
  echo "$left"
  exit 1
fi
echo "All demo resources are gone. The budget alerts (envs/aws-account) stay in place."
