# ============================================================
# pipeline/nodes/blog_blueprint.py
# ============================================================

from langchain_core.messages import HumanMessage

from content_engine.pipeline.state import PipelineState
from content_engine.backend.llm.providers import get_llm
from content_engine.backend.utils.debug_nodes import save_debug

from content_engine.backend.llm.prompts import BLOG_BLUEPRINT_PROMPT
from content_engine.pipeline.utils.node_wrapper import pipeline_node


llm = get_llm()


@pipeline_node("blog_blueprint")
def blog_blueprint_node(state: PipelineState) -> PipelineState:
    """
    Generates a structured blueprint for the blog post.
    """

    platforms = state.get("platforms", [])
    if "blog" not in [p.lower() for p in platforms]:
        return {"blog_blueprint": ""}

    context = state.get("context", "")
    style_guide = state.get("style_guide", "")

    extra_material = state.get("extra_material", "").strip()
    if not extra_material:
        extra_material = "No additional material provided. Use the engineering context only."

    if not context or len(context.strip()) < 30:
        return {"blog_blueprint": "[No context available for blog blueprint]"}

    prompt = BLOG_BLUEPRINT_PROMPT.format(
        context=context,
        extra_material=extra_material,
        style_guide=style_guide
    )

    response = llm.invoke([HumanMessage(content=prompt)])

    blueprint = response.content.strip()
    save_debug("blog_blueprint",blueprint)
    return {"blog_blueprint": blueprint}