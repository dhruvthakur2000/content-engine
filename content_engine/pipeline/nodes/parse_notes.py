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
    """
    Extracts structured engineering signals from raw developer notes.
 
    Reads:  state["raw_notes"]
    Writes: state["parsed_notes"]
 
    The LLM is prompted to extract: METRICS, ENGINEERING_ACTIONS,
    PROBLEMS, DECISIONS, EXPERIMENTS, INSIGHTS, SUMMARY.
    This structured format makes it easy for context_builder to
    combine notes + git into a coherent unified context.
    """
 
    raw_notes = state.get("raw_notes", "").strip()
 
    # If no notes, return graceful fallback — don't crash
    if not raw_notes:
        logger.info("parse_notes_skipped", reason="no_notes_provided")
        return {
            "parsed_notes": (
                "METRICS: None\n"
                "ENGINEERING_ACTIONS: None\n"
                "PROBLEMS: None\n"
                "DECISIONS: None\n"
                "EXPERIMENTS: None\n"
                "INSIGHTS: None\n"
                "SUMMARY: No developer notes were provided."
            )
        }
 
    # Cache check — same pattern as parse_git
    cached = cache.read(input_data=raw_notes, node_name=NODE_NAME)
    if cached is not None and isinstance(cached, dict) and "parsed_notes" in cached:
        existing_hits = state.get("cache_hits", [])
        return {
            "parsed_notes": cached["parsed_notes"],
            "cache_hits": existing_hits + [NODE_NAME],
        }
 
    prompt = PARSE_NOTES_PROMPT.format(raw_notes=raw_notes)
 
    try:
        response = llm.invoke([HumanMessage(content=prompt)], task="parse")
        parsed_notes = response.content.strip()
    except Exception as e:
        logger.error("parse_notes_llm_error", error=str(e))
        parsed_notes = f"SUMMARY: Error parsing notes: {str(e)}\nMETRICS: Unknown"
 
    # Only cache successful parses
    if not parsed_notes.startswith("SUMMARY: Error"):
        cache.write(
            input_data=raw_notes,
            result={"parsed_notes": parsed_notes},
            node_name=NODE_NAME,
        )
 
    return {"parsed_notes": parsed_notes}