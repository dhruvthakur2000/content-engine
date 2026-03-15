from pydantic import BaseModel, Field
from typing import List, Optional


class ContentRequest(BaseModel):

    raw_notes: str = Field(
        ...,
        description="Developer notes describing work done"
    )

    raw_git_log: Optional[str] = Field(
        default="",
        description="Optional git commit history"
    )

    platforms: Optional[List[str]] = Field(
        default=["linkedin", "twitter"],
        description="Platforms to generate content for"
    )

    author_name: Optional[str] = Field(
        default="Developer"
    )

    style: Optional[str] = Field(
        default="dhruv_default"
    )

    extra_material: Optional[str] = Field(
        default=""
    )