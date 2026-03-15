from collections.abc import Sequence
from typing import Protocol

from document_intelligence.domain.document_catalog.entities import Chunk, Document
from document_intelligence.domain.jobs.entities import IngestionJob


class DocumentRepository(Protocol):
    def save(self, document: Document) -> None: ...

    def get(self, document_id: str) -> Document | None: ...


class ChunkRepository(Protocol):
    """Store and load retrieval-ready chunks associated with a document."""

    def replace_for_document(
        self,
        document_id: str,
        chunks: Sequence[Chunk],
    ) -> None: ...

    def for_document(self, document_id: str) -> Sequence[Chunk]: ...


class JobRepository(Protocol):
    def save(self, job: IngestionJob) -> None: ...

    def get(self, job_id: str) -> IngestionJob | None: ...
