from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Document Intelligence Platform", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/document_intelligence",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        alias="CELERY_RESULT_BACKEND",
    )
    azure_blob_endpoint: str = Field(
        default="http://127.0.0.1:10000/devstoreaccount1",
        alias="AZURE_BLOB_ENDPOINT",
    )
    azure_storage_account_name: str = Field(
        default="devstoreaccount1",
        alias="AZURE_STORAGE_ACCOUNT_NAME",
    )
    azure_storage_account_key: str = Field(
        default="",
        alias="AZURE_STORAGE_ACCOUNT_KEY",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
