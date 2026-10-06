#!/usr/bin/env bash
# Run terraform from infra/terraform: the local binary if installed, else the pinned Docker image.
#   scripts/tf.sh fmt -recursive
#   scripts/tf.sh -chdir=envs/aws validate
set -euo pipefail
TF_VERSION="${TF_VERSION:-1.9.8}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/infra/terraform"
if command -v terraform >/dev/null 2>&1; then
  exec terraform "$@"
fi
exec docker run --rm -u "$(id -u):$(id -g)" -e TF_IN_AUTOMATION=1 \
  -v "$PWD:/tf" -w /tf "hashicorp/terraform:${TF_VERSION}" "$@"
