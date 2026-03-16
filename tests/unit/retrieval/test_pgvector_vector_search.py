from psycopg.errors import UndefinedColumn
from sqlalchemy.exc import ProgrammingError

from document_intelligence.adapters.retrieval.pgvector import (
    _is_missing_embedding_metadata,
)


def test_detects_missing_embedding_model_column_error() -> None:
    error = ProgrammingError(
        "SELECT ...",
        {},
        UndefinedColumn('column chunks.embedding_model does not exist'),
    )

    assert _is_missing_embedding_metadata(error) is True


def test_ignores_other_programming_errors() -> None:
    error = ProgrammingError(
        "SELECT ...",
        {},
        UndefinedColumn('column chunks.other_column does not exist'),
    )

    assert _is_missing_embedding_metadata(error) is False
