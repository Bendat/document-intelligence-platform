from typing import cast

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from document_intelligence.application.document_catalog.commands import (
    CreateDocumentCommand,
)
from document_intelligence.application.document_catalog.queries import GetDocumentQuery
from document_intelligence.application.document_catalog.services import (
    CreateDocument,
    DocumentNotFoundError,
    GetDocument,
)
from document_intelligence.bootstrap import ApplicationContainer
from document_intelligence.domain.document_catalog.entities import Chunk, Document

router = APIRouter(prefix="/documents", tags=["documents"])


class CreateDocumentRequest(BaseModel):
    source_uri: str
    title: str
    media_type: str


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    index: int
    text: str
    embedding: list[float]

    @classmethod
    def from_domain(cls, chunk: Chunk) -> "ChunkResponse":
        return cls(
            id=chunk.id,
            document_id=chunk.document_id,
            index=chunk.index,
            text=chunk.text,
            embedding=list(chunk.embedding),
        )


class DocumentResponse(BaseModel):
    id: str
    source_uri: str
    title: str
    media_type: str
    status: str
    classification: dict[str, str | float | None] | None
    summary: dict[str, str] | None

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentResponse":
        classification = None
        if document.classification is not None:
            classification = {
                "label": document.classification.label,
                "confidence": document.classification.confidence,
            }

        summary = None
        if document.summary is not None:
            summary = {"text": document.summary.text}

        return cls(
            id=document.id,
            source_uri=document.source_uri,
            title=document.title,
            media_type=document.media_type,
            status=document.status.value,
            classification=classification,
            summary=summary,
        )


class DocumentDetailsResponse(BaseModel):
    document: DocumentResponse
    chunks: list[ChunkResponse]


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def create_document(
    payload: CreateDocumentRequest,
    request: Request,
) -> DocumentResponse:
    container = get_container(request)
    service = CreateDocument(
        document_repository=container.document_repository,
        dispatcher=container.task_dispatcher,
        transaction_manager=container.transaction_manager,
    )
    document = service.execute(
        CreateDocumentCommand(
            source_uri=payload.source_uri,
            title=payload.title,
            media_type=payload.media_type,
        )
    )
    return DocumentResponse.from_domain(document)


@router.get("/{document_id}")
def get_document(document_id: str, request: Request) -> DocumentDetailsResponse:
    container = get_container(request)
    service = GetDocument(
        document_repository=container.document_repository,
        chunk_repository=container.chunk_repository,
    )

    try:
        details = service.execute(GetDocumentQuery(document_id=document_id))
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {error.args[0]} not found",
        ) from error

    return DocumentDetailsResponse(
        document=DocumentResponse.from_domain(details.document),
        chunks=[ChunkResponse.from_domain(chunk) for chunk in details.chunks],
    )
