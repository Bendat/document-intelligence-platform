from typing import cast

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from document_intelligence.adapters.ai import ProviderRequestError
from document_intelligence.api.routes.search import SearchHitResponse
from document_intelligence.application.common.ports.retrieval import (
    RetrievalBackendSchemaError,
)
from document_intelligence.application.retrieval.queries import AskQuestionQuery
from document_intelligence.application.retrieval.services import (
    AskQuestion,
    QueryEmbeddingCountMismatchError,
    SemanticSearch,
)
from document_intelligence.bootstrap import ApplicationContainer

router = APIRouter(tags=["retrieval"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    citations: list[SearchHitResponse]


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


@router.post("/ask")
def ask_question(payload: AskRequest, request: Request) -> AskResponse:
    container = get_container(request)
    search = SemanticSearch(
        embedding_provider=container.embedding_provider,
        vector_search=container.vector_search,
    )
    service = AskQuestion(
        search=search,
        generation_provider=container.generation_provider,
    )

    try:
        result = service.execute(
            AskQuestionQuery(
                question=payload.question,
                limit=payload.limit,
            )
        )
    except RetrievalBackendSchemaError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except (
        ProviderRequestError,
        QueryEmbeddingCountMismatchError,
        ValueError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return AskResponse(
        answer=result.answer,
        citations=[
            SearchHitResponse.from_retrieved_chunk(hit) for hit in result.citations
        ],
    )
