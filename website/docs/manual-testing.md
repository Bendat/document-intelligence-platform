---
sidebar_position: 8
---

# Manual Testing

## Goal

Run a repeatable API smoke test with Postman that covers:

- service health
- create-and-enqueue ingestion (`POST /documents/ingest`)
- synchronous local ingestion (`POST /documents/ingest/local`)
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

## Request Order And Expectations

Run requests in this exact order:

1. `01 - Health`
Expectation: `200 OK`, payload contains `{"status": "ok"}`.

2. `02 - Ingest Document (Create + Enqueue)`
Expectation: `201 Created`, response status is `enrichment_pending`, `document_id` is captured.

3. `03 - Get Document (Enqueued)`
Expectation: `200 OK`, `document.status` is `enrichment_pending`, `chunks` is empty.

4. `04 - Ingest Local Document (Sync End-to-End)`
Expectation: `201 Created`, response status is `ready`, `local_document_id` is captured.

5. `05 - Get Document (Locally Ingested)`
Expectation: `200 OK`, `document.status` is `ready`, `chunks.length > 0`.

6. `06 - Ingest Local Missing File (Expected 404)`
Expectation: `404 Not Found`.

7. `07 - Ingest Local Unsupported Media Type (Expected 415)`
Expectation: `415 Unsupported Media Type`.

8. `08 - Ollama Chat Smoke`
Expectation: `200 OK`, response content includes `OK`.

9. `09 - Ollama Embedding Smoke`
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
