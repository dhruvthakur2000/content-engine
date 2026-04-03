from langchain_core.messages import HumanMessage

from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node
from content_engine.backend.llm.providers import get_llm
from content_engine.backend.llm.prompts import PARSE_GIT_PROMPT
from content_engine.backend.cache.cache_manager import get_cache
from content_engine.backend.utils.logger import get_logger
from content_engine.backend.utils.debug_nodes import save_debug  

logger = get_logger(__name__)

NODE_NAME = "parse_git"

GIT_UNAVAILABLE = "[GIT LOG UNAVAILABLE]"

llm = get_llm()
cache = get_cache()

MAX_GIT_LOG_CHARS=15000


_GIT_UNAVAILABLE_RESPONSE = (
    "FEATURES: Not available (no git log provided)\n"
    "FIXES: Not available\n"
    "REFACTORING: Not available\n"
    "AREAS_OF_CODE_TOUCHED: Unknown\n"
    "DEVELOPMENT_DIRECTION: Unknown — content from notes only\n"
    "TODAYS_WORK_SUMMARY: Git history not available.\n"
    "STORY: No git data. Content will be generated from notes only."
)

@pipeline_node(NODE_NAME)
def parse_git_node(state:PipelineState) -> PipelineState:
    """
    Extracts structured engineering knowledge from git history.
 
s    Reads:  state["raw_git_log"]  (from git_parsar auto-detect
                                   OR manual paste)
    Writes: state["parsed_git"]   (structured extraction for context_builder)
 
    FLOW:
      1. Check if git data exists → skip if not
      2. Check cache → return cached result if hit
      3. Call LLM with PARSE_GIT_PROMPT → extract structured data
      4. Write to cache
      5. Return parsed_git to state
    """ 
    availability = state.get("input_availability", {})
    has_git = availability.get("has_git", False)

    # --- SKIP IF NO GIT ---
    if not has_git:
        logger.info("parse_git_skipped", reason="no_git_available")
        return {
            "parsed_git": _GIT_UNAVAILABLE_RESPONSE,
            "git_available": False
        }

    # --- INPUT NORMALIZATION ---
    raw_git_log = str(state.get("raw_git_log", "")).strip()

    if not raw_git_log:
        logger.info("parse_git_skipped", reason="empty_git_log")
        return {
            "parsed_git": _GIT_UNAVAILABLE_RESPONSE,
            "git_available": False
        }

    # --- SIZE CONTROL ---
    if len(raw_git_log) > MAX_GIT_LOG_CHARS:
        logger.warning("git_log_truncated", original_length=len(raw_git_log))
        raw_git_log = raw_git_log[:MAX_GIT_LOG_CHARS]

    # --- CACHE ---
    cached = cache.read(input_data=raw_git_log, node_name=NODE_NAME)

    if cached and "parsed_git" in cached:
        logger.info("parse_git_cache_hit")

        save_debug("parsed_git_cache", cached["parsed_git"])

        return {
            "parsed_git": cached["parsed_git"],
            "cache_hits": state.get("cache_hits", []) + [NODE_NAME],
            "git_available": True
        }

    # --- LLM CALL ---
    prompt = PARSE_GIT_PROMPT.format(git_log=raw_git_log)

    try:
        response = llm.invoke(
            [HumanMessage(content=prompt)],
            task="parse",
        )
        parsed_git = response.content.strip()

    except Exception as e:
        logger.error("parse_git_llm_error", error=str(e))

        parsed_git = (
            "FEATURES: Error during git parsing\n"
            f"STORY: {str(e)}\n"
            "TODAYS_WORK_SUMMARY: Failed to parse git."
        )

    # --- VALIDATION (LIGHT) ---
    if "FEATURES:" not in parsed_git:
        logger.warning("parse_git_invalid_structure")

    # --- CACHE WRITE ---
    if not parsed_git.startswith("FEATURES: Error"):
        cache.write(
            input_data=raw_git_log,
            result={"parsed_git": parsed_git},
            node_name=NODE_NAME,
        )

    save_debug("parsed_git", parsed_git)

    return {
        "parsed_git": parsed_git,
        "git_available": True
    }