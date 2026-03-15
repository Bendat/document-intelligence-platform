UV ?= uv
ENV_FILE ?= .env
DOTENV_GENERATION_MODEL := $(strip $(shell sed -n 's/^GENERATION_MODEL=//p' $(ENV_FILE) 2>/dev/null | head -n 1))
DOTENV_EMBEDDING_MODEL := $(strip $(shell sed -n 's/^EMBEDDING_MODEL=//p' $(ENV_FILE) 2>/dev/null | head -n 1))
GENERATION_MODEL ?= $(if $(DOTENV_GENERATION_MODEL),$(DOTENV_GENERATION_MODEL),qwen3:4b)
EMBEDDING_MODEL ?= $(if $(DOTENV_EMBEDDING_MODEL),$(DOTENV_EMBEDDING_MODEL),qwen3-embedding:0.6b)
AI_READY_RETRIES ?= 60
AI_READY_SLEEP_SECONDS ?= 2
SEED_BASE_URL ?= http://127.0.0.1:8000
SEED_CORPUS_DIR ?= fixtures/seed_corpus

.PHONY: help doctor bootstrap up down logs sync api dev-postgres worker test lint format typecheck docs-build db-upgrade db-downgrade ai-up ai-models ai-smoke github-models-smoke seed-corpus

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make doctor      Check required local tools and basic env setup' \
		'  make bootstrap   Create .env if missing, run doctor, and install dependencies' \
		'  make up          Start Docker infrastructure in the background' \
		'  make down        Stop Docker infrastructure' \
		'  make logs        Tail Docker service logs' \
		'  make sync        Install Python dependencies with uv' \
		'  make api         Run the FastAPI app on the host' \
		'  make dev-postgres Run migrations and start the API with Postgres persistence' \
		'  make worker      Run the Celery worker on the host' \
			'  make ai-up       Start only the Ollama service' \
		'  make ai-models   Pull GENERATION_MODEL and EMBEDDING_MODEL into Ollama (.env aware)' \
		'  make ai-smoke    Check Ollama readiness, model presence, chat, and embeddings' \
		'  make github-models-smoke  Check GitHub Models chat + embeddings with token auth' \
		'  make seed-corpus Seed the realistic local corpus through POST /documents/ingest/local' \
		'  make test        Run pytest' \
		'  make lint        Run ruff check' \
		'  make format      Run ruff format' \
		'  make typecheck   Run mypy' \
		'  make docs-build  Build the Docusaurus site' \
		'  make db-upgrade  Apply Alembic migrations' \
		'  make db-downgrade Roll back one Alembic migration'

doctor:
	./scripts/check_prereqs.sh

bootstrap:
	@if [ ! -f "$(ENV_FILE)" ]; then cp .env.example "$(ENV_FILE)"; echo "Created $(ENV_FILE) from .env.example"; fi
	$(MAKE) doctor
	$(MAKE) sync

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

dev-postgres:
	PERSISTENCE_BACKEND=postgres $(UV) run alembic upgrade head
	PERSISTENCE_BACKEND=postgres $(UV) run uvicorn document_intelligence.app:create_app --factory --reload

worker:
	$(UV) run celery -A document_intelligence.worker_app:celery_app worker --loglevel=info

ai-up:
	docker compose up -d ollama

ai-models: ai-up
	@attempt=0; \
	until docker compose exec -T ollama ollama list >/dev/null 2>&1; do \
		attempt=$$((attempt + 1)); \
		if [ "$$attempt" -ge "$(AI_READY_RETRIES)" ]; then \
			echo "Ollama did not become ready after $(AI_READY_RETRIES) attempts." >&2; \
			exit 1; \
		fi; \
		sleep "$(AI_READY_SLEEP_SECONDS)"; \
	done
	docker compose exec -T ollama ollama pull $(GENERATION_MODEL)
	docker compose exec -T ollama ollama pull $(EMBEDDING_MODEL)

ai-smoke:
	./scripts/ollama_smoke_test.sh

github-models-smoke:
	./scripts/github_models_smoke_test.sh

seed-corpus:
	$(UV) run python scripts/seed_local_corpus.py --base-url $(SEED_BASE_URL) --corpus-dir $(SEED_CORPUS_DIR)

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
