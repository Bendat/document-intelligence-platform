#!/usr/bin/env bash
set -euo pipefail

GITHUB_MODELS_BASE_URL="${GITHUB_MODELS_BASE_URL:-https://models.github.ai/inference}"
GITHUB_MODELS_API_VERSION="${GITHUB_MODELS_API_VERSION:-2026-03-10}"
GENERATION_MODEL="${GENERATION_MODEL:-openai/gpt-4.1-mini}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-openai/text-embedding-3-small}"
GITHUB_MODELS_TOKEN="${GITHUB_MODELS_TOKEN:-${GITHUB_TOKEN:-}}"
CURL_TIMEOUT_SECONDS="${CURL_TIMEOUT_SECONDS:-120}"

if [[ -z "${GITHUB_MODELS_TOKEN}" ]]; then
  echo "GITHUB_MODELS_TOKEN or GITHUB_TOKEN is required." >&2
  exit 1
fi

request_json() {
  local path="$1"
  local payload="$2"
  curl -fsS --max-time "${CURL_TIMEOUT_SECONDS}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GITHUB_MODELS_TOKEN}" \
    -H "X-GitHub-Api-Version: ${GITHUB_MODELS_API_VERSION}" \
    -d "${payload}" \
    "${GITHUB_MODELS_BASE_URL%/}/${path}"
}

echo "Running GitHub Models chat smoke test with ${GENERATION_MODEL}"
chat_payload="$(cat <<JSON
{
  "model": "${GENERATION_MODEL}",
  "messages": [
    {"role": "user", "content": "Reply with exactly: OK"}
  ]
}
JSON
)"

chat_response="$(request_json "chat/completions" "${chat_payload}")"
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

echo "Running GitHub Models embedding smoke test with ${EMBEDDING_MODEL}"
embedding_payload="$(cat <<JSON
{
  "model": "${EMBEDDING_MODEL}",
  "input": "Document intelligence platform"
}
JSON
)"

embedding_response="$(request_json "embeddings" "${embedding_payload}")"
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

echo "GitHub Models smoke test passed."
