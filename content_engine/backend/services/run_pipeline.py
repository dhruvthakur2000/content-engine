# ============================================================
# PRODUCTION PIPELINE SERVICE
# Clean, robust, observable, failure-tolerant
# ============================================================

import time
import uuid
from typing import Optional, List, Dict, Any

from content_engine.pipeline.graph import invoke_pipeline
from content_engine.pipeline.state import PipelineState

from content_engine.backend.ingestion.dump_parser import DumpParserService
from content_engine.backend.ingestion.git_parsar import auto_ingest_git
from content_engine.backend.ingestion.url_fetcher import fetch_and_summarize_urls

from content_engine.backend.memory.content_memory import search_memory, store_memory
from content_engine.agents.orchestrator import run_agents_sync

from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


# ============================================================
# MEMORY FORMATTER
# ============================================================

def _format_memory_context(memory_result: dict) -> str:
    if not memory_result or not memory_result.get("past_posts"):
        return ""

    past_posts = memory_result["past_posts"]
    similarity = memory_result.get("similarity", 0)
    timestamp = memory_result.get("timestamp", "unknown")[:10]

    lines = [
        f"=== PAST SIMILAR CONTENT (similarity: {similarity:.2f}) ===",
        f"Generated: {timestamp}",
        "",
        "Use as tone/structure REFERENCE ONLY. Do NOT copy.",
        "",
    ]

    if past_posts.get("linkedin"):
        lines += ["--- Past LinkedIn ---", past_posts["linkedin"][:400], ""]

    if past_posts.get("twitter"):
        lines += ["--- Past Twitter ---", past_posts["twitter"][:300], ""]

    lines.append("=== END PAST CONTENT ===")

    return "\n".join(lines)


# ============================================================
# MAIN SERVICE
# ============================================================

def run_pipeline_service(
    raw_notes: str = "",
    raw_git_log: str = "",
    platforms: Optional[List[str]] = None,
    author_name: str = "Developer",
    style: str = "dhruv_default",
    extra_material: str = "",

    blog_urls: Optional[List[str]] = None,
    code_context: Optional[str] = None,
    transcript: Optional[str] = None,
    doc_references: Optional[str] = None,
    blog_style: Optional[str] = None,

    git_repo_path: str = ".",
    github_owner: Optional[str] = None,
    github_repo: Optional[str] = None,
) -> Dict[str, Any]:

    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    logger.info(
        "pipeline_started",
        request_id=request_id,
        style=style,
        platforms=platforms,
    )

    # --------------------------------------------------------
    # STEP 1: PLATFORM NORMALIZATION
    # --------------------------------------------------------

    platforms = platforms or settings.default_platforms_list
    platforms = [p.lower().strip() for p in platforms]
    platforms = ["blog" if p == "blogs" else p for p in platforms]

    VALID = {"linkedin", "twitter", "blog"}
    platforms = [p for p in platforms if p in VALID] or ["linkedin"]

    # --------------------------------------------------------
    # STEP 2: NOTES
    # --------------------------------------------------------

    try:
        cleaned_notes = (
            DumpParserService().parse_notes_from_string(raw_notes)
            if raw_notes else ""
        )
    except Exception as e:
        return _error_response(request_id, f"Notes error: {str(e)}", start_time)

