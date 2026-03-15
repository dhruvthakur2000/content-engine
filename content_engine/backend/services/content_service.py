from content_engine.pipeline.graph import build_pipeline
from content_engine.pipeline.state import PipelineState

class ContentService:
    """
    Runs the langgraph pipeline
    """

    def __init__(self):
        self.graph_pipeline = build_pipeline()

    async def generate_content(self, notes: str, git_log: str | None, platform: str):
        
        state= PipelineState(
            raw_notes = notes,
            git_log = git_log or "",
            platform=platform
        )

        result =  await self.graph_pipeline.ainvoke(state)

        return result["generated_text"]