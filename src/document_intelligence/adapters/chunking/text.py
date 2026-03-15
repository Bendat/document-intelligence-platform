from document_intelligence.application.common.ports.chunking import TextChunker


class DeterministicTextChunker(TextChunker):
    """Chunk text by stable character windows while preserving paragraph flow."""

    def __init__(self, max_chunk_chars: int = 1000) -> None:
        if max_chunk_chars < 100:
            raise ValueError("max_chunk_chars must be >= 100")
        self._max_chunk_chars = max_chunk_chars

    def chunk(self, text: str) -> list[str]:
        normalized = text.replace("\r\n", "\n").strip()
        if not normalized:
            return []

        chunks: list[str] = []
        current = ""

        for paragraph in _paragraphs(normalized):
            if len(paragraph) > self._max_chunk_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(_split_long(paragraph, self._max_chunk_chars))
                continue

            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if len(candidate) <= self._max_chunk_chars:
                current = candidate
            else:
                chunks.append(current)
                current = paragraph

        if current:
            chunks.append(current)

        return chunks


def _paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]


def _split_long(text: str, max_chars: int) -> list[str]:
    segments: list[str] = []
    remainder = text

    while len(remainder) > max_chars:
        segment = remainder[:max_chars]
        split_at = segment.rfind(" ")
        if split_at <= max_chars // 2:
            split_at = max_chars
        segments.append(remainder[:split_at].strip())
        remainder = remainder[split_at:].strip()

    if remainder:
        segments.append(remainder)

    return segments
