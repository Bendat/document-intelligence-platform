# GitHub Copilot Instructions

## Project context

This repository is building a document intelligence platform MVP for technical
knowledge documents. The system ingests documents, enriches them, indexes them,
and answers grounded questions with citations.

## Preferred architecture

- Use a modular monolith for the MVP.
- Follow hexagonal architecture.
- Apply tactical DDD.
- Keep domain and application logic independent from frameworks and vendor SDKs.
- Introduce infrastructure through ports and adapters.

## Preferred patterns

- Put business logic in application services and domain types.
- Keep FastAPI handlers thin.
- Keep Celery task modules thin.
- Use explicit repository/provider/parser/dispatcher interfaces.
- Prefer clear, boring code over clever abstractions.

## Avoid

- framework logic leaking into the domain layer
- direct SDK calls from use-case code
- generic base classes that obscure the domain model
- premature microservices
- premature multi-agent orchestration
- adding MongoDB, Kubernetes, or Databricks to the MVP without an explicit
  decision change

## Current stack

- Python 3.13
- FastAPI
- PostgreSQL + pgvector
- Azure Blob Storage
- Celery + Redis
- Alembic
- pytest
- ruff
- mypy

## Local development assumptions

- Infrastructure runs in Docker Compose.
- API and worker run on the host during early development.
- Local Blob emulation uses Azurite.

## Testing expectations

- Add or update tests with code changes.
- Use `pytest`.
- Keep `mypy` strict.
- Scope typing workarounds narrowly when third-party libraries are untyped.
- Before moving to the next unit of work, run the relevant local build, lint,
  and test commands.
- Prefer small, regular commits once a workable unit is complete.

## File layout expectations

Use the established structure under `src/document_intelligence/`:

- `domain/`
- `application/`
- `api/`
- `adapters/`

Keep docs in `website/` aligned with major architectural changes.
