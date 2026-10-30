"""Application settings, loaded from the environment via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Mithaq API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mithaq API"
    app_version: str = "0.1.0"

    # Comma-separated. Production adds the deployed frontend domain (NFR-08).
    allowed_origins: str = "http://localhost:3000"

    # When unset the app falls back to the in-memory repository, which is fine
    # locally but NOT on Vercel, where functions keep no memory between
    # requests (NFR-07).
    database_url: str = ""

    # When empty, POST /api/demo/reset answers 404 and the reset path does not
    # exist at all. Never commit a real token.
    demo_reset_token: str = ""

    # Left empty on purpose: real values belong in .env, never in git.
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    @property
    def cors_origins(self) -> list[str]:
        """Parse ``allowed_origins`` into a list, dropping blanks."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def uses_database(self) -> bool:
        """True when a Postgres URL is configured."""
        return bool(self.database_url.strip())


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
