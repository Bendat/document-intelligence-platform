import pytest

from document_intelligence.config import Settings


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
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("ENABLE_LOCAL_FILE_INGESTION", "")

    settings = Settings(_env_file=None)

    assert settings.enable_local_file_ingestion is None
    assert settings.local_file_ingestion_enabled is expected_enabled
