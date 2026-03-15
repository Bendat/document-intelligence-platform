---
sidebar_position: 5
---

# Decision Log

## Current decisions

### Scope v1 around technical knowledge

Reason:
Technical documentation is easier to source, demo, and evaluate than legal or
compliance content, while still proving the same platform patterns.

### Start as a modular monolith

Reason:
The boundaries are clear, but splitting into microservices now would add
deployment and debugging cost before the workflows are stable.

### Use hexagonal design principles

Reason:
The system needs to preserve clean use cases while keeping storage, queueing,
parsing, and model integrations replaceable.

### Use citations as a hard requirement

Reason:
The product is only useful if users can inspect the source material behind an
answer.

### Keep multi-agent orchestration as a planned extension

Reason:
It is useful enough to shape the architecture now, but it should not inflate the
scope of the first delivery.

### Initial tech stack

Reason:
Use Python 3.13, FastAPI, PostgreSQL, pgvector, Azure Blob Storage, Celery,
Redis, Alembic, Docker, pytest, ruff, mypy, and GitHub Actions as the baseline
stack. This is pragmatic for v1 and aligns with the need for AI workflows, APIs,
async jobs, and replaceable infrastructure.

### Use tactical DDD

Reason:
The project benefits from bounded contexts, explicit domain concepts, and
application-layer use cases, but it does not need heavyweight DDD ceremony.

### Do not use Gherkin or Cucumber in v1

Reason:
The acceptance layer can be covered with pytest while the domain and API are
still evolving. Executable Gherkin is only worth the added cost if scenario
review becomes a real collaboration requirement.

### Use a hybrid local development stack

Reason:
Run infrastructure with Docker Compose and keep application processes on the
host machine during early development. Today that means the API, and later the
worker once async execution lands. This keeps iteration fast without giving up a
reproducible local environment.

### Use Ollama plus Qwen3 as the local Slice 5 default

Reason:
Slice 5 needs free local embeddings, classification, and summarization without
locking the application layer to a hosted provider. Ollama provides a pragmatic
local runtime, `qwen3-embedding:0.6b` is the default embedding model, and
`qwen3:4b` is the default local generation model. Larger local Qwen3 variants
remain a straightforward upgrade path. See
[EDR 001](./edr-001-local-model-defaults.md).

## Open decisions

- hosted production embedding and generation provider choices
- final parser package selection after prototyping
- local development container strategy
- evaluation dataset structure

## Update rule

When a technical or product choice materially changes the architecture, capture
the decision here with the reason and expected tradeoff.
