from dataclasses import dataclass

from document_intelligence.adapters.persistence.in_memory import (
    InMemoryChunkRepository,
    InMemoryDocumentRepository,
    InMemoryJobRepository,
    InMemoryTransactionManager,
)
from document_intelligence.adapters.persistence.postgres import (
    PostgresChunkRepository,
    PostgresDocumentRepository,
    PostgresJobRepository,
    SqlAlchemyTransactionManager,
    create_session_factory,
)
from document_intelligence.adapters.queue.in_memory import InMemoryTaskDispatcher
from document_intelligence.application.common.ports.dispatch import TaskDispatcher
from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
    JobRepository,
)
from document_intelligence.application.common.ports.transactions import (
    TransactionManager,
)
from document_intelligence.config import Settings, get_settings


@dataclass(slots=True)
class ApplicationContainer:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository
    job_repository: JobRepository
    task_dispatcher: TaskDispatcher
    transaction_manager: TransactionManager


def create_in_memory_container() -> ApplicationContainer:
    job_repository = InMemoryJobRepository()
    return ApplicationContainer(
        document_repository=InMemoryDocumentRepository(),
        chunk_repository=InMemoryChunkRepository(),
        job_repository=job_repository,
        task_dispatcher=InMemoryTaskDispatcher(job_repository=job_repository),
        transaction_manager=InMemoryTransactionManager(),
    )


def create_postgres_container(database_url: str) -> ApplicationContainer:
    session_factory = create_session_factory(database_url)
    job_repository = PostgresJobRepository(session_factory=session_factory)
    return ApplicationContainer(
        document_repository=PostgresDocumentRepository(session_factory=session_factory),
        chunk_repository=PostgresChunkRepository(session_factory=session_factory),
        job_repository=job_repository,
        task_dispatcher=InMemoryTaskDispatcher(job_repository=job_repository),
        transaction_manager=SqlAlchemyTransactionManager(
            session_factory=session_factory
        ),
    )


def create_container(settings: Settings | None = None) -> ApplicationContainer:
    resolved_settings = settings if settings is not None else get_settings()
    if resolved_settings.persistence_backend == "postgres":
        return create_postgres_container(database_url=resolved_settings.database_url)
    return create_in_memory_container()
