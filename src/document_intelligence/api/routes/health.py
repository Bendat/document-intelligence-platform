from fastapi import APIRouter

from document_intelligence.application.system.services import HealthService
from document_intelligence.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    service = HealthService(settings=get_settings())
    return service.status()
