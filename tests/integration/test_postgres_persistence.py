import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from document_intelligence.adapters.persistence.postgres.repositories import (
    PostgresChunkRepository,
    PostgresDocumentRepository,
    PostgresJobRepository,
)
from document_intelligence.adapters.persistence.postgres.session import (
    SqlAlchemyTransactionManager,
)
from document_intelligence.app import create_app
from document_intelligence.application.common.ports.dispatch import TaskDispatcher
from document_intelligence.application.document_catalog.commands import (
    CreateDocumentCommand,
)
from document_intelligence.application.document_catalog.services import CreateDocument
from document_intelligence.config import get_settings
from document_intelligence.domain.document_catalog.entities import (
    Chunk,
    Classification,
    Document,
    DocumentStatus,
    Summary,
)
from document_intelligence.domain.jobs.entities import IngestionJob, JobStatus

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = REPO_ROOT / "alembic.ini"


@pytest.fixture(scope="module")
def migrated_database_url() -> Iterator[str]:
    database_url = _resolve_test_database_url()
    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        engine.dispose()
        pytest.skip(f"Postgres is unavailable: {error}")

    engine.dispose()

    command.upgrade(_alembic_config(database_url), "head")

    try:
        yield database_url
    finally:
        command.downgrade(_alembic_config(database_url), "base")


@pytest.fixture()
def postgres_session_factory(
    migrated_database_url: str,
) -> Iterator[sessionmaker[Session]]:
    engine = create_engine(migrated_database_url)

    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE TABLE chunks, jobs, documents RESTART IDENTITY CASCADE")
        )

    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    yield factory

    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE TABLE chunks, jobs, documents RESTART IDENTITY CASCADE")
        )
    engine.dispose()


@pytest.fixture()
def postgres_environment(
    migrated_database_url: str,
) -> Iterator[None]:
    previous_backend = os.getenv("PERSISTENCE_BACKEND")
    previous_database_url = os.getenv("DATABASE_URL")

    os.environ["PERSISTENCE_BACKEND"] = "postgres"
    os.environ["DATABASE_URL"] = migrated_database_url
    get_settings.cache_clear()

    try:
        yield
    finally:
        if previous_backend is None:
            os.environ.pop("PERSISTENCE_BACKEND", None)
        else:
            os.environ["PERSISTENCE_BACKEND"] = previous_backend

        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url

        get_settings.cache_clear()


