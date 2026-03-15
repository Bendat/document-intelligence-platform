from collections.abc import Sequence
from typing import NoReturn

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
    JobRepository,
)
from document_intelligence.domain.document_catalog.entities import (
    Chunk,
    Classification,
    Document,
    DocumentStatus,
    Summary,
)
from document_intelligence.domain.jobs.entities import IngestionJob, JobStatus

from .models import ChunkModel, DocumentModel, JobModel
from .session import read_session, write_session


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, document: Document) -> None:
        with write_session(self._session_factory) as (session, should_commit):
            model = session.get(DocumentModel, document.id)
            if model is None:
                model = DocumentModel(
                    id=document.id,
                    source_uri=document.source_uri,
                    title=document.title,
                    media_type=document.media_type,
                    extracted_text=document.extracted_text,
                    status=document.status.value,
                )
            model.source_uri = document.source_uri
            model.title = document.title
            model.media_type = document.media_type
            model.extracted_text = document.extracted_text
            model.status = document.status.value
            model.classification_label = (
                document.classification.label
                if document.classification is not None
                else None
            )
            model.classification_confidence = (
                document.classification.confidence
                if document.classification is not None
                else None
            )
            model.summary_text = (
                document.summary.text if document.summary is not None else None
            )
            session.add(model)
            if should_commit:
                session.commit()

    def get(self, document_id: str) -> Document | None:
        with read_session(self._session_factory) as session:
            model = session.get(DocumentModel, document_id)
            if model is None:
                return None
            return _document_from_model(model)


class PostgresChunkRepository(ChunkRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def replace_for_document(self, document_id: str, chunks: Sequence[Chunk]) -> None:
        with write_session(self._session_factory) as (session, should_commit):
            if should_commit:
                with session.begin():
                    _replace_chunks(session, document_id=document_id, chunks=chunks)
                return
            _replace_chunks(session, document_id=document_id, chunks=chunks)

    def for_document(self, document_id: str) -> Sequence[Chunk]:
        statement = (
            select(ChunkModel)
            .where(ChunkModel.document_id == document_id)
            .order_by(ChunkModel.chunk_index.asc(), ChunkModel.id.asc())
        )
        with read_session(self._session_factory) as session:
            models = session.scalars(statement).all()
            return [_chunk_from_model(model) for model in models]


class PostgresJobRepository(JobRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, job: IngestionJob) -> None:
        with write_session(self._session_factory) as (session, should_commit):
            model = session.get(JobModel, job.id)
            if model is None:
                model = JobModel(
                    id=job.id,
                    document_id=job.document_id,
                    status=job.status.value,
                )
            model.document_id = job.document_id
            model.status = job.status.value
            session.add(model)
            if should_commit:
                session.commit()

    def get(self, job_id: str) -> IngestionJob | None:
        with read_session(self._session_factory) as session:
            model = session.get(JobModel, job_id)
            if model is None:
                return None
            return IngestionJob(
                id=model.id,
                document_id=model.document_id,
                status=JobStatus(model.status),
            )


def _document_from_model(model: DocumentModel) -> Document:
    classification = None
    if model.classification_label is not None:
        classification = Classification(
            label=model.classification_label,
            confidence=model.classification_confidence,
        )

    summary = (
        Summary(text=model.summary_text) if model.summary_text is not None else None
    )

    return Document(
        id=model.id,
        source_uri=model.source_uri,
        title=model.title,
        media_type=model.media_type,
        extracted_text=model.extracted_text,
        status=DocumentStatus(model.status),
        classification=classification,
        summary=summary,
    )


def _chunk_from_model(model: ChunkModel) -> Chunk:
    return Chunk(
        id=model.id,
        document_id=model.document_id,
        index=model.chunk_index,
        text=model.text,
        embedding=list(model.embedding) if model.embedding is not None else [],
    )


def _replace_chunks(
    session: Session,
    document_id: str,
    chunks: Sequence[Chunk],
) -> None:
    session.execute(delete(ChunkModel).where(ChunkModel.document_id == document_id))
    models_to_insert: list[ChunkModel] = []
    for chunk in chunks:
        if chunk.document_id != document_id:
            _raise_chunk_document_mismatch(chunk.id, chunk.document_id, document_id)
        models_to_insert.append(
            ChunkModel(
                id=chunk.id,
                document_id=document_id,
                chunk_index=chunk.index,
                text=chunk.text,
                embedding=list(chunk.embedding) if chunk.embedding else None,
            )
        )

    session.add_all(
        models_to_insert
    )


def _raise_chunk_document_mismatch(
    chunk_id: str,
    chunk_document_id: str,
    expected_document_id: str,
) -> NoReturn:
    raise ValueError(
        "Chunk document_id mismatch for chunk "
        f"{chunk_id}: expected {expected_document_id}, got {chunk_document_id}"
    )
