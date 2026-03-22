from pydantic import BaseModel, Field
from typing import Optional, List, Dict


# ---------------------------------------------------------
# REQUEST
# ---------------------------------------------------------

class GenerateRequest(BaseModel):
    raw_notes: str = Field(..., min_length=10, description="Developer notes (min 10 chars)")
    raw_git_log: Optional[str] = Field(default="", description="Optional git log")
    platforms: List[str] = Field(default=["linkedin"], description="Platforms to generate for")
    author_name: Optional[str] = Field(default="Developer", description="Developer name")
    style: Optional[str] = Field(default="dhruv_default", description="Style profile")
    extra_material: Optional[str] = Field(default="", description="Extra material for blog")


class GenerateFromFileRequest(BaseModel):
    notes_file_path: str = Field(default="inputs/today_dump.txt", description="Server-side path to notes file")
    git_repo_path: str = Field(default=".", description="Server-side path to git repo")
    days_back: int = Field(default=1, ge=1, le=30, description="Days of git history (1-30)")
    platforms: List[str] = Field(default=["linkedin"], description="Platforms to generate for")
    author_name: Optional[str] = Field(default="Developer", description="Developer name")
    style: Optional[str] = Field(default="dhruv_default", description="Style profile")
    extra_material: Optional[str] = Field(default="", description="Extra material for blog")


# ---------------------------------------------------------
# RESPONSE
# ---------------------------------------------------------

class GenerateResponse(BaseModel):
    success: bool
    generated_posts: Dict[str, str]
    metadata: Dict
    error: Optional[str] = None