import pytest

from document_intelligence.config import Settings


def clear_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var in (
        "MODEL_API_BASE_URL",
        "GENERATION_MODEL",
        "EMBEDDING_MODEL",
        "AI_PROVIDER_BACKEND",
        "GITHUB_MODELS_TOKEN",
        "GITHUB_MODELS_ORG",
        "GITHUB_MODELS_API_VERSION",
        "GITHUB_TOKEN",
    ):
        monkeypatch.delenv(env_var, raising=False)


@pytest.mark.parametrize(
    ("app_env", "expected_enabled"),
    [
        ("development", True),
        ("production", False),
    ],
)
def test_empty_enable_local_file_ingestion_uses_environment_default(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
    expected_enabled: bool,
) -> None:
    clear_model_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("ENABLE_LOCAL_FILE_INGESTION", "")

    settings = Settings(_env_file=None)

    assert settings.enable_local_file_ingestion is None
    assert settings.local_file_ingestion_enabled is expected_enabled


def test_model_settings_require_explicit_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_model_env(monkeypatch)
    settings = Settings(_env_file=None)

    assert settings.ai_provider_backend == "auto"
    assert settings.model_api_base_url is None
    assert settings.generation_model is None
    assert settings.embedding_model is None
    assert settings.has_openai_model_configuration is False


def test_empty_model_settings_are_normalized_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_model_env(monkeypatch)
    monkeypatch.setenv("MODEL_API_BASE_URL", "")
    monkeypatch.setenv("GENERATION_MODEL", "")
    monkeypatch.setenv("EMBEDDING_MODEL", "")

    settings = Settings(_env_file=None)

    assert settings.model_api_base_url is None
    assert settings.generation_model is None
    assert settings.embedding_model is None


def test_openai_model_configuration_property(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_API_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("GENERATION_MODEL", "qwen3:4b")
    monkeypatch.setenv("EMBEDDING_MODEL", "qwen3-embedding:0.6b")

    settings = Settings(_env_file=None)

    assert settings.has_openai_model_configuration is True


def test_resolved_github_models_token_prefers_explicit_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_model_env(monkeypatch)
    monkeypatch.setenv("GITHUB_MODELS_TOKEN", "explicit-token")
    monkeypatch.setenv("GITHUB_TOKEN", "fallback-token")

    settings = Settings(_env_file=None)

    assert settings.resolved_github_models_token == "explicit-token"


def test_resolved_github_models_token_falls_back_to_github_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_model_env(monkeypatch)
    monkeypatch.setenv("GITHUB_TOKEN", "fallback-token")

    settings = Settings(_env_file=None)

    assert settings.resolved_github_models_token == "fallback-token"
