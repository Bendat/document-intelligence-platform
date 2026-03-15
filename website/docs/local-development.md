---
sidebar_position: 6
---

# Local Development

## Approach

Use a hybrid local stack.

Run infrastructure in Docker Compose and run the application processes on the
host machine. This keeps the inner loop fast while still making the data
services reproducible.

## Compose services

- PostgreSQL with `pgvector`
- Redis
- Azurite for Azure Blob Storage emulation

## Host processes

- FastAPI API
- Celery worker
- pytest, ruff, and mypy
- Alembic migrations

## Why this setup

- you get reliable local infrastructure without containerizing every code change
- app debugging and reload stay simple
- adapters still target real networked dependencies
- it preserves a clean path to a fuller containerized setup later

## Standard workflow

```bash
cp .env.example .env
make up
make sync
make api
```

In a second shell:

```bash
make worker
```

To run the API with Postgres-backed persistence in this slice:

```bash
PERSISTENCE_BACKEND=postgres make db-upgrade
PERSISTENCE_BACKEND=postgres make api
```

## Compose notes

- PostgreSQL listens on `localhost:5432`
- Redis listens on `localhost:6379`
- Azurite Blob Storage listens on `localhost:10000`

## Deliberate non-goals for now

- running API and worker in Compose by default
- adding pgAdmin or other admin tooling before there is a real need
- introducing Kubernetes into the local workflow