def test_document_repository_round_trip(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    repository = PostgresDocumentRepository(session_factory=postgres_session_factory)
    document = Document(
        id="doc-roundtrip",
        source_uri="file:///docs/roundtrip.md",
        title="Round Trip",
        media_type="text/markdown",
        status=DocumentStatus.READY,
        classification=Classification(label="runbook", confidence=0.91),
        summary=Summary(text="Short summary"),
    )

    repository.save(document)
    loaded = repository.get(document.id)

    assert loaded is not None
    assert loaded.id == document.id
    assert loaded.status is DocumentStatus.READY
    assert loaded.classification is not None
    assert loaded.classification.label == "runbook"
    assert loaded.classification.confidence == pytest.approx(0.91)
    assert loaded.summary is not None
    assert loaded.summary.text == "Short summary"


def test_chunk_repository_replace_for_document(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    document_repository = PostgresDocumentRepository(
        session_factory=postgres_session_factory
    )
    chunk_repository = PostgresChunkRepository(session_factory=postgres_session_factory)

    document = Document(
        id="doc-chunks",
        source_uri="file:///docs/chunks.md",
        title="Chunks",
        media_type="text/markdown",
    )
    document_repository.save(document)

    chunk_repository.replace_for_document(
        document.id,
        [
            Chunk(id="chunk-old", document_id=document.id, index=0, text="Old chunk"),
        ],
    )
    chunk_repository.replace_for_document(
        document.id,
        [
            Chunk(id="chunk-two", document_id=document.id, index=2, text="Third"),
            Chunk(id="chunk-zero", document_id=document.id, index=0, text="First"),
        ],
    )

    loaded = chunk_repository.for_document(document.id)

    assert [chunk.id for chunk in loaded] == ["chunk-zero", "chunk-two"]
    assert [chunk.text for chunk in loaded] == ["First", "Third"]


def test_chunk_repository_rejects_mismatched_document_id(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    document_repository = PostgresDocumentRepository(
        session_factory=postgres_session_factory
    )
    chunk_repository = PostgresChunkRepository(session_factory=postgres_session_factory)

    document_repository.save(
        Document(
            id="doc-a",
            source_uri="file:///docs/a.md",
            title="A",
            media_type="text/markdown",
        )
    )

    with pytest.raises(ValueError, match="Chunk document_id mismatch"):
        chunk_repository.replace_for_document(
            "doc-a",
            [Chunk(id="chunk-bad", document_id="doc-b", index=0, text="Wrong doc")],
        )

    assert chunk_repository.for_document("doc-a") == []


def test_job_repository_persists_updates(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    document_repository = PostgresDocumentRepository(
        session_factory=postgres_session_factory
    )
    job_repository = PostgresJobRepository(session_factory=postgres_session_factory)

    document_repository.save(
        Document(
            id="doc-job",
            source_uri="file:///docs/job.md",
            title="Job",
            media_type="text/markdown",
        )
    )

    job_repository.save(
        IngestionJob(id="job-1", document_id="doc-job", status=JobStatus.PENDING)
    )
    job_repository.save(
        IngestionJob(id="job-1", document_id="doc-job", status=JobStatus.RUNNING)
    )

    loaded = job_repository.get("job-1")

    assert loaded is not None
    assert loaded.document_id == "doc-job"
    assert loaded.status is JobStatus.RUNNING


def test_postgres_backend_persists_across_app_instances(
    postgres_environment: None,
) -> None:
    with TestClient(create_app()) as first_client:
        create_response = first_client.post(
            "/documents/ingest",
            json={
                "source_uri": "file:///docs/persisted.md",
                "title": "Persisted Document",
                "media_type": "text/markdown",
            },
        )

    assert create_response.status_code == 201
    created_document = create_response.json()

    with TestClient(create_app()) as second_client:
        get_response = second_client.get(f"/documents/{created_document['id']}")

    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["document"]["title"] == "Persisted Document"


def test_create_document_rollback_on_dispatch_error(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    document_repository = PostgresDocumentRepository(
        session_factory=postgres_session_factory
    )
    job_repository = PostgresJobRepository(session_factory=postgres_session_factory)
    transaction_manager = SqlAlchemyTransactionManager(
        session_factory=postgres_session_factory
    )

    service = CreateDocument(
        document_repository=document_repository,
        dispatcher=FailingDispatcher(job_repository=job_repository),
        transaction_manager=transaction_manager,
    )

    with pytest.raises(RuntimeError, match="simulated enqueue failure"):
        service.execute(
            CreateDocumentCommand(
                source_uri="file:///docs/atomicity.md",
                title="Atomicity",
                media_type="text/markdown",
            )
        )

    with postgres_session_factory() as session:
        document_count = session.scalar(text("SELECT COUNT(*) FROM documents"))
        job_count = session.scalar(text("SELECT COUNT(*) FROM jobs"))

    assert document_count == 0
    assert job_count == 0


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _resolve_test_database_url() -> str:
    configured_url = os.getenv("POSTGRES_TEST_DATABASE_URL")
    if not configured_url:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is not set; skipping Postgres tests.")

    parsed = make_url(configured_url)
    database_name = parsed.database or ""
    if not database_name.endswith("_test"):
        pytest.skip(
            "POSTGRES_TEST_DATABASE_URL must target a dedicated *_test database."
        )

    return configured_url


class FailingDispatcher(TaskDispatcher):
    def __init__(self, job_repository: PostgresJobRepository) -> None:
        self._job_repository = job_repository

    def enqueue_enrichment(self, document_id: str) -> str:
        self._job_repository.save(
            IngestionJob(
                id="job-failing",
                document_id=document_id,
                status=JobStatus.PENDING,
            )
        )
        raise RuntimeError("simulated enqueue failure")
