from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node as _pn2
from content_engine.backend.llm.providers import get_llm as _get_llm2
from content_engine.backend.cache.cache_manager import get_cache as _get_cache2
from content_engine.backend.utils.logger import get_logger as _get_logger2
 
_llm2 = _get_llm2()
_cache2 = _get_cache2()
_logger2 = _get_logger2("parse_code")
 
_PARSE_CODE_PROMPT = """
You are analyzing code provided by a developer. Extract structured technical information.
 
CODE:
{code}
 
Return in this exact format:
 
LANGUAGE: [Python | TypeScript | Rust | other]
PURPOSE: [What does this code do — one sentence]
KEY_FUNCTIONS: [List main function/class names with their roles]
DEPENDENCIES: [External libraries or modules imported]
PATTERNS_USED: [Design patterns: singleton, decorator, async, etc.]
COMPLEXITY_NOTES: [Any notably complex or clever parts worth writing about]
PROBLEMS_SOLVED: [What engineering problem does this code address]
SUMMARY: [2-3 sentence technical summary suitable for a blog post]
"""
 
_CODE_UNAVAILABLE = (
    "LANGUAGE: Not provided\n"
    "PURPOSE: No code context available\n"
    "SUMMARY: No code was provided for analysis."
)
 
 
@_pn2("parse_code")
def parse_code_node(state: PipelineState) -> PipelineState:
    """
    Parses code snippets/files into structured technical summary.
 
    Reads:  state["code_context"], state["input_availability"]
    Writes: state["parsed_code"]
    """
 
    availability = state.get("input_availability", {})
 
    # If input_detector said no code, skip immediately
    if not availability.get("has_code", False):
        return {"parsed_code": _CODE_UNAVAILABLE}
 
    code = state.get("code_context", "").strip()
 
    # Truncate very large files — LLM context has limits
    # 8000 chars ≈ ~2000 tokens — enough for most function files
    if len(code) > 8000:
        code = code[:8000] + "\n\n[... code truncated for analysis ...]"
        _logger2.warning("code_context_truncated", original_len=len(state.get("code_context", "")))
 
    cached = _cache2.read(input_data=code, node_name="parse_code")
    if cached and isinstance(cached, dict) and "parsed_code" in cached:
        existing_hits = state.get("cache_hits", [])
        return {
            "parsed_code": cached["parsed_code"],
            "cache_hits": existing_hits + ["parse_code"],
        }
 
    prompt = _PARSE_CODE_PROMPT.format(code=code)
 
    try:
        from langchain_core.messages import HumanMessage as HM
        response = _llm2.invoke([HM(content=prompt)], task="parse")
        parsed_code = response.content.strip()
    except Exception as e:
        _logger2.error("parse_code_llm_error", error=str(e))
        parsed_code = f"PURPOSE: Error parsing code\nSUMMARY: Code parsing failed: {str(e)}"
 
    if "Error" not in parsed_code:
        _cache2.write(input_data=code, result={"parsed_code": parsed_code}, node_name="parse_code")
 
    return {"parsed_code": parsed_code}