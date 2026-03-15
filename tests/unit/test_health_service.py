from document_intelligence.application.system.services import HealthService
from document_intelligence.config import Settings


def test_health_service_returns_basic_status() -> None:
    service = HealthService(settings=Settings())

    assert service.status()["status"] == "ok"
