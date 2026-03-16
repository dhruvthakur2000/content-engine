from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================
    # LLM PROVIDER
    # =========================================================

    hf_token: str = Field(
        default="",
        description="HuggingFace API token"
    )

    hf_base_url: str = Field(
        default="https://router.huggingface.co/v1",
        description="HF OpenAI-compatible router"
    )

    # =========================================================
    # TASK BASED MODEL ROUTING
    # =========================================================

    parse_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct",
        description="Model used for parsing tasks"
    )

    reason_model: str = Field(
        default="Qwen/Qwen2.5-14B-Instruct",
        description="Model used for reasoning"
    )

    generation_model: str = Field(
        default="Qwen/Qwen2.5-72B-Instruct",
        description="Primary generation model"
    )

    blog_model: str = Field(
        default="Qwen/Qwen2.5-72B-Instruct",
        description="Model used for blog generation"
    )

    # =========================================================
    # FALLBACK MODELS
    # =========================================================

    fallback_model_1: str = Field(
        default="Qwen/Qwen2.5-32B-Instruct",
        description="First fallback model"
    )

    fallback_model_2: str = Field(
        default="Qwen/Qwen2.5-14B-Instruct",
        description="Second fallback model"
    )

    llm_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max retry attempts per model"
    )

    # =========================================================
    # GENERATION PARAMETERS
    # =========================================================

    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0
    )

    llm_max_tokens: int = Field(
        default=2500,
        ge=256,
        le=8192
    )

    llm_request_timeout: int = Field(
        default=120,
        ge=30,
        le=300
    )

    # =========================================================
    # PROMPT VERSIONING
    # Used by cache manager to invalidate cache when prompts change
    # =========================================================

    prompt_version: str = Field(
        default="v1",
        description="Used for cache invalidation when prompts change"
    )

    # =========================================================
    # CACHE LAYER
    # =========================================================

    cache_enabled: bool = Field(
        default=True
    )

    cache_dir: str = Field(
        default="cache"
    )

    cache_ttl_hours: float = Field(
        default=24.0
    )

    # =========================================================
    # SEMANTIC MEMORY
    # =========================================================

    memory_enabled: bool = Field(
        default=False
    )

    memory_dir: str = Field(
        default="memory"
    )

    memory_similarity_threshold: float = Field(
        default=0.82,
        ge=0.0,
        le=1.0
    )

    # =========================================================
    # PIPELINE EXECUTION
    # =========================================================

    max_pipeline_workers: int = Field(
        default=4,
        description="Concurrent pipeline executions"
    )

    # =========================================================
    # APPLICATION SETTINGS
    # =========================================================

    app_env: str = Field(
        default="development"
    )

    api_port: int = Field(
        default=8000
    )

    streamlit_port: int = Field(
        default=8501
    )

    allowed_origins: str = Field(
        default="*"
    )

    default_platforms: str = Field(
        default="linkedin,twitter"
    )

    # =========================================================
    # LOGGING
    # =========================================================

    log_level: str = Field(
        default="INFO"
    )

    log_dir: str = Field(
        default="logs"
    )

    # =========================================================
    # APP METADATA
    # =========================================================

    app_name: str = Field(
        default="AI Content Engine"
    )

    app_version: str = Field(
        default="2.0.0"
    )

    # =========================================================
    # COMPUTED PROPERTIES
    # =========================================================

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def hf_token_configured(self) -> bool:
        return bool(self.hf_token and self.hf_token.strip())

    @property
    def api_base_url(self) -> str:
        return f"http://localhost:{self.api_port}"

    @property
    def allowed_origins_list(self):
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def default_platforms_list(self):
        return [p.strip() for p in self.default_platforms.split(",") if p.strip()]


# ============================================================
# SETTINGS SINGLETON
# ============================================================

@lru_cache()
def get_settings() -> Settings:
    """
    Singleton settings loader.
    Parses .env exactly once.
    """
    return Settings()