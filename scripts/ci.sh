#!/usr/bin/env bash
# Local mirror of .github/workflows/ci.yml (the repo is hosted on Cursor Origin, without Actions).
# Integration tests use a separate compose project on separate ports, so a running `make up`
# dev stack is left alone.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
UV="${UV:-uv}"

export COMPOSE_PROJECT_NAME=patchloop-ci
export POSTGRES_PORT="${CI_POSTGRES_PORT:-25432}" LOCALSTACK_PORT="${CI_LOCALSTACK_PORT:-24566}"
export API_PORT=28420 OLLAMA_PORT=21434

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
started=$(date +%s)

step "lint";      make lint
step "typecheck"; make typecheck
step "unit tests"; make test

step "terraform static checks (no credentials)"
make tf-check

step "kubernetes manifests render"
for overlay in deploy/k8s/overlays/*/; do
  kubectl kustomize "$overlay" >/dev/null && echo "ok: $overlay"
done

step "docker build"
make images TAG=ci

step "integration tests (compose: postgres + localstack + terraform + migrations)"
cleanup() { docker compose down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT
[[ -f .env ]] || cp .env.example .env
docker compose up -d --wait postgres localstack
docker compose up --build --exit-code-from infra infra
docker compose up --build --exit-code-from migrate migrate
PATCHLOOP_DATABASE_URL="postgresql+psycopg://patchloop:patchloop@localhost:${POSTGRES_PORT}/patchloop" \
PATCHLOOP_AWS_ENDPOINT_URL="http://localhost:${LOCALSTACK_PORT}" \
  "$UV" run pytest -m integration tests/integration
cleanup
trap - EXIT

step "security: bandit, semgrep, pip-audit, trivy (fs + images)"
mkdir -p build
TAG=ci scripts/security.sh

printf '\n\033[1;32mci: all green in %ss\033[0m\n' "$(( $(date +%s) - started ))"
