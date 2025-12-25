# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/
#
# Syndicate - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: help build up down logs shell test lint clean

# Default target
help:
	@echo "Syndicate - Docker Commands"
	@echo "================================"
	@echo ""
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start all services"
	@echo "  make up-full      - Start with full monitoring"
	@echo "  make up-dev       - Start development environment"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Follow Syndicate logs"
	@echo "  make shell        - Open shell in container"
	@echo "  make test         - Run tests in container"
	@echo "  make lint         - Run linting"
	@echo "  make clean        - Remove containers and volumes"
	@echo ""

# Build images
build:
	docker compose build

# Start services
up:
	docker compose up -d

# Start with full monitoring stack
up-full:
	docker compose --profile monitoring --profile logging up -d

# Start development environment
up-dev:
	docker compose --profile dev up -d

# Stop services
down:
	docker compose down

# Follow logs
logs:
	docker compose logs -f gost

# Open shell
shell:
	docker compose exec gost /bin/bash

# Run tests
test:
	docker compose run --rm gost pytest tests/ -v

# Run linting
lint:
	docker compose run --rm gost ruff check .

# Clean up everything
clean:
	docker compose down -v --rmi local
	docker volume prune -f

# One-time execution
run-once:
	docker compose run --rm gost python run.py --once

# Interactive mode
interactive:
	docker compose run --rm -it gost python run.py --interactive

# Health check
health:
	@docker compose exec gost python -c "from db_manager import get_system_health; import json; print(json.dumps(get_system_health(), indent=2))"

# Show status
status:
	@docker compose ps
	@echo ""
	@echo "Endpoints:"
	@echo "  Grafana:      http://localhost:3000 (admin/syndicate)"
	@echo "  Prometheus:   http://localhost:9090"
	@echo "  Alertmanager: http://localhost:9093"
