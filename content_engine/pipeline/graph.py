from langgraph.graph import StateGraph, END   # Core LangGraph classes

from pipeline.state import PipelineState             # Our shared state schema

# Import all pipeline node functions
from pipeline.nodes.parse_notes import parse_notes_node       # Stage 1
from pipeline.nodes.parse_git import parse_git_node           # Stage 2
from pipeline.nodes.context_builder import context_builder_node  # Stage 3
from pipeline.nodes.angle import angle_node                   # Stage 4
from pipeline.nodes.post_generator import post_generator_node # Stage 5

from backend.utils.logger import get_logger

logger = get_logger(__name__)


def build_pipeline():
    """
    Constructs and compiles the LangGraph content generation pipeline.

    This function is called ONCE at startup (in run_pipeline.py).
    The compiled graph is then reused for every request.

    Returns:
        A compiled LangGraph graph object with a `.invoke()` method.

    Usage:
        graph = build_pipeline()
        result = graph.invoke({
            "raw_notes": "...",
            "raw_git_log": "...",
            "platforms": ["linkedin", "twitter"]
        })
    """

    # ── Step 1: Create a StateGraph ───────────────────────────
    # StateGraph is LangGraph's core class.
    # We pass our PipelineState TypedDict to tell it the state schema.
    # This enables type checking and IDE autocomplete.
    graph = StateGraph(PipelineState)

    # ── Step 2: Add nodes ─────────────────────────────────────
    # .add_node(name, function) registers a node with the graph.
    # The name is used to reference this node in edges below.
    # The function is the actual Python function to call.

    graph.add_node("parse_notes", parse_notes_node)
    # parse_notes_node receives PipelineState, reads raw_notes,
    # returns {"parsed_notes": "..."}

    graph.add_node("parse_git", parse_git_node)
    # parse_git_node receives PipelineState, reads raw_git_log,
    # returns {"parsed_git": "..."}

    graph.add_node("context_builder", context_builder_node)
    # context_builder_node reads parsed_notes + parsed_git,
    # returns {"context": "..."}

    graph.add_node("angle_generator", angle_node)
    # angle_node reads context, calls LLM,
    # returns {"narrative_angle": "...", "hook": "...", "key_detail": "..."}

    graph.add_node("post_generator", post_generator_node)
    # post_generator_node reads context + angle + hook + key_detail,
    # generates posts for all platforms,
    # returns {"generated_posts": {...}, "metadata": {...}}

    # ── Step 3: Set the entry point ───────────────────────────
    # .set_entry_point() tells LangGraph which node to execute FIRST
    # when .invoke() is called.
    graph.set_entry_point("parse_notes")

    # ── Step 4: Add edges (define execution order) ────────────
    # .add_edge(from_node, to_node) creates a directed connection.
    # After from_node completes, to_node runs next.
    # The state is passed between nodes automatically.

    graph.add_edge("parse_notes", "parse_git")
    # After parse_notes completes → run parse_git
    # NOTE: These run sequentially. Future improvement: run them
    # in parallel since they don't depend on each other.

    graph.add_edge("parse_git", "context_builder")
    # After parse_git completes → run context_builder
    # context_builder needs BOTH parsed_notes AND parsed_git to be ready

    graph.add_edge("context_builder", "angle_generator")
    # After context_builder → run angle_generator

    graph.add_edge("angle_generator", "post_generator")
    # After angle_generator → run post_generator

    graph.add_edge("post_generator", END)
    # After post_generator → pipeline is done (END is a special LangGraph constant)

    # ── Step 5: Compile the graph ─────────────────────────────
    # .compile() validates the graph structure (no orphan nodes, etc.)
    # and returns an executable Runnable object with .invoke() method.
    compiled_graph = graph.compile()

    logger.info(
        "pipeline_compiled",
        nodes=["parse_notes", "parse_git", "context_builder", "angle_generator", "post_generator"],
        stages=5,
    )

    return compiled_graph


# ── Module-level singleton ────────────────────────────────────
# Build the pipeline ONCE when this module is imported.
# This avoids rebuilding on every API request (which would be slow).
#
# `_pipeline_instance` is a private module variable (convention: leading underscore)
_pipeline_instance = None


def get_pipeline():
    """
    Returns the singleton compiled pipeline instance.

    Uses lazy initialization — builds the pipeline on first call,
    then reuses the same instance for all subsequent calls.

    This is thread-safe for read-only usage (LangGraph graphs are immutable after compile).

    Returns:
        Compiled LangGraph pipeline ready to invoke.
    """
    global _pipeline_instance  # Access the module-level variable

    # If the pipeline hasn't been built yet, build it now
    if _pipeline_instance is None:
        logger.info("pipeline_initializing")
        _pipeline_instance = build_pipeline()
        logger.info("pipeline_ready")

    return _pipeline_instance