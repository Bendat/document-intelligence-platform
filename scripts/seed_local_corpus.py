#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    default_corpus_dir = repo_root / "fixtures" / "seed_corpus"

    parser = argparse.ArgumentParser(
        description="Seed the local API with the repo's realistic test corpus."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the running API.",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=default_corpus_dir,
        help="Directory containing markdown files to ingest.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-request timeout in seconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    corpus_dir = args.corpus_dir.expanduser().resolve()
    if not corpus_dir.is_dir():
        print(f"Corpus directory does not exist: {corpus_dir}", file=sys.stderr)
        return 1

    markdown_files = sorted(corpus_dir.rglob("*.md"))
    if not markdown_files:
        print(f"No markdown files found in {corpus_dir}", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    for path in markdown_files:
        print(f"Seeding {path.name}", file=sys.stderr)
        try:
            response_payload = ingest_document(
                base_url=args.base_url,
                source_path=path,
                timeout=args.timeout,
            )
        except RuntimeError as error_message:
            print(str(error_message), file=sys.stderr)
            return 1

        results.append(
            {
                "document_id": response_payload["id"],
                "title": response_payload["title"],
                "status": response_payload["status"],
                "source_uri": path.as_uri(),
            }
        )

    print(
        json.dumps(
            {
                "base_url": args.base_url.rstrip("/"),
                "seeded_documents": results,
            },
            indent=2,
        )
    )
    return 0


def ingest_document(base_url: str, source_path: Path, timeout: float) -> dict[str, Any]:
    payload = json.dumps({"source_uri": source_path.as_uri()}).encode("utf-8")
    endpoint = f"{base_url.rstrip('/')}/documents/ingest/local"
    http_request = request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Failed to seed {source_path.name}: HTTP {exc.code} from {endpoint}: "
            f"{error_body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"Failed to reach {endpoint}: {exc.reason}. Is the API running?"
        ) from exc

    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError(
            f"Unexpected response while seeding {source_path.name}: {body}"
        )
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
