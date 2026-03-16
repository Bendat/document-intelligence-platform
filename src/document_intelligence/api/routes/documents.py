from typing import cast

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from document_intelligence.adapters.ai import ProviderRequestError
from document_intelligence.application.document_catalog.commands import (
    CreateDocumentCommand,
)
from document_intelligence.application.document_catalog.enrichment import (
    ClassifyDocument,
    DocumentContentUnavailableError,
    EmbeddingCountMismatchError,
    EmbedDocumentChunks,
    EnrichDocument,
    InvalidProviderResponseError,
    SummarizeDocument,
)
from document_intelligence.application.document_catalog.queries import GetDocumentQuery
from document_intelligence.application.document_catalog.services import (
    CreateDocument,
    DocumentNotFoundError,
    GetDocument,
)
from document_intelligence.application.ingestion.commands import (
    IngestLocalDocumentCommand,
)
from document_intelligence.application.ingestion.services import (
    IngestLocalDocument,
    InvalidSourceError,
    SourceNotFoundError,
    UnsupportedMediaTypeError,
)
from document_intelligence.bootstrap import ApplicationContainer
from document_intelligence.config import Settings
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


class IngestLocalDocumentRequest(BaseModel):
    source_uri: str
    title: str | None = None
    media_type: str | None = None


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


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


@router.post("/ingest/local", status_code=status.HTTP_201_CREATED)
def ingest_local_document(
    payload: IngestLocalDocumentRequest,
    request: Request,
) -> DocumentResponse:
    if not get_settings(request).local_file_ingestion_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local file ingestion is disabled",
        )

    container = get_container(request)
    service = IngestLocalDocument(
        document_repository=container.document_repository,
        chunk_repository=container.chunk_repository,
        parser_registry=container.parser_registry,
        chunker=container.text_chunker,
        transaction_manager=container.transaction_manager,
        enrich_document=EnrichDocument(
            document_repository=container.document_repository,
            embed_document_chunks=EmbedDocumentChunks(
                document_repository=container.document_repository,
                chunk_repository=container.chunk_repository,
                embedding_provider=container.embedding_provider,
                embedding_model=get_settings(request).resolved_embedding_model_id,
            ),
            classify_document=ClassifyDocument(
                document_repository=container.document_repository,
                chunk_repository=container.chunk_repository,
                generation_provider=container.generation_provider,
            ),
            summarize_document=SummarizeDocument(
                document_repository=container.document_repository,
                chunk_repository=container.chunk_repository,
                generation_provider=container.generation_provider,
            ),
        ),
    )

    try:
        result = service.execute(
            IngestLocalDocumentCommand(
                source_uri=payload.source_uri,
                title=payload.title,
                media_type=payload.media_type,
            )
        )
    except SourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except UnsupportedMediaTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(error),
        ) from error
    except InvalidSourceError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except DocumentContentUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except (
        ProviderRequestError,
        InvalidProviderResponseError,
        EmbeddingCountMismatchError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return DocumentResponse.from_domain(result.document)


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
