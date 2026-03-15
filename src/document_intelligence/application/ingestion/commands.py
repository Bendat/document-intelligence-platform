from dataclasses import dataclass


@dataclass(slots=True)
class IngestLocalDocumentCommand:
    source_uri: str
    title: str | None = None
    media_type: str | None = None
