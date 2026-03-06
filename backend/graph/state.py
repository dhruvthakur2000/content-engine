from typing import TypedDict

class ContentState(TypedDict):

    commits: list[str]
    dump_text: str

    context_summary: str
    technical_summary: str
    persona: str

    x_post: str
    linkedin_post: str
    thread: str
    blog: str