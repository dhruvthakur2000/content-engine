from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node as _pn4
from content_engine.backend.llm.providers import get_llm as _get_llm4
from content_engine.backend.cache.cache_manager import get_cache as _get_cache4
from content_engine.backend.llm.prompts import ANGLE_PROMPT
from content_engine.backend.utils.logger import get_logger as _get_logger4

_llm4 = _get_llm4()
_cache4 = _get_cache4()
_logger4 = _get_logger4("angle_node")

NODE_NAME = "angle_generator"

DEFAULT_ANGLE = "SYSTEM_INSIGHT"
DEFAULT_HOOK = "Here's what I built today."
DEFAULT_KEY_DETAIL = "See context for details."


@_pn4(NODE_NAME)
def angle_node(state: PipelineState) -> PipelineState:

    context = state.get("context", "").strip()

    if not context or len(context) < 50:
        return {
            "narrative_angle": DEFAULT_ANGLE,
            "hook": DEFAULT_HOOK,
            "key_detail": DEFAULT_KEY_DETAIL,
        }

    cache_key = f"{context}|v2"

    cached = _cache4.read(input_data=cache_key, node_name=NODE_NAME)

    if isinstance(cached, dict) and "narrative_angle" in cached:
        return {
            "narrative_angle": cached.get("narrative_angle", DEFAULT_ANGLE),
            "hook": cached.get("hook", DEFAULT_HOOK),
            "key_detail": cached.get("key_detail", DEFAULT_KEY_DETAIL),
            "cache_hits": state.get("cache_hits", []) + [NODE_NAME],
        }

    prompt = ANGLE_PROMPT.format(context=context)

    try:
        from langchain_core.messages import HumanMessage as HM4
        response = _llm4.invoke([HM4(content=prompt)], task="reason")
        raw_output = response.content.strip()

    except Exception as e:
        _logger4.error("angle_llm_error", error=str(e))
        return {
            "narrative_angle": DEFAULT_ANGLE,
            "hook": DEFAULT_HOOK,
            "key_detail": DEFAULT_KEY_DETAIL,
        }

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

    result = {
        "narrative_angle": narrative_angle,
        "hook": hook,
        "key_detail": key_detail,
    }

    _cache4.write(input_data=cache_key, result=result, node_name=NODE_NAME)

    return result