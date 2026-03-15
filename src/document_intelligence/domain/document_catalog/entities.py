from dataclasses import dataclass, field


@dataclass(slots=True)
class Classification:
    label: str
    confidence: float | None = None


@dataclass(slots=True)
class Summary:
    text: str


@dataclass(slots=True)
class Citation:
    chunk_id: str
    source_uri: str


@dataclass(slots=True)
class Chunk:
    id: str
    document_id: str
    index: int
    text: str
    embedding: list[float] = field(default_factory=list)


@dataclass(slots=True)
class Document:
    id: str
    source_uri: str
    title: str
    media_type: str
    classification: Classification | None = None
    summary: Summary | None = None
