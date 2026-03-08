from langchain_core.messages import HumanMessage

from pipeline.state import PipelineState
from backend.llm.providers import get_llm
from backend.llm.prompts import PARSE_NOTES_PROMPT
from pipeline.utils.node_wrapper import pipeline_node

llm = get_llm()


@pipeline_node("parse_notes")
def parse_notes_node(state: PipelineState) -> PipelineState:

    raw_notes = state.get("raw_notes", "")

    if not raw_notes or not raw_notes.strip():
        return {
            "parsed_notes": "SUMMARY: No notes provided.\nMETRICS: None\nIMPROVEMENTS: None"
        }

    prompt = PARSE_NOTES_PROMPT.format(raw_notes=raw_notes)

    response = llm.invoke([HumanMessage(content=prompt)])

    parsed_notes = response.content.strip()

    return {"parsed_notes": parsed_notes}