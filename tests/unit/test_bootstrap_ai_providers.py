import pytest

from document_intelligence.adapters.ai import (
    DeterministicEmbeddingProvider,
    DeterministicGenerationProvider,
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleGenerationProvider,
)
from document_intelligence.bootstrap import create_container
from document_intelligence.config import Settings


def _clear_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var in (
        "AI_PROVIDER_BACKEND",
        "MODEL_API_BASE_URL",
        "GENERATION_MODEL",
        "EMBEDDING_MODEL",
        "GITHUB_MODELS_TOKEN",
        "GITHUB_MODELS_ORG",
        "GITHUB_MODELS_API_VERSION",
        "GITHUB_TOKEN",
    ):
        monkeypatch.delenv(env_var, raising=False)


def test_create_container_uses_deterministic_backend_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_ai_env(monkeypatch)
    monkeypatch.setenv("AI_PROVIDER_BACKEND", "deterministic")
    settings = Settings(_env_file=None)

    container = create_container(settings=settings)

    assert isinstance(container.embedding_provider, DeterministicEmbeddingProvider)
    assert isinstance(container.generation_provider, DeterministicGenerationProvider)


def test_create_container_uses_github_models_backend_with_embeddings_and_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_ai_env(monkeypatch)
    monkeypatch.setenv("AI_PROVIDER_BACKEND", "github_models")
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", "test-token")
    monkeypatch.setenv("GENERATION_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

    settings = Settings(_env_file=None)
    container = create_container(settings=settings)

    assert isinstance(container.embedding_provider, OpenAICompatibleEmbeddingProvider)
    assert isinstance(container.generation_provider, OpenAICompatibleGenerationProvider)
    assert (
        container.generation_provider.model_api_base_url
        == "https://models.github.ai/inference"
    )
    assert (
        container.embedding_provider.model_api_base_url
        == "https://models.github.ai/inference"
    )

    generation_headers = container.generation_provider.extra_headers
    assert generation_headers is not None
    assert generation_headers["Authorization"] == "Bearer test-token"
    assert generation_headers["Accept"] == "application/vnd.github+json"
    assert generation_headers["X-GitHub-Api-Version"] == "2026-03-10"


def test_create_container_uses_org_scoped_github_models_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_ai_env(monkeypatch)
    monkeypatch.setenv("AI_PROVIDER_BACKEND", "github_models")
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_MODELS_ORG", "platform-team")
    monkeypatch.setenv("GENERATION_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

    settings = Settings(_env_file=None)
    container = create_container(settings=settings)

    assert (
        container.generation_provider.model_api_base_url
        == "https://models.github.ai/orgs/platform-team/inference"
    )


def test_create_container_rejects_github_models_backend_without_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_ai_env(monkeypatch)
    monkeypatch.setenv("AI_PROVIDER_BACKEND", "github_models")
    monkeypatch.setenv("GENERATION_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
    settings = Settings(_env_file=None)

    with pytest.raises(ValueError, match="GITHUB_MODELS_TOKEN"):
        create_container(settings=settings)
