from typing import Optional
import time
import uuid
from content_engine.pipeline.graph import get_pipeline
from backend.ingestion.dump_parser import DumpParserService
from backend.ingestion.git_parsar import GitLogService
from backend.utils.logger import get_logger


logger = get_logger(__name__)

def run_pipeline_service(
    raw_notes: str,
    raw_git_log: str,
    platforms: Optional[list[str]] = None,
    author_name: str = "Developer",
    style: str ="dhruv_default",
    extra_material: str = "",
    ) -> dict[str, any]:
    
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    logger.info(
        "Pipeline has started",
        platforms=platforms,
        style=style,
        has_extra_material = bool(extra_material)
        )
    
    # default platforms
    if platforms is None:
        platforms=["linkedin","twitter"]
        
        platforms= [p.lower().strip() for p in platforms]
        
        valid_platforms = {"linkedin","twitter","blog"}
        platforms = [p for p in platforms if p in valid_platforms]
        
        if not platforms:
            platforms = ["linkedin","twitter"]
            
            #--parse developer notes------
            
        try:
            cleaned_notes = DumpParserService.parse_notes_from_string(raw_notes)
        except ValueError as e:
            
            return {
                "succes": False,
                "generated_posts": {},
                "metadata": {"request_id":request_id},
                "error": str(e)
            }
            
            
        #__parse git log--------------------------
        cleaned_git_logs=(
            GitLogService.parse_git_log_string(raw_git_log)
            if raw_git_log and raw_git_log.strip()
            else "[GIT_LOG_UNAVAILABLE]" 
        )
        
        # -- initial state-------------------------------------
        
        initial_state={
            "raw_notes": cleaned_notes,
            "raw_git_log": cleaned_git_logs,
            "platforms":platforms,
            "author_name": author_name,
            "style": style,
            "extra_material": extra_material   
        }
        
        # -- Execute Pipeline---------------------------
        
        
        try:
            pipeline = get_pipeline()
            final_state = pipeline.invoke(initial_state)
            
        except Exception as e:
            
            total_ms = int((time.time()-start_time)*1000)
            
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

    # ── Build response ───────────────────────────────

    generated_posts = final_state.get("generated_posts", {})

    metadata = final_state.get("metadata", {})

    total_ms = int((time.time() - start_time) * 1000)

    metadata.update({
        "request_id": request_id,
        "pipeline_version": "v2",
        "total_service_duration_ms": total_ms,
    })

    logger.info(
        "pipeline_completed",
        request_id=request_id,
        duration_ms=total_ms,
    )

    return {
        "success": True,
        "generated_posts": generated_posts,
        "metadata": metadata,
        "error": None,
    }
                           
    


"""
    pipeline_graph = build_pipeline()

    state = {
        "commits": [],
        "dump_text": "",
        "context_summary": "",
        "technical_summary": "",
        "persona": "",
        "x_post": "",
        "linkedin_post": "",
        "thread": "",
        "blog": ""
    }
"""
