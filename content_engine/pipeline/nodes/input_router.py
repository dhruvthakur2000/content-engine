from langchain_core.messages import HumanMessage
from content_engine.pipeline.state import PipelineState
from content_engine.backend.llm.prompts import ROUTING_PROMPT
from content_engine.pipeline.utils.node_wrapper import pipeline_node
from content_engine.backend.llm.providers import get_llm
from content_engine.backend.cache.cache_manager import get_cache
from content_engine.backend.utils.logger import get_logger

import json

logger = get_logger(__name__)
NODE_NAME = "routing_agent"

llm = get_llm()
cache = get_cache()

@pipeline_node(NODE_NAME)
def routing_agent_node(state: PipelineState) -> PipelineState:
    """
    AI-driven routing decision node.

    Reads:
        raw_notes, raw_git_log, code_context, extra_material

    Writes:
        routing_decision (dict)

    This node decides WHICH inputs should actually be used.
    """

    raw_notes = str(state.get("raw_notes", "")).strip()
    raw_git = str(state.get("raw_git_log", "")).strip()
    code = str(state.get("code_context", "")).strip()
    extra = str(state.get("extra_material", "")).strip()

    # --- CACHE KEY ---
    cache_key = f"{raw_notes}|{raw_git}|{code}|{extra}|routing_v1"

    cached = cache.read(input_data=cache_key, node_name=NODE_NAME)

    if cached and "routing_decision" in cached:
        logger.info("routing_agent_cache_hit")
        return {
            "routing_decision": cached["routing_decision"],
            "cache_hits": state.get("cache_hits", []) + [NODE_NAME],
        }

    # --- PROMPT ---
    prompt = ROUTING_PROMPT.format(
        notes=raw_notes[:2000],
        git=raw_git[:2000],
        code=code[:2000],
        extra=extra[:1000],
    )

    try:
        response = llm.invoke(
            [HumanMessage(content=prompt)],
            task="reason",
        )

        raw_output = response.content.strip()

        try:
            decision = json.loads(raw_output)
        except Exception:
            logger.warning("routing_json_parse_failed", raw_output=raw_output[:200])

            decision = {
                "use_notes": True if raw_notes else False,
                "use_git": False,
                "use_code": False,
                "use_extra": False,
                "reason": "fallback_decision_due_to_parse_error"
            }

    except Exception as e:
        logger.error("routing_agent_llm_error", error=str(e))

        decision = {
            "use_notes": True if raw_notes else False,
            "use_git": False,
            "use_code": False,
            "use_extra": False,
            "reason": "fallback_due_to_llm_error"
        }

    # --- SAFETY NORMALIZATION ---
    decision = {
        "use_notes": bool(decision.get("use_notes")),
        "use_git": bool(decision.get("use_git")),
        "use_code": bool(decision.get("use_code")),
        "use_extra": bool(decision.get("use_extra")),
        "reason": decision.get("reason", "no_reason_provided"),
    }

    logger.info("routing_decision_made", decision=decision)

    # --- CACHE WRITE ---
    cache.write(
        input_data=cache_key,
        result={"routing_decision": decision},
        node_name=NODE_NAME,
    )

    return {"routing_decision": decision}