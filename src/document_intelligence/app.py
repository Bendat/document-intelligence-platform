from fastapi import FastAPI

from document_intelligence.api.routes.documents import router as documents_router
from document_intelligence.api.routes.health import router as health_router
from document_intelligence.bootstrap import create_container
from document_intelligence.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.state.container = create_container()
    app.include_router(documents_router)
    app.include_router(health_router)
    return app
