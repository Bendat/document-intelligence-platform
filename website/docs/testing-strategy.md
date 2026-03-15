---
sidebar_position: 7
---

# Testing Strategy

## Recommendation

Do not start with Gherkin and a Cucumber runner.

For this MVP, the better default is:

- `pytest` for unit and integration tests
- a few high-value API contract tests
- a small acceptance test layer written in plain Python

## Why not Cucumber first

- it adds another abstraction layer before the domain model is stable
- most early scenarios will be technical, not business-readable
- step definitions often become indirect wrappers around code that is easier to
  express directly in Python tests
- it slows down refactoring during the phase where design is still moving

## Where Gherkin can still help

Gherkin is useful as a documentation format for a few core journeys:

- ingest a document and enrich it successfully
- answer a grounded question with citations
- retry a failed ingestion job

If you want that style, keep the scenarios as living acceptance notes in the
docs first. Add a runner only if those scenarios become part of regular
cross-functional review.

## Test pyramid

### Unit tests

Focus on:

- domain rules
- application services
- port contracts via test doubles
- chunking, classification mapping, and citation assembly logic

### Integration tests

Focus on:

- PostgreSQL repository adapters
- pgvector retrieval adapter
- Celery task wiring
- parser adapters
- FastAPI route integration

### Acceptance tests

Focus on end-to-end flows:

- ingest document
- enrich document
- search document
- answer question with citations

These can be implemented in `pytest` without a separate BDD runner.

## Suggested test layout

```text
tests/
  unit/
    domain/
    application/
  integration/
    adapters/
    api/
  acceptance/
    test_ingest_document_flow.py
    test_answer_question_flow.py
  fixtures/
    documents/
    embeddings/
```

## Example acceptance test shape

```python
def test_user_can_ask_grounded_question(app_client, seeded_documents):
    response = app_client.post(
        "/ask",
        json={"question": "Which ADR covers service ownership?"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["answer"]
    assert payload["citations"]
```

## Decision

Use `pytest` only for now.

Revisit Gherkin and a Cucumber runner later if:

- product requirements are being reviewed in scenario form
- non-engineering stakeholders need executable examples
- the acceptance layer becomes hard to understand in plain Python
