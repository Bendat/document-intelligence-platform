# ADR-004: Retrieval Stack for the Internal Knowledge Assistant

## Status

Accepted

## Date

2026-02-04

## Context

The document intelligence platform needs a retrieval stack that supports:

- ingestion from local files in the MVP
- semantic search over chunked documents
- grounded question answering with inspectable citations
- a low-friction local development setup
- a clean path to more production-hardening later

The team considered external vector databases, a hosted managed search service,
and storing embeddings directly in PostgreSQL with `pgvector`.

## Decision

Use PostgreSQL plus `pgvector` as the retrieval store for the MVP, and keep the
retrieval adapter inside the modular monolith.

Documents are chunked into stable text windows, embeddings are stored alongside
chunk text, and semantic search is executed by the retrieval adapter using
cosine distance over stored vectors. The search response contract includes the
chunk text, source metadata, and score so the caller can inspect evidence.

## Why `pgvector`

The team chose `pgvector` for the MVP for four reasons:

1. It keeps retrieval inside the same operational stack already required for the
   application database.
2. It minimizes new infrastructure during early development and testing.
3. It is good enough for moderate corpus sizes expected in the MVP.
4. It lets the team ship grounded search and question answering before taking on
   a separate search platform.

The decision is explicitly pragmatic. It is not a claim that PostgreSQL is the
final retrieval architecture for all future scale scenarios.

## Rejected Alternatives

### External vector database

Pros:

- stronger ANN features
- easier scaling for very large embedding collections
- richer retrieval tuning options

Cons:

- another datastore to provision, secure, and operate
- more integration code in the MVP
- more failure modes in local development

The team rejected this for the MVP because it added complexity before there was
evidence the initial corpus size required it.

### Hosted managed search

Pros:

- potentially faster path to production-scale operations
- built-in access controls and management tools

Cons:

- higher early cost
- stronger coupling to a platform decision not yet validated
- slower local iteration

The team deferred this until the product demonstrates clear retrieval demand and
access patterns.

## Consequences

Positive:

- one fewer infrastructure component in local development
- easier testing of persistence and retrieval together
- simpler data model for citations because chunks and documents stay close

Negative:

- retrieval quality tuning will be more limited than in a specialized system
- large-scale ANN optimization is deferred
- migrations must preserve embedding compatibility carefully

## Chunking Guidance

The MVP uses deterministic chunking by stable character windows while trying to
preserve paragraph boundaries. Chunks should be large enough to preserve local
meaning but small enough to avoid stuffing the generation prompt with entire
documents. Retrieval responses should preserve chunk identity and source
metadata so grounded answers can point back to the supporting evidence.

## Prompting Guidance

Grounded Q&A prompts must:

- clearly instruct the model to use only provided evidence
- return a machine-readable payload
- fail safely when evidence is insufficient

Prompt files remain version-controlled so retrieval behavior can evolve through
reviewable changes instead of hidden prompt edits.

## Follow-up Decisions

The team still needs to decide:

- when to add approximate nearest-neighbor indexes
- how to track embedding model changes across re-indexing cycles
- whether a separate retrieval store is justified by corpus size or latency
- how to evaluate citation quality systematically

## FAQ

### Why did the team choose `pgvector`?

Because it keeps retrieval in the existing PostgreSQL stack, reduces MVP
operational complexity, and is sufficient for the expected early corpus size.

### Is this the final architecture?

No. It is a pragmatic MVP decision that preserves a migration path to a more
specialized retrieval system later.
