# AGENTS.md

## Purpose

This repository contains the planning site and backend implementation for the
document intelligence platform MVP.

The current system target is a backend-first technical knowledge assistant that:

- ingests documents from local files and Azure Blob Storage
- extracts, chunks, classifies, and summarizes documents
- supports semantic search
- answers grounded questions with citations

## Architecture rules

- Use a modular monolith for the MVP.
- Follow hexagonal architecture.
- Keep domain and application logic independent from frameworks.
- Put infrastructure concerns behind ports and adapters.
- Prefer tactical DDD over heavyweight DDD ceremony.
- Keep the design ready for future multi-agent orchestration without adding it
  to the MVP prematurely.

## Boundaries

Current bounded contexts:

- `document_catalog`
- `ingestion`
- `retrieval`
- `jobs`

Expected layer split:

- `domain/`: entities, value objects, domain language
- `application/`: use cases, orchestration, ports
- `adapters/`: HTTP, persistence, AI providers, storage, queueing, parsers
- `api/`: route wiring and transport contracts

## Tech stack

- Python 3.13
- FastAPI
- PostgreSQL + pgvector
- Azure Blob Storage
- Celery + Redis
- Alembic
- pytest
- ruff
- mypy
- Docker Compose for local infrastructure

## Local development

Use the hybrid local setup:

- Run infrastructure with `docker compose`
- Run the API and worker on the host

Expected local services:

- PostgreSQL
- Redis
- Azurite

Important files:

- `docker-compose.yml`
- `.env.example`
- `Makefile`
- `pyproject.toml`

## Implementation guidance

- Build in vertical slices that can be merged independently.
- Complete work in small, coherent units that are independently reviewable.
- Prefer explicit domain concepts over generic utility abstractions.
- Do not couple use cases to FastAPI, Celery, SQLAlchemy, or provider SDKs.
- Keep prompts version-controlled.
- Treat citation quality as a core requirement.
- Add tests with each slice.
- When a workable unit is complete, run the relevant local checks before moving
  on.
- Commit completed workable units regularly instead of accumulating large
  uncommitted batches.

## Testing guidance

- Use `pytest` for unit, integration, and acceptance-style tests.
- Do not introduce Gherkin or Cucumber in v1.
- Keep `mypy` strict for our code.
- If a third-party library lacks typing metadata, scope any mypy override
  narrowly to that dependency.
- Before starting the next unit of work, ensure the applicable build, lint, and
  test commands pass locally.

## CI guidance

Current CI should remain small and fast:

- backend checks
- docs build
- compose config validation

Local quality gate expectation before committing a workable unit:

- backend: lint, type check, tests, and any relevant compile/build step
- docs: Docusaurus build when docs change
- compose: config validation when local stack files change

Do not add deployment or release workflows until there is a real deployment
target.

## Documentation

The planning site in `website/` is the source of truth for:

- MVP scope
- architecture
- implementation plan
- local development
- testing strategy

Keep code and docs aligned when architectural decisions change.
