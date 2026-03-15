from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from document_intelligence.application.common.ports.transactions import (
    TransactionManager,
)

_active_session: ContextVar[Session | None] = ContextVar(
    "document_intelligence_active_session",
    default=None,
)


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Build a SQLAlchemy session factory for the configured database URL."""

    engine = create_engine(database_url)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_active_session() -> Session | None:
    return _active_session.get()


@contextmanager
def read_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    active_session = get_active_session()
    if active_session is not None:
        yield active_session
        return

    with session_factory() as session:
        yield session


@contextmanager
def write_session(
    session_factory: sessionmaker[Session],
) -> Iterator[tuple[Session, bool]]:
    active_session = get_active_session()
    if active_session is not None:
        yield active_session, False
        return

    with session_factory() as session:
        yield session, True


class SqlAlchemyTransactionManager(TransactionManager):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def transaction(self) -> Iterator[None]:
        # Reuse the outer transaction when nested.
        if get_active_session() is not None:
            yield
            return

        with self._session_factory() as session:
            token = _active_session.set(session)
            try:
                with session.begin():
                    yield
            finally:
                _active_session.reset(token)
