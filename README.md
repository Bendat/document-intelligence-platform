# Document Intelligence Platform

This repository contains the planning site and backend scaffold for the
document intelligence platform MVP.

## Local stack

Infrastructure runs in Docker Compose:

- PostgreSQL with pgvector
- Redis
- Azurite for local Blob Storage emulation
- Ollama for local model inference

Application processes run on the host during early development:

- FastAPI API
- Celery worker once Slice 7 async execution lands
- tests, linting, and type checks

## Commands

Start local infrastructure only:

```bash
cp .env.example .env
make up
```

Equivalent raw Docker Compose command:

```bash
docker compose up -d
```

Show the available `make` targets:

```bash
make help
```

Pull the default local models after the infrastructure is up:

```bash
make ai-models
```

Run an Ollama smoke test against the configured chat and embedding models:

```bash
make ai-smoke
```

If `uv` is installed:

```bash
make sync
make api
make test
```

Run `make worker` only when you are working on the async execution slice or
later; the current slices still use the in-process dispatcher stub.

To use Postgres persistence for the API/runtime:

```bash
PERSISTENCE_BACKEND=postgres make db-upgrade
PERSISTENCE_BACKEND=postgres make api
```

Typical local startup modes:

- infrastructure only: `make up`
- infrastructure plus local models: `make up && make ai-models`
- Ollama verification: `make ai-smoke`
- current full local dev loop: `make up && make sync && make ai-models`, then
  run `make api`
- async development loop for Slice 7+: `make up && make sync && make ai-models`,
  then run `make api` and `make worker` in separate shells

## Documentation

- [Planning site](./website/README.md)
- [Implementation plan](./website/docs/implementation-plan.md)
- [Local development](./website/docs/local-development.md)
- [Manual testing (Postman)](./website/docs/manual-testing.md)
