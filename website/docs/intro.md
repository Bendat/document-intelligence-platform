---
sidebar_position: 1
slug: /
---

# Document Intelligence Platform

This site is the working plan for an internal-facing document intelligence
platform focused on technical knowledge.

## Problem

Engineering organizations accumulate architecture notes, runbooks, ADRs,
incident reviews, and support documentation across many systems. That material
exists, but it is hard to search, hard to trust, and expensive to keep current.

## Product thesis

Build a technical knowledge assistant that:

- ingests documents from Azure Blob Storage or local upload
- extracts, chunks, and indexes content with metadata
- classifies documents into a small, fixed taxonomy
- generates concise summaries for each document
- answers questions over the corpus with grounded citations

## MVP

The MVP is a production-shaped backend for technical document intelligence. It
must be useful on its own, but it should also leave clean extension points for
future workflow orchestration.

Core capabilities:

- ingest documents from local files and Azure Blob Storage
- extract and normalize text from PDF, DOCX, Markdown, and plain text
- chunk and index documents with metadata
- classify documents into the initial taxonomy
- generate concise document summaries
- expose semantic search
- expose grounded Q&A with citations
- process ingestion and enrichment asynchronously with job tracking

## Architecture constraints

- use a modular monolith
- follow hexagonal design principles
- isolate infrastructure behind ports and adapters
- avoid coupling domain workflows to a single model provider
- keep orchestration seams ready for future multi-agent workflows

## Deferred

- multi-agent orchestration
- Kubernetes
- Databricks
- RBAC
- human review workflows
- model comparison dashboards

## Success criteria

- known test questions return relevant chunks
- every generated answer includes source citations
- classification works for the initial taxonomy
- summaries are stable and concise
- ingestion jobs complete reliably and can be retried

## Documentation map

- [MVP](./mvp.md)
- [Product thesis](./product-thesis.md)
- [Architecture](./architecture.md)
- [Tech stack](./tech-stack.md)
- [Roadmap](./roadmap.md)
- [Decision log](./decision-log.md)
