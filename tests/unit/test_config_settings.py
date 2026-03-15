import pytest

from document_intelligence.config import Settings


def clear_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var in ("MODEL_API_BASE_URL", "GENERATION_MODEL", "EMBEDDING_MODEL"):
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

    assert settings.model_api_base_url is None
    assert settings.generation_model is None
    assert settings.embedding_model is None


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
