from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from document_intelligence.adapters.persistence.in_memory import (
    InMemoryChunkRepository,
    InMemoryDocumentRepository,
)
from document_intelligence.app import create_app
from document_intelligence.bootstrap import ApplicationContainer
from document_intelligence.config import get_settings


class BrokenGenerationProvider:
    def generate(self, prompt: str) -> str:
        assert prompt
        return "not json"


class ShortEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        assert texts
        return [[0.1, 0.2]]


def test_create_and_get_document() -> None:
    client = TestClient(create_app())

    create_response = client.post(
        "/documents/ingest",
        json={
            "source_uri": "file:///docs/service-overview.md",
            "title": "Service Overview",
            "media_type": "text/markdown",
        },
    )

    assert create_response.status_code == 201
    created_document = create_response.json()
    assert created_document["status"] == "enrichment_pending"

    get_response = client.get(f"/documents/{created_document['id']}")

    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["document"]["title"] == "Service Overview"
    assert payload["chunks"] == []


def test_get_missing_document_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/documents/missing-document")

    assert response.status_code == 404


def test_local_ingest_endpoint_persists_chunks(tmp_path: Path) -> None:
    source = tmp_path / "runbook.md"
    source.write_text(
        "# Payments Runbook\n\nFirst paragraph.\n\nSecond paragraph with more details.",
        encoding="utf-8",
    )

    client = TestClient(create_app())

    ingest_response = client.post(
        "/documents/ingest/local",
        json={"source_uri": str(source)},
    )

    assert ingest_response.status_code == 201
    created_document = ingest_response.json()
    assert created_document["status"] == "ready"
    assert created_document["title"] == "Payments Runbook"
    assert created_document["classification"] is not None
    assert created_document["summary"] is not None

    get_response = client.get(f"/documents/{created_document['id']}")

    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["document"]["status"] == "ready"
    assert payload["document"]["classification"] is not None
    assert payload["document"]["summary"] is not None
    assert payload["chunks"]
    assert payload["chunks"][0]["embedding"]
    assert isinstance(payload["chunks"][0]["embedding"][0], float)


def test_local_ingest_endpoint_returns_404_for_missing_file(tmp_path: Path) -> None:
    client = TestClient(create_app())

    response = client.post(
        "/documents/ingest/local",
        json={"source_uri": str(tmp_path / 'missing.md')},
    )

    assert response.status_code == 404


def test_local_ingest_endpoint_returns_415_for_unsupported_media_type(
    tmp_path: Path,
) -> None:
    source = tmp_path / "unsupported.pdf"
    source.write_text("synthetic content", encoding="utf-8")

    client = TestClient(create_app())

    response = client.post(
        "/documents/ingest/local",
        json={"source_uri": str(source)},
    )

    assert response.status_code == 415


def test_local_ingest_persists_extracted_text_in_repository(tmp_path: Path) -> None:
    source = tmp_path / "architecture.md"
    source_text = (
        "# Architecture Notes\n\n"
        "Hexagonal boundaries keep application logic independent from adapters."
    )
    source.write_text(source_text, encoding="utf-8")

    app = create_app()
    client = TestClient(app)

    ingest_response = client.post(
        "/documents/ingest/local",
        json={"source_uri": str(source)},
    )

    assert ingest_response.status_code == 201
    document_id = ingest_response.json()["id"]

    get_response = client.get(f"/documents/{document_id}")
    assert get_response.status_code == 200

    container = cast(ApplicationContainer, app.state.container)
    stored_document = container.document_repository.get(document_id)
    assert stored_document is not None
    assert stored_document.extracted_text == source_text


def test_local_ingest_returns_502_when_generation_response_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "runbook.md"
    source.write_text("# Runbook\n\nRecovery details.", encoding="utf-8")

    monkeypatch.setenv("PERSISTENCE_BACKEND", "in_memory")
    get_settings.cache_clear()
    try:
        app = create_app()
        container = cast(ApplicationContainer, app.state.container)
        container.generation_provider = BrokenGenerationProvider()
        client = TestClient(app)

        document_repository = cast(
            InMemoryDocumentRepository, container.document_repository
        )
        chunk_repository = cast(InMemoryChunkRepository, container.chunk_repository)
        before_document_ids = set(document_repository._documents)
        before_chunk_document_ids = set(chunk_repository._chunks_by_document)

        response = client.post(
            "/documents/ingest/local",
            json={"source_uri": str(source)},
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 502
    assert set(document_repository._documents) == before_document_ids
    assert set(chunk_repository._chunks_by_document) == before_chunk_document_ids


def test_local_ingest_returns_502_when_embedding_count_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "long-runbook.md"
    source.write_text(
        f"# Runbook\n\n{'recovery ' * 150}\n\n{'incident ' * 150}",
        encoding="utf-8",
    )

    monkeypatch.setenv("PERSISTENCE_BACKEND", "in_memory")
    get_settings.cache_clear()
    try:
        app = create_app()
        container = cast(ApplicationContainer, app.state.container)
        container.embedding_provider = ShortEmbeddingProvider()
        client = TestClient(app)

        response = client.post(
            "/documents/ingest/local",
            json={"source_uri": str(source)},
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 502


def test_local_ingest_returns_422_for_empty_document_content(
    tmp_path: Path,
) -> None:
    source = tmp_path / "empty.txt"
    source.write_text("", encoding="utf-8")

    client = TestClient(create_app())
    response = client.post(
        "/documents/ingest/local",
        json={"source_uri": str(source)},
    )

    assert response.status_code == 422


def test_local_ingest_endpoint_disabled_outside_development_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "runbook.md"
    source.write_text("# Runbook\n\nSample content.", encoding="utf-8")

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENABLE_LOCAL_FILE_INGESTION", raising=False)
    get_settings.cache_clear()

    try:
        client = TestClient(create_app())
        response = client.post(
            "/documents/ingest/local",
            json={"source_uri": str(source)},
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 404
