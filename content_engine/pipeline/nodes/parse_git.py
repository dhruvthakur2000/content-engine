import time

from langchain_core.messages import HumanMessage

from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node
from content_engine.backend.utils.debug_nodes import save_debug


from content_engine.backend.llm.providers import get_llm
from content_engine.backend.llm.prompts import PARSE_GIT_PROMPT
from content_engine.backend.cache.cache_manager import get_cache
from content_engine.backend.utils.logger import get_logger


logger = get_logger(__name__)

NODE_NAME = "parse_git"
GIT_UNAVAILABLE_PREFIX = "[GIT LOG UNAVAILABLE]"

llm = get_llm()
cache = get_cache()


_GIT_UNAVAILABLE_RESPONSE = (
    "FEATURES: Not available (no git log provided)\n"
    "FIXES: Not available\n"
    "REFACTORS: Not available\n"
    "FOCUS_AREA: Unknown — using notes only\n"
    "STORY: Git history not available. Content will be generated from notes only."
)


@pipeline_node(NODE_NAME)
def parse_git_node(state: PipelineState) -> PipelineState:

    start_time = time.time()

    raw_git_log = state.get("raw_git_log", "")

    # =====================================================
    # SKIP IF GIT NOT AVAILABLE
    # =====================================================

    if not raw_git_log or raw_git_log.startswith(GIT_UNAVAILABLE_PREFIX):
        return {
            "parsed_git": _GIT_UNAVAILABLE_RESPONSE
        }

    # =====================================================
    # CACHE CHECK
    # =====================================================

    cached = cache.read(
        input_data=raw_git_log,
        node_name=NODE_NAME
    )

    if cached is not None:

        if isinstance(cached, dict) and "parsed_git" in cached:

            existing_hits = state.get("cache_hits", [])

            return {
                "parsed_git": cached["parsed_git"],
                "cache_hits": existing_hits + [NODE_NAME],
            }

    # =====================================================
    # LLM CALL
    # =====================================================

    prompt = PARSE_GIT_PROMPT.format(git_log=raw_git_log)

    try:

        response = llm.invoke(
            [HumanMessage(content=prompt)],
            task="parse"
        )

        parsed_git = response.content.strip()

    except Exception as e:

        logger.error(
            "parse_git_llm_error",
            error=str(e)
        )

        parsed_git = (
            "FEATURES: Error parsing git log\n"
            f"STORY: Git parsing failed: {str(e)}"
        )

    # =====================================================
    # WRITE CACHE (only cache successful results)
    # =====================================================

    if not parsed_git.startswith("FEATURES: Error"):

        cache.write(
            input_data=raw_git_log,
            result={"parsed_git": parsed_git},
            node_name=NODE_NAME,
        )
    save_debug("parsed_git",parsed_git)
    return {
        "parsed_git": parsed_git
    }