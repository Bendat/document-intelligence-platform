from typing import cast

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from document_intelligence.adapters.ai import ProviderRequestError
from document_intelligence.application.common.ports.retrieval import (
    RetrievalBackendSchemaError,
    RetrievedChunk,
)
from document_intelligence.application.retrieval.queries import SemanticSearchQuery
from document_intelligence.application.retrieval.services import (
    QueryEmbeddingCountMismatchError,
    SemanticSearch,
)
from document_intelligence.bootstrap import ApplicationContainer

router = APIRouter(prefix="/search", tags=["retrieval"])


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SearchHitResponse(BaseModel):
    chunk_id: str
    document_id: str
    source_uri: str
    document_title: str
    chunk_index: int
    text: str
    score: float

    @classmethod
    def from_retrieved_chunk(cls, hit: RetrievedChunk) -> "SearchHitResponse":
        return cls(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            source_uri=hit.source_uri,
            document_title=hit.document_title,
            chunk_index=hit.chunk_index,
            text=hit.text,
            score=hit.score,
        )


class SemanticSearchResponse(BaseModel):
    results: list[SearchHitResponse]


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


@router.post("/semantic")
def semantic_search(
    payload: SemanticSearchRequest,
    request: Request,
) -> SemanticSearchResponse:
    container = get_container(request)
    service = SemanticSearch(
        embedding_provider=container.embedding_provider,
        vector_search=container.vector_search,
    )

    try:
        results = service.execute(
            SemanticSearchQuery(
                query=payload.query,
                limit=payload.limit,
            )
        )
    except RetrievalBackendSchemaError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except (ProviderRequestError, QueryEmbeddingCountMismatchError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return SemanticSearchResponse(
        results=[SearchHitResponse.from_retrieved_chunk(hit) for hit in results]
    )
