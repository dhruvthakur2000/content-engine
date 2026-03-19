import time

from langchain_core.messages import HumanMessage

from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node

from content_engine.backend.llm.providers import get_llm
from content_engine.backend.llm.prompts import PARSE_NOTES_PROMPT
from content_engine.backend.cache.cache_manager import get_cache
from content_engine.backend.utils.logger import get_logger


logger = get_logger(__name__)

NODE_NAME = "parse_notes"

llm = get_llm()
cache = get_cache()


@pipeline_node(NODE_NAME)
def parse_notes_node(state: PipelineState) -> PipelineState:

    start_time = time.time()

    raw_notes = state.get("raw_notes", "")

    if not raw_notes or not raw_notes.strip():
        return {
            "parsed_notes": "SUMMARY: No notes provided.\nMETRICS: None\nIMPROVEMENTS: None"
        }

    # =====================================================
    # CACHE CHECK
    # =====================================================

    cached = cache.read(
        input_data=raw_notes,
        node_name=NODE_NAME
    )

    if cached is not None:
        # Defensive check: ensure cached result has required field
        if isinstance(cached, dict) and "parsed_notes" in cached:
            existing_hits = state.get("cache_hits", [])
            return {
                "parsed_notes": cached["parsed_notes"],
                "cache_hits": existing_hits + [NODE_NAME],
            }

    # =====================================================
    # LLM CALL
    # =====================================================

    prompt = PARSE_NOTES_PROMPT.format(raw_notes=raw_notes)

    try:

        response = llm.invoke(
            [HumanMessage(content=prompt)],
            task="parse"
        )

        parsed_notes = response.content.strip()

    except Exception as e:

        logger.error(
            "parse_notes_llm_error",
            error=str(e)
        )

        parsed_notes = f"SUMMARY: Error parsing notes: {str(e)}\nMETRICS: Unknown"

    # =====================================================
    # WRITE CACHE (only cache successful results)
    # =====================================================

    if not parsed_notes.startswith("SUMMARY: Error"):
        cache.write(
            input_data=raw_notes,
            result={"parsed_notes": parsed_notes},
            node_name=NODE_NAME,
        )

    # Note: @pipeline_node decorator will log node_completed automatically
    return {
        "parsed_notes": parsed_notes
    }