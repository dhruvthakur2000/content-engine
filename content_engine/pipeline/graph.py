from langgraph.graph import StateGraph

from backend.graph.state import ContentState

from backend.nodes.ingest_git import ingest_git
from backend.nodes.parse_dump import parse_dump
from backend.nodes.build_context import build_context
from backend.nodes.summarize_context import summarize_context
from backend.nodes.persona_inject import persona_inject
from backend.nodes.generate_posts import generate_posts


def build_graph():

    builder = StateGraph(ContentState)

    builder.add_node("git", ingest_git)
    builder.add_node("dump", parse_dump)
    builder.add_node("context", build_context)
    builder.add_node("summary", summarize_context)
    builder.add_node("persona", persona_inject)
    builder.add_node("generate", generate_posts)

    builder.set_entry_point("git")

    builder.add_edge("git", "dump")
    builder.add_edge("dump", "context")
    builder.add_edge("context", "summary")
    builder.add_edge("summary", "persona")
    builder.add_edge("persona", "generate")

    return builder.compile()