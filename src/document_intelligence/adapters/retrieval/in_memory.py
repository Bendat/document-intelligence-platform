from collections.abc import Sequence
from math import sqrt

from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
)
from document_intelligence.application.common.ports.retrieval import (
    RetrievedChunk,
    VectorSearchPort,
)
from document_intelligence.domain.document_catalog.entities import DocumentStatus


class InMemoryVectorSearch(VectorSearchPort):
    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        embedding_model: str | None = None,
    ) -> None:
        self._document_repository = document_repository
        self._chunk_repository = chunk_repository
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

        matches: list[RetrievedChunk] = []
        for document in self._document_repository.list():
            if document.status is not DocumentStatus.READY:
                continue

            for chunk in self._chunk_repository.for_document(document.id):
                if (
                    self._embedding_model is not None
                    and chunk.embedding_model is not None
                    and chunk.embedding_model != self._embedding_model
                ):
                    continue
                chunk_dimensions = (
                    chunk.embedding_dimensions
                    if chunk.embedding_dimensions is not None
                    else len(chunk.embedding)
                )
                if chunk_dimensions != query_dimensions:
                    continue

                score = _cosine_similarity(query_vector, chunk.embedding)
                if score is None:
                    continue

                matches.append(
                    RetrievedChunk(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        source_uri=document.source_uri,
                        document_title=document.title,
                        chunk_index=chunk.index,
                        text=chunk.text,
                        score=score,
                    )
                )

        matches.sort(
            key=lambda hit: (
                -hit.score,
                hit.document_id,
                hit.chunk_index,
                hit.chunk_id,
            )
        )
        return matches[:limit]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float | None:
    if not left or not right:
        return None
    if len(left) != len(right):
        return None

    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return None
    return numerator / (left_norm * right_norm)
