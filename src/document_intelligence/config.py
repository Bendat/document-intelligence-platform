import os
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Document Intelligence Platform", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    persistence_backend: Literal["in_memory", "postgres"] = Field(
        default="in_memory",
        alias="PERSISTENCE_BACKEND",
    )
    enable_local_file_ingestion: bool | None = Field(
        default=None,
        alias="ENABLE_LOCAL_FILE_INGESTION",
    )

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
    model_api_base_url: str | None = Field(
        default=None,
        alias="MODEL_API_BASE_URL",
    )
    generation_model: str | None = Field(
        default=None,
        alias="GENERATION_MODEL",
    )
    embedding_model: str | None = Field(
        default=None,
        alias="EMBEDDING_MODEL",
    )
    ai_provider_backend: Literal[
        "auto",
        "deterministic",
        "openai_compatible",
        "github_models",
    ] = Field(default="auto", alias="AI_PROVIDER_BACKEND")
    github_models_token: str | None = Field(
        default=None,
        alias="GITHUB_MODELS_TOKEN",
    )
    github_models_org: str | None = Field(
        default=None,
        alias="GITHUB_MODELS_ORG",
    )
    github_models_api_version: str = Field(
        default="2026-03-10",
        alias="GITHUB_MODELS_API_VERSION",
    )

    @field_validator(
        "enable_local_file_ingestion",
        "model_api_base_url",
        "generation_model",
        "embedding_model",
        "github_models_token",
        "github_models_org",
        mode="before",
    )
    @classmethod
    def _empty_string_value_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @property
    def local_file_ingestion_enabled(self) -> bool:
        """Enable local file ingestion by default only in development."""

        if self.enable_local_file_ingestion is not None:
            return self.enable_local_file_ingestion
        return self.app_env == "development"

    @property
    def has_openai_model_configuration(self) -> bool:
        return (
            self.model_api_base_url is not None
            and self.generation_model is not None
            and self.embedding_model is not None
        )

    @property
    def resolved_github_models_token(self) -> str | None:
        return self.github_models_token or os.getenv("GITHUB_TOKEN")

    @property
    def resolved_embedding_model_id(self) -> str | None:
        if self.ai_provider_backend == "deterministic":
            return "deterministic"
        if self.ai_provider_backend == "auto":
            if not self.has_openai_model_configuration:
                return "deterministic"
            return self.embedding_model
        return self.embedding_model


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
