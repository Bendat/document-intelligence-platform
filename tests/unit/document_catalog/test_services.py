from document_intelligence.adapters.persistence.in_memory import (
    InMemoryChunkRepository,
    InMemoryDocumentRepository,
    InMemoryJobRepository,
)
from document_intelligence.adapters.queue.in_memory import InMemoryTaskDispatcher
from document_intelligence.application.document_catalog.commands import (
    ChunkInput,
    CreateDocumentCommand,
    RecordChunksCommand,
)
from document_intelligence.application.document_catalog.queries import GetDocumentQuery
from document_intelligence.application.document_catalog.services import (
    CreateDocument,
    GetDocument,
    RecordChunks,
)
from document_intelligence.domain.document_catalog.entities import DocumentStatus
from document_intelligence.domain.jobs.entities import JobStatus


def test_create_document_marks_document_pending_and_creates_job() -> None:
    document_repository = InMemoryDocumentRepository()
    job_repository = InMemoryJobRepository()
    dispatcher = InMemoryTaskDispatcher(job_repository=job_repository)

    service = CreateDocument(
        document_repository=document_repository,
        dispatcher=dispatcher,
    )

    document = service.execute(
        CreateDocumentCommand(
            source_uri="file:///docs/runbook.md",
            title="Payments Runbook",
            media_type="text/markdown",
        )
    )

    assert document.status is DocumentStatus.ENRICHMENT_PENDING
    stored_document = document_repository.get(document.id)
    assert stored_document is not None
    assert stored_document.title == "Payments Runbook"
    jobs = list(job_repository._jobs.values())
    assert len(jobs) == 1
    assert jobs[0].document_id == document.id
    assert jobs[0].status is JobStatus.PENDING


def test_get_document_returns_recorded_chunks() -> None:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    job_repository = InMemoryJobRepository()
    dispatcher = InMemoryTaskDispatcher(job_repository=job_repository)

    create_service = CreateDocument(
        document_repository=document_repository,
        dispatcher=dispatcher,
    )
    record_chunks = RecordChunks(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
    )
    get_document = GetDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
    )

    document = create_service.execute(
        CreateDocumentCommand(
            source_uri="file:///docs/adr-001.md",
            title="ADR 001",
            media_type="text/markdown",
        )
    )
    record_chunks.execute(
        RecordChunksCommand(
            document_id=document.id,
            chunks=[
                ChunkInput(index=2, text="Third chunk"),
                ChunkInput(index=0, text="First chunk"),
                ChunkInput(index=1, text="Second chunk"),
            ],
        )
    )

    details = get_document.execute(GetDocumentQuery(document_id=document.id))

    assert details.document.id == document.id
    assert [chunk.text for chunk in details.chunks] == [
        "First chunk",
        "Second chunk",
        "Third chunk",
    ]


def test_record_chunks_replaces_previous_chunk_set_for_document() -> None:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    job_repository = InMemoryJobRepository()
    dispatcher = InMemoryTaskDispatcher(job_repository=job_repository)

    create_service = CreateDocument(
        document_repository=document_repository,
        dispatcher=dispatcher,
    )
    record_chunks = RecordChunks(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
    )
    get_document = GetDocument(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
    )

    document = create_service.execute(
        CreateDocumentCommand(
            source_uri="file:///docs/retry.md",
            title="Retryable Document",
            media_type="text/markdown",
        )
    )
    record_chunks.execute(
        RecordChunksCommand(
            document_id=document.id,
            chunks=[ChunkInput(index=0, text="Old chunk")],
        )
    )
    record_chunks.execute(
        RecordChunksCommand(
            document_id=document.id,
            chunks=[
                ChunkInput(index=0, text="New chunk"),
                ChunkInput(index=1, text="Another chunk"),
            ],
        )
    )

    details = get_document.execute(GetDocumentQuery(document_id=document.id))

    assert [chunk.text for chunk in details.chunks] == ["New chunk", "Another chunk"]
