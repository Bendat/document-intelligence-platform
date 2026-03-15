#!/usr/bin/env bash
set -euo pipefail

required_commands=(
  docker
  uv
  node
  npm
)

missing=0

echo "Checking local prerequisites..."

for command_name in "${required_commands[@]}"; do
  if command -v "${command_name}" >/dev/null 2>&1; then
    echo "  OK   ${command_name}: $(command -v "${command_name}")"
  else
    echo "  MISS ${command_name}: not found on PATH" >&2
    missing=1
  fi
done

if docker compose version >/dev/null 2>&1; then
  echo "  OK   docker compose: available"
else
  echo "  MISS docker compose: unavailable" >&2
  missing=1
fi

if [[ -f ".env" ]]; then
  echo "  OK   .env: present"
else
  echo "  WARN .env: missing (copy .env.example to .env or run make bootstrap)"
fi

if [[ "${missing}" -ne 0 ]]; then
  echo
  echo "One or more required tools are missing." >&2
  exit 1
fi

echo
echo "Environment looks ready for the standard local workflow."
