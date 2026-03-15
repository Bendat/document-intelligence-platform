from typing import Protocol


class TextChunker(Protocol):
    """Split parsed document text into deterministic retrieval chunks."""

    def chunk(self, text: str) -> list[str]: ...
