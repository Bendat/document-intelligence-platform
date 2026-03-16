from collections.abc import Sequence

from psycopg.errors import UndefinedColumn
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from document_intelligence.adapters.persistence.postgres.models import (
    ChunkModel,
    DocumentModel,
)
from document_intelligence.adapters.persistence.postgres.session import read_session
from document_intelligence.application.common.ports.retrieval import (
    RetrievalBackendSchemaError,
    RetrievedChunk,
    VectorSearchPort,
)
from document_intelligence.domain.document_catalog.entities import DocumentStatus


class PgvectorVectorSearch(VectorSearchPort):
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        embedding_model: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_model = embedding_model

    def search(
        self,
        query_embedding: Sequence[float],
        limit: int,
    ) -> Sequence[RetrievedChunk]:
        if limit <= 0:
            return []

        query_vector = [float(value) for value in query_embedding]
        if not query_vector:
            return []
        query_dimensions = len(query_vector)

        distance_expr = ChunkModel.embedding.cosine_distance(query_vector)
        where_conditions = [
            ChunkModel.embedding.is_not(None),
            _embedding_dimensions_match(query_dimensions),
            DocumentModel.status == DocumentStatus.READY.value,
        ]
        if self._embedding_model is not None:
            where_conditions.append(_embedding_model_matches(self._embedding_model))
        statement = (
            select(
                ChunkModel,
                DocumentModel.source_uri,
                DocumentModel.title,
                distance_expr.label("distance"),
            )
            .join(DocumentModel, DocumentModel.id == ChunkModel.document_id)
            .where(*where_conditions)
            .order_by(distance_expr.asc(), ChunkModel.id.asc())
            .limit(limit)
        )

        try:
            with read_session(self._session_factory) as session:
                rows = session.execute(statement).all()
        except ProgrammingError as error:
            if _is_missing_embedding_metadata(error):
                raise RetrievalBackendSchemaError(
                    "Retrieval schema is out of date. "
                    "Run `alembic upgrade head` or `make db-upgrade`."
                ) from error
            raise

        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                source_uri=source_uri,
                document_title=title,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                score=_distance_to_score(float(distance)),
            )
            for chunk, source_uri, title, distance in rows
        ]


def _embedding_dimensions_match(query_dimensions: int) -> ColumnElement[bool]:
    return or_(
        ChunkModel.embedding_dimensions == query_dimensions,
        and_(
            ChunkModel.embedding_dimensions.is_(None),
            func.vector_dims(ChunkModel.embedding) == query_dimensions,
        ),
    )


def _embedding_model_matches(embedding_model: str) -> ColumnElement[bool]:
    return or_(
        ChunkModel.embedding_model == embedding_model,
        ChunkModel.embedding_model.is_(None),
    )


def _distance_to_score(distance: float) -> float:
    if distance < 0:
        return 1.0 / (1.0 + abs(distance))
    return 1.0 / (1.0 + distance)


def _is_missing_embedding_metadata(error: ProgrammingError) -> bool:
    if not isinstance(error.orig, UndefinedColumn):
        return False

    message = str(error.orig)
    return (
        "chunks.embedding_model" in message
        or "chunks.embedding_dimensions" in message
    )
