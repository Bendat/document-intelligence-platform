from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class RetrievalBackendSchemaError(Exception):
    """Raised when the retrieval backend schema is missing required fields."""


@dataclass(slots=True, frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    source_uri: str
    document_title: str
    chunk_index: int
    text: str
    score: float


class VectorSearchPort(Protocol):
    def search(
        self,
        query_embedding: Sequence[float],
        limit: int,
    ) -> Sequence[RetrievedChunk]: ...
