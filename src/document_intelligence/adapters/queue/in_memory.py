from uuid import uuid4

from document_intelligence.application.common.ports.dispatch import TaskDispatcher
from document_intelligence.application.common.ports.repositories import JobRepository
from document_intelligence.domain.jobs.entities import IngestionJob, JobStatus


class InMemoryTaskDispatcher(TaskDispatcher):
    def __init__(self, job_repository: JobRepository) -> None:
        self._job_repository = job_repository

    def enqueue_enrichment(self, document_id: str) -> str:
        job_id = str(uuid4())
        job = IngestionJob(id=job_id, document_id=document_id, status=JobStatus.PENDING)
        self._job_repository.save(job)
        return job_id
