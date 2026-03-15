from dataclasses import dataclass, field
from enum import StrEnum


class DocumentStatus(StrEnum):
    """High-level lifecycle state for a document in the ingestion pipeline."""

    CREATED = "created"
    ENRICHMENT_PENDING = "enrichment_pending"
    READY = "ready"


@dataclass(slots=True)
class Classification:
    label: str
    confidence: float | None = None


@dataclass(slots=True)
class Summary:
    text: str


@dataclass(slots=True)
class Citation:
    """A reference back to the source chunk used to support an answer."""

    chunk_id: str
    source_uri: str


@dataclass(slots=True)
class Chunk:
    """A smaller unit of document text used for retrieval and citation.

    Long documents are split into chunks so search and question-answering can
    work with focused passages instead of whole files. `index` preserves the
    original document order.
    """

    id: str
    document_id: str
    index: int
    text: str
    embedding: list[float] = field(default_factory=list)


@dataclass(slots=True)
class Document:
    """Metadata and enrichment state for a source document."""

    id: str
    source_uri: str
    title: str
    media_type: str
    status: DocumentStatus = DocumentStatus.CREATED
    classification: Classification | None = None
    summary: Summary | None = None

    def mark_enrichment_pending(self) -> None:
        """Mark the document as waiting for downstream enrichment work."""

        self.status = DocumentStatus.ENRICHMENT_PENDING
