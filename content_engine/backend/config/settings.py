from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):

    # pydantic-settings reads this to find and parse the .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # HF_TOKEN == hf_token in .env
        extra="ignore",         # Unknown .env keys don't cause errors
    )

    # ==========================================================
    # LLM PROVIDER
    # ==========================================================

    hf_token: str = Field(default="", description="HuggingFace API token")

    hf_base_url: str = Field(
        default="https://router.huggingface.co/v1",
        description="HF OpenAI-compatible router endpoint"
    )

    # Parsing = extract structured info from raw text — cheap model ok
    parse_model: str = Field(
        default="mistralai/Mistral-7B-v0.1",
        description="Model for parse_notes, parse_git, parse_code nodes"
    )

    # Reasoning = angle selection, orchestration decisions — mid-tier
    reason_model: str = Field(
        default="mistralai/Mistral-7B-v0.1",
        description="Model for angle_node, orchestrator_agent"
    )

    # Generation = final content output — use best available
    generation_model: str = Field(
        default="mistralai/Mistral-7B-v0.1",
        description="Primary model for post_generator and blog"
    )

    # Blog = two-stage blog generation — needs highest quality
    blog_model: str = Field(
        default="mistralai/Mistral-7B-v0.1",
        description="Model for blog_blueprint and blog generation"
    )

    # Evaluation = scoring generated content — needs judgment ability
    eval_model: str = Field(
        default="mistralai/Mistral-7B-v0.1",
        description="Model for evaluator_node — judges output quality"
    )

    # ==========================================================
    # FALLBACK MODELS
    # If primary model fails after max_retries, try these in order.
    # This is why ProviderManager has a models_to_try loop.
    # ==========================================================

    fallback_model_1: str = Field(
        default="stabilityai/stable-code-3b",
        description="First fallback if primary model fails"
    )

    fallback_model_2: str = Field(
        default="stabilityai/stable-code-3b",
        description="Second fallback"
    )

    llm_max_retries: int = Field(default=3, ge=1, le=10)

    # ==========================================================
    # GENERATION PARAMETERS
    # ==========================================================

    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2500, ge=256, le=8192)
    llm_request_timeout: int = Field(default=120, ge=30, le=300)

    # ==========================================================
    # PROMPT VERSIONING
    # When you change a prompt, bump this version.
    # The cache key is hash(prompt_version + node_name + input),
    # so bumping the version invalidates ALL existing cache entries
    # automatically — no manual cache clearing needed.
    # ==========================================================

    prompt_version: str = Field(default="v3", description="Cache invalidation key")

    # ==========================================================
    # CACHE LAYER
    # ==========================================================

    cache_enabled: bool = Field(default=True)
    cache_dir: str = Field(default="cache")
    cache_ttl_hours: float = Field(default=24.0)

    # ==========================================================
    # SEMANTIC MEMORY (ChromaDB)
    # ==========================================================

    memory_enabled: bool = Field(default=False)
    memory_dir: str = Field(default="memory")
    memory_similarity_threshold: float = Field(default=0.82, ge=0.0, le=1.0)

    # ==========================================================
    # MULTI-AGENT CONFIG (V3)
    # ==========================================================

    # Max parallel agents — controls asyncio.gather() concurrency
    max_agent_workers: int = Field(default=4, ge=1, le=10)

    # If True, agents run in parallel via asyncio.gather()
    # If False, agents run sequentially (safer for debugging)
    agent_parallel_execution: bool = Field(default=True)

    # ==========================================================
    # EVALUATION FRAMEWORK (V3 Phase 4)
    # ==========================================================

    eval_enabled: bool = Field(
        default=True,
        description="Run evaluator_node after generation"
    )

    eval_min_specificity: int = Field(
        default=6, ge=1, le=10,
        description="Minimum specificity score (1-10) to pass"
    )

    eval_max_ai_tone: int = Field(
        default=4, ge=1, le=10,
        description="Maximum AI-tone score (1-10) to pass — lower is better"
    )

    eval_max_regenerations: int = Field(
        default=2, ge=0, le=5,
        description="Max times to regenerate if eval fails"
    )

    # ==========================================================
    # SECURITY (V3 Phase 5)
    # ==========================================================

    security_enabled: bool = Field(
        default=True,
        description="Run security_node before pipeline starts"
    )

    # Comma-separated list of forbidden patterns in user input
    security_blocked_patterns: str = Field(
        default="ignore previous instructions,disregard your,you are now,act as,jailbreak",
        description="Prompt injection detection patterns"
    )

    # ==========================================================
    # GITHUB INTEGRATION
    # ==========================================================

    github_token: str = Field(default="", description="GitHub personal access token")
    github_owner: str = Field(default="", description="GitHub username or org")
    github_repo: str = Field(default="", description="Default GitHub repo name")

    # ==========================================================
    # APPLICATION
    # ==========================================================

    app_env: str = Field(default="development")
    api_port: int = Field(default=8000)
    streamlit_port: int = Field(default=8501)
    allowed_origins: str = Field(default="*")
    default_platforms: str = Field(default="linkedin,twitter")
    max_pipeline_workers: int = Field(default=4)

    # ==========================================================
    # SECURITY — ADMIN ENDPOINTS
    # ==========================================================

    admin_api_key: str = Field(default="", description="Protects /cache and /memory endpoints")

    # ==========================================================
    # LOGGING
    # ==========================================================

    log_level: str = Field(default="INFO")
    log_dir: str = Field(default="logs")

    # ==========================================================
    # APP METADATA
    # ==========================================================

    app_name: str = Field(default="AI Content Engine")
    app_version: str = Field(default="3.0.0")

    # ==========================================================
    # AUTHOR CONFIGURATION
    # Injected into PERSONA_BLOCK — every LLM call starts with this
    # ==========================================================

    author_name: str = Field(default="Developer")
    author_role: str = Field(default="AI/ML Engineer")
    author_project: str = Field(default="My Project")

    # ==========================================================
    # COMPUTED PROPERTIES
    # @property means these are derived values — not stored in .env
    # They're recalculated each time they're accessed.
    # ==========================================================

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def hf_token_configured(self) -> bool:
        # bool("") = False, bool("hf_xxx") = True
        return bool(self.hf_token and self.hf_token.strip())

    @property
    def admin_auth_enabled(self) -> bool:
        return bool(self.admin_api_key and self.admin_api_key.strip())

    @property
    def allowed_origins_list(self):
        # "http://localhost:3000,http://localhost:8501" → list
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def default_platforms_list(self):
        return [p.strip() for p in self.default_platforms.split(",") if p.strip()]

    @property
    def security_blocked_patterns_list(self):
        return [p.strip().lower() for p in self.security_blocked_patterns.split(",") if p.strip()]


# ============================================================
# SINGLETON
# @lru_cache ensures get_settings() returns the SAME object
# on every call. .env is parsed exactly once at startup.
# Thread-safe because lru_cache uses a lock internally.
# ============================================================

@lru_cache()
def get_settings() -> Settings:
    return Settings()