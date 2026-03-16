from collections.abc import Sequence

import pytest

from document_intelligence.application.common.ports.retrieval import RetrievedChunk
from document_intelligence.application.retrieval.queries import (
    AskQuestionQuery,
    SemanticSearchQuery,
)
from document_intelligence.application.retrieval.services import (
    AskQuestion,
    GroundedAnswer,
    QueryEmbeddingCountMismatchError,
    SemanticSearch,
)


class StubEmbeddingProvider:
    def __init__(self, vectors: Sequence[Sequence[float]]) -> None:
        self._vectors = vectors
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        self.calls.append(list(texts))
        return self._vectors


class StubVectorSearch:
    def __init__(self, hits: Sequence[RetrievedChunk]) -> None:
        self._hits = list(hits)
        self.calls: list[tuple[list[float], int]] = []

    def search(
        self,
        query_embedding: Sequence[float],
        limit: int,
    ) -> Sequence[RetrievedChunk]:
        self.calls.append(([float(value) for value in query_embedding], limit))
        return self._hits[:limit]


class StubGenerationProvider:
    def __init__(self, output: str) -> None:
        self._output = output
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._output


def test_semantic_search_embeds_query_and_calls_vector_search() -> None:
    hits = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            source_uri="file:///docs/a.md",
            document_title="A",
            chunk_index=0,
            text="Service ownership lives in ADR-004.",
            score=0.88,
        )
    ]
    embedding_provider = StubEmbeddingProvider(vectors=[[0.1, 0.2, 0.3]])
    vector_search = StubVectorSearch(hits=hits)

    service = SemanticSearch(
        embedding_provider=embedding_provider,
        vector_search=vector_search,
    )
    result = service.execute(SemanticSearchQuery(query="service ownership", limit=3))

    assert result == hits
    assert embedding_provider.calls == [["service ownership"]]
    assert vector_search.calls == [([0.1, 0.2, 0.3], 3)]


def test_semantic_search_raises_when_embedding_provider_returns_wrong_count() -> None:
    service = SemanticSearch(
        embedding_provider=StubEmbeddingProvider(vectors=[]),
        vector_search=StubVectorSearch(hits=[]),
    )

    with pytest.raises(QueryEmbeddingCountMismatchError):
        service.execute(SemanticSearchQuery(query="question", limit=5))


def test_ask_question_returns_grounded_answer_with_citations() -> None:
    hits = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            source_uri="file:///docs/adr-004.md",
            document_title="ADR 004",
            chunk_index=2,
            text="ADR-004 assigns service ownership to platform teams.",
            score=0.91,
        ),
        RetrievedChunk(
            chunk_id="chunk-2",
            document_id="doc-2",
            source_uri="file:///docs/runbook.md",
            document_title="Runbook",
            chunk_index=1,
            text="Escalation details for incident response.",
            score=0.80,
        ),
    ]
    search = SemanticSearch(
        embedding_provider=StubEmbeddingProvider(vectors=[[0.1, 0.2, 0.3]]),
        vector_search=StubVectorSearch(hits=hits),
    )
    generation = StubGenerationProvider(
        output='{"answer":"Service ownership is covered by ADR-004."}'
    )

    service = AskQuestion(search=search, generation_provider=generation)
    result = service.execute(
        AskQuestionQuery(
            question="Which ADR covers service ownership?",
            limit=2,
        )
    )

    assert result == GroundedAnswer(
        answer="Service ownership is covered by ADR-004.",
        citations=hits,
    )
    assert generation.prompts
    assert "chunk-1" in generation.prompts[0]
    assert "Which ADR covers service ownership?" in generation.prompts[0]


def test_ask_question_rejects_payload_without_answer_field() -> None:
    hits = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            source_uri="file:///docs/adr-004.md",
            document_title="ADR 004",
            chunk_index=2,
            text="ADR-004 assigns service ownership to platform teams.",
            score=0.91,
        )
    ]
    search = SemanticSearch(
        embedding_provider=StubEmbeddingProvider(vectors=[[0.1, 0.2, 0.3]]),
        vector_search=StubVectorSearch(hits=hits),
    )
    generation = StubGenerationProvider(output='{"text":"not valid for qa"}')

    service = AskQuestion(search=search, generation_provider=generation)

    with pytest.raises(ValueError, match="non-empty answer"):
        service.execute(
            AskQuestionQuery(
                question="Which ADR covers service ownership?",
                limit=1,
            )
        )


def test_ask_question_returns_fallback_message_when_no_hits() -> None:
    search = SemanticSearch(
        embedding_provider=StubEmbeddingProvider(vectors=[[0.1, 0.2]]),
        vector_search=StubVectorSearch(hits=[]),
    )
    generation = StubGenerationProvider(output='{"answer":"unused"}')

    service = AskQuestion(search=search, generation_provider=generation)
    result = service.execute(AskQuestionQuery(question="unknown", limit=3))

    assert not result.citations
    assert "could not find supporting evidence" in result.answer
    assert generation.prompts == []


def test_ask_question_returns_only_citations_used_in_prompt_context() -> None:
    hits = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            source_uri="file:///docs/one.md",
            document_title="One",
            chunk_index=0,
            text="A" * 180,
            score=0.93,
        ),
        RetrievedChunk(
            chunk_id="chunk-2",
            document_id="doc-2",
            source_uri="file:///docs/two.md",
            document_title="Two",
            chunk_index=1,
            text="B" * 180,
            score=0.89,
        ),
    ]
    search = SemanticSearch(
        embedding_provider=StubEmbeddingProvider(vectors=[[0.1, 0.2]]),
        vector_search=StubVectorSearch(hits=hits),
    )
    generation = StubGenerationProvider(output='{"answer":"Grounded reply."}')
    service = AskQuestion(
        search=search,
        generation_provider=generation,
        max_context_chars=260,
    )

    result = service.execute(AskQuestionQuery(question="question", limit=5))

    assert result.answer == "Grounded reply."
    assert [citation.chunk_id for citation in result.citations] == ["chunk-1"]
    assert "chunk-1" in generation.prompts[0]
    assert "chunk-2" not in generation.prompts[0]


def test_ask_question_truncates_first_evidence_section_to_context_budget() -> None:
    hits = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            source_uri="file:///docs/one.md",
            document_title="One",
            chunk_index=0,
            text="A" * 400,
            score=0.93,
        )
    ]
    search = SemanticSearch(
        embedding_provider=StubEmbeddingProvider(vectors=[[0.1, 0.2]]),
        vector_search=StubVectorSearch(hits=hits),
    )
    generation = StubGenerationProvider(output='{"answer":"Grounded reply."}')
    service = AskQuestion(
        search=search,
        generation_provider=generation,
        max_context_chars=120,
    )

    result = service.execute(AskQuestionQuery(question="question", limit=5))

    assert result.answer == "Grounded reply."
    assert result.citations == hits
    assert len(generation.prompts[0]) < 500
    assert "chunk-1" in generation.prompts[0]
