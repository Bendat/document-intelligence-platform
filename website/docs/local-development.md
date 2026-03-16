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
- Adminer for PostgreSQL browsing
- Redis
- Azurite for Azure Blob Storage emulation
- Ollama for local chat and embedding inference

## Host processes

- FastAPI API
- Celery worker once Slice 7 async execution lands
- pytest, ruff, and mypy
- Alembic migrations

## Why this setup

- you get reliable local infrastructure without containerizing every code change
- app debugging and reload stay simple
- adapters still target real networked dependencies
- it preserves a clean path to a fuller containerized setup later

## Standard workflow

Check prerequisites and create local config:

```bash
make bootstrap
```

That target:

- copies `.env.example` to `.env` if `.env` does not exist
- checks for required local tools
- installs Python dependencies with `uv`

Then start local infrastructure:

```bash
make up
```

If you want to run the checks without changing anything:

```bash
make doctor
```

Pull the default local models:

```bash
make ai-models
```

Run the Ollama smoke test:

```bash
make ai-smoke
```

Run the GitHub Models smoke test (chat + embeddings):

```bash
GITHUB_MODELS_TOKEN=... \
GENERATION_MODEL=openai/gpt-4.1-mini \
EMBEDDING_MODEL=openai/text-embedding-3-small \
make github-models-smoke
```

Run the API on the host:

```bash
make api
```

For the current slices, stop there. `POST /documents/ingest` still uses the
in-process dispatcher stub, so there is no background work for a Celery worker
to pick up yet.

When working on Slice 7 or later, run the worker in a second shell:

```bash
make worker
```

To run the API with Postgres-backed persistence in this slice:

```bash
PERSISTENCE_BACKEND=postgres make db-upgrade
PERSISTENCE_BACKEND=postgres make api
```

Equivalent combined target:

```bash
make dev-postgres
```

## Seeded Retrieval Workflow

For realistic search and grounded Q&A testing, use the repo's seed corpus in
`fixtures/seed_corpus/`.

Recommended flow:

In the first shell:

```bash
make bootstrap
make up
make ai-models
make dev-postgres
```

In a second shell:

```bash
make seed-corpus
```

That ingests the markdown files in `fixtures/seed_corpus/` through
`POST /documents/ingest/local` and prints the created document IDs as JSON.

Important notes:

- this seed flow assumes the API is running on the host at `http://127.0.0.1:8000`
- the stack is still hybrid: Docker Compose runs infrastructure, while seeding
  happens against the host API
- rerunning `make seed-corpus` adds another copy of each document; for a clean
  rerun, reset the local Postgres data or start with a fresh dev database
- if you change `EMBEDDING_MODEL`, reseed from a clean database so all chunks
  share the same embedding model metadata

For a step-by-step Postman smoke flow, see [Manual Testing](./manual-testing.md).

## Startup modes

Use one of these depending on what you need:

- infrastructure only: `make up`
- infrastructure plus local models: `make up && make ai-models`
- local model verification: `make ai-smoke`
- current full local development: `make up && make sync && make ai-models`, then
  run `make api`
- async-development loop for Slice 7+: `make up && make sync && make ai-models`,
  then run `make api` and `make worker` in separate shells
- GitHub Models verification: `make github-models-smoke` with token and model IDs

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

Start only the Adminer service:

```bash
docker compose up -d adminer
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
- Adminer listens on `localhost:8080` by default (`ADMINER_PORT`)
- Redis listens on `localhost:6379`
- Azurite Blob Storage listens on `localhost:10000`
- Ollama listens on `localhost:11434`

Adminer login defaults:

- system: `PostgreSQL`
- server: `postgres` (service name on the Compose network)
- username: value of `POSTGRES_USER` (default `postgres`)
- password: value of `POSTGRES_PASSWORD` (default `postgres`)
- database: value of `POSTGRES_DB` (default `document_intelligence`)

## Platform Notes

Current local workflow assumptions:

- examples use POSIX-style shell syntax
- on Windows, prefer WSL2 for the documented commands
- the supported GitHub Models auth path is `GITHUB_MODELS_TOKEN` or
  `GITHUB_TOKEN`
- OS-specific secret-store integration such as macOS Keychain, Windows
  Credential Manager, or Linux secret services is not implemented in this repo

## Local model defaults

Slice 5 preparation uses these defaults:

- `AI_PROVIDER_BACKEND=auto`
- `MODEL_API_BASE_URL=http://localhost:11434/v1`
- `GENERATION_MODEL=qwen3:4b`
- `EMBEDDING_MODEL=qwen3-embedding:0.6b`

Optional stronger-machine upgrades:

- `GENERATION_MODEL=qwen3:8b`
- `EMBEDDING_MODEL=qwen3-embedding:4b`

`AI_PROVIDER_BACKEND=auto` uses the OpenAI-compatible adapter when model
settings are present, and falls back to deterministic local providers when they
are not. You can force behavior with:

- `AI_PROVIDER_BACKEND=openai_compatible`
- `AI_PROVIDER_BACKEND=deterministic`
- `AI_PROVIDER_BACKEND=github_models`

GitHub Models configuration (generation + embeddings):

- `AI_PROVIDER_BACKEND=github_models`
- `GITHUB_MODELS_TOKEN` (or rely on `GITHUB_TOKEN` in CI)
- `GENERATION_MODEL` as a GitHub Models chat model ID
  (for example `openai/gpt-4.1-mini`)
- `EMBEDDING_MODEL` as a GitHub Models embedding model ID
  (for example `openai/text-embedding-3-small`)
- optional `GITHUB_MODELS_ORG` to target org-scoped inference routes

For GitHub Actions, store the PAT as `GH_MODELS_TOKEN` (GitHub disallows custom
secret names that start with `GITHUB_`). The workflow maps it to
`GITHUB_MODELS_TOKEN` at runtime.

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
- adding heavy database admin suites before there is a real need
- introducing Kubernetes into the local workflow
