SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

UV        ?= uv
COMPOSE   ?= docker compose
SERVICES  := api scanner fixer verifier
TAG       ?= local

##@ Setup
.PHONY: help install
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2} /^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)}' $(MAKEFILE_LIST)

install: ## Install Python deps + pre-commit hooks
	$(UV) sync
	$(UV) run pre-commit install
	@test -f .env || cp .env.example .env

##@ Quality
.PHONY: fmt lint typecheck test todo test-integration test-e2e
fmt: ## Format code (ruff + terraform)
	$(UV) run ruff format .
	$(UV) run ruff check --fix .
	scripts/tf.sh fmt -recursive

lint: ## Ruff lint + format check
	$(UV) run ruff check .
	$(UV) run ruff format --check .

typecheck: ## mypy --strict
	$(UV) run mypy

test: ## Unit tests (TODO(simon) tests xfail until implemented)
	$(UV) run pytest

todo: ## List every TODO(simon) and the tests waiting for it
	@grep -rn --include='*.py' 'TODO(simon)' packages services | sed 's/^/  /'
	@$(UV) run pytest -q -rx -m "todo or not todo" tests/unit 2>/dev/null | grep -E '^XFAIL' | sed 's/ - TODO.*//' || true

test-integration: ## Integration tests against compose deps (run `make deps-up` first)
	$(UV) run pytest -m integration tests/integration

test-e2e: ## End-to-end tests against the full stack (run `make up` first)
	$(UV) run pytest -m e2e tests/e2e

##@ Local stack (docker compose + LocalStack)
.PHONY: up down deps-up deps-down logs ps migrate db-revision demo-tarball
.env:
	cp .env.example .env

up: .env ## Build and start everything (API on http://localhost:8420/docs)
	$(COMPOSE) up -d --build --wait api scanner fixer verifier
	@echo "API: http://localhost:$${API_PORT:-8420}/docs"

down: ## Stop the stack and delete volumes (LocalStack is ephemeral anyway)
	$(COMPOSE) --profile ollama down -v --remove-orphans

deps-up: .env ## Only Postgres + LocalStack (+ terraform apply + migrations)
	$(COMPOSE) up -d --wait postgres localstack
	$(COMPOSE) up --build --exit-code-from infra infra
	$(COMPOSE) up --build --exit-code-from migrate migrate

deps-down: ## Stop deps
	$(COMPOSE) down -v --remove-orphans

logs: ## Tail service logs
	$(COMPOSE) logs -f --tail=100 api scanner fixer verifier

ps: ## Show containers
	$(COMPOSE) ps -a

migrate: ## Run alembic upgrade head in the stack
	$(COMPOSE) run --rm migrate

db-revision: ## New Alembic revision from models: make db-revision m="create core tables"
	@test -n "$(m)" || (echo 'usage: make db-revision m="message"' && exit 1)
	set -a; source .env; set +a; $(UV) run alembic revision --autogenerate -m "$(m)"

demo-tarball: ## Pack the demo target for POST /v1/jobs/upload
	mkdir -p build
	tar -C demo-targets/vulnerable-app --exclude=__pycache__ -czf build/vulnerable-app.tar.gz .
	@echo "curl -F file=@build/vulnerable-app.tar.gz;type=application/gzip localhost:8420/v1/jobs/upload"

##@ Terraform (LocalStack only - runs in the `infra` container)
.PHONY: tf-plan tf-apply tf-destroy tf-output tf-check
tf-plan: ## terraform plan against LocalStack
	$(COMPOSE) run --rm --build infra plan

tf-apply: ## terraform apply against LocalStack
	$(COMPOSE) run --rm --build infra apply

tf-destroy: ## terraform destroy against LocalStack
	$(COMPOSE) run --rm --build infra destroy

tf-output: ## terraform outputs (JSON)
	$(COMPOSE) run --rm --build infra output

tf-check: ## fmt + validate + tflint + checkov on every env and module (no credentials)
	scripts/tf-check.sh

##@ Images & security
.PHONY: images security
images: ## Build all service images (TAG=local)
	@for s in $(SERVICES); do \
	  echo "==> patchloop-$$s:$(TAG)"; \
	  docker build -q -f docker/Dockerfile --target $$s --build-arg SERVICE=$$s -t patchloop-$$s:$(TAG) . ; \
	done
	docker build -q -f docker/terraform.Dockerfile -t patchloop-infra:$(TAG) .

security: ## Bandit + Semgrep + pip-audit + Trivy (fs, config, images) on this repo
	scripts/security.sh

##@ Kubernetes (kind)
.PHONY: kind-up kind-down
kind-up: ## Create a kind cluster, load images, deploy (KEDA=0 to skip KEDA)
	scripts/kind-up.sh

kind-down: ## Delete the kind cluster
	kind delete cluster --name patchloop

##@ Real AWS (costs money - see README "Real AWS demo")
.PHONY: aws-budget aws-up aws-down aws-check
aws-budget: ## One-time: budget alerts ($$10/$$25/$$50) - kept permanently
	cd infra/terraform/envs/aws-account && terraform init -input=false && terraform apply

aws-up: ## Build/push images to ECR and apply envs/aws (asks for confirmation)
	scripts/aws-up.sh

aws-down: ## Destroy envs/aws and check for leftovers
	scripts/aws-down.sh

aws-check: tf-check ## Credential-free checks for the AWS env (alias of tf-check)

##@ CI
.PHONY: ci clean
ci: ## Everything GitHub Actions runs, locally
	scripts/ci.sh

clean: ## Remove caches and build output
	rm -rf build .mypy_cache .ruff_cache .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
