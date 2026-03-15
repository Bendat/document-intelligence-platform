from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from document_intelligence.application.common.ports.parsers import (
    DocumentParser,
    ParsedDocument,
    ParserNotFoundError,
    ParserRegistry,
)


@dataclass(slots=True)
class LocalFileContent:
    path: Path
    text: str


class LocalFileSourceReader:
    """Read UTF-8 local files from file:// URIs or filesystem paths."""

    def read(self, source_uri: str) -> LocalFileContent:
        path = self.resolve_path(source_uri)
        if not path.exists():
            raise FileNotFoundError(path)
        if not path.is_file():
            raise ValueError(f"Source is not a file: {path}")
        return LocalFileContent(path=path, text=path.read_text(encoding="utf-8"))

    def resolve_path(self, source_uri: str) -> Path:
        if _is_windows_absolute_path(source_uri):
            return Path(source_uri).expanduser().resolve()

        parsed = urlparse(source_uri)
        if parsed.scheme not in {"", "file"}:
            raise ValueError(
                "Only local file paths or file:// URIs are supported for ingestion"
            )

        if parsed.scheme == "file":
            if parsed.netloc not in {"", "localhost"}:
                raise ValueError(
                    "Only local file paths or file:// URIs are supported for ingestion"
                )
            raw_path = unquote(parsed.path)
            if not raw_path:
                raise ValueError("File URI must include a path")
            return Path(raw_path).expanduser().resolve()

        return Path(source_uri).expanduser().resolve()


class PlainTextLocalFileParser(DocumentParser):
    def __init__(self, reader: LocalFileSourceReader) -> None:
        self._reader = reader

    def parse(self, source_uri: str) -> ParsedDocument:
        content = self._reader.read(source_uri)
        return ParsedDocument(
            title=content.path.stem,
            text=content.text,
            media_type="text/plain",
        )


class MarkdownLocalFileParser(DocumentParser):
    def __init__(self, reader: LocalFileSourceReader) -> None:
        self._reader = reader

    def parse(self, source_uri: str) -> ParsedDocument:
        content = self._reader.read(source_uri)
        return ParsedDocument(
            title=_extract_markdown_title(content.text) or content.path.stem,
            text=content.text,
            media_type="text/markdown",
        )


class MediaTypeParserRegistry(ParserRegistry):
    def __init__(self, parsers: dict[str, DocumentParser]) -> None:
        self._parsers = {key.lower(): parser for key, parser in parsers.items()}

    def for_media_type(self, media_type: str) -> DocumentParser:
        normalized = media_type.split(";", maxsplit=1)[0].strip().lower()
        parser = self._parsers.get(normalized)
        if parser is None:
            raise ParserNotFoundError(normalized)
        return parser


def create_default_local_file_parser_registry() -> ParserRegistry:
    reader = LocalFileSourceReader()
    return MediaTypeParserRegistry(
        parsers={
            "text/plain": PlainTextLocalFileParser(reader=reader),
            "text/markdown": MarkdownLocalFileParser(reader=reader),
        }
    )


def _extract_markdown_title(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and len(stripped) > 2:
            return stripped[2:].strip()
    return None


def _is_windows_absolute_path(value: str) -> bool:
    if len(value) < 3:
        return False
    return value[0].isalpha() and value[1] == ":" and value[2] in {"\\", "/"}
