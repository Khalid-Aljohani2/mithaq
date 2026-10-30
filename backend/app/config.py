"""Application settings, loaded from the environment via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

#: The model every AI stage uses unless settings or a per-stage override says
#: otherwise. Declared here as configuration, not inline at a call site.
DEFAULT_MODEL = "claude-sonnet-5-5"


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

    # ---- AI provider ----
    # Left empty on purpose: real values belong in .env, never in git.
    #: "anthropic" uses the real provider; anything else uses the scripted one.
    llm_provider: str = ""
    #: Never logged, never echoed, never included in an error message.
    llm_api_key: str = ""
    #: The default model for every AI stage. Configuration, never hardcoded.
    #: An empty value in .env falls back to DEFAULT_MODEL rather than to "",
    #: so a blank line in an env file cannot silently unset the model.
    llm_model: str = ""
    #: Per-stage overrides, e.g. "INTAKE=claude-haiku-5-5,RISK_COMPLIANCE=claude-opus-5-5".
    llm_model_overrides: str = ""
    #: Effort level. Empty means the model's own default.
    llm_effort: str = ""
    llm_timeout_seconds: float = 90.0
    #: SDK-level retries for connection errors, 429 and 5xx. The one retry on a
    #: schema-invalid response is separate and lives in the provider (NFR-03).
    llm_max_retries: int = 2
    llm_max_tokens: int = 4096

    # ---- Rate limiting (NFR-08) ----
    #: Requests per window per client IP against the AI endpoints. 0 disables.
    ai_rate_limit_requests: int = 20
    ai_rate_limit_window_seconds: int = 60

    @property
    def cors_origins(self) -> list[str]:
        """Parse ``allowed_origins`` into a list, dropping blanks."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def uses_database(self) -> bool:
        """True when a Postgres URL is configured."""
        return bool(self.database_url.strip())

    @property
    def uses_live_provider(self) -> bool:
        """True only when the real provider is both selected and usable.

        A selected provider with no key is not usable, and saying so here keeps
        the fallback decision in one place.
        """
        return self.llm_provider.strip().lower() == "anthropic" and bool(self.llm_api_key.strip())

    @property
    def llm_provider_requested(self) -> bool:
        """True when anthropic was asked for, whether or not a key is present."""
        return self.llm_provider.strip().lower() == "anthropic"

    @property
    def default_model(self) -> str:
        """The configured default, or DEFAULT_MODEL when unset."""
        return self.llm_model.strip() or DEFAULT_MODEL

    def model_for(self, stage: str) -> str:
        """The model a stage runs on: its override, else the default."""
        return self.stage_model_overrides.get(stage, self.default_model)

    @property
    def stage_model_overrides(self) -> dict[str, str]:
        """Parse ``llm_model_overrides`` into a stage to model map."""
        overrides: dict[str, str] = {}
        for pair in self.llm_model_overrides.split(","):
            stage, _, model = pair.partition("=")
            if stage.strip() and model.strip():
                overrides[stage.strip().upper()] = model.strip()
        return overrides

    @property
    def rate_limit_enabled(self) -> bool:
        return self.ai_rate_limit_requests > 0


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
