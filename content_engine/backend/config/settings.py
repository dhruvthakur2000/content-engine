from functools import lru_cache          # Caches the settings object after first call
from pydantic_settings import BaseSettings, SettingsConfigDict  # Core config engine
from pydantic import Field               # Adds default values and descriptions


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.

    Pydantic-Settings automatically:
      - Reads each attribute from the matching ENV VAR (case-insensitive)
      - Falls back to the default value if the env var is missing
      - Raises a ValidationError if a required var is missing
    """

    # ── model_config ─────────────────────────────────────────
    # Tells Pydantic-Settings WHERE to find the .env file and
    # whether env var names are case-sensitive.
    model_config = SettingsConfigDict(
        env_file=".env",          # Load from .env at project root
        env_file_encoding="utf-8",
        case_sensitive=False,     # OPENROUTER_API_KEY == openrouter_api_key
        extra="ignore",           # Silently ignore unknown env vars
    )

    # ── OpenRouter / LLM Settings ─────────────────────────────
    # OpenRouter is an API gateway that routes to many LLMs.
    # We use it like the OpenAI SDK — just swap the base_url.
    openrouter_api_key: str = Field(
        default="",
        description="API key from https://openrouter.ai/keys"
    )

    # Which model to use — can be any model supported by OpenRouter.
    # Default: a capable, cheap open-source model.
    llm_model: str = Field(
        default="meta-llama/llama-3.1-8b-instruct:free",
        description="OpenRouter model identifier"
    )

    # Base URL for the OpenRouter API — uses OpenAI-compatible endpoint.
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )

    # ── Application Settings ──────────────────────────────────
    app_env: str = Field(
        default="development",
        description="Environment: development | production"
    )

    # Port the FastAPI server listens on.
    api_port: int = Field(
        default=8000,
        description="FastAPI server port"
    )

    # Port the Streamlit frontend listens on.
    streamlit_port: int = Field(
        default=8501,
        description="Streamlit frontend port"
    )

    # ── Logging Settings ──────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG | INFO | WARNING | ERROR"
    )

    log_dir: str = Field(
        default="logs",
        description="Directory where log files are written"
    )

    # ── App Identity ──────────────────────────────────────────
    app_name: str = Field(
        default="AI Content Engine",
        description="Human-readable application name"
    )

    app_version: str = Field(
        default="0.1.0",
        description="Application version string"
    )

    @property
    def is_production(self) -> bool:
        """Convenience property: True when running in production mode."""
        return self.app_env.lower() == "production"

    @property
    def api_base_url(self) -> str:
        """Full URL of the FastAPI server — used by Streamlit to call the API."""
        return f"http://localhost:{self.api_port}"


@lru_cache()  # <- This decorator ensures we only parse .env ONCE per process
def get_settings() -> Settings:
    """
    Returns the singleton Settings instance.

    Usage anywhere in the codebase:
        from backend.config.settings import get_settings
        settings = get_settings()
        print(settings.llm_model)
    """
    return Settings()