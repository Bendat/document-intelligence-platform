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
- Ollama for local chat and embedding inference

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

Start local infrastructure:

```bash
cp .env.example .env
make up
```

Install Python dependencies:

```bash
make sync
```

Pull the default local models:

```bash
make ai-models
```

Run the Ollama smoke test:

```bash
make ai-smoke
```

Run the API on the host:

```bash
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

For a step-by-step Postman smoke flow, see [Manual Testing](./manual-testing.md).

## Startup modes

Use one of these depending on what you need:

- infrastructure only: `make up`
- infrastructure plus local models: `make up && make ai-models`
- local model verification: `make ai-smoke`
- full local development: `make up && make sync && make ai-models`, then run
  `make api` and `make worker` in separate shells

## Equivalent raw Docker Compose commands

If you do not want to use `make`, these are the direct Compose equivalents:

Start the full infrastructure in the background:

```bash
docker compose up -d
```

Start the full infrastructure with logs attached:

```bash
docker compose up
```

Start only the Ollama service:

```bash
docker compose up -d ollama
```

Show running services:

```bash
docker compose ps
```

Stop the infrastructure:

```bash
docker compose down
```

Tail logs:

```bash
docker compose logs -f
```

## Make target discovery

To see the local helper commands available in this repo:

```bash
make help
```

## Compose notes

- PostgreSQL listens on `localhost:5432`
- Redis listens on `localhost:6379`
- Azurite Blob Storage listens on `localhost:10000`
- Ollama listens on `localhost:11434`

## Local model defaults

Slice 5 local development uses these defaults:

- `MODEL_API_BASE_URL=http://localhost:11434/v1`
- `GENERATION_MODEL=qwen3:4b`
- `EMBEDDING_MODEL=qwen3-embedding:0.6b`

Optional stronger-machine upgrades:

- `GENERATION_MODEL=qwen3:8b`
- `EMBEDDING_MODEL=qwen3-embedding:4b`

`make ai-models` pulls the default Ollama models into the local Docker volume.
That step is intentionally explicit so `make up` stays reasonably fast and does
not download multi-gigabyte model weights unless the developer wants them. It
honors `GENERATION_MODEL` and `EMBEDDING_MODEL` if you override them in your
environment.

`make ai-smoke` verifies the configured Ollama endpoint is reachable, confirms
the configured models are installed, and exercises both chat completion and
embedding generation over the OpenAI-compatible API.

## Deliberate non-goals for now

- running API and worker in Compose by default
- adding pgAdmin or other admin tooling before there is a real need
- introducing Kubernetes into the local workflow
