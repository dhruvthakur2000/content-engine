# ============================================================
# pipeline/nodes/parse_git.py
# ============================================================

from langchain_core.messages import HumanMessage

from pipeline.state import PipelineState
from backend.llm.providers import get_llm
from backend.llm.prompts import PARSE_GIT_PROMPT
from pipeline.utils.node_wrapper import pipeline_node


# Create LLM once at module load
llm = get_llm()


# Prefix used when git log cannot be retrieved
GIT_UNAVAILABLE_PREFIX = "[GIT LOG UNAVAILABLE"


@pipeline_node("parse_git")
def parse_git_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node that converts raw git commit history
    into structured engineering context using an LLM.
    """

    raw_git_log = state.get("raw_git_log", "")

    # Skip LLM call if git log unavailable
    if not raw_git_log or raw_git_log.startswith(GIT_UNAVAILABLE_PREFIX):
        return {
            "parsed_git": (
                "FEATURES: Not available (no git log provided)\n"
                "FIXES: Not available\n"
                "REFACTORS: Not available\n"
                "FOCUS_AREA: Unknown — using notes only\n"
                "STORY: Git history not available. Content will be generated from notes only."
            )
        }

    prompt = PARSE_GIT_PROMPT.format(git_log=raw_git_log)

    response = llm.invoke([HumanMessage(content=prompt)])

    parsed_git = response.content.strip()

    return {"parsed_git": parsed_git}