import time
from functools import wraps
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def pipeline_node(node_name: str):
    """
    Decorator for LangGraph nodes that adds:
    - start/end logging
    - execution timing
    - error handling
    """

    def decorator(func):

        @wraps(func)
        def wrapper(state):

            start = time.time()

            logger.info("node_started", node=node_name)

            try:
                result = func(state)

            except Exception as e:
                logger.error(
                    "node_failed",
                    node=node_name,
                    error=str(e),
                )

                result = {"error": f"{node_name} failed: {str(e)}"}

            duration_ms = int((time.time() - start) * 1000)

            logger.info(
                "node_completed",
                node=node_name,
                duration_ms=duration_ms,
            )

            return result

        return wrapper

    return decorator