# Document Intelligence Platform

This repository contains the planning site and backend scaffold for the
document intelligence platform MVP.

## Local stack

Infrastructure runs in Docker Compose:

- PostgreSQL with pgvector
- Redis
- Azurite for local Blob Storage emulation

Application processes run on the host during early development:

- FastAPI API
- Celery worker
- tests, linting, and type checks

## Commands

```bash
cp .env.example .env
make up
```

If `uv` is installed:

```bash
make sync
make api
make worker
make test
```

To use Postgres persistence for the API/runtime:

```bash
PERSISTENCE_BACKEND=postgres make db-upgrade
PERSISTENCE_BACKEND=postgres make api
```

## Documentation

- [Planning site](./website/README.md)
- [Implementation plan](./website/docs/implementation-plan.md)
- [Local development](./website/docs/local-development.md)
- [Manual testing (Postman)](./website/docs/manual-testing.md)
