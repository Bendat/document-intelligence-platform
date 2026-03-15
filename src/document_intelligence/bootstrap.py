from dataclasses import dataclass

from document_intelligence.adapters.ai import (
    DeterministicEmbeddingProvider,
    DeterministicGenerationProvider,
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleGenerationProvider,
)
from document_intelligence.adapters.chunking.text import DeterministicTextChunker
from document_intelligence.adapters.parsing.local_files import (
    create_default_local_file_parser_registry,
)
from document_intelligence.adapters.persistence.in_memory import (
    InMemoryChunkRepository,
    InMemoryDocumentRepository,
    InMemoryJobRepository,
    InMemoryTransactionManager,
)
from document_intelligence.adapters.persistence.postgres import (
    PostgresChunkRepository,
    PostgresDocumentRepository,
    PostgresJobRepository,
    SqlAlchemyTransactionManager,
    create_session_factory,
)
from document_intelligence.adapters.queue.in_memory import InMemoryTaskDispatcher
from document_intelligence.adapters.retrieval import (
    InMemoryVectorSearch,
    PgvectorVectorSearch,
)
from document_intelligence.application.common.ports.chunking import TextChunker
from document_intelligence.application.common.ports.dispatch import TaskDispatcher
from document_intelligence.application.common.ports.parsers import ParserRegistry
from document_intelligence.application.common.ports.providers import (
    EmbeddingProvider,
    GenerationProvider,
)
from document_intelligence.application.common.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
    JobRepository,
)
from document_intelligence.application.common.ports.retrieval import VectorSearchPort
from document_intelligence.application.common.ports.transactions import (
    TransactionManager,
)
from document_intelligence.config import Settings, get_settings


@dataclass(slots=True)
class ApplicationContainer:
    document_repository: DocumentRepository
    chunk_repository: ChunkRepository
    job_repository: JobRepository
    embedding_provider: EmbeddingProvider
    generation_provider: GenerationProvider
    vector_search: VectorSearchPort
    task_dispatcher: TaskDispatcher
    parser_registry: ParserRegistry
    text_chunker: TextChunker
    transaction_manager: TransactionManager


def create_in_memory_container(settings: Settings) -> ApplicationContainer:
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()
    job_repository = InMemoryJobRepository()
    transaction_manager = InMemoryTransactionManager(
        resources=[document_repository, chunk_repository, job_repository]
    )
    embedding_provider, generation_provider = _resolve_ai_providers(settings)
    return ApplicationContainer(
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        job_repository=job_repository,
        embedding_provider=embedding_provider,
        generation_provider=generation_provider,
        vector_search=InMemoryVectorSearch(
            document_repository=document_repository,
            chunk_repository=chunk_repository,
            embedding_model=settings.resolved_embedding_model_id,
        ),
        task_dispatcher=InMemoryTaskDispatcher(job_repository=job_repository),
        parser_registry=create_default_local_file_parser_registry(),
        text_chunker=DeterministicTextChunker(),
        transaction_manager=transaction_manager,
    )


def create_postgres_container(
    database_url: str,
    settings: Settings,
) -> ApplicationContainer:
    session_factory = create_session_factory(database_url)
    job_repository = PostgresJobRepository(session_factory=session_factory)
    embedding_provider, generation_provider = _resolve_ai_providers(settings)
    return ApplicationContainer(
        document_repository=PostgresDocumentRepository(session_factory=session_factory),
        chunk_repository=PostgresChunkRepository(session_factory=session_factory),
        job_repository=job_repository,
        embedding_provider=embedding_provider,
        generation_provider=generation_provider,
        vector_search=PgvectorVectorSearch(
            session_factory=session_factory,
            embedding_model=settings.resolved_embedding_model_id,
        ),
        task_dispatcher=InMemoryTaskDispatcher(job_repository=job_repository),
        parser_registry=create_default_local_file_parser_registry(),
        text_chunker=DeterministicTextChunker(),
        transaction_manager=SqlAlchemyTransactionManager(
            session_factory=session_factory
        ),
    )


def create_container(settings: Settings | None = None) -> ApplicationContainer:
    resolved_settings = settings if settings is not None else get_settings()
    if resolved_settings.persistence_backend == "postgres":
        return create_postgres_container(
            database_url=resolved_settings.database_url,
            settings=resolved_settings,
        )
    return create_in_memory_container(settings=resolved_settings)


def _resolve_ai_providers(
    settings: Settings,
) -> tuple[EmbeddingProvider, GenerationProvider]:
    if settings.ai_provider_backend == "deterministic":
        return _deterministic_providers()

    if settings.ai_provider_backend == "github_models":
        return _github_models_providers(settings)

    if settings.ai_provider_backend == "openai_compatible":
        if not settings.has_openai_model_configuration:
            raise ValueError(
                "AI_PROVIDER_BACKEND=openai_compatible requires MODEL_API_BASE_URL, "
                "GENERATION_MODEL, and EMBEDDING_MODEL."
            )
        return _openai_compatible_providers(settings)

    if settings.has_openai_model_configuration:
        return _openai_compatible_providers(settings)
    return _deterministic_providers()


def _openai_compatible_providers(
    settings: Settings,
) -> tuple[EmbeddingProvider, GenerationProvider]:
    model_api_base_url = settings.model_api_base_url
    generation_model = settings.generation_model
    embedding_model = settings.embedding_model
    if (
        model_api_base_url is None
        or generation_model is None
        or embedding_model is None
    ):
        raise ValueError(
            "MODEL_API_BASE_URL, GENERATION_MODEL, and EMBEDDING_MODEL are required."
        )

    return (
        OpenAICompatibleEmbeddingProvider(
            model_api_base_url=model_api_base_url,
            model_name=embedding_model,
        ),
        OpenAICompatibleGenerationProvider(
            model_api_base_url=model_api_base_url,
            model_name=generation_model,
        ),
    )


def _deterministic_providers() -> tuple[EmbeddingProvider, GenerationProvider]:
    return (
        DeterministicEmbeddingProvider(),
        DeterministicGenerationProvider(),
    )


def _github_models_providers(
    settings: Settings,
) -> tuple[EmbeddingProvider, GenerationProvider]:
    token = settings.resolved_github_models_token
    generation_model = settings.generation_model
    embedding_model = settings.embedding_model
    if token is None:
        raise ValueError(
            "AI_PROVIDER_BACKEND=github_models requires GITHUB_MODELS_TOKEN "
            "or GITHUB_TOKEN."
        )
    if generation_model is None or embedding_model is None:
        raise ValueError(
            "AI_PROVIDER_BACKEND=github_models requires GENERATION_MODEL and "
            "EMBEDDING_MODEL."
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": settings.github_models_api_version,
    }
    base_url = "https://models.github.ai/inference"
    if settings.github_models_org is not None:
        base_url = f"https://models.github.ai/orgs/{settings.github_models_org}/inference"

    return (
        OpenAICompatibleEmbeddingProvider(
            model_api_base_url=base_url,
            model_name=embedding_model,
            extra_headers=headers,
        ),
        OpenAICompatibleGenerationProvider(
            model_api_base_url=base_url,
            model_name=generation_model,
            extra_headers=headers,
        ),
    )
