"""Application settings, loaded from the environment via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the ScopeGuard AI API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ScopeGuard AI API"
    app_version: str = "0.1.0"

    # Only the Next.js dev origin may call this API.
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)

    # Left empty on purpose: real values belong in .env, never in git.
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
