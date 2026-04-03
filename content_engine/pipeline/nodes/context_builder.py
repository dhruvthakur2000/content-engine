from datetime import datetime
from content_engine.pipeline.utils.node_wrapper import pipeline_node as _pn3
from content_engine.backend.utils.logger import get_logger as _get_logger3

_logger3 = _get_logger3("context_builder")


@_pn3("context_builder")
def context_builder_node(state):
    """
    PRODUCTION CONTEXT BUILDER (V4)

    High-signal fusion layer:
    - Uses structured git (primary truth)
    - Builds core engineering narrative
    - Orders signals by importance
    - Controls context size
    """

    availability = state.get("input_availability", {})
    author_name = state.get("author_name", "Developer")
    platforms = state.get("platforms", ["linkedin"])
    today_str = datetime.now().strftime("%B %d, %Y")

    parts = []

    # =========================================================
    # HEADER
    # =========================================================
    parts += [
        "===== ENGINEERING CONTEXT =====",
        f"Date: {today_str}",
        f"Developer: {author_name}",
        f"Platforms: {', '.join(platforms)}",
        "",
    ]

    # =========================================================
    # 🔥 CORE STORY (NEW — MOST IMPORTANT)
    # =========================================================

    core_story = _build_core_story(state)

    if core_story:
        parts += [
            "=== CORE ENGINEERING STORY ===",
            core_story,
            "",
        ]

    # =========================================================
    # PRIMARY SIGNALS
    # =========================================================

    # ---------- GIT (PRIMARY SOURCE) ----------
    parsed_git = state.get("parsed_git", "")
    if parsed_git and "No git data" not in parsed_git:
        parts += [
            "--- Git Activity ---",
            parsed_git,
            "",
        ]

    # ---------- NOTES ----------
    parsed_notes = state.get("parsed_notes", "")
    if parsed_notes and "No developer notes" not in parsed_notes:
        parts += [
            "--- Developer Notes ---",
            parsed_notes,
            "",
        ]

    # ---------- CODE ----------
    parsed_code = state.get("parsed_code", "")
    if parsed_code and "Not provided" not in parsed_code:
        parts += [
            "--- Code Insights ---",
            parsed_code,
            "",
        ]

    # =========================================================
    # INTELLIGENCE LAYER
    # =========================================================

    # ---------- AGENTS ----------
    agent_results = state.get("agent_results", {})
    if agent_results:
        parts.append("--- Agent Intelligence ---")
        for name, output in agent_results.items():
            if output:
                parts.append(f"[{name.upper()}]")
                parts.append(output[:400])
                parts.append("")

    # ---------- EXTERNAL REFERENCES ----------
    refs = state.get("parsed_references", "") or state.get("url_summaries", "")
    if refs:
        parts += [
            "--- External Knowledge ---",
            refs[:1200],
            "",
        ]

    # ---------- MEMORY ----------
    memory = state.get("memory_context", "")
    if memory:
        parts += [
            "--- Past Content Reference ---",
            memory[:800],
            "",
        ]

    # =========================================================
    # DATA QUALITY
    # =========================================================

    quality = _assess_quality(availability)

    parts += [
        "--- Data Quality ---",
        quality,
        "",
        "=================================",
    ]

    context = "\n".join(parts)

    _logger3.info(
        "context_built_v4",
        sources=availability.get("source_count", 0),
        chars=len(context),
    )

    return {"context": context, "fusion_context": context}


# =========================================================
# 🔥 CORE STORY BUILDER
# =========================================================

def _build_core_story(state):

    git = state.get("parsed_git", "")
    notes = state.get("parsed_notes", "")

    if not git and not notes:
        return ""

    story_parts = []

    if git:
        story_parts.append("Work focused on system/code changes derived from git activity.")

    if notes:
        story_parts.append("Developer notes indicate reasoning, debugging, and decisions behind implementation.")

    return " ".join(story_parts)


# =========================================================
# QUALITY ASSESSMENT
# =========================================================

def _assess_quality(availability):

    has_notes = availability.get("has_notes", False)
    has_git = availability.get("has_git", False)
    has_code = availability.get("has_code", False)
    count = availability.get("source_count", 0)

    if count >= 3:
        return "RICH — multiple strong signals available"
    if has_notes and has_git:
        return "STRONG — notes + git"
    if has_git:
        return "MEDIUM — git only"
    if has_notes:
        return "MEDIUM — notes only"
    if has_code:
        return "LIMITED — code only"
    return "WEAK — minimal data"