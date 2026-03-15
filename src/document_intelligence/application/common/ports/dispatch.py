from typing import Protocol


class TaskDispatcher(Protocol):
    """Dispatch background work without coupling use cases to a queue system."""

    def enqueue_enrichment(self, document_id: str) -> str: ...
