from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from document_intelligence.app import create_app
from document_intelligence.config import get_settings


@pytest.fixture(autouse=True)
def force_in_memory_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSISTENCE_BACKEND", "in_memory")
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


def test_semantic_search_returns_retrieval_hits(tmp_path: Path) -> None:
    source = tmp_path / "ownership.md"
    source.write_text(
        "# Ownership ADR\n\n"
        "ADR-004 defines service ownership boundaries for the platform team.\n\n"
        "It also includes escalation expectations during incidents.",
        encoding="utf-8",
    )

    client = TestClient(create_app())

    ingest_response = client.post(
        "/documents/ingest/local",
        json={"source_uri": str(source)},
    )
    assert ingest_response.status_code == 201

    search_response = client.post(
        "/search/semantic",
        json={"query": "service ownership ADR", "limit": 3},
    )

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["results"]

    hit = payload["results"][0]
    assert hit["chunk_id"]
    assert hit["document_id"] == ingest_response.json()["id"]
    assert hit["source_uri"] == str(source)
    assert hit["document_title"] == "Ownership ADR"
    assert hit["text"]
    assert isinstance(hit["score"], float)


def test_ask_returns_answer_with_citations(tmp_path: Path) -> None:
    source = tmp_path / "runbook.md"
    source.write_text(
        "# Payments Runbook\n\n"
        "This runbook describes how to recover the payments service.\n\n"
        "Service ownership sits with the platform reliability team.",
        encoding="utf-8",
    )

    client = TestClient(create_app())

    ingest_response = client.post(
        "/documents/ingest/local",
        json={"source_uri": str(source)},
    )
    assert ingest_response.status_code == 201

    ask_response = client.post(
        "/ask",
        json={"question": "Who owns the payments service?", "limit": 4},
    )

    assert ask_response.status_code == 200
    payload = ask_response.json()
    assert isinstance(payload["answer"], str)
    assert payload["answer"]
    assert payload["citations"]
    assert payload["citations"][0]["source_uri"] == str(source)
