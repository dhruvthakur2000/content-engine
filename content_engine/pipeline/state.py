from typing import TypedDict, Optional, Any

class PipelineState(TypedDict, total= False):
    """
    Shared state object passed through all langraph nodes
    """
    #--Input fields ------------
    
    

    commits: list[str]
    dump_text: str

    context_summary: str
    technical_summary: str
    persona: str

    x_post: str
    linkedin_post: str
    thread: str
    blog: str