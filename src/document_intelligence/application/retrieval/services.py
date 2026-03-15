import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from document_intelligence.application.common.ports.providers import (
    EmbeddingProvider,
    GenerationProvider,
)
from document_intelligence.application.common.ports.retrieval import (
    RetrievedChunk,
    VectorSearchPort,
)
from document_intelligence.application.retrieval.queries import (
    AskQuestionQuery,
    SemanticSearchQuery,
)


class QueryEmbeddingCountMismatchError(Exception):
    """Raised when query embedding generation returns an unexpected shape."""


@dataclass(slots=True)
class SemanticSearch:
    embedding_provider: EmbeddingProvider
    vector_search: VectorSearchPort

    def execute(self, query: SemanticSearchQuery) -> list[RetrievedChunk]:
        embeddings = self.embedding_provider.embed([query.query])
        if len(embeddings) != 1:
            raise QueryEmbeddingCountMismatchError(
                "Embedding provider returned "
                f"{len(embeddings)} vectors for a single query"
            )

        query_embedding = [float(value) for value in embeddings[0]]
        if not query_embedding:
            return []

        return list(
            self.vector_search.search(
                query_embedding=query_embedding,
                limit=query.limit,
            )
        )


@dataclass(slots=True)
class GroundedAnswer:
    answer: str
    citations: list[RetrievedChunk]


@dataclass(slots=True)
class AskQuestion:
    search: SemanticSearch
    generation_provider: GenerationProvider
    max_context_chars: int = 8000

    def execute(self, query: AskQuestionQuery) -> GroundedAnswer:
        hits = self.search.execute(
            SemanticSearchQuery(query=query.question, limit=query.limit)
        )
        if not hits:
            return GroundedAnswer(
                answer=(
                    "I could not find supporting evidence in the current corpus "
                    "to answer that question."
                ),
                citations=[],
            )

        evidence_text, evidence_hits = _render_evidence(
            hits,
            max_chars=self.max_context_chars,
        )
        prompt = _render_prompt(
            "qa_v1.txt",
            question=query.question,
            evidence=evidence_text,
        )
        raw_answer = self.generation_provider.generate(prompt)
        answer = _parse_answer(raw_answer)
        return GroundedAnswer(answer=answer, citations=evidence_hits)


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


def _render_evidence(
    hits: Sequence[RetrievedChunk],
    *,
    max_chars: int,
) -> tuple[str, list[RetrievedChunk]]:
    if max_chars <= 0:
        return "", []

    sections: list[str] = []
    selected_hits: list[RetrievedChunk] = []
    total_chars = 0

    for hit in hits:
        section = (
            f"[chunk_id={hit.chunk_id}; source_uri={hit.source_uri}; "
            f"chunk_index={hit.chunk_index}; score={hit.score:.4f}]\n"
            f"{hit.text.strip()}"
        )
        remaining_chars = max_chars - total_chars
        if remaining_chars <= 0:
            break
        if len(section) > remaining_chars:
            if sections:
                break
            section = section[:remaining_chars].rstrip()
            if not section:
                break
        sections.append(section)
        selected_hits.append(hit)
        total_chars += len(section)

    return "\n\n".join(sections), selected_hits


def _parse_answer(raw_response: str) -> str:
    payload = _parse_json_object(raw_response)

    answer = payload.get("answer")
    if isinstance(answer, str) and answer.strip():
        return answer.strip()

    raise ValueError("Answer payload did not contain a non-empty answer.")


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

    return {"text": text}


def _attempt_json_parse(candidate: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    return parsed
