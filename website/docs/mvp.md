---
sidebar_position: 2
---

# MVP

## Goal

Ship a backend-first technical knowledge assistant that can ingest internal
engineering documents, enrich them, and answer grounded questions over the
corpus.

## In scope

### Inputs

- local file upload
- Azure Blob Storage sync
- supported formats: PDF, DOCX, Markdown, plain text

### Processing

- text extraction
- metadata capture
- chunking
- embeddings generation
- document classification
- document summarization

### Outputs

- document detail endpoint
- semantic search endpoint
- grounded Q&A endpoint with citations
- async job status endpoint

## Initial taxonomy

- architecture-doc
- runbook
- adr
- incident-review
- service-overview
- support-note

## Non-functional requirements

- retries for transient ingestion failures
- structured logs
- prompt templates in version-controlled files
- provider and storage abstractions defined from day one
- testable application services without live infrastructure dependencies

## Explicit non-goals

- UI-heavy product work
- multi-agent orchestration in v1
- advanced access control
- hybrid retrieval at launch
- evaluation dashboards
- Kubernetes deployment

## Multi-agent readiness

The MVP should not implement agent orchestration yet, but it should prepare for
it by keeping:

- retrieval as a separate application service
- synthesis isolated from retrieval and extraction
- domain use cases independent from HTTP and queue frameworks
- model calls routed through provider ports
- workflow state representable outside a single request cycle

## Definition of done

- a document can be ingested end to end and queried successfully
- answers include citations to retrieved chunks
- ingestion, classification, summarization, and Q&A are exposed via REST APIs
- infrastructure choices can be swapped without rewriting core use cases
