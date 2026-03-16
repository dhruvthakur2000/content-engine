from pydantic import BaseModel, Field
from typing import Optional, List, Dict


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class GenerateRequest(BaseModel):
    """
    Request body for POST /generate endpoint.
    
    Accepts developer notes and optional git history,
    generates content for specified platforms.
    """

    raw_notes: str = Field(
        ...,
        min_length=10,
        description="Developer notes describing today's work",
        example="Optimized websocket buffering and reduced latency from 820ms to 580ms.",
    )

    raw_git_log: Optional[str] = Field(
        default="",
        description="Optional git log output (from `git log --oneline -20`)",
        example="fix: websocket buffering\nfeat: add redis caching"
    )

    platforms: Optional[List[str]] = Field(
        default=["linkedin", "twitter"],
        description="Platforms to generate content for (linkedin, twitter, blog)",
        example=["linkedin", "twitter"]
    )

    author_name: Optional[str] = Field(
        default="Developer",
        description="Developer name for personalization",
        example="Dhruv"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "raw_notes": "Fixed websocket buffering. Latency: 820ms → 580ms.",
                "raw_git_log": "fix: websocket buffer",
                "platforms": ["linkedin", "twitter"],
                "author_name": "Dhruv"
            }
        }


class GenerateFromFileRequest(BaseModel):
    """
    Request body for POST /generate/file endpoint.
    
    Reads notes from server-side files instead of request body.
    Useful for automated workflows.
    """

    notes_file_path: str = Field(
        default="inputs/today_dump.txt",
        description="Server-side path to notes file",
        example="inputs/today_dump.txt"
    )

    git_repo_path: str = Field(
        default=".",
        description="Server-side path to git repository",
        example="."
    )

    days_back: int = Field(
        default=1,
        ge=1,
        le=30,
        description="Number of days of git history to include (1-30)",
        example=1
    )

    platforms: Optional[List[str]] = Field(
        default=["linkedin", "twitter"],
        description="Platforms to generate content for",
        example=["linkedin", "twitter"]
    )

    author_name: Optional[str] = Field(
        default="Developer",
        description="Developer name for personalization",
        example="Dhruv"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "notes_file_path": "inputs/today_dump.txt",
                "git_repo_path": ".",
                "days_back": 1,
                "platforms": ["linkedin", "twitter"],
                "author_name": "Dhruv"
            }
        }


# ============================================================
# RESPONSE SCHEMAS
# ============================================================

class GenerateResponse(BaseModel):
    """
    Response from generate endpoints.
    
    Returns generated posts for all requested platforms,
    plus execution metadata (timing, cache hits, etc.).
    """

    success: bool = Field(
        description="Whether content generation succeeded"
    )

    generated_posts: dict = Field(
        description="Platform → generated content mapping. Example: {'linkedin': '...', 'twitter': '...'}"
    )

    metadata: dict = Field(
        description="Execution metadata: request_id, cache_hits, cached_node_count, memory_hit, total_service_duration_ms, style_used, model, platforms_generated"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if success=False. None if successful."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "generated_posts": {
                    "linkedin": "Just fixed a critical websocket buffering bug...",
                    "twitter": "1/ Fixed websocket buffering issue that was killing our latency...",
                },
                "metadata": {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "cache_hits": [],
                    "cached_node_count": 0,
                    "memory_hit": False,
                    "total_service_duration_ms": 8340,
                    "style_used": "dhruv_default",
                    "model": "meta-llama/llama-3.1-8b-instruct:free",
                    "platforms_generated": ["linkedin", "twitter"]
                },
                "error": None
            }
        }


class RootResponse(BaseModel):
    """
    Response for GET / (root health check endpoint).
    
    Simple confirmation that server is running.
    """

    status: str = Field(
        description="Server status (always 'online' if responding)"
    )

    app: str = Field(
        description="Application name"
    )

    version: str = Field(
        description="Application version"
    )

    environment: str = Field(
        description="Environment (dev, staging, prod)"
    )

    timestamp: str = Field(
        description="ISO 8601 timestamp"
    )

    docs: str = Field(
        description="URL to API documentation (/docs)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "online",
                "app": "AI Content Engine API",
                "version": "0.1.0",
                "environment": "dev",
                "timestamp": "2026-03-17T10:30:45.123456Z",
                "docs": "/docs"
            }
        }


class HealthCheckResponse(BaseModel):
    """
    Response for GET /health endpoint.
    
    Checks system components and reports health status.
    """

    status: str = Field(
        description="Overall health status (healthy or degraded)"
    )

    checks: Dict = Field(
        description="Individual component checks: api_key_configured, log_directory, inputs_directory, model"
    )

    timestamp: str = Field(
        description="ISO 8601 timestamp of health check"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "checks": {
                    "api_key_configured": True,
                    "log_directory": True,
                    "inputs_directory": True,
                    "model": "meta-llama/llama-3.1-8b-instruct:free"
                },
                "timestamp": "2026-03-17T10:30:45.123456Z"
            }
        }


class ModelsListResponse(BaseModel):
    """
    Response for GET /models endpoint.
    
    Lists available LLM models from OpenRouter.
    Useful for frontend model selector dropdowns.
    """

    current_model: str = Field(
        description="Currently configured LLM model"
    )

    available_models: List[Dict] = Field(
        description="List of available models with id, name, description"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "current_model": "meta-llama/llama-3.1-8b-instruct:free",
                "available_models": [
                    {
                        "id": "meta-llama/llama-3.1-8b-instruct:free",
                        "name": "Llama 3.1 8B (Free)",
                        "description": "Fast, capable, free tier"
                    },
                    {
                        "id": "mistralai/mixtral-8x7b-instruct",
                        "name": "Mixtral 8x7B",
                        "description": "Strong reasoning and writing"
                    }
                ]
            }
        }