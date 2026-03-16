from document_intelligence.adapters.persistence.in_memory import (
    InMemoryChunkRepository,
    InMemoryDocumentRepository,
)
from document_intelligence.adapters.retrieval import InMemoryVectorSearch
from document_intelligence.domain.document_catalog.entities import (
    Chunk,
    Document,
    DocumentStatus,
)


def test_in_memory_vector_search_filters_mismatched_model_and_dimensions() -> None:
    documents = InMemoryDocumentRepository()
    chunks = InMemoryChunkRepository()

    ready_document = Document(
        id="doc-1",
        source_uri="file:///docs/one.md",
        title="One",
        media_type="text/markdown",
        status=DocumentStatus.READY,
    )
    documents.save(ready_document)

    chunks.replace_for_document(
        ready_document.id,
        [
            Chunk(
                id="chunk-valid",
                document_id=ready_document.id,
                index=0,
                text="Valid",
                embedding=[1.0, 0.0, 0.0],
                embedding_model="embed-v1",
                embedding_dimensions=3,
            ),
            Chunk(
                id="chunk-model-mismatch",
                document_id=ready_document.id,
                index=1,
                text="Model mismatch",
                embedding=[1.0, 0.0, 0.0],
                embedding_model="embed-v2",
                embedding_dimensions=3,
            ),
            Chunk(
                id="chunk-dim-mismatch",
                document_id=ready_document.id,
                index=2,
                text="Dim mismatch",
                embedding=[1.0, 0.0],
                embedding_model="embed-v1",
                embedding_dimensions=2,
            ),
        ],
    )

    search = InMemoryVectorSearch(
        document_repository=documents,
        chunk_repository=chunks,
        embedding_model="embed-v1",
    )

    hits = search.search(query_embedding=[1.0, 0.0, 0.0], limit=5)

    assert [hit.chunk_id for hit in hits] == ["chunk-valid"]


def test_in_memory_vector_search_includes_legacy_chunks_without_metadata() -> None:
    documents = InMemoryDocumentRepository()
    chunks = InMemoryChunkRepository()

    ready_document = Document(
        id="doc-1",
        source_uri="file:///docs/legacy.md",
        title="Legacy",
        media_type="text/markdown",
        status=DocumentStatus.READY,
    )
    documents.save(ready_document)

    chunks.replace_for_document(
        ready_document.id,
        [
            Chunk(
                id="chunk-legacy",
                document_id=ready_document.id,
                index=0,
                text="Legacy metadata",
                embedding=[1.0, 0.0, 0.0],
            )
        ],
    )

    search = InMemoryVectorSearch(
        document_repository=documents,
        chunk_repository=chunks,
        embedding_model="embed-v1",
    )

    hits = search.search(query_embedding=[1.0, 0.0, 0.0], limit=5)

    assert [hit.chunk_id for hit in hits] == ["chunk-legacy"]
