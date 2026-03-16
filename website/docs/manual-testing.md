---
sidebar_position: 8
---

# Manual Testing

## Goal

Run a repeatable API smoke test with Postman that covers:

- service health
- create-and-enqueue ingestion (`POST /documents/ingest`)
- synchronous local ingestion (`POST /documents/ingest/local`)
- local enrichment outputs (classification, summary, chunk embeddings)
- expected error handling for missing and unsupported local sources
- optional Ollama chat and embedding smoke checks

## Prerequisites

- local infrastructure is running (`make up`)
- API is running on host (`make api`)
- optional: Postgres-backed runtime for persistence checks
- optional: Ollama models are pulled for smoke checks (`make ai-models`)

For Postgres-backed runtime:

```bash
PERSISTENCE_BACKEND=postgres make db-upgrade
PERSISTENCE_BACKEND=postgres make api
```

## Prepare Local Test Files

Create the files used by the Postman collection variables:

```bash
cat > /tmp/document-intelligence-sample.md <<'EOF'
# Sample Service Overview

This is a sample markdown document used for manual ingestion testing.

It contains enough content to produce one or more retrieval chunks.
EOF

cat > /tmp/document-intelligence-unsupported.pdf <<'EOF'
This is plain text content with a .pdf extension for unsupported media testing.
EOF
```

Do not create `/tmp/document-intelligence-missing.md`; it is used for the expected 404 case.

## Recommended Retrieval Corpus

The one-file smoke flow above is enough to validate the endpoint wiring. For
more realistic retrieval and grounded Q&A behavior, seed the repo corpus first:

```bash
PERSISTENCE_BACKEND=postgres make db-upgrade
PERSISTENCE_BACKEND=postgres make api
```

In a second shell:

```bash
make seed-corpus
```

The seeded corpus lives in `fixtures/seed_corpus/` and includes:

- a payments service runbook
- a vendor production access policy
- a checkout latency postmortem
- a retrieval ADR
- a customer exports PRD
- an on-call handoff playbook

Use the seeded corpus when you want to judge:

- whether semantic search ranks the right document near the top
- whether grounded answers stay inside the evidence
- whether citations point to the expected source document
- whether multi-section documents are chunked and retrieved sensibly

If you change the embedding model or want a clean corpus, reset the local
database before seeding again. The current helper does not deduplicate existing
documents.

## Import Postman Assets

1. Import collection: `postman/document-intelligence-platform.postman_collection.json`
2. Import environment: `postman/local.postman_environment.json`
3. Select environment: `Document Intelligence Platform Local`
4. Confirm `base_url` is `http://127.0.0.1:8000`
5. Optional for Ollama smoke requests: confirm `ollama_base_url`,
   `generation_model`, and `embedding_model` match your local setup

Collection variables are preconfigured:

- `local_source_uri=file:///tmp/document-intelligence-sample.md`
- `missing_source_uri=file:///tmp/document-intelligence-missing.md`
- `unsupported_source_uri=file:///tmp/document-intelligence-unsupported.pdf`
- `search_query=service ownership runbook`
- `grounded_question=Who owns the service?`

## Request Order And Expectations

Run requests in this exact order:

1. `01 - Health`
Expectation: `200 OK`, payload contains `{"status": "ok"}`.

2. `02 - Ingest Document (Create + Enqueue)`
Expectation: `201 Created`, response status is `enrichment_pending`, `document_id` is captured.

3. `03 - Get Document (Enqueued)`
Expectation: `200 OK`, `document.status` is `enrichment_pending`, `chunks` is empty.

4. `04 - Ingest Local Document (Sync End-to-End)`
Expectation: `201 Created`, response status is `ready`, `classification` and `summary` are present, `local_document_id` is captured.

5. `05 - Get Document (Locally Ingested)`
Expectation: `200 OK`, `document.status` is `ready`, `document.classification` and `document.summary` are present, `chunks.length > 0`, and `chunks[0].embedding.length > 0`.

6. `05A - Search Semantic`
Expectation: `200 OK`, `results.length > 0`, top result references the captured `local_document_id`, and each result includes `score`, chunk text, and source metadata.

7. `05B - Ask Grounded Question`
Expectation: `200 OK`, response includes a non-empty `answer` and `citations.length > 0`.

8. `06 - Ingest Local Missing File (Expected 404)`
Expectation: `404 Not Found`.

9. `07 - Ingest Local Unsupported Media Type (Expected 415)`
Expectation: `415 Unsupported Media Type`.

10. `08 - Ollama Chat Smoke`
Expectation: `200 OK`, response content includes `OK`.

11. `09 - Ollama Embedding Smoke`
Expectation: `200 OK`, `data[0].embedding` is a non-empty numeric array.

## Important Notes

- `GET /documents/{id}` intentionally does not return full `extracted_text`.
- `extracted_text` persistence is validated by automated tests, not by default read-model payloads.
- If request 07 returns `404` instead of `415`, verify `/tmp/document-intelligence-unsupported.pdf` exists.
- Requests 08 and 09 target Ollama directly, not the FastAPI app.

## Troubleshooting

- `Connection refused`: API is not running on `{{base_url}}`.
- `500` on local ingest: verify path is local (`file://` or local filesystem path) and UTF-8 readable.
- Unexpected statuses: rerun request 01 and confirm environment selection in Postman.
- Ollama smoke failures: run `make ai-models` and confirm `{{ollama_base_url}}` is reachable.

## Effective Search And Q&A Checks

Once the realistic corpus is seeded, use a mix of direct search, grounded Q&A,
and no-evidence prompts. These are good baseline checks:

1. Search: `payments service owner`
Expected: the payments runbook ranks near the top and clearly names Platform
Reliability as the primary owner.

2. Ask: `Who owns the payments service and which team is the backup?`
Expected: the answer says Platform Reliability owns it and Checkout Experience
is the secondary owner, with citations from the payments runbook.

3. Ask: `What was the main contributor to the checkout latency incident on 2026-02-18?`
Expected: the answer points to Redis connection pool exhaustion in
`risk-evaluator`, citing the postmortem.

4. Ask: `What controls are required for vendor production access?`
Expected: the answer mentions just-in-time approval, MFA, session recording,
named-user identity, and the time-bound session requirement, citing the vendor
access policy.

5. Ask: `Why did the team choose pgvector for retrieval?`
Expected: the answer cites MVP simplicity, reuse of PostgreSQL, and avoiding
extra infrastructure, citing ADR-004.

6. Ask: `What are the launch metrics for customer exports?`
Expected: the answer includes `95 percent of export jobs complete within 10
minutes` and `support tickets decrease by 30 percent`, citing the PRD.

7. Ask: `What color is the CEO's office sofa?`
Expected: the answer should say there is not enough evidence in the corpus,
with no confident fabricated detail.
