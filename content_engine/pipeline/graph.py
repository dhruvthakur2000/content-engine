import threading

from langgraph.graph import StateGraph, END

from content_engine.pipeline.state import PipelineState

from content_engine.pipeline.nodes.parse_notes import parse_notes_node
from content_engine.pipeline.nodes.parse_git import parse_git_node
from content_engine.pipeline.nodes.context_builder import context_builder_node
from content_engine.pipeline.nodes.angle import angle_node
from content_engine.pipeline.nodes.style_selector import style_selector_node
from content_engine.pipeline.nodes.blog_blueprint import blog_blueprint_node
from content_engine.pipeline.nodes.post_generator import post_generator_node

from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)

_pipeline_instance = None
_pipeline_lock = threading.Lock()


# ------------------------------------------------------------
# BUILD GRAPH
# ------------------------------------------------------------

def build_pipeline():

    graph = StateGraph(PipelineState)

    # --------------------------------------------------------
    # REGISTER NODES
    # --------------------------------------------------------

    nodes = {
        "parse_notes": parse_notes_node,
        
        "parse_git": parse_git_node,
        "context_builder": context_builder_node,
        "angle_generator": angle_node,
        "style_selector": style_selector_node,
        "blog_blueprint": blog_blueprint_node,
        "post_generator": post_generator_node,
    }

    for name, node in nodes.items():
        graph.add_node(name, node)

    # --------------------------------------------------------
    # ENTRY POINT
    # --------------------------------------------------------

    graph.set_entry_point("parse_notes")

    graph.add_edge("parse_notes", "parse_git")
    graph.add_edge("parse_git", "context_builder")

    # --------------------------------------------------------
    # MAIN PIPELINE
    # --------------------------------------------------------

    graph.add_edge("context_builder", "angle_generator")
    graph.add_edge("angle_generator", "style_selector")
    graph.add_edge("style_selector", "blog_blueprint")
    graph.add_edge("blog_blueprint", "post_generator")
    graph.add_edge("post_generator", END)

    compiled = graph.compile()

    logger.info(
        "pipeline has been compiled with:",
        node_count=len(nodes),
        nodes=list(nodes.keys()),
    )

    return compiled


# ------------------------------------------------------------
# SINGLETON ACCESS
# ------------------------------------------------------------

def get_pipeline():

    global _pipeline_instance

    if _pipeline_instance is None:
        with _pipeline_lock:
            if _pipeline_instance is None:
                _pipeline_instance = build_pipeline()

    return _pipeline_instance