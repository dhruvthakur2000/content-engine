import time
import uuid
from typing import Optional, List, Dict, Any

from content_engine.pipeline.graph import get_pipeline

from backend.ingestion.dump_parser import DumpParserService
from backend.ingestion.git_parsar import GitLogService

from backend.memory.content_memory import search_memory, store_memory

from backend.config.settings import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


# ------------------------------------------------------------
# MEMORY CONTEXT FORMATTER
# ------------------------------------------------------------

def _format_memory_context(memory_result: dict) -> str:
    """
    Converts memory search result into prompt-injectable text.
    """

    if not memory_result or not memory_result.get("past_posts"):
        return ""

    past_posts = memory_result["past_posts"]
    similarity = memory_result.get("similarity", 0)
    timestamp = memory_result.get("timestamp", "unknown")[:10]

    lines = [
        f"=== PAST SIMILAR CONTENT (similarity: {similarity}) ===",
        f"Generated on: {timestamp}",
        "",
        "Use this as a tone and structure REFERENCE ONLY.",
        "Do NOT copy it. Generate fresh content.",
        "",
    ]

    if past_posts.get("linkedin"):
        lines.append("--- Past LinkedIn Post ---")
        lines.append(past_posts["linkedin"][:600])
        lines.append("")

    if past_posts.get("twitter"):
        lines.append("--- Past Twitter Thread ---")
        lines.append(past_posts["twitter"][:400])
        lines.append("")

    lines.append("=== END PAST CONTENT ===")

    return "\n".join(lines)


# ------------------------------------------------------------
# MAIN PIPELINE RUNNER
# ------------------------------------------------------------

def run_pipeline_service(
    raw_notes: str,
    raw_git_log: str = "",
    platforms: Optional[List[str]] = None,
    author_name: str = "Developer",
    style: str = "dhruv_default",
    extra_material: str = "",
) -> Dict[str, Any]:

    start_time = time.time()
    request_id = str(uuid.uuid4())

    logger.info(
        "pipeline_started",
        request_id=request_id,
        style=style,
        platforms=platforms,
    )

    # --------------------------------------------------------
    # PLATFORM VALIDATION
    # --------------------------------------------------------

    if platforms is None:
        platforms = ["linkedin", "twitter"]

    platforms = [p.lower().strip() for p in platforms]

    valid_platforms = {"linkedin", "twitter", "blog"}

    platforms = [p for p in platforms if p in valid_platforms] or ["linkedin", "twitter"]

    # --------------------------------------------------------
    # INPUT PARSING
    # --------------------------------------------------------

    try:
        cleaned_notes = DumpParserService.parse_notes_from_string(raw_notes)

    except ValueError as e:

        return {
            "success": False,
            "generated_posts": {},
            "metadata": {"request_id": request_id},
            "error": str(e),
        }

    cleaned_git = (
        GitLogService.parse_git_log_string(raw_git_log)
        if raw_git_log and raw_git_log.strip()
        else "[GIT LOG UNAVAILABLE]"
    )

    # --------------------------------------------------------
    # MEMORY SEARCH (BEFORE PIPELINE)
    # --------------------------------------------------------

    memory_hit = False
    memory_context = ""

    try:

        if settings.memory_enabled:

            memory_result = search_memory(cleaned_notes)

            if memory_result:

                memory_hit = True
                memory_context = _format_memory_context(memory_result)

                logger.info(
                    "memory_match_found",
                    request_id=request_id,
                    similarity=memory_result.get("similarity"),
                )

    except Exception as e:

        logger.warning(
            "memory_search_failed",
            request_id=request_id,
            error=str(e),
        )

    # --------------------------------------------------------
    # BUILD INITIAL PIPELINE STATE
    # --------------------------------------------------------

    initial_state = {
        "raw_notes": cleaned_notes,
        "raw_git_log": cleaned_git,
        "platforms": platforms,
        "author_name": author_name,
        "style": style,
        "extra_material": extra_material,
        "cache_hits": [],
        "memory_hit": memory_hit,
        "memory_context": memory_context,
    }

    # --------------------------------------------------------
    # EXECUTE PIPELINE
    # --------------------------------------------------------

    try:

        pipeline = get_pipeline()

        final_state = pipeline.invoke(initial_state)

    except Exception as e:

        total_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "pipeline_failed",
            request_id=request_id,
            error=str(e),
            duration_ms=total_ms,
        )

        return {
            "success": False,
            "generated_posts": {},
            "metadata": {
                "request_id": request_id,
                "duration_ms": total_ms,
            },
            "error": f"Pipeline failed: {str(e)}",
        }

    # --------------------------------------------------------
    # EXTRACT OUTPUT
    # --------------------------------------------------------

    generated_posts = final_state.get("generated_posts", {})
    cache_hits = final_state.get("cache_hits", [])

    # --------------------------------------------------------
    # STORE RESULT IN MEMORY
    # --------------------------------------------------------

    try:

        if settings.memory_enabled and generated_posts:

            meta_for_memory = {
                "style_used": style,
                "platforms": platforms,
            }

            stored = store_memory(
                input_notes=cleaned_notes,
                generated_posts=generated_posts,
                metadata=meta_for_memory,
            )

            if stored:
                logger.info("memory_stored_after_run", request_id=request_id)

    except Exception as e:

        logger.warning(
            "memory_store_failed",
            request_id=request_id,
            error=str(e),
        )

    # --------------------------------------------------------
    # BUILD METADATA
    # --------------------------------------------------------

    total_ms = int((time.time() - start_time) * 1000)

    metadata = final_state.get("metadata", {})

    metadata.update({
        "request_id": request_id,
        "cache_hits": cache_hits,
        "cached_node_count": len(cache_hits),
        "memory_hit": memory_hit,
        "total_service_duration_ms": total_ms,
        "style_used": style,
    })

    logger.info(
        "pipeline_completed",
        request_id=request_id,
        duration_ms=total_ms,
        cache_hits=cache_hits,
        memory_hit=memory_hit,
    )

    return {
        "success": True,
        "generated_posts": generated_posts,
        "metadata": metadata,
        "error": None,
    }