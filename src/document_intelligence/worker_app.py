from celery import Celery

from document_intelligence.config import get_settings

settings = get_settings()

celery_app = Celery(
    "document_intelligence",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
