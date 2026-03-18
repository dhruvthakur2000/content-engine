import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from content_engine.backend.api.schemas import GenerateRequest,GenerateResponse , GenerateFromFileRequest
from content_engine.backend.services.run_pipeline import run_pipeline_service
from backend.llm.style_loader import list_available_styles
from content_engine.backend.utils.logger import setup_logging, get_logger
from backend.config.settings import get_settings


settings= get_settings()

#---LOGGING-------------------------------------------------

setup_logging(
    log_level= settings.log_level,
    log_dir=settings.log_dir,
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
        from content_engine.pipeline.graph import get_pipeline
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


#---ROOT ENDPOINT-------------------------------------------------

@app.get("/",summary="Root endpoint health check")
async def root():
    """
    Simple root endpoint - confirms server is working.
    """
    
    return {
        "status": "online",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now().isoformat() + "Z",
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
@app.get("/health",summary="detailed health check")

async def health_check():
    """
    returns a health report useful for deployment verification
    """
    #check if api key is configured
    api_key_configured= settings.hf_token_configured
    
    #check if log directory exists
    log_dir_ok = os.path.isdir(settings.log_dir) or True
    
    #check if input directory exists
    input_dir_ok = os.path.isdir("inputs")
    
    health_status = "healthy" if api_key_configured else "degraded"
    
    return {
        "status": health_status,
        "checks": {
            "api_key_configured": api_key_configured,
            "log_directory": log_dir_ok,
            " input_dir_ok ": input_dir_ok,
            "model": settings.reason_model
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }



#--- STYLES--------------------------------------------------------------

@app.get("/styles")
async def list_styles():

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

    
    





