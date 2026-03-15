from dataclasses import dataclass


@dataclass(slots=True)
class GetDocumentQuery:
    document_id: str
