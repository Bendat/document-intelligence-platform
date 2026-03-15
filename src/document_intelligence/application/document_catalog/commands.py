from dataclasses import dataclass


@dataclass(slots=True)
class CreateDocumentCommand:
    source_uri: str
    title: str
    media_type: str


@dataclass(slots=True)
class ChunkInput:
    index: int
    text: str


@dataclass(slots=True)
class RecordChunksCommand:
    document_id: str
    chunks: list[ChunkInput]
