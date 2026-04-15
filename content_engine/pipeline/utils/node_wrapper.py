# ============================================================
# pipeline/utils/node_wrapper.py
#
# DECORATOR PATTERN EXPLAINED:
# @pipeline_node("my_node") wraps any function with:
#   1. start/end logging with structlog
#   2. millisecond timing
#   3. exception catching — node failures don't crash the pipeline
#
# HOW DECORATORS WORK (reverse engineering):
#
#   @pipeline_node("my_node")
#   def my_function(state): ...
#
# This is syntactic sugar for:
#   my_function = pipeline_node("my_node")(my_function)
#
# pipeline_node("my_node") returns `decorator`
# decorator(my_function) returns `wrapper`
# wrapper IS the function LangGraph calls
#
# The @wraps(func) call preserves the original function's
# __name__ and __doc__ — without it, all nodes would appear
# as "wrapper" in stack traces, making debugging impossible.
# ============================================================

import time
from functools import wraps
from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)


def pipeline_node(node_name: str):
    """
    Decorator factory for LangGraph pipeline nodes.

    Usage:
        @pipeline_node("my_node_name")
        def my_node(state: PipelineState) -> PipelineState:
            ...

    Args:
        node_name: String identifier used in logs and metrics.
                   Should match the key used in graph.add_node().
    """

    # `decorator` is the actual decorator — it receives the function
    def decorator(func):

        # `wrapper` replaces the original function
        # *args and **kwargs pass through whatever LangGraph sends
        @wraps(func)  # Preserves func.__name__, func.__doc__ etc.
        def wrapper(state):

            start = time.time()  # Wall-clock time in seconds (float)

            # Log node start — structlog adds timestamp automatically
            logger.info("node_started", node=node_name)

            try:
                # Call the actual node function with the pipeline state
                result = func(state)

            except Exception as e:
                # Catch ALL exceptions — a crashing node would stall
                # the entire LangGraph execution. Instead, we log the
                # error and return a partial state with an error key.
                # The pipeline continues — context_builder will see
                # empty/error values and adapt accordingly.
                logger.error(
                    "node_failed",
                    node=node_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Return partial state — only the error field
                # Other fields stay unchanged in PipelineState
                result = {"errors": [f"{node_name} failed: {str(e)}"]}

            # Calculate duration AFTER try/except so we always log timing
            duration_ms = int((time.time() - start) * 1000)

            logger.info(
                "node_completed",
                node=node_name,
                duration_ms=duration_ms,
            )

            return result

        return wrapper   # LangGraph calls this instead of func
    return decorator     # @pipeline_node("x") returns this