# ============================================================
# pipeline/nodes/style_selector.py
# ============================================================

from content_engine.pipeline.state import PipelineState
from content_engine.backend.llm.style_loader import load_style
from content_engine.pipeline.utils.node_wrapper import pipeline_node


DEFAULT_STYLE = "dhruv_default"


@pipeline_node("style_selector")
def style_selector_node(state: PipelineState) -> PipelineState:
    """
    Loads the creator style profile and injects it into the pipeline state.
    """

    style_name = state.get("style", DEFAULT_STYLE) or DEFAULT_STYLE

    style_guide = load_style(style_name)

    return {"style_guide": style_guide}