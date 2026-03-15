from dataclasses import dataclass
from typing import Protocol


class ParserNotFoundError(LookupError):
    """Raised when no parser is registered for the requested media type."""


@dataclass(slots=True)
class ParsedDocument:
    title: str
    text: str
    media_type: str


class DocumentParser(Protocol):
    def parse(self, source_uri: str) -> ParsedDocument: ...


class ParserRegistry(Protocol):
    def for_media_type(self, media_type: str) -> DocumentParser: ...
