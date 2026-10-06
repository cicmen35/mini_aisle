#!/bin/sh
# Entrypoint of the `infra` container: terraform against LocalStack only.
#   apply (default) | plan | destroy | output | <any terraform args>
set -eu

: "${TF_VAR_localstack_endpoint:=http://localstack:4566}"
export TF_VAR_localstack_endpoint
STATE_PATH="${TF_STATE_PATH:-/work/terraform.tfstate}"

cd /infra/envs/localstack
terraform init -input=false -no-color -backend-config="path=${STATE_PATH}" >/tmp/init.log 2>&1 \
  || { cat /tmp/init.log; exit 1; }

cmd="${1:-apply}"
[ "$#" -gt 0 ] && shift
case "$cmd" in
  apply)   exec terraform apply -input=false -auto-approve "$@" ;;
  plan)    exec terraform plan -input=false "$@" ;;
  destroy) exec terraform destroy -input=false -auto-approve "$@" ;;
  output)  exec terraform output -json "$@" ;;
  *)       exec terraform "$cmd" "$@" ;;
esac
