.PHONY: install lint format test test-cov migrate migrate-create dev dev-bot dev-api dev-scheduler clean

UV ?= uv
ALEMBIC = $(UV) run alembic

install:
	$(UV) sync --all-groups

lint:
	$(UV) run ruff check src tests
	$(UV) run ruff format --check src tests
	$(UV) run mypy

format:
	$(UV) run ruff check --fix src tests
	$(UV) run ruff format src tests

test:
	$(UV) run pytest

test-cov:
	$(UV) run pytest --cov=src/mdk_bot --cov-report=term-missing --cov-report=html

migrate:
	$(ALEMBIC) upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	$(ALEMBIC) revision --autogenerate -m "$$msg"

migrate-down:
	$(ALEMBIC) downgrade -1

dev:
	docker compose up --build

dev-api:
	$(UV) run python -m mdk_bot api

dev-bot:
	$(UV) run python -m mdk_bot bot

dev-scheduler:
	$(UV) run python -m mdk_bot scheduler

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage dist build
