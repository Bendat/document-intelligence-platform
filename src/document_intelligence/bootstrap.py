from dataclasses import dataclass

from document_intelligence.adapters.persistence.in_memory import (
    InMemoryChunkRepository,
    InMemoryDocumentRepository,
    InMemoryJobRepository,
)
from document_intelligence.adapters.queue.in_memory import InMemoryTaskDispatcher
from document_intelligence.application.common.ports.dispatch import TaskDispatcher
from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
    JobRepository,
)


@dataclass(slots=True)
class ApplicationContainer:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository
    job_repository: JobRepository
    task_dispatcher: TaskDispatcher


def create_container() -> ApplicationContainer:
    job_repository = InMemoryJobRepository()
    return ApplicationContainer(
        document_repository=InMemoryDocumentRepository(),
        chunk_repository=InMemoryChunkRepository(),
        job_repository=job_repository,
        task_dispatcher=InMemoryTaskDispatcher(job_repository=job_repository),
    )
