#!/usr/bin/env bash
set -euo pipefail

OPENAI_BASE_URL="${MODEL_API_BASE_URL:-http://localhost:11434/v1}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-${OPENAI_BASE_URL%/v1}}"
GENERATION_MODEL="${GENERATION_MODEL:-qwen3:4b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding:0.6b}"
CURL_TIMEOUT_SECONDS="${CURL_TIMEOUT_SECONDS:-120}"
OLLAMA_READY_RETRIES="${OLLAMA_READY_RETRIES:-60}"
OLLAMA_READY_SLEEP_SECONDS="${OLLAMA_READY_SLEEP_SECONDS:-2}"

log() {
  printf '%s\n' "$*"
}

curl_json() {
  curl -fsS --max-time "${CURL_TIMEOUT_SECONDS}" "$@"
}

log "Checking Ollama readiness at ${OLLAMA_BASE_URL}"
for _ in $(seq 1 "${OLLAMA_READY_RETRIES}"); do
  if curl_json "${OLLAMA_BASE_URL}/api/tags" >/dev/null 2>&1; then
    break
  fi
  sleep "${OLLAMA_READY_SLEEP_SECONDS}"
done

tags_json="$(curl_json "${OLLAMA_BASE_URL}/api/tags")"

python3 - "${GENERATION_MODEL}" "${EMBEDDING_MODEL}" <<'PY' <<<"${tags_json}"
import json
import sys

generation_model = sys.argv[1]
embedding_model = sys.argv[2]
payload = json.load(sys.stdin)
available = {model["name"] for model in payload.get("models", [])}
missing = [
    model for model in (generation_model, embedding_model) if model not in available
]

if missing:
    joined = ", ".join(missing)
    raise SystemExit(
        f"Missing Ollama models: {joined}. Pull them with `make ai-models` first."
    )
PY

log "Running chat completion smoke test with ${GENERATION_MODEL}"
chat_payload="$(cat <<JSON
{
  "model": "${GENERATION_MODEL}",
  "messages": [
    {"role": "user", "content": "Reply with exactly: OK"}
  ]
}
JSON
)"

chat_response="$(
  curl_json \
    -H "Content-Type: application/json" \
    -d "${chat_payload}" \
    "${OPENAI_BASE_URL}/chat/completions"
)"

python3 - <<'PY' <<<"${chat_response}"
import json
import sys

payload = json.load(sys.stdin)
content = payload["choices"][0]["message"]["content"].strip()

if not content:
    raise SystemExit("Chat completion returned empty content.")

if "OK" not in content:
    raise SystemExit(f"Chat completion response did not contain OK: {content!r}")
PY

log "Running embedding smoke test with ${EMBEDDING_MODEL}"
embedding_payload="$(cat <<JSON
{
  "model": "${EMBEDDING_MODEL}",
  "input": "Document intelligence platform"
}
JSON
)"

embedding_response="$(
  curl_json \
    -H "Content-Type: application/json" \
    -d "${embedding_payload}" \
    "${OPENAI_BASE_URL}/embeddings"
)"

python3 - <<'PY' <<<"${embedding_response}"
import json
import sys

payload = json.load(sys.stdin)
embedding = payload["data"][0]["embedding"]

if not embedding:
    raise SystemExit("Embedding response was empty.")

if not isinstance(embedding[0], (int, float)):
    raise SystemExit("Embedding response did not contain numeric values.")
PY

log "Ollama smoke test passed."
