from contextlib import AbstractContextManager
from typing import Protocol


class TransactionManager(Protocol):
    """Run a use case within a transaction boundary."""

    def transaction(self) -> AbstractContextManager[None]: ...
