---
sidebar_position: 3
---

# Architecture

## Approach

Start with a modular monolith. The system should have clear boundaries, but it
does not need distributed deployment until the workflows are validated.

## Architectural style

Use hexagonal architecture.

The domain and application layers should define the behavior of the system. HTTP,
database, queue, storage, and model-provider concerns should live in adapters
that plug into those core use cases.

### Inner layers

- domain entities such as `Document`, `Chunk`, `Job`, and `Citation`
- use cases such as `IngestDocument`, `ClassifyDocument`, `SummarizeDocument`,
  `SemanticSearch`, and `AnswerQuestion`
- ports for persistence, retrieval, storage, parsing, queueing, and model calls

## DDD guidance

Apply DDD tactically rather than ceremonially.

Use DDD where it improves clarity:

- bounded contexts for major capability areas
- explicit domain language
- entities and value objects where identity and invariants matter
- repository abstractions at application boundaries

Avoid DDD where it would add ceremony without value:

- generic base classes for every domain concept
- deep inheritance hierarchies
- abstract factories that hide simple construction
- aggregate rules that do not map to real consistency needs

## Likely domain concepts

- `Document`
- `Chunk`
- `Summary`
- `Classification`
- `Citation`
- `IngestionJob`
- `Question`
- `Answer`

### Outer layers

- FastAPI controllers
- PostgreSQL repositories
- Azure Blob storage client
- Celery task runners
- parser integrations
- LLM provider clients

## Core components

### API layer

- `FastAPI` for REST endpoints
- document, search, question-answering, and job endpoints

### Processing layer

- parsers for PDF, DOCX, Markdown, and plain text
- chunking and metadata normalization
- embedding generation
- summarization and classification jobs

### Data layer

- `Azure Blob Storage` for source documents
- `PostgreSQL` for metadata, jobs, and document state
- `pgvector` for semantic retrieval

### Background execution

- async worker for ingestion and enrichment jobs
- retries for transient failures
- job status tracking for operators

## Logical modules

- `ingestion`
- `processing`
- `intelligence`
- `search`
- `qa`
- `jobs`

## Bounded contexts

- `document_catalog`
- `ingestion`
- `retrieval`
- `jobs`

## Key ports

- `DocumentRepository`
- `ChunkRepository`
- `JobRepository`
- `BlobStoragePort`
- `EmbeddingProvider`
- `GenerationProvider`
- `VectorSearchPort`
- `DocumentParser`
- `TaskDispatcher`

## Adapter strategy

Each infrastructure dependency should have a default adapter in v1 and a clear
replacement path.

- PostgreSQL adapters back repository ports
- pgvector backs vector retrieval
- Azure Blob Storage backs document source storage
- Celery backs async dispatch
- provider SDK adapters back generation and embedding ports

## Multi-agent readiness

Multi-agent orchestration is not part of the MVP, but the current design should
not block it.

Prepare for that by keeping:

- retrieval, extraction, and synthesis as separate use cases
- workflow state serializable so it can move between tasks or agents
- prompt and tool definitions outside HTTP handlers
- model interactions expressed through provider ports
- orchestration logic outside the domain layer

That lets the future system introduce an orchestrator or graph runtime without
rewriting core business logic.

## Data flow

1. A document is uploaded or synced from Blob Storage.
2. The ingestion pipeline stores document metadata and source references.
3. The processing pipeline extracts text, splits chunks, and generates
   embeddings.
4. Intelligence jobs classify the document and generate a summary.
5. Search and Q&A endpoints retrieve the best chunks and produce grounded
   answers with citations.

## API surface

- `POST /documents/ingest`
- `POST /documents/ingest/local`
- `GET /documents/{id}`
- `POST /search/semantic`
- `POST /documents/{id}/classify`
- `POST /documents/{id}/summarize`
- `POST /ask`
- `GET /jobs/{id}`
- `GET /health`

Current ingestion route semantics:

- `POST /documents/ingest` creates a document record and enqueues async enrichment
  (status transitions to `enrichment_pending`)
- `POST /documents/ingest/local` performs synchronous local-file ingestion
  (parse + extracted-text persistence + chunk persistence; status transitions to
  `ready`)

## Design principles

- keep core use cases framework-agnostic
- depend inward on ports, not concrete infrastructure
- keep prompts versioned
- validate structured outputs
- prefer observable async jobs over opaque pipelines
- treat citation quality as a core feature, not a nice-to-have
