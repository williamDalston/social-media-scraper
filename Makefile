.PHONY: help build up down restart logs shell test migrate backup clean install

# Default target
.DEFAULT_GOAL := help

# Variables
COMPOSE := docker-compose
PYTHON := python3
PIP := pip3

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies locally
	$(PIP) install -r requirements.txt

build: ## Build Docker images
	$(COMPOSE) build

up: ## Start all services
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

logs: ## View logs from all services
	$(COMPOSE) logs -f

logs-app: ## View logs from app service
	$(COMPOSE) logs -f app

logs-worker: ## View logs from celery worker
	$(COMPOSE) logs -f celery-worker

logs-beat: ## View logs from celery beat
	$(COMPOSE) logs -f celery-beat

shell: ## Open shell in app container
	$(COMPOSE) exec app /bin/bash

shell-worker: ## Open shell in celery worker container
	$(COMPOSE) exec celery-worker /bin/bash

test: ## Run tests
	$(PYTHON) -m pytest tests/ -v

test-cov: ## Run tests with coverage
	$(PYTHON) -m pytest tests/ --cov=. --cov-report=html --cov-report=term

migrate: ## Run database migrations
	$(COMPOSE) exec app alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	$(COMPOSE) exec app alembic revision --autogenerate -m "$(MESSAGE)"

migrate-downgrade: ## Downgrade database by one version
	$(COMPOSE) exec app alembic downgrade -1

migrate-history: ## Show migration history
	$(COMPOSE) exec app alembic history

migrate-current: ## Show current migration version
	$(COMPOSE) exec app alembic current

backup: ## Backup database
	./scripts/backup_db.sh

restore: ## Restore database (usage: make restore BACKUP=backups/db_backup_xxx.db)
	./scripts/restore_db.sh $(BACKUP)

init-db: ## Initialize database (create tables, run migrations)
	$(COMPOSE) exec app alembic upgrade head
	@echo "Database initialized"

deploy: ## Run deployment script
	./scripts/deploy.sh

start: ## Start services using start script
	./scripts/start.sh start

stop: ## Stop services using start script
	./scripts/start.sh stop

status: ## Check service status
	./scripts/start.sh status

clean: ## Clean up containers, volumes, and images
	$(COMPOSE) down -v --rmi all
	docker system prune -f

clean-logs: ## Clean log files
	rm -rf logs/*.log

clean-backups: ## Clean old backups (older than 30 days)
	find backups/ -name "*.db*" -mtime +30 -delete
	find backups/ -name "*.sql*" -mtime +30 -delete

health: ## Check application health
	curl -f http://localhost:5000/health || echo "Health check failed"

ps: ## Show running containers
	$(COMPOSE) ps

config: ## Validate configuration
	$(PYTHON) -c "from config.settings import config, validate_config_on_startup; validate_config_on_startup(); print('Configuration valid!')"

dev: ## Start development environment
	cp docker-compose.override.yml.example docker-compose.override.yml 2>/dev/null || true
	$(COMPOSE) up -d
	@echo "Development environment started. Use 'make logs' to view logs."

prod: ## Start production environment
	$(COMPOSE) -f docker-compose.yml up -d
	@echo "Production environment started."

