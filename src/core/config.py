"""
Application configuration using Pydantic Settings.

Loads configuration from environment variables with type validation.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    # static files
    STATIC_URL: str = "/static"
    STATIC_ROOT: str = "static"

    MEDIA_URL: str = "/media"
    MEDIA_ROOT: str = "media"

    # Application
    APP_NAME: str = "collab-editor"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "collab_editor"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 24 * 60 * 7
    ALGORITHM: str = "HS256"

    # SMTP (Email)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str = "noreply@collab.local"
    EMAILS_FROM_NAME: str = "Collab Editor"

    # CORS
    CORS_ORIGINS: Annotated[list[str], Field(default_factory=list)]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle JSON-like string or comma-separated
            if v.startswith("["):
                import json

                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: str | bool) -> bool:
        """Parse DEBUG from string or bool."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
