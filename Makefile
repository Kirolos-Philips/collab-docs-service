# Collaborative Document Editor - Makefile
# Default: local | Switch with: ENV=prod

.PHONY: help up down build logs debug shell lint format test clean ps restart

#------------------------------------------------------------------------------
# Environment Configuration (calculated once)
#------------------------------------------------------------------------------
ENV ?= local
REPLICAS ?= 2

ifeq ($(ENV),prod)
    STACK_NAME := collab-editor
    DOCKERFILE := infrastructure/prod/Dockerfile
    # Production uses docker stack commands
    CMD_UP = docker stack deploy -c infrastructure/prod/docker-stack.yml $(STACK_NAME)
    CMD_DOWN = docker stack rm $(STACK_NAME)
    CMD_BUILD = docker build -f $(DOCKERFILE) -t $(STACK_NAME):latest .
    CMD_LOGS = docker service logs -f $(STACK_NAME)_app
    CMD_PS = docker stack services $(STACK_NAME)
    CMD_RESTART = docker service update --force $(STACK_NAME)_app
    # Use head -n 1 to handle scaled services (multiple containers)
    CMD_SHELL = docker exec -it $$(docker ps -q -f name=$(STACK_NAME)_app | head -n 1) /bin/bash
    CMD_SHELL_MONGO = docker exec -it $$(docker ps -q -f name=$(STACK_NAME)_mongo | head -n 1) mongosh
    CMD_SHELL_REDIS = docker exec -it $$(docker ps -q -f name=$(STACK_NAME)_redis | head -n 1) redis-cli
    IS_LOCAL := false
else
    COMPOSE := docker compose -f infrastructure/local/docker-compose.yml
    COMPOSE_DEBUG := $(COMPOSE) -f infrastructure/local/docker-compose.debug.yml
    DOCKERFILE := infrastructure/local/Dockerfile.dev
    # Local uses docker compose commands
    CMD_UP = $(COMPOSE) up -d
    CMD_DOWN = $(COMPOSE) down
    CMD_BUILD = $(COMPOSE) build
    CMD_LOGS = $(COMPOSE) logs -f
    CMD_PS = $(COMPOSE) ps
    CMD_RESTART = $(COMPOSE) restart
    CMD_SHELL = $(COMPOSE) exec app /bin/bash
    CMD_SHELL_MONGO = $(COMPOSE) exec mongo mongosh
    CMD_SHELL_REDIS = $(COMPOSE) exec redis redis-cli
    IS_LOCAL := true
endif

# Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m

#------------------------------------------------------------------------------
# Help
#------------------------------------------------------------------------------
help: ## Show help
	@echo "$(BLUE)Collaborative Document Editor$(NC) [ENV=$(ENV)]"
	@echo ""
	@echo "Usage: make [command] [ENV=prod]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-12s$(NC) %s\n", $$1, $$2}'

#------------------------------------------------------------------------------
# Docker Commands
#------------------------------------------------------------------------------
up: ## Start services
	@echo "$(GREEN)Starting $(ENV)...$(NC)"
	@$(CMD_UP)

down: ## Stop services
	@echo "$(YELLOW)Stopping $(ENV)...$(NC)"
	@$(CMD_DOWN)

build: ## Build images
	@echo "$(GREEN)Building $(ENV)...$(NC)"
	@$(CMD_BUILD)

rebuild: build up ## Rebuild and start

logs: ## View logs (follow)
	@$(CMD_LOGS)

logs-app: ## View app logs only
	@$(CMD_LOGS)

ps: ## List services
	@$(CMD_PS)

restart: ## Restart services
	@$(CMD_RESTART)

shell: ## Shell into app container
	@$(CMD_SHELL)

shell-mongo: ## MongoDB shell
	@$(CMD_SHELL_MONGO)

shell-redis: ## Redis CLI
	@$(CMD_SHELL_REDIS)

#------------------------------------------------------------------------------
# Local Only
#------------------------------------------------------------------------------
debug: ## Start with debugpy (local only)
ifeq ($(IS_LOCAL),true)
	@echo "$(GREEN)Starting debugpy on :5678...$(NC)"
	@$(COMPOSE_DEBUG) up -d
	@echo "$(YELLOW)Attach VS Code debugger...$(NC)"
else
	@echo "$(RED)Error: debug only available locally$(NC)"
	@exit 1
endif

debug-down: ## Stop debug mode
ifeq ($(IS_LOCAL),true)
	@$(COMPOSE_DEBUG) down
else
	@echo "$(RED)Error: debug-down only available locally$(NC)"
endif

#------------------------------------------------------------------------------
# Prod Only
#------------------------------------------------------------------------------
scale: ## Scale replicas (ENV=prod REPLICAS=N)
ifeq ($(IS_LOCAL),false)
	@echo "$(GREEN)Scaling to $(REPLICAS) replicas...$(NC)"
	docker service scale $(STACK_NAME)_app=$(REPLICAS)
else
	@echo "$(RED)Error: scale only available in prod$(NC)"
	@echo "$(YELLOW)Usage: make scale ENV=prod REPLICAS=3$(NC)"
	@exit 1
endif

rollback: ## Rollback app (prod only)
ifeq ($(IS_LOCAL),false)
	@echo "$(YELLOW)Rolling back...$(NC)"
	docker service rollback $(STACK_NAME)_app
else
	@echo "$(RED)Error: rollback only available in prod$(NC)"
	@exit 1
endif

#------------------------------------------------------------------------------
# Code Quality (runs locally with uv)
#------------------------------------------------------------------------------
lint: ## Run linter
	@uv run ruff check src tests

lint-fix: ## Fix lint errors
	@uv run ruff check src tests --fix

format: ## Format code
	@uv run ruff format src tests

test: ## Run tests
	@uv run pytest

test-cov: ## Tests with coverage
	@uv run pytest --cov=src --cov-report=html

# Run lint/test inside container (ensures matching environment)
lint-docker: ## Run linter in container
ifeq ($(IS_LOCAL),true)
	@$(COMPOSE) exec app uv run ruff check src tests
else
	@echo "$(RED)Use 'make lint' for prod CI/CD$(NC)"
endif

test-docker: ## Run tests in container
ifeq ($(IS_LOCAL),true)
	@$(COMPOSE) exec app uv run pytest
else
	@echo "$(RED)Use 'make test' for prod CI/CD$(NC)"
endif

#------------------------------------------------------------------------------
# Dependencies
#------------------------------------------------------------------------------
install: ## Install deps
	@uv sync

install-dev: ## Install dev deps
	@uv sync --extra dev

install-all: ## Install all deps
	@uv sync --all-extras

#------------------------------------------------------------------------------
# Cleanup
#------------------------------------------------------------------------------
clean: ## Clean cache files
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

docker-clean: ## Remove volumes & images (local only)
ifeq ($(IS_LOCAL),true)
	@echo "$(YELLOW)Removing local Docker resources...$(NC)"
	@$(COMPOSE) down -v --rmi local
	@echo "$(GREEN)Cleanup complete$(NC)"
else
	@echo "$(RED)Error: docker-clean is disabled for production$(NC)"
	@echo "$(YELLOW)Use 'docker stack rm $(STACK_NAME)' manually for prod cleanup$(NC)"
	@exit 1
endif
