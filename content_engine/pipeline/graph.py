import threading
from langgraph.graph import StateGraph, END

from content_engine.pipeline.state import PipelineState

# -------------------------------
# NODES
# -------------------------------

from content_engine.pipeline.nodes.input_detector import input_detector_node
from content_engine.pipeline.nodes.parse_notes import parse_notes_node
from content_engine.pipeline.nodes.parse_git import parse_git_node
from content_engine.pipeline.nodes.parse_code import parse_code_node

from content_engine.pipeline.nodes.context_builder import context_builder_node
from content_engine.pipeline.nodes.angle import angle_node
from content_engine.pipeline.nodes.style_selector import style_selector_node
from content_engine.pipeline.nodes.blog_blueprint import blog_blueprint_node
from content_engine.pipeline.nodes.post_generator import post_generator_node
from content_engine.pipeline.nodes.humanize import humanize_node

from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)

_pipeline_instance = None
_pipeline_lock = threading.Lock()


# ============================================================
# 🔥 CRITICAL: ADAPTER LAYER
# ============================================================

def _adapt(node_fn):
    def wrapper(lg_state: dict):
        state: PipelineState = lg_state["state"]

        result = node_fn(state)

        if result:
            state.update(result)

        return {"state": state}   # 🚨 CRITICAL

    return wrapper


# ============================================================
# BUILD GRAPH
# ============================================================

def build_pipeline():

    graph = StateGraph(dict)   # 🚨 IMPORTANT: dict, not PipelineState

    nodes = {
        "input_detector": input_detector_node,
        "parse_notes": parse_notes_node,
        "parse_git": parse_git_node,
        "parse_code": parse_code_node,
        "context_builder": context_builder_node,
        "angle_generator": angle_node,
        "style_selector": style_selector_node,
        "blog_blueprint": blog_blueprint_node,
        "post_generator": post_generator_node,
        "humanize": humanize_node,
    }

    # ✅ Wrap nodes
    for name, node in nodes.items():
        graph.add_node(name, _adapt(node))

    # -------------------------------
    # ENTRY
    # -------------------------------

    graph.set_entry_point("input_detector")

    # -------------------------------
    # FLOW
    # -------------------------------

    graph.add_edge("input_detector", "parse_notes")
    graph.add_edge("input_detector", "parse_git")
    graph.add_edge("input_detector", "parse_code")

    graph.add_edge("parse_notes", "context_builder")
    graph.add_edge("parse_git", "context_builder")
    graph.add_edge("parse_code", "context_builder")

    graph.add_edge("context_builder", "angle_generator")
    graph.add_edge("angle_generator", "style_selector")
    graph.add_edge("style_selector", "blog_blueprint")
    graph.add_edge("blog_blueprint", "post_generator")
    graph.add_edge("post_generator", "humanize")
    graph.add_edge("humanize", END)

    compiled = graph.compile()

    logger.info(
        "pipeline_compiled_final",
        node_count=len(nodes),
        nodes=list(nodes.keys()),
    )

    return compiled


# ============================================================
# SINGLETON
# ============================================================

def get_pipeline():
    global _pipeline_instance

    if _pipeline_instance is None:
        with _pipeline_lock:
            if _pipeline_instance is None:
                _pipeline_instance = build_pipeline()

    return _pipeline_instance


# ============================================================
# 🚀 INVOKE FUNCTION (CRITICAL)
# ============================================================

def invoke_pipeline(state: PipelineState) -> PipelineState:

    pipeline = get_pipeline()

    result = pipeline.invoke({"state": state})

    if not result or "state" not in result:
        raise ValueError("Pipeline returned invalid result")

    return result["state"]