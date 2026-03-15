from fastapi.testclient import TestClient

from document_intelligence.app import create_app


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
