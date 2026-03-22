import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status, Query, Depends
from fastapi.middleware.cors import CORSMiddleware

from content_engine.backend.ingestion.git_parsar import GitLogService
from content_engine.backend.ingestion.dump_parser import DumpParserService
from content_engine.backend.api.schemas import GenerateRequest, GenerateResponse, GenerateFromFileRequest
from content_engine.backend.services.run_pipeline import run_pipeline_service
from content_engine.backend.llm.style_loader import list_available_styles
from content_engine.backend.utils.logger import setup_logging, get_logger
from content_engine.backend.config.settings import get_settings
from content_engine.backend.cache.cache_manager import CacheManager
from content_engine.backend.memory.content_memory import get_memory_stats
from content_engine.pipeline.graph import get_pipeline


settings= get_settings()

#---LOGGING-------------------------------------------------

setup_logging(
    log_level=settings.log_level,
)

logger = get_logger(__name__)

#--- LIFESPAN CONTEXT MANAGER -------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when FASTAPI starts and once whhen it shuts down
    """
    
    # Startup
    logger.info(
        "server_starting",
        app=settings.app_name,
        version=settings.app_version,
        cache_enabled=settings.cache_enabled
    )

    # prewarm pipeline
    try:
        get_pipeline()
        logger.info("pipeline_pre_warmed")
    except Exception as e:
        logger.warning("pipeline_prewarm_failed", error= str(e))
        
    yield
    
    # Shutdown
    logger.info("server_shutdown")


#--- FASTAPI App -------------------------------------------------

app = FastAPI(
    title= settings.app_name,
    description="Transform developer notes and git history into build-in-public content",
    version=settings.app_version,
    docs_url="/docs",
    redocs_url= "/redocs",
    lifespan=lifespan,
    )

#---CORS-cross origin resource sharing------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#--- AUTHENTICATION DEPENDENCY FOR ADMIN ENDPOINTS -------------------------------------------------

async def verify_admin_api_key(x_api_key: str = Query(None, description="Admin API key")) -> str:
    """
    Dependency to verify admin API key for protected endpoints.
    If admin_auth_enabled is False (dev mode), allows all requests with warning log.
    If enabled, requires valid API key.
    """
    if not settings.admin_auth_enabled:
        logger.warning(
            "admin_endpoint_called_without_auth",
            message="Admin auth is disabled in settings. Enable in production!"
        )
        return "authorized"  # Dev mode: allow without key
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API key required. Provide via ?x_api_key=<key> query parameter.",
        )
    
    if x_api_key != settings.admin_api_key:
        logger.warning("admin_endpoint_unauthorized", ip="<client_ip>")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return "authorized"


#---ROOT ENDPOINT-------------------------------------------------

@app.get("/",summary="Root endpoint health check")
async def root() -> Dict[str, Any]:
    """
    Simple root endpoint - confirms server is working.
    """
    
    return {
        "status": "online",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "features":[
            "platform_psychology",
            "creator_styles",
            "two_stage_blog",
            "cache",
            "memory",
            ],   
    } 

#--- health check---------------------------------------------
@app.get("/health", summary="detailed health check")
async def health_check() -> Dict[str, Any]:
    """
    Returns a comprehensive health report useful for deployment verification
    """
    checks = {}
    
    # Check 1: API key configuration
    checks["api_key_configured"] = settings.hf_token_configured
    
    # Check 2: Log directory existence and writability
    checks["log_directory"] = os.path.isdir(settings.log_dir)
    if checks["log_directory"]:
        try:
            # Test write permission
            test_file = os.path.join(settings.log_dir, ".health_check")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            checks["log_directory_writable"] = True
        except Exception as e:
            checks["log_directory_writable"] = False
            logger.warning("log_directory_not_writable", error=str(e))
    
    # Check 3: Input directory existence
    checks["input_dir_exists"] = os.path.isdir("inputs")
    
    # Check 4: Pipeline compilation
    pipeline_compiled = False
    try:
        pipeline = get_pipeline()
        pipeline_compiled = pipeline is not None
    except Exception as e:
        logger.warning("pipeline_compilation_failed", error=str(e))
    checks["pipeline_compiled"] = pipeline_compiled
    
    # Check 5: Memory/ChromaDB availability (if enabled)
    if settings.memory_enabled:
        try:
            memory_stats = get_memory_stats()
            checks["memory_available"] = memory_stats.get("status") == "healthy"
        except Exception as e:
            logger.warning("memory_check_failed", error=str(e))
            checks["memory_available"] = False
    
    # Check 6: Cache system availability
    try:
        cache_stats = cache_stats
        checks["cache_available"] = cache_stats.get("status") == "healthy"
    except Exception as e:
        logger.warning("cache_check_failed", error=str(e))
        checks["cache_available"] = False
    
    # Determine overall health status
    critical_checks = ["api_key_configured", "log_directory", "pipeline_compiled"]
    critical_ok = all(checks.get(check, False) for check in critical_checks)
    health_status = "healthy" if critical_ok else "degraded"
    
    return {
        "status": health_status,
        "checks": checks,
        "model": settings.reason_model,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }



#--- STYLES--------------------------------------------------------------

@app.get("/styles")
async def list_styles() -> Dict[str, Any]:

    return {
        "available_styles": list_available_styles(),
        "default_style": "dhruv_default",
        "style_dir": "creator_styles/",
        "how_to_add": "Create creator_styles/yourstyle.md",
    }


#---GENERATE CONTENT---------------------------------------------

@app.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_content(request:GenerateRequest):
    
    logger.info(
        "generate_endpoint_called",
        platform=request.platforms,
        author= request.author_name,
    )
    
    result= run_pipeline_service(
        raw_notes=request.raw_notes,
        raw_git_log=request.raw_git_log,
        platforms=request.platforms,
        author_name=request.author_name,
        style=request.style,
        extra_material=request.extra_material,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Pipeline error"),
        )

    return GenerateResponse(**result)


#--- GENERATE FROM FILE --------------------------------------------

@app.post(
    "/generate/file",
    response_model=GenerateResponse
)
async def generate_from_file(request: GenerateFromFileRequest):
    
    try:
        raw_notes = DumpParserService.load_and_parse_dump(request.notes_file_path)
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    raw_git_log=GitLogService.get_git_log(
        repo_path=request.git_repo_path,
        days_back=request.days_back,
    )
    
    result = run_pipeline_service(
        raw_notes=raw_notes,
        raw_git_log=raw_git_log,
        platforms=request.platforms,
        author_name=request.author_name,
        style= request.style,
        extra_material=request.extra_material,
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error"),
        )
        
    return GenerateResponse(**result)

# ============================================================
# MODELS
# ============================================================

@app.get("/models")
async def list_models() -> Dict[str, Any]:

    return {
        "current_model": settings.generation_model,
        "recommended": "Qwen/Qwen2.5-72B-Instruct:sambanova",
        "available_models": [
            {"id": "Qwen/Qwen2.5-72B-Instruct", "name": "Qwen 2.5 72B (auto)"},
            {"id": "Qwen/Qwen2.5-72B-Instruct:sambanova", "name": "Qwen 2.5 72B (SambaNova)"},
            {"id": "Qwen/Qwen2.5-72B-Instruct:together", "name": "Qwen 2.5 72B (Together AI)"},
            {"id": "Qwen/Qwen2.5-72B-Instruct:nebius", "name": "Qwen 2.5 72B (Nebius)"},
        ],
    }


# ============================================================
# CACHE ENDPOINTS
# ============================================================

@app.get("/cache/stats")
async def cache_stats(_: str = Depends(verify_admin_api_key)) -> Dict[str, Any]:
    try:
        return cache_stats()
    except Exception as e:
        logger.error("cache_stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics",
        )


@app.post("/cache/clear")
async def cache_clear(
    older_than_hours: float = Query(
        default=0,
        ge=0,
        description="Delete files older than this many hours. 0 = delete everything. Must be >= 0.",
    ),
    _: str = Depends(verify_admin_api_key),
) -> Dict[str, Any]:
    try:
        deleted = cache_clear(older_than_hours=older_than_hours)
        logger.info("cache_cleared", deleted_files=deleted, older_than_hours=older_than_hours)
        return {
            "deleted_files": deleted,
            "older_than_hours": older_than_hours,
            "message": f"Deleted {deleted} cache file(s).",
        }
    except Exception as e:
        logger.error("cache_clear_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache",
        )


# ============================================================
# MEMORY ENDPOINT
# ============================================================

@app.get("/memory/stats")
async def memory_stats(_: str = Depends(verify_admin_api_key)) -> Dict[str, Any]:
    try:
        return get_memory_stats()
    except Exception as e:
        logger.error("memory_stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory statistics",
        )


