from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Protocol

from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
    JobRepository,
)
from document_intelligence.application.common.ports.transactions import (
    TransactionManager,
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

    def list(self) -> Sequence[Document]:
        return list(self._documents.values())

    def snapshot(self) -> dict[str, Document]:
        return deepcopy(self._documents)

    def restore(self, snapshot: dict[str, Document]) -> None:
        self._documents = snapshot


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self) -> None:
        self._chunks_by_document: dict[str, list[Chunk]] = {}

    def replace_for_document(self, document_id: str, chunks: Sequence[Chunk]) -> None:
        self._chunks_by_document[document_id] = list(chunks)

    def for_document(self, document_id: str) -> Sequence[Chunk]:
        return list(self._chunks_by_document.get(document_id, []))

    def snapshot(self) -> dict[str, list[Chunk]]:
        return deepcopy(self._chunks_by_document)

    def restore(self, snapshot: dict[str, list[Chunk]]) -> None:
        self._chunks_by_document = snapshot


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}

    def save(self, job: IngestionJob) -> None:
        self._jobs[job.id] = job

    def get(self, job_id: str) -> IngestionJob | None:
        return self._jobs.get(job_id)

    def snapshot(self) -> dict[str, IngestionJob]:
        return deepcopy(self._jobs)

    def restore(self, snapshot: dict[str, IngestionJob]) -> None:
        self._jobs = snapshot


class SnapshotResource(Protocol):
    def snapshot(self) -> Any: ...

    def restore(self, snapshot: Any) -> None: ...


class InMemoryTransactionManager(TransactionManager):
    def __init__(self, resources: Sequence[SnapshotResource] | None = None) -> None:
        self._resources = list(resources or [])
        self._depth = 0

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._depth > 0:
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return

        snapshots = [(resource, resource.snapshot()) for resource in self._resources]
        self._depth = 1
        try:
            yield
        except Exception:
            for resource, snapshot in snapshots:
                resource.restore(snapshot)
            raise
        finally:
            self._depth = 0
