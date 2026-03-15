from typing import Protocol


class TaskDispatcher(Protocol):
    def enqueue_enrichment(self, document_id: str) -> str: ...
