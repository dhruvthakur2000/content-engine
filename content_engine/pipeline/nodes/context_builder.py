# ============================================================
# pipeline/nodes/context_builder.py
# ============================================================

from datetime import datetime

from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node


@pipeline_node("context_builder")
def context_builder_node(state: PipelineState) -> PipelineState:
    """
    Combines parsed notes and git history into a unified
    engineering context document.
    """

    parsed_notes = state.get("parsed_notes", "").strip()
    parsed_git = state.get("parsed_git", "").strip()

    author_name = state.get("author_name", "Developer")
    platforms = state.get("platforms", ["linkedin", "twitter"])

    today_str = datetime.now().strftime("%B %d, %Y")

    context_parts = []

    # Header
    context_parts.append("===== ENGINEERING CONTEXT =====")
    context_parts.append(f"Date: {today_str}")
    context_parts.append(f"Developer: {author_name}")
    context_parts.append(f"Target Platforms: {', '.join(platforms)}")
    context_parts.append("")

    # Notes section
    if parsed_notes:
        context_parts.append("--- From Developer Notes ---")
        context_parts.append(parsed_notes)
        context_parts.append("")
    else:
        context_parts.append("--- Developer Notes: Not provided ---")
        context_parts.append("")

    # Git section
    if parsed_git:
        context_parts.append("--- From Git Activity ---")
        context_parts.append(parsed_git)
        context_parts.append("")
    else:
        context_parts.append("--- Git Activity: Not available ---")
        context_parts.append("")

    # Data quality assessment
    has_notes = bool(parsed_notes and "No notes provided" not in parsed_notes)
    has_git = bool(parsed_git and "Not available" not in parsed_git)

    if has_notes and has_git:
        data_quality = "FULL: Both notes and git history available."
    elif has_notes:
        data_quality = "PARTIAL: Notes available, no git history. Generate from notes only."
    elif has_git:
        data_quality = "PARTIAL: Git history available, no notes. Generate from git only."
    else:
        data_quality = "MINIMAL: Limited data available. Generate with caution."

    context_parts.append("--- Data Quality ---")
    context_parts.append(data_quality)
    context_parts.append("")
    context_parts.append("=================================")

    context = "\n".join(context_parts)

    return {"context": context}