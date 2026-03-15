from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import pytest

from document_intelligence.adapters.chunking.text import DeterministicTextChunker
from document_intelligence.adapters.parsing.local_files import (
    create_default_local_file_parser_registry,
)
from document_intelligence.adapters.persistence.in_memory import (
    InMemoryChunkRepository,
    InMemoryDocumentRepository,
)
from document_intelligence.application.common.ports.transactions import (
    TransactionManager,
)
from document_intelligence.application.ingestion.commands import (
    IngestLocalDocumentCommand,
)
from document_intelligence.application.ingestion.services import (
    IngestLocalDocument,
    InvalidSourceError,
    SourceNotFoundError,
    UnsupportedMediaTypeError,
)
from document_intelligence.domain.document_catalog.entities import (
    Chunk,
    Document,
    DocumentStatus,
)


class CountingDocumentRepository(InMemoryDocumentRepository):
    def __init__(self) -> None:
        super().__init__()
        self.save_calls = 0

    def save(self, document: Document) -> None:
        self.save_calls += 1
        super().save(document)


class CountingChunkRepository(InMemoryChunkRepository):
    def __init__(self) -> None:
        super().__init__()
        self.replace_calls = 0

    def replace_for_document(
        self,
        document_id: str,
        chunks: Sequence[Chunk],
    ) -> None:
        self.replace_calls += 1
        super().replace_for_document(document_id=document_id, chunks=chunks)


class CountingTransactionManager(TransactionManager):
    def __init__(self) -> None:
        self.entered = 0

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.entered += 1
        yield


def test_ingest_local_markdown_document_persists_document_and_chunks(
    tmp_path: Path,
) -> None:
    source = tmp_path / "service-overview.md"
    source.write_text(
        "# Service Overview\n\n"
        "This is the first paragraph in the document.\n\n"
        "This second paragraph is intentionally long so we can validate that "
        "deterministic chunking keeps ordering stable for retrieval.",
        encoding="utf-8",
    )

    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    service = IngestLocalDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        parser_registry=create_default_local_file_parser_registry(),
        chunker=DeterministicTextChunker(max_chunk_chars=120),
        transaction_manager=CountingTransactionManager(),
    )

    result = service.execute(
        IngestLocalDocumentCommand(
            source_uri=str(source),
        )
    )

    assert result.document.title == "Service Overview"
    assert result.document.media_type == "text/markdown"
    assert result.document.status is DocumentStatus.READY

    stored_document = document_repository.get(result.document.id)
    assert stored_document is not None
    assert stored_document.status is DocumentStatus.READY
    assert stored_document.extracted_text is not None
    assert "This is the first paragraph" in stored_document.extracted_text

    stored_chunks = list(chunk_repository.for_document(result.document.id))
    assert len(stored_chunks) >= 2
    assert [chunk.index for chunk in stored_chunks] == list(range(len(stored_chunks)))
    assert [chunk.text for chunk in stored_chunks] == [
        chunk.text for chunk in result.chunks
    ]


def test_ingest_local_document_raises_when_source_is_missing(tmp_path: Path) -> None:
    missing_source = tmp_path / "missing.md"

    document_repository = CountingDocumentRepository()
    chunk_repository = CountingChunkRepository()
    transaction_manager = CountingTransactionManager()
    service = IngestLocalDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        parser_registry=create_default_local_file_parser_registry(),
        chunker=DeterministicTextChunker(),
        transaction_manager=transaction_manager,
    )

    with pytest.raises(SourceNotFoundError, match="Source file not found"):
        service.execute(IngestLocalDocumentCommand(source_uri=str(missing_source)))

    assert transaction_manager.entered == 0
    assert document_repository.save_calls == 0
    assert chunk_repository.replace_calls == 0


def test_ingest_local_document_raises_for_unsupported_media_type(
    tmp_path: Path,
) -> None:
    source = tmp_path / "design.pdf"
    source.write_text(
        "This is not a real PDF but keeps extension-based detection simple."
    )

    service = IngestLocalDocument(
        document_repository=InMemoryDocumentRepository(),
        chunk_repository=InMemoryChunkRepository(),
        parser_registry=create_default_local_file_parser_registry(),
        chunker=DeterministicTextChunker(),
        transaction_manager=CountingTransactionManager(),
    )

    with pytest.raises(UnsupportedMediaTypeError, match="Unsupported media type"):
        service.execute(IngestLocalDocumentCommand(source_uri=str(source)))


def test_ingest_local_document_rejects_remote_source_uri() -> None:
    service = IngestLocalDocument(
        document_repository=InMemoryDocumentRepository(),
        chunk_repository=InMemoryChunkRepository(),
        parser_registry=create_default_local_file_parser_registry(),
        chunker=DeterministicTextChunker(),
        transaction_manager=CountingTransactionManager(),
    )

    with pytest.raises(InvalidSourceError, match="Only local file paths"):
        service.execute(
            IngestLocalDocumentCommand(
                source_uri="https://example.com/service-overview.md",
                media_type="text/markdown",
            )
        )
