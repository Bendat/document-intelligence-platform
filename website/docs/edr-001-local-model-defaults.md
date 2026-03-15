---
sidebar_position: 10
---

# EDR 001: Local Model Defaults for Slice 5

## Status

Accepted on 2026-03-15.

## Context

Slice 5 adds the first model-backed enrichment capabilities:

- embedding generation
- document classification
- document summarization

The architecture already commits to model access through internal ports and to
OpenAI-compatible providers where practical. The project also uses a hybrid
local-development setup, so the local model path should be easy to run on a
developer machine without introducing paid hosted dependencies.

The previous open decision was which models to use for local development while
keeping the production provider choice flexible.

## Decision

Use `Ollama` as the default local model runtime for Slice 5.

Use these default local models:

- embeddings: `qwen3-embedding:0.6b`
- classification and summarization: `qwen3:4b`

Use these optional upgrades on stronger machines:

- embeddings: `qwen3-embedding:4b`
- classification and summarization: `qwen3:8b`

Classification should not introduce a separate classifier model in v1. Use the
generation model with a constrained prompt and structured JSON output against
the project taxonomy.

Keep the application boundary provider-agnostic:

- one embedding port
- one generation port
- one adapter that can target an OpenAI-compatible local endpoint

This decision applies to local development defaults only. A hosted production
provider decision remains open.

## Rationale

- `Ollama` gives the team a free local runtime that exposes both chat and
  embedding APIs.
- It fits the existing architectural preference for OpenAI-compatible adapters
  behind internal ports.
- `qwen3-embedding:0.6b` is a strong small embedding model for technical text
  and keeps laptop requirements reasonable.
- `qwen3:4b` is a practical local summarization and classification model for
  development and acceptance-style testing.
- The larger `Qwen3` variants preserve a low-friction upgrade path without
  changing application code.
- A dedicated classifier model would add operational complexity before there is
  evidence that the taxonomy requires it.

## Consequences

Positive:

- local Slice 5 work can run without paid provider accounts
- one local runtime serves both embeddings and generation
- model wiring remains consistent with the hexagonal architecture
- developers can scale up model size without changing ports or route contracts

Negative:

- first-time local setup now includes pulling model weights
- local inference speed will vary materially by machine
- Docker Compose provides the runtime, but developers still need to choose when
  to pull the default models

## Operational guidance

Local default environment values:

- `MODEL_API_BASE_URL=http://localhost:11434/v1`
- `GENERATION_MODEL=qwen3:4b`
- `EMBEDDING_MODEL=qwen3-embedding:0.6b`

Local workflow:

1. start infrastructure with Docker Compose
2. pull the default local models
3. run the API and worker on the host

CI impact:

- current CI should continue to validate docs and Compose configuration
- CI should not require live local model execution until Slice 5 adds tests that
  depend on model-backed adapters

## Follow-up

- add the Ollama-backed OpenAI-compatible adapter in Slice 5
- add deterministic tests around classification and summarization prompts
- revisit production provider options separately from the local default
