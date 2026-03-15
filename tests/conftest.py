from collections.abc import Iterator

import pytest

from document_intelligence.config import get_settings


@pytest.fixture(autouse=True)
def force_deterministic_ai_backend(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AI_PROVIDER_BACKEND", "deterministic")
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()
