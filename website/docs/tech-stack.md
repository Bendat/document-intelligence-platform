---
sidebar_position: 5
---

# Tech Stack

## Application

- `Python 3.13`
- `FastAPI` for the HTTP API
- `Pydantic` for contracts and validation
- `uv` for project and dependency management

## Persistence

- `PostgreSQL` for metadata, jobs, and document state
- `pgvector` for semantic retrieval
- `Azure Blob Storage` for raw documents
- `Alembic` for database migrations

## Background processing

- `Celery` for async jobs
- `Redis` as the initial broker and result backend

## AI integration

- OpenAI-compatible chat and embedding providers behind internal ports
- `Ollama` as the default local model runtime for Slice 5 development
- `qwen3-embedding:0.6b` as the default local embedding model
- `qwen3:4b` as the default local classification and summarization model
- provider-specific SDKs isolated to adapter modules
- prompt templates stored in version-controlled files

## Document processing

- `pymupdf` for PDF extraction
- `python-docx` for DOCX parsing
- `markdown-it-py` or plain Markdown parsing for `.md` inputs

## Packaging and quality

- `Docker` for local and deployment packaging
- `pytest` for tests
- `ruff` for linting and formatting
- `mypy` for static type checking
- `GitHub Actions` for CI
- no `Cucumber` runner in v1

## Why this stack

- Python and FastAPI keep the AI and API work in one language
- PostgreSQL plus pgvector is simple enough for v1 and does not lock the
  retrieval design to a managed vector service
- Celery and Redis are conventional and easy to replace later if workload or
  operations demand a different queue
- provider-specific AI code stays out of the core domain through ports and
  adapters
- the local default model runtime stays free to use while preserving a clean
  upgrade path to hosted providers later
- `pytest` is enough for acceptance coverage while the domain and API shape are
  still moving

## Planned seams

These areas must be abstracted behind interfaces so they can be swapped later:

- LLM and embedding providers
- vector retrieval implementation
- document source connectors
- queue and job execution
- document parsers
