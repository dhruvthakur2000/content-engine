from typing import TypedDict, Optional, List, Dict, Any

# ============================================================
# PIPELINE STATE
# ============================================================

class PipelineState(TypedDict):
    """Pipeline state containing all data flowing through the graph"""
    # Input
    raw_notes: str
    raw_git_log: Optional[str]
    platforms: List[str]
    author_name: str
    style: str
    extra_material: Optional[str]
    memory_context: Optional[str]
    
    # Intermediate
    parsed_notes: Optional[str]
    parsed_git: Optional[str]
    context: Optional[str]
    narrative_angle: Optional[str]
    hook: Optional[str]
    key_detail: Optional[str]
    style_guide: Optional[str]
    blog_blueprint: Optional[str]
    
    # Output
    generated_posts: Optional[Dict[str, str]]
    metadata: Optional[Dict[str, Any]]
    cache_hits: List[str]


# Note: Pipeline building logic is in graph.py to avoid circular imports