# ============================================================
# backend/api/schemas.py — FINAL
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class GenerateRequest(BaseModel):
    """V3 request — accepts any combination of inputs."""

    raw_notes: str = Field(default="", description="Developer notes")
    raw_git_log: str = Field(default="", description="Manual git log")

    # ⚠️ FIX: avoid mutable default list bug
    platforms: List[str] = Field(default_factory=lambda: ["linkedin", "twitter"])

    author_name: str = Field(default="Developer")
    style: str = Field(default="dhruv_default")
    extra_material: str = Field(default="")

    # Optional inputs
    blog_urls: Optional[List[str]] = None
    code_context: Optional[str] = None
    transcript: Optional[str] = None
    doc_references: Optional[str] = None

    blog_style: Optional[str] = Field(default="build_in_public")

    # Git
    git_repo_path: str = Field(default=".")
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None


class GenerateFromFileRequest(BaseModel):

    notes_file_path: str = Field(default="inputs/today_dump.txt")
    git_repo_path: str = Field(default=".")
    days_back: int = Field(default=1, ge=1, le=30)

    platforms: List[str] = Field(default_factory=lambda: ["linkedin", "twitter"])

    author_name: str = Field(default="Developer")
    style: str = Field(default="dhruv_default")
    extra_material: str = Field(default="")
    blog_style: str = Field(default="build_in_public")


class GenerateResponse(BaseModel):
    success: bool
    generated_posts: Dict[str, str]
    metadata: Dict
    error: Optional[str] = None