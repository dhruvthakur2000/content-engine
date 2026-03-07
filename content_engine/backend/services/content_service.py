from content_engine.pipeline.graph import build_graph
from content_engine.pipeline.state import PipelineState

class ContentService:
    """
    Runs the langgraph pipeline
    """

    def __init__(self):
        self.graph = build_graph()

    async def generate_content(self, notes: str, git_log: str | None, platform: str)
        
        state= PipelineState(
            raw_notes = notes,
            git_log = git_log or "",
            platform=platform
        )

        result =  await self.graph.ainvoke(state)

        return result["generated_text"]