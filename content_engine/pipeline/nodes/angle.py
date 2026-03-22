from langchain_core.messages import HumanMessage

from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node
from content_engine.backend.llm.providers import get_llm
from content_engine.backend.llm.prompts import ANGLE_PROMPT
from content_engine.backend.cache.cache_manager import get_cache
from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)

NODE_NAME = "angle_generator"

DEFAULT_ANGLE = "ENGINEERING_UPDATE"
DEFAULT_HOOK = "Here's what I built today."
DEFAULT_KEY_DETAIL = "See context for details."

llm = get_llm()
cache = get_cache()


@pipeline_node(NODE_NAME)
def angle_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node: Selects narrative angle, hook, and key detail.

    Reads:
        state["context"]

    Writes:
        state["narrative_angle"]
        state["hook"]
        state["key_detail"]
    """

    context = state.get("context", "")

    # -----------------------------------------------------
    # HANDLE EMPTY CONTEXT
    # -----------------------------------------------------
    if not context or len(context.strip()) < 50:
        return {
            "narrative_angle": DEFAULT_ANGLE,
            "hook": DEFAULT_HOOK,
            "key_detail": DEFAULT_KEY_DETAIL,
        }

    # -----------------------------------------------------
    # CACHE CHECK
    # -----------------------------------------------------
    cached = cache.read(input_data=context, node_name=NODE_NAME)

    if isinstance(cached, dict) and "narrative_angle" in cached:
        existing_hits = state.get("cache_hits", [])

        return {
            "narrative_angle": cached.get("narrative_angle", DEFAULT_ANGLE),
            "hook": cached.get("hook", DEFAULT_HOOK),
            "key_detail": cached.get("key_detail", DEFAULT_KEY_DETAIL),
            "cache_hits": existing_hits + [NODE_NAME],
        }

    # -----------------------------------------------------
    # LLM CALL (cache miss)
    # -----------------------------------------------------
    prompt = ANGLE_PROMPT.format(context=context)

    try:
        response = llm.invoke(
            [HumanMessage(content=prompt)],
            task="reason"
        )

        raw_output = response.content.strip()

    except Exception as e:
        logger.error("angle_node_llm_error", error=str(e))

        return {
            "narrative_angle": DEFAULT_ANGLE,
            "hook": DEFAULT_HOOK,
            "key_detail": DEFAULT_KEY_DETAIL,
        }

    # -----------------------------------------------------
    # PARSE STRUCTURED OUTPUT
    # -----------------------------------------------------
    narrative_angle = DEFAULT_ANGLE
    hook = DEFAULT_HOOK
    key_detail = DEFAULT_KEY_DETAIL

    for line in raw_output.split("\n"):

        line = line.strip()

        if line.upper().startswith("ANGLE:"):
            narrative_angle = line.split(":", 1)[1].strip()

        elif line.upper().startswith("HOOK:"):
            hook = line.split(":", 1)[1].strip()

        elif line.upper().startswith("KEY_DETAIL:"):
            key_detail = line.split(":", 1)[1].strip()

    # Warn if parsing failed
    if narrative_angle == DEFAULT_ANGLE and hook == DEFAULT_HOOK:
        logger.warning(
            "angle_parse_incomplete",
            raw_output_preview=raw_output[:200]
        )

    # -----------------------------------------------------
    # WRITE CACHE
    # -----------------------------------------------------
    result_to_cache = {
        "narrative_angle": narrative_angle,
        "hook": hook,
        "key_detail": key_detail,
    }

    cache.write(
        input_data=context,
        result=result_to_cache,
        node_name=NODE_NAME,
    )

    return result_to_cache