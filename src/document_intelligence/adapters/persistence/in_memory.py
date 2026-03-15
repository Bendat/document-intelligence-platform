from collections.abc import Sequence

from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
    JobRepository,
)
from document_intelligence.domain.document_catalog.entities import Chunk, Document
from document_intelligence.domain.jobs.entities import IngestionJob


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}

    def save(self, document: Document) -> None:
        self._documents[document.id] = document

    def get(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self) -> None:
        self._chunks_by_document: dict[str, list[Chunk]] = {}

    def replace_for_document(self, document_id: str, chunks: Sequence[Chunk]) -> None:
        self._chunks_by_document[document_id] = list(chunks)

    def for_document(self, document_id: str) -> Sequence[Chunk]:
        return list(self._chunks_by_document.get(document_id, []))


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}

    def save(self, job: IngestionJob) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: str) -> IngestionJob | None:
        return self._jobs.get(job_id)
