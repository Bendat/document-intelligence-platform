from dataclasses import dataclass
from uuid import uuid4

from document_intelligence.application.common.ports.dispatch import TaskDispatcher
from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
)
from document_intelligence.application.common.ports.transactions import (
    TransactionManager,
)
from document_intelligence.application.document_catalog.commands import (
    CreateDocumentCommand,
    RecordChunksCommand,
)
from document_intelligence.application.document_catalog.queries import GetDocumentQuery
from document_intelligence.domain.document_catalog.entities import Chunk, Document


class DocumentNotFoundError(Exception):
    """Raised when a requested document does not exist."""


@dataclass(slots=True)
class DocumentDetails:
    """Document plus its stored chunks for read-side API responses."""

    document: Document
    chunks: list[Chunk]


@dataclass(slots=True)
class CreateDocument:
    document_repository: DocumentRepository
    dispatcher: TaskDispatcher
    transaction_manager: TransactionManager | None = None

    def execute(self, command: CreateDocumentCommand) -> Document:
        """Create a document record and queue it for enrichment.

        At this stage "enrichment" means later processing steps such as parsing,
        chunking, embeddings, classification, and summarization.
        """

        if self.transaction_manager is None:
            return self._execute(command)

        with self.transaction_manager.transaction():
            return self._execute(command)

    def _execute(self, command: CreateDocumentCommand) -> Document:
        document = Document(
            id=str(uuid4()),
            source_uri=command.source_uri,
            title=command.title,
            media_type=command.media_type,
        )
        document.mark_enrichment_pending()
        self.document_repository.save(document)
        self.dispatcher.enqueue_enrichment(document.id)
        return document


@dataclass(slots=True)
class GetDocument:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository

    def execute(self, query: GetDocumentQuery) -> DocumentDetails:
        """Load a document and return its chunks in source order."""

        document = self.document_repository.get(query.document_id)
        if document is None:
            raise DocumentNotFoundError(query.document_id)

        chunks = sorted(
            self.chunk_repository.for_document(query.document_id),
            key=lambda chunk: chunk.index,
        )
        return DocumentDetails(document=document, chunks=chunks)


@dataclass(slots=True)
class RecordChunks:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository

    def execute(self, command: RecordChunksCommand) -> list[Chunk]:
        """Replace the stored chunk set for a document.

        Chunk recording is treated as idempotent for a given document so a retry
        of parsing or chunking does not leave duplicate passages behind.
        """

        document = self.document_repository.get(command.document_id)
        if document is None:
            raise DocumentNotFoundError(command.document_id)

        chunks = [
            Chunk(
                id=str(uuid4()),
                document_id=document.id,
                index=chunk.index,
                text=chunk.text,
            )
            for chunk in command.chunks
        ]
        self.chunk_repository.replace_for_document(document.id, chunks)
        return chunks
