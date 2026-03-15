from collections.abc import Sequence

import pytest

from document_intelligence.adapters.persistence.in_memory import (
    InMemoryChunkRepository,
    InMemoryDocumentRepository,
)
from document_intelligence.application.document_catalog.enrichment import (
    ClassifyDocument,
    EmbeddingCountMismatchError,
    EmbedDocumentChunks,
    EnrichDocument,
    InvalidProviderResponseError,
    SummarizeDocument,
)
from document_intelligence.domain.document_catalog.entities import Chunk, Document


class StaticEmbeddingProvider:
    def __init__(self, vectors: Sequence[Sequence[float]]) -> None:
        self._vectors = vectors

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        assert texts
        return self._vectors


class QueueGenerationProvider:
    def __init__(self, responses: Sequence[str]) -> None:
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        assert prompt
        if not self._responses:
            raise AssertionError("No queued responses remain.")
        return self._responses.pop(0)


def test_embed_document_chunks_replaces_embeddings() -> None:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    document = Document(
        id="doc-embeddings",
        source_uri="file:///docs/runbook.md",
        title="Runbook",
        media_type="text/markdown",
        extracted_text="Runbook content",
    )
    document_repository.save(document)
    chunk_repository.replace_for_document(
        document.id,
        [
            Chunk(id="chunk-1", document_id=document.id, index=0, text="First"),
            Chunk(id="chunk-2", document_id=document.id, index=1, text="Second"),
        ],
    )

    service = EmbedDocumentChunks(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        embedding_provider=StaticEmbeddingProvider([[0.1, 0.2], [0.3, 0.4]]),
    )

    service.execute(document.id)

    stored_chunks = list(chunk_repository.for_document(document.id))
    assert stored_chunks[0].embedding == [0.1, 0.2]
    assert stored_chunks[1].embedding == [0.3, 0.4]


def test_embed_document_chunks_raises_on_vector_count_mismatch() -> None:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    document = Document(
        id="doc-vector-mismatch",
        source_uri="file:///docs/mismatch.md",
        title="Mismatch",
        media_type="text/markdown",
        extracted_text="Mismatch text",
    )
    document_repository.save(document)
    chunk_repository.replace_for_document(
        document.id,
        [
            Chunk(id="chunk-1", document_id=document.id, index=0, text="First"),
            Chunk(id="chunk-2", document_id=document.id, index=1, text="Second"),
        ],
    )

    service = EmbedDocumentChunks(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        embedding_provider=StaticEmbeddingProvider([[0.1, 0.2]]),
    )

    with pytest.raises(EmbeddingCountMismatchError):
        service.execute(document.id)


def test_classify_document_stores_structured_result() -> None:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    document = Document(
        id="doc-classify",
        source_uri="file:///docs/runbook.md",
        title="Payments Runbook",
        media_type="text/markdown",
        extracted_text="This runbook includes recovery steps for payment delays.",
    )
    document_repository.save(document)

    service = ClassifyDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        generation_provider=QueueGenerationProvider(
            ['{"label":"runbook","confidence":0.9}']
        ),
    )

    classification = service.execute(document.id)

    assert classification.label == "runbook"
    assert classification.confidence == pytest.approx(0.9)
    stored_document = document_repository.get(document.id)
    assert stored_document is not None
    assert stored_document.classification is not None
    assert stored_document.classification.label == "runbook"


def test_classify_document_rejects_label_outside_taxonomy() -> None:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    document = Document(
        id="doc-invalid-class",
        source_uri="file:///docs/unknown.md",
        title="Unknown",
        media_type="text/markdown",
        extracted_text="Random text",
    )
    document_repository.save(document)

    service = ClassifyDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        generation_provider=QueueGenerationProvider(
            ['{"label":"memo","confidence":0.8}']
        ),
    )

    with pytest.raises(InvalidProviderResponseError):
        service.execute(document.id)


def test_summarize_document_accepts_json_in_markdown_fence() -> None:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    document = Document(
        id="doc-summary",
        source_uri="file:///docs/overview.md",
        title="Overview",
        media_type="text/markdown",
        extracted_text="Service overview with architecture and operational details.",
    )
    document_repository.save(document)

    service = SummarizeDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        generation_provider=QueueGenerationProvider(
            ['```json\n{"summary":"Concise summary text."}\n```']
        ),
    )

    summary = service.execute(document.id)

    assert summary.text == "Concise summary text."
    stored_document = document_repository.get(document.id)
    assert stored_document is not None
    assert stored_document.summary is not None
    assert stored_document.summary.text == "Concise summary text."


def test_enrich_document_embeds_classifies_summarizes_and_marks_ready() -> None:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    document = Document(
        id="doc-enrich",
        source_uri="file:///docs/service-overview.md",
        title="Service Overview",
        media_type="text/markdown",
        extracted_text="Service overview and architecture details.",
    )
    document.mark_enrichment_pending()
    document_repository.save(document)
    chunk_repository.replace_for_document(
        document.id,
        [
            Chunk(id="chunk-1", document_id=document.id, index=0, text="Overview"),
            Chunk(id="chunk-2", document_id=document.id, index=1, text="Architecture"),
        ],
    )

    embed = EmbedDocumentChunks(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        embedding_provider=StaticEmbeddingProvider([[0.01, 0.02], [0.03, 0.04]]),
    )
    generation_provider = QueueGenerationProvider(
        [
            '{"label":"architecture-doc","confidence":0.77}',
            '{"summary":"A concise technical summary."}',
        ]
    )
    classify = ClassifyDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        generation_provider=generation_provider,
    )
    summarize = SummarizeDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        generation_provider=generation_provider,
    )
    service = EnrichDocument(
        document_repository=document_repository,
        embed_document_chunks=embed,
        classify_document=classify,
        summarize_document=summarize,
    )

    enriched_document = service.execute(document.id)

    assert enriched_document.status.value == "ready"
    assert enriched_document.classification is not None
    assert enriched_document.classification.label == "architecture-doc"
    assert enriched_document.summary is not None
    assert enriched_document.summary.text == "A concise technical summary."
    stored_chunks = list(chunk_repository.for_document(document.id))
    assert stored_chunks[0].embedding == [0.01, 0.02]
    assert stored_chunks[1].embedding == [0.03, 0.04]
