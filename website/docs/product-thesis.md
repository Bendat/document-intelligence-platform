---
sidebar_position: 2
---

# Product Thesis

## Primary user

The initial user is an engineer or engineering manager who needs a fast,
trustworthy way to find information across internal technical documentation.

## Primary use cases

- "What service owns this integration?"
- "Summarize the recovery steps for this component."
- "Which ADR explains this architectural decision?"
- "What incident documents mention this dependency?"

## Why technical knowledge first

This domain is the best fit for v1 because it is easy to source realistic
documents and easy to evaluate with concrete questions. It also demonstrates the
same core platform capabilities needed for policy, compliance, or contract work
later.

## Initial taxonomy

- architecture-doc
- runbook
- adr
- incident-review
- service-overview
- support-note

## User promise

The platform should answer technical questions quickly, cite its evidence, and
make each document easier to understand through concise summaries and metadata.

## Non-goals

- generating authoritative answers without evidence
- replacing source systems of record
- supporting every document type on day one
- building a chat-first product before retrieval quality is proven
