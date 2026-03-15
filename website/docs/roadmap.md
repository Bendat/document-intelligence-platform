---
sidebar_position: 4
---

# Roadmap

## Phase 1: Foundation

- scaffold the API and worker services
- define document, chunk, citation, and job schemas
- define ports and adapters for storage, retrieval, parsing, and model access
- connect PostgreSQL and pgvector
- support local file ingestion first

## Phase 2: Core intelligence

- add Azure Blob ingestion
- implement parsing and chunking
- generate embeddings and semantic search
- add document classification
- add summary generation

## Phase 3: Grounded Q&A

- implement retrieval pipeline
- add answer generation with citations
- create a small evaluation set of known questions
- measure relevance, grounding, latency, and cost

## Phase 4: Operational quality

- Dockerize the application
- add CI for linting, tests, and docs build
- improve retries, logging, and job visibility
- seed observability for token usage and failures

## Later extensions

- multi-agent orchestration over retrieval, extraction, and synthesis flows
- hybrid keyword plus vector retrieval
- citation highlighting in the UI
- event-driven ingestion
- prompt registry and evaluation runs
- domain-specific expansion into policy or compliance content
