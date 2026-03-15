UV ?= uv

.PHONY: up down logs sync api worker test lint format typecheck docs-build db-upgrade db-downgrade

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

sync:
	$(UV) sync

api:
	$(UV) run uvicorn document_intelligence.app:create_app --factory --reload

worker:
	$(UV) run celery -A document_intelligence.worker_app:celery_app worker --loglevel=info

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

typecheck:
	$(UV) run mypy src

docs-build:
	cd website && npm run build

db-upgrade:
	$(UV) run alembic upgrade head

db-downgrade:
	$(UV) run alembic downgrade -1
