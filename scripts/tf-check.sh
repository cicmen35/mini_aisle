#!/usr/bin/env bash
# Static Terraform checks for every env and module. Needs NO cloud credentials and never plans
# or applies, so it is safe for CI and for the real-AWS env.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="$ROOT/scripts/tf.sh"
TFLINT_IMAGE="${TFLINT_IMAGE:-ghcr.io/terraform-linters/tflint:v0.55.1}"
CHECKOV_IMAGE="${CHECKOV_IMAGE:-bridgecrew/checkov:3.2.500}"

echo "==> terraform fmt -check"
"$TF" fmt -check -recursive

for env in localstack aws aws-account; do
  echo "==> terraform validate envs/$env"
  "$TF" -chdir="envs/$env" init -backend=false -input=false >/dev/null
  "$TF" -chdir="envs/$env" validate -no-color
done

echo "==> tflint"
cd "$ROOT/infra/terraform"
tflint() {
  docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/data" -w /data \
    -e TFLINT_PLUGIN_DIR=/data/.tflint.d -e GITHUB_TOKEN="${GITHUB_TOKEN:-}" "$TFLINT_IMAGE" "$@"
}
tflint --init --config=/data/.tflint.hcl >/dev/null
for dir in envs/* modules/*; do
  tflint --chdir="$dir" --config=/data/.tflint.hcl -f compact
done

echo "==> checkov"
docker run --rm -v "$PWD:/tf" -w /tf "$CHECKOV_IMAGE" -d /tf --config-file /tf/.checkov.yaml
