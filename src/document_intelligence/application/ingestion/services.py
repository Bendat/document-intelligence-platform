import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse
from uuid import uuid4

from document_intelligence.application.common.ports.chunking import TextChunker
from document_intelligence.application.common.ports.parsers import (
    DocumentParser,
    ParsedDocument,
    ParserNotFoundError,
    ParserRegistry,
)
from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
)
from document_intelligence.application.common.ports.transactions import (
    TransactionManager,
)
from document_intelligence.application.ingestion.commands import (
    IngestLocalDocumentCommand,
)
from document_intelligence.domain.document_catalog.entities import Chunk, Document

if TYPE_CHECKING:
    from document_intelligence.application.document_catalog.enrichment import (
        EnrichDocument,
    )


class SourceNotFoundError(Exception):
    """Raised when a local document source cannot be found."""


class InvalidSourceError(Exception):
    """Raised when a document source URI is invalid for local ingestion."""


class UnsupportedMediaTypeError(Exception):
    """Raised when no parser is registered for a media type."""


@dataclass(slots=True)
class IngestionResult:
    document: Document
    chunks: list[Chunk]


@dataclass(slots=True)
class IngestLocalDocument:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository
    parser_registry: ParserRegistry
    chunker: TextChunker
    transaction_manager: TransactionManager | None = None
    enrich_document: "EnrichDocument | None" = None

    def execute(self, command: IngestLocalDocumentCommand) -> IngestionResult:
        result = self._prepare(command)
        if self.transaction_manager is None:
            self._persist(result)
            self._enrich_if_configured(result.document.id)
            return self._load_persisted_result(result)

        with self.transaction_manager.transaction():
            self._persist(result)
            self._enrich_if_configured(result.document.id)
            return self._load_persisted_result(result)

    def _prepare(self, command: IngestLocalDocumentCommand) -> IngestionResult:
        media_type = _resolve_media_type(command)
        parser = _resolve_parser(self.parser_registry, media_type)
        parsed = _parse_document(parser, command.source_uri)

        document = Document(
            id=str(uuid4()),
            source_uri=command.source_uri,
            title=command.title or parsed.title,
            media_type=parsed.media_type,
            extracted_text=parsed.text,
        )
        if self.enrich_document is None:
            document.mark_ready()
        else:
            document.mark_enrichment_pending()

        chunks = [
            Chunk(
                id=str(uuid4()),
                document_id=document.id,
                index=index,
                text=chunk_text,
            )
            for index, chunk_text in enumerate(self.chunker.chunk(parsed.text))
        ]

        return IngestionResult(document=document, chunks=chunks)

    def _persist(self, result: IngestionResult) -> None:
        self.document_repository.save(result.document)
        self.chunk_repository.replace_for_document(
            result.document.id,
            result.chunks,
        )

    def _enrich_if_configured(self, document_id: str) -> None:
        if self.enrich_document is None:
            return
        self.enrich_document.execute(document_id)

    def _load_persisted_result(self, fallback: IngestionResult) -> IngestionResult:
        document = self.document_repository.get(fallback.document.id)
        if document is None:
            return fallback

        chunks = list(self.chunk_repository.for_document(document.id))
        return IngestionResult(document=document, chunks=chunks)


def _resolve_media_type(command: IngestLocalDocumentCommand) -> str:
    if command.media_type is not None:
        return _normalize_media_type(command.media_type)

    inferred = _infer_media_type(command.source_uri)
    if inferred is None:
        raise UnsupportedMediaTypeError(
            f"Unsupported media type for source URI: {command.source_uri}"
        )
    return inferred


def _resolve_parser(registry: ParserRegistry, media_type: str) -> DocumentParser:
    try:
        return registry.for_media_type(media_type)
    except ParserNotFoundError as error:
        raise UnsupportedMediaTypeError(
            f"Unsupported media type: {media_type}"
        ) from error


def _parse_document(parser: DocumentParser, source_uri: str) -> ParsedDocument:
    try:
        return parser.parse(source_uri)
    except FileNotFoundError as error:
        raise SourceNotFoundError(f"Source file not found: {source_uri}") from error
    except ValueError as error:
        raise InvalidSourceError(str(error)) from error
    except OSError as error:
        raise InvalidSourceError(f"Unable to read source file: {error}") from error


def _normalize_media_type(media_type: str) -> str:
    normalized = media_type.split(";", maxsplit=1)[0].strip().lower()
    if not normalized:
        raise UnsupportedMediaTypeError("Media type cannot be empty")
    return normalized


def _infer_media_type(source_uri: str) -> str | None:
    parsed = urlparse(source_uri)
    path = source_uri
    if parsed.scheme == "file":
        path = unquote(parsed.path)

    suffix = Path(path).suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "text/markdown"
    if suffix in {".txt", ".text"}:
        return "text/plain"

    guessed, _ = mimetypes.guess_type(path)
    if guessed is None:
        return None
    return _normalize_media_type(guessed)
