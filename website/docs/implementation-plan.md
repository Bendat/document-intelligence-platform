---
sidebar_position: 6
---

# Implementation Plan

## Delivery strategy

Build in vertical slices that are independently reviewable and mergeable. Each
slice should cut through domain, application, adapters, and tests.

The goal is to avoid large infrastructure-first branches that do not yet prove a
user-visible capability.

## DDD approach

Use lightweight tactical DDD.

That means:

- model the core domain explicitly
- keep use cases in application services
- isolate infrastructure in adapters
- use repositories and ports at the application boundary
- avoid over-modeling with excessive factories, aggregates, or generic patterns

## Initial bounded contexts

### Document Catalog

Owns document metadata, taxonomy, summaries, and chunk references.

### Ingestion

Owns source intake, parsing orchestration, and processing lifecycle.

### Retrieval and Q&A

Owns semantic search, citation assembly, and grounded answer generation.

### Job Execution

Owns async task dispatch, retries, and job state transitions.

## Proposed PR slices

### Slice 1: project skeleton

Scope:

- create package layout
- add config and dependency wiring
- add FastAPI app entrypoint
- add test tooling, linting, typing, and CI stubs

Deliverable:

- service boots
- health endpoint works
- CI passes on formatting, linting, types, and tests

### Slice 2: document catalog core

Scope:

- define domain models for `Document`, `Chunk`, `Job`, and `Citation`
- define repository and provider ports
- implement in-memory adapters for tests
- add first application services

Deliverable:

- use cases can run without HTTP or database dependencies

### Slice 3: persistence adapters

Scope:

- add PostgreSQL schema and migrations
- implement repository adapters
- add pgvector-compatible schema support for stored embeddings

Deliverable:

- documents and chunks persist
- stored embeddings have a durable home in PostgreSQL before retrieval work lands

### Slice 4: ingestion pipeline

Scope:

- add local file ingestion
- implement parser ports and default adapters
- persist extracted text, metadata, and chunks

Deliverable:

- a document can be ingested end to end from a local source
- this is exposed as `POST /documents/ingest/local` in the MVP, while
  `POST /documents/ingest` remains the create-and-enqueue path

### Slice 5: intelligence enrichment

Scope:

- add embedding provider adapter
- add classification use case
- add summarization use case
- store summaries and classification results

Implementation note:

- local Ollama/Qwen setup may land just ahead of this slice as development
  scaffolding, but the slice is only complete once provider-backed enrichment is
  wired through the application layer

Deliverable:

- ingested documents are enriched and queryable

Default local development target for this slice:

- `Ollama` as the local OpenAI-compatible runtime
- `qwen3-embedding:0.6b` for embeddings
- `qwen3:4b` for classification and summarization
- optional local upgrades to `qwen3-embedding:4b` and `qwen3:8b` on stronger
  machines

### Slice 6: search and Q&A API

Scope:

- add vector search port and pgvector retrieval adapter
- add search endpoint
- add grounded Q&A endpoint
- add citation response contracts

Deliverable:

- users can query the corpus and inspect evidence

### Slice 7: async execution

Scope:

- add Celery and Redis adapters
- move ingestion and enrichment to background jobs
- expose job status endpoints

Deliverable:

- long-running work is observable and retryable

### Slice 8: Azure Blob integration

Scope:

- implement Blob storage adapter
- add sync or intake workflow for Blob-based sources

Deliverable:

- Azure-hosted documents flow through the same domain use cases

## Suggested package layout

```text
src/document_intelligence/
  app.py
  config.py
  api/
    routes/
      documents.py
      search.py
      qa.py
      jobs.py
  domain/
    document_catalog/
      entities.py
      value_objects.py
    ingestion/
      entities.py
    retrieval/
      entities.py
    jobs/
      entities.py
  application/
    common/
      ports/
        repositories.py
        providers.py
        parsers.py
        dispatch.py
    document_catalog/
      commands.py
      queries.py
      services.py
    ingestion/
      commands.py
      services.py
    retrieval/
      queries.py
      services.py
    jobs/
      services.py
  adapters/
    persistence/
      postgres/
    retrieval/
      pgvector/
    storage/
      azure_blob/
      local_files/
    ai/
      openai/
    parsing/
      pdf/
      docx/
      markdown/
    queue/
      celery/
    web/
      fastapi/
  prompts/
  tests/
    unit/
    integration/
    contract/
```

## Example use-case shape

```python
from dataclasses import dataclass


@dataclass(slots=True)
class IngestDocumentCommand:
    source_uri: str
    media_type: str
    requested_by: str | None = None


class IngestDocument:
    def __init__(
        self,
        document_repository,
        parser_registry,
        chunker,
        dispatcher,
    ) -> None:
        self._document_repository = document_repository
        self._parser_registry = parser_registry
        self._chunker = chunker
        self._dispatcher = dispatcher

    def execute(self, command: IngestDocumentCommand) -> str:
        parser = self._parser_registry.for_media_type(command.media_type)
        parsed = parser.parse(command.source_uri)
        document = parsed.to_document()

        self._document_repository.save(document)
        self._dispatcher.enqueue_enrichment(document.id)

        return document.id
```

The important part is not the exact syntax. The important part is that the use
case depends on ports and stays independent from HTTP, Celery, or PostgreSQL.
