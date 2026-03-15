import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from document_intelligence.application.common.ports.providers import (
    EmbeddingProvider,
    GenerationProvider,
)
from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
)
from document_intelligence.domain.document_catalog.entities import (
    Chunk,
    Classification,
    Document,
    Summary,
)
from document_intelligence.domain.document_catalog.taxonomy import (
    DOCUMENT_TAXONOMY,
    is_valid_document_label,
)

from .services import DocumentNotFoundError


class DocumentContentUnavailableError(Exception):
    """Raised when no source text is available for enrichment."""


class InvalidProviderResponseError(Exception):
    """Raised when a provider response cannot be parsed safely."""


class EmbeddingCountMismatchError(Exception):
    """Raised when the embedding provider returns an unexpected vector count."""


@dataclass(slots=True)
class EmbedDocumentChunks:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository
    embedding_provider: EmbeddingProvider

    def execute(self, document_id: str) -> list[Chunk]:
        document = self.document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        chunks = list(self.chunk_repository.for_document(document_id))
        if not chunks:
            return []

        embeddings = self.embedding_provider.embed([chunk.text for chunk in chunks])
        if len(embeddings) != len(chunks):
            raise EmbeddingCountMismatchError(
                "Embedding provider returned "
                f"{len(embeddings)} vectors for {len(chunks)} chunks"
            )

        enriched_chunks = [
            Chunk(
                id=chunk.id,
                document_id=chunk.document_id,
                index=chunk.index,
                text=chunk.text,
                embedding=[float(value) for value in embedding],
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self.chunk_repository.replace_for_document(document_id, enriched_chunks)
        return enriched_chunks


@dataclass(slots=True)
class ClassifyDocument:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository
    generation_provider: GenerationProvider
    max_source_chars: int = 12000

    def execute(self, document_id: str) -> Classification:
        document = _load_document(self.document_repository, document_id)
        source_text = _resolve_source_text(
            document=document,
            chunk_repository=self.chunk_repository,
            max_source_chars=self.max_source_chars,
        )

        prompt = _render_prompt(
            "classification_v1.txt",
            taxonomy="\n".join(f"- {label}" for label in DOCUMENT_TAXONOMY),
            document_text=source_text,
        )
        payload = _parse_json_object(self.generation_provider.generate(prompt))

        label_value = payload.get("label")
        if not isinstance(label_value, str):
            raise InvalidProviderResponseError(
                "Classification payload must include a string label."
            )

        label = label_value.strip().lower()
        if not is_valid_document_label(label):
            raise InvalidProviderResponseError(
                f"Classification label is outside taxonomy: {label!r}"
            )

        confidence = _parse_confidence(payload.get("confidence"))
        classification = Classification(label=label, confidence=confidence)
        document.classification = classification
        self.document_repository.save(document)
        return classification


@dataclass(slots=True)
class SummarizeDocument:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository
    generation_provider: GenerationProvider
    max_source_chars: int = 12000

    def execute(self, document_id: str) -> Summary:
        document = _load_document(self.document_repository, document_id)
        source_text = _resolve_source_text(
            document=document,
            chunk_repository=self.chunk_repository,
            max_source_chars=self.max_source_chars,
        )

        prompt = _render_prompt(
            "summary_v1.txt",
            document_text=source_text,
        )
        payload = _parse_json_object(self.generation_provider.generate(prompt))

        summary_value = payload.get("summary")
        if not isinstance(summary_value, str) or not summary_value.strip():
            raise InvalidProviderResponseError(
                "Summary payload must include a non-empty string summary."
            )

        summary = Summary(text=summary_value.strip())
        document.summary = summary
        self.document_repository.save(document)
        return summary


@dataclass(slots=True)
class EnrichDocument:
    document_repository: DocumentRepository
    embed_document_chunks: EmbedDocumentChunks
    classify_document: ClassifyDocument
    summarize_document: SummarizeDocument

    def execute(self, document_id: str) -> Document:
        self.embed_document_chunks.execute(document_id)
        self.classify_document.execute(document_id)
        self.summarize_document.execute(document_id)

        document = _load_document(self.document_repository, document_id)
        document.mark_ready()
        self.document_repository.save(document)
        return document


def _load_document(
    document_repository: DocumentRepository,
    document_id: str,
) -> Document:
    document = document_repository.get(document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)
    return document


def _resolve_source_text(
    document: Document,
    chunk_repository: ChunkRepository,
    max_source_chars: int,
) -> str:
    source_text = document.extracted_text.strip() if document.extracted_text else ""
    if not source_text:
        chunks = chunk_repository.for_document(document.id)
        source_text = "\n\n".join(chunk.text for chunk in chunks).strip()

    if not source_text:
        raise DocumentContentUnavailableError(
            f"Document {document.id} has no extracted text or chunks."
        )

    return source_text[:max_source_chars]


def _parse_confidence(value: Any) -> float | None:
    if value is None:
        return None

    candidate: float
    if isinstance(value, (int, float)):
        candidate = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            candidate = float(stripped)
        except ValueError as error:
            raise InvalidProviderResponseError(
                f"Confidence value is not numeric: {value!r}"
            ) from error
    else:
        raise InvalidProviderResponseError(
            "Confidence value must be numeric, string, or null."
        )

    if candidate < 0 or candidate > 1:
        raise InvalidProviderResponseError(
            f"Confidence value must be between 0 and 1, got {candidate}."
        )
    return candidate


@lru_cache(maxsize=8)
def _load_prompt_template(name: str) -> str:
    path = _prompt_directory() / name
    return path.read_text(encoding="utf-8")


def _render_prompt(name: str, **replacements: str) -> str:
    prompt = _load_prompt_template(name)
    for key, value in replacements.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", value)
    return prompt


def _prompt_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts"


def _parse_json_object(raw_response: str) -> dict[str, Any]:
    text = raw_response.strip()
    direct = _attempt_json_parse(text)
    if direct is not None:
        return direct

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match is not None:
        parsed = _attempt_json_parse(fenced_match.group(1))
        if parsed is not None:
            return parsed

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        parsed = _attempt_json_parse(text[first_brace : last_brace + 1])
        if parsed is not None:
            return parsed

    raise InvalidProviderResponseError("Provider response did not contain JSON object.")


def _attempt_json_parse(candidate: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    return parsed