# --------------------------------------------------------
# STEP 3: GIT
# --------------------------------------------------------

    cleaned_git = ""
    git_structured = None

    try:
        if raw_git_log.strip():
            from content_engine.backend.ingestion.git_parsar import GitLogService

            cleaned_git = GitLogService().parse_git_log_string(raw_git_log)

            logger.info("git_source", type="manual")

        else:
            git_result = auto_ingest_git(
                repo_path=git_repo_path,
                github_owner=github_owner,
                github_repo=github_repo,
            )

            git_structured = git_result 

            cleaned_git = git_result.to_pipeline_string()

            logger.info("git_auto", commits=len(git_result.commits))

    except Exception as e:
        logger.warning("git_failed", error=str(e))
        cleaned_git = "[GIT UNAVAILABLE]"

    # --------------------------------------------------------
    # STEP 4: URLS
    # --------------------------------------------------------

    url_summaries = ""
    if blog_urls:
        try:
            url_summaries = fetch_and_summarize_urls(blog_urls)
        except Exception as e:
            logger.warning("url_failed", error=str(e))

    # --------------------------------------------------------
    # STEP 5: MEMORY
    # --------------------------------------------------------

    memory_context = ""
    memory_hit = False

    try:
        if settings.memory_enabled and cleaned_notes:
            mem = search_memory(cleaned_notes)
            if mem:
                memory_context = _format_memory_context(mem)
                memory_hit = True
    except Exception as e:
        logger.warning("memory_failed", error=str(e))

    # --------------------------------------------------------
    # STEP 6: AGENTS (CORE INTELLIGENCE)
    # --------------------------------------------------------

    agent_results = {}

    try:
        agent_results = run_agents_sync(
            availability={
                "has_notes": bool(cleaned_notes),
                "has_git": bool(cleaned_git and "UNAVAILABLE" not in cleaned_git),
                "has_code": bool(code_context),
                "has_urls": bool(blog_urls),
            },
            git_data=cleaned_git,
            notes_data=cleaned_notes,
            code_data=code_context or "",
            reference_data="\n\n".join(filter(None, [
                url_summaries,
                doc_references or "",
                transcript or "",
            ])),
        )

        logger.info("agents_done", agents=list(agent_results.keys()))

    except Exception as e:
        logger.warning("agents_failed", error=str(e))

    # --------------------------------------------------------
    # STEP 7: BUILD STATE
    # --------------------------------------------------------

    state = PipelineState()

    state.update({
        "raw_notes": cleaned_notes,
        "raw_git_log": cleaned_git,
        "git_structured": git_structured,
        "platforms": platforms,
        "author_name": author_name,
        "style": style,
        "extra_material": extra_material,

        "blog_urls": blog_urls or [],
        "code_context": code_context or "",
        "transcript": transcript or "",
        "doc_references": doc_references or "",
        "blog_style": blog_style or "build_in_public",
        "url_summaries": url_summaries,

        "memory_context": memory_context,
        "memory_hit": memory_hit,
        "agent_results": agent_results,
    })

    # --------------------------------------------------------
    # STEP 8: PIPELINE EXECUTION
    # --------------------------------------------------------

    try:
        final_state = invoke_pipeline(state)
        if final_state is None:
            raise ValueError("Pipeline returned None — graph adapter broken")
    except Exception as e:
        logger.error("pipeline_failed", error=str(e))
        return _error_response(request_id, str(e), start_time)

    # --------------------------------------------------------
    # STEP 9: SECURITY CHECK
    # --------------------------------------------------------

    sec = final_state.get("security_check", {})
    if not sec.get("passed", True):
        return {
            "success": False,
            "generated_posts": {},
            "metadata": {"request_id": request_id},
            "error": sec.get("blocked_reason", "Blocked"),
        }

    # --------------------------------------------------------
    # STEP 10: MEMORY STORE
    # --------------------------------------------------------

    posts = final_state.get("generated_posts", {})

    try:
        if settings.memory_enabled and posts:
            store_memory(cleaned_notes, posts)
    except Exception as e:
        logger.warning("memory_store_failed", error=str(e))

    # --------------------------------------------------------
    # STEP 11: METADATA
    # --------------------------------------------------------

    total_ms = int((time.time() - start_time) * 1000)

    metadata = final_state.get("metadata", {})
    metadata.update({
        "request_id": request_id,
        "total_service_duration_ms": total_ms,
        "agents_used": list(agent_results.keys()),
        "cache_hits": final_state.get("cache_hits", []),
        "evaluation_scores": final_state.get("evaluation_scores", {}),
        "regeneration_count": final_state.get("regeneration_count", 0),
    })

    logger.info(
        "pipeline_completed",
        request_id=request_id,
        ms=total_ms
    )

    return {
        "success": True,
        "generated_posts": posts,
        "metadata": metadata,
        "error": None,
    }


# ============================================================
# ERROR RESPONSE
# ============================================================

def _error_response(request_id: str, error: str, start_time: float):
    return {
        "success": False,
        "generated_posts": {},
        "metadata": {
            "request_id": request_id,
            "total_service_duration_ms": int((time.time() - start_time) * 1000),
        },
        "error": error,
    }