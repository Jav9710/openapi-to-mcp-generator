"""
Configuración centralizada de la aplicación.

Usa Pydantic Settings para cargar configuración desde variables
de entorno y archivos .env.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class OllamaSettings(BaseSettings):
    """Configuración de Ollama para integración IA."""

    host: str = Field(default="localhost", alias="OLLAMA_HOST")
    port: int = Field(default=11434, alias="OLLAMA_PORT")
    timeout: int = Field(default=120, alias="OLLAMA_TIMEOUT")

    # Modelos por caso de uso
    model_spec_analysis: str = Field(
        default="llama3.2:3b",
        alias="OLLAMA_MODEL_SPEC_ANALYSIS",
    )
    model_code_generation: str = Field(
        default="codellama:7b",
        alias="OLLAMA_MODEL_CODE_GENERATION",
    )
    model_documentation: str = Field(
        default="llama3.2:3b",
        alias="OLLAMA_MODEL_DOCUMENTATION",
    )
    model_validation: str = Field(
        default="llama3.2:1b",
        alias="OLLAMA_MODEL_VALIDATION",
    )

    # Rate limiting
    rate_limit_rpm: int = Field(default=30, alias="OLLAMA_RATE_LIMIT_RPM")
    concurrent_requests: int = Field(
        default=3, alias="OLLAMA_CONCURRENT_REQUESTS"
    )

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    model_config = {"env_prefix": "", "populate_by_name": True}


class MinIOSettings(BaseSettings):
    """Configuración de MinIO para almacenamiento de artefactos."""

    endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    secure: bool = Field(default=False, alias="MINIO_SECURE")
    region: str = Field(default="us-east-1", alias="MINIO_REGION")

    # Nombres de buckets
    bucket_specs: str = Field(
        default="openapi-specs", alias="MINIO_BUCKET_SPECS"
    )
    bucket_artifacts: str = Field(
        default="mcp-artifacts", alias="MINIO_BUCKET_ARTIFACTS"
    )
    bucket_reports: str = Field(
        default="reports", alias="MINIO_BUCKET_REPORTS"
    )
    bucket_backups: str = Field(
        default="backups", alias="MINIO_BUCKET_BACKUPS"
    )

    model_config = {"env_prefix": "", "populate_by_name": True}


class OAuth2Settings(BaseSettings):
    """Configuración de OAuth2 para autenticación."""

    issuer: Optional[str] = Field(default=None, alias="OAUTH2_ISSUER")
    client_id: Optional[str] = Field(default=None, alias="OAUTH2_CLIENT_ID")
    client_secret: Optional[str] = Field(
        default=None, alias="OAUTH2_CLIENT_SECRET"
    )
    redirect_uri: Optional[str] = Field(
        default=None, alias="OAUTH2_REDIRECT_URI"
    )
    scopes: str = Field(default="openid profile email", alias="OAUTH2_SCOPES")

    # Token store backend: memory, redis, database
    token_store_backend: str = Field(
        default="memory", alias="OAUTH2_TOKEN_STORE"
    )

    # Refresh buffer (seconds before expiry to trigger refresh)
    refresh_buffer_seconds: int = Field(
        default=300, alias="OAUTH2_REFRESH_BUFFER"
    )

    @property
    def enabled(self) -> bool:
        return self.issuer is not None and self.client_id is not None

    @property
    def scopes_list(self) -> list[str]:
        return self.scopes.split()

    model_config = {"env_prefix": "", "populate_by_name": True}


class RedisSettings(BaseSettings):
    """Configuración de Redis para cache y message broker."""

    url: str = Field(
        default="redis://localhost:6379/0", alias="REDIS_URL"
    )
    cache_ttl: int = Field(default=3600, alias="REDIS_CACHE_TTL")

    model_config = {"env_prefix": "", "populate_by_name": True}


class CelerySettings(BaseSettings):
    """Configuración de Celery para workers."""

    broker_url: str = Field(
        default="redis://localhost:6379/1", alias="CELERY_BROKER_URL"
    )
    result_backend: str = Field(
        default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND"
    )

    model_config = {"env_prefix": "", "populate_by_name": True}


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    # Base de datos
    database_type: str = Field(default="sqlite", alias="DATABASE_TYPE")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="openapi_mcp", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: Optional[str] = Field(default=None, alias="DB_PASSWORD")

    # Flask
    secret_key: str = Field(
        default="dev-secret-key-change-in-production", alias="SECRET_KEY"
    )
    flask_env: str = Field(default="development", alias="FLASK_ENV")
    flask_debug: bool = Field(default=False, alias="FLASK_DEBUG")

    # Encryption
    encryption_key: Optional[str] = Field(
        default=None, alias="ENCRYPTION_KEY"
    )

    # Sub-configuraciones
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    oauth2: OAuth2Settings = Field(default_factory=OAuth2Settings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)

    # Features toggles
    enable_ai: bool = Field(default=False, alias="ENABLE_AI")
    enable_storage: bool = Field(default=False, alias="ENABLE_STORAGE")
    enable_oauth2: bool = Field(default=False, alias="ENABLE_OAUTH2")
    enable_agents: bool = Field(default=False, alias="ENABLE_AGENTS")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "",
        "populate_by_name": True,
    }


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Obtiene la instancia global de configuración."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Resetea la configuración (útil para testing)."""
    global _settings
    _settings = None
