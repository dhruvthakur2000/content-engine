from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node as _pn5
from content_engine.backend.llm.style_loader import load_style
from content_engine.backend.utils.logger import get_logger as _get_logger5

_logger5 = _get_logger5("style_selector")


@_pn5("style_selector")
def style_selector_node(state: PipelineState) -> PipelineState:

    style_name = state.get("style", "dhruv_default")

    try:
        style_guide = load_style(style_name)

    except Exception as e:
        _logger5.error("style_load_failed", error=str(e))
        style_guide = "Default writing style."

    _logger5.info("style_selected", style=style_name, chars=len(style_guide))

    return {"style_guide": style_guide}