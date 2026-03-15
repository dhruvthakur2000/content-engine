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

    # ============================================================
    # HuggingFace Router Settings
    # ============================================================

    hf_api_key: str = Field(
        default="",
        description="HuggingFace API token"
    )

    hf_base_url: str = Field(
        default="https://router.huggingface.co/v1",
        description="HuggingFace inference router base URL"
    )

    # ============================================================
    # MODEL ROUTING (Task-specific models)
    # ============================================================

    parse_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct",
        description="Model used for parsing tasks"
    )

    reason_model: str = Field(
        default="Qwen/Qwen2.5-14B-Instruct",
        description="Model used for reasoning tasks"
    )

    generation_model: str = Field(
        default="Qwen/Qwen2.5-72B-Instruct",
        description="Model used for LinkedIn/Twitter generation"
    )

    blog_model: str = Field(
        default="Qwen/Qwen2.5-72B-Instruct",
        description="Model used for blog generation"
    )

    # ============================================================
    # FALLBACK MODELS
    # ============================================================

    fallback_model_1: str = Field(
        default="meta-llama/Meta-Llama-3-8B-Instruct",
        description="First fallback model"
    )

    fallback_model_2: str = Field(
        default="mistralai/Mistral-7B-Instruct-v0.3",
        description="Second fallback model"
    )

    # ============================================================
    # LLM GENERATION PARAMETERS
    # ============================================================

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

    llm_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for LLM calls"
    )

    # ============================================================
    # CACHE SETTINGS (LangGraph Node Cache)
    # ============================================================

    prompt_version: str ="v1"
    
    
    cache_enabled: bool = Field(
        default=True,
        description="Enable node-level caching"
    )

    cache_dir: str = Field(
        default="cache",
        description="Directory where cache files are stored"
    )

    cache_ttl_hours: int = Field(
        default=72,
        description="Cache expiration time"
    )

    # ============================================================
    # CONTENT MEMORY SETTINGS (Semantic memory)
    # ============================================================

    enable_memory: bool = Field(
        default=False,
        description="Enable semantic memory layer"
    )

    memory_collection: str = Field(
        default="content_engine_memory"
    )

    memory_top_k: int = Field(
        default=3,
        description="How many similar past results to retrieve"
    )

    # ============================================================
    # APPLICATION SETTINGS
    # ============================================================

    app_env: str = Field(
        default="development"
    )

    api_port: int = Field(
        default=8000
    )

    streamlit_port: int = Field(
        default=8501
    )

    max_pipeline_workers: int = Field(
        default=4
    )

    # ============================================================
    # PLATFORM DEFAULTS
    # ============================================================

    default_platforms: str = Field(
        default="linkedin,twitter"
    )

    allowed_origins: str = Field(
        default="*"
    )

    # ============================================================
    # LOGGING
    # ============================================================

    log_level: str = Field(
        default="INFO"
    )

    log_dir: str = Field(
        default="logs"
    )

    # ============================================================
    # APP METADATA
    # ============================================================

    app_name: str = Field(
        default="AI Content Engine"
    )

    app_version: str = Field(
        default="0.1.0"
    )

    # ============================================================
    # COMPUTED PROPERTIES
    # ============================================================

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def hf_token_configured(self) -> bool:
        return bool(self.hf_api_key and self.hf_api_key.strip())

    @property
    def api_base_url(self) -> str:
        return f"http://localhost:{self.api_port}"

    @property
    def allowed_origins_list(self):
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()