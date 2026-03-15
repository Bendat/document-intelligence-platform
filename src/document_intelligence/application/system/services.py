from dataclasses import dataclass

from document_intelligence.config import Settings


@dataclass(slots=True)
class HealthService:
    settings: Settings

    def status(self) -> dict[str, str]:
        return {
            "status": "ok",
            "environment": self.settings.app_env,
            "service": self.settings.app_name,
        }
