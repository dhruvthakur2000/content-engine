from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node as _pn6
from content_engine.backend.llm.providers import get_llm as _get_llm6
from content_engine.backend.cache.cache_manager import get_cache as _get_cache6
from content_engine.backend.llm.prompts import BLOG_BLUEPRINT_PROMPT
from content_engine.backend.utils.logger import get_logger as _get_logger6

_llm6 = _get_llm6()
_cache6 = _get_cache6()
_logger6 = _get_logger6("blog_blueprint")

NODE_NAME = "blog_blueprint"


@_pn6(NODE_NAME)
def blog_blueprint_node(state: PipelineState) -> PipelineState:

    platforms = [p.lower() for p in state.get("platforms", [])]

    if "blog" not in platforms:
        return {"blog_blueprint": ""}

    context = state.get("context", "").strip()

    if not context or len(context) < 30:
        return {"blog_blueprint": "[No context available]"}

    cache_key = f"{context}|blog_blueprint_v1"

    cached = _cache6.read(input_data=cache_key, node_name=NODE_NAME)

    if cached and "blog_blueprint" in cached:
        return {"blog_blueprint": cached["blog_blueprint"]}

    extra_material = state.get("extra_material", "").strip() or "No additional material provided."
    blog_style = state.get("blog_style", "build_in_public")

    prompt = BLOG_BLUEPRINT_PROMPT.format(
        context=context,
        extra_material=extra_material,
        blog_style=blog_style,
    )

    try:
        from langchain_core.messages import HumanMessage as HM6
        response = _llm6.invoke([HM6(content=prompt)], task="blog")
        blueprint = response.content.strip()

    except Exception as e:
        _logger6.error("blog_blueprint_error", error=str(e))
        blueprint = f"[Blueprint generation failed: {str(e)}]"

    _cache6.write(input_data=cache_key, result={"blog_blueprint": blueprint}, node_name=NODE_NAME)

    return {"blog_blueprint": blueprint}