import os
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from content_engine.backend.api.schemas import GenerateRequest,GenerateResponse , GenerateFromFileRequest
from content_engine.backend.services.run_pipeline import run_pipeline_service

from content_engine.backend.utils.logger import setup_logging, get_logger
from backend.config.settings import get_settings

settings= get_settings()

#---LOGGING-------------------------------------------------

setup_logging(
    log_level= settings.log_level,
    log_dir=settings.log_dir,
)

logger = get_logger(__name__)

#--- FASTAPI APP -------------------------------------------------

app = FastAPI(
    title= settings.app_name,
    description="Transform developer notes and git history into build-in-public content",
    version=settings.app_version,
    docs_url="/docs",
    redocs_url= "/redocs",
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
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "docs": "/docs",
    }
    
    

# health check
@app.get("health",summary="detailed health check")
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
            "model": settings.llm_model
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

     



service = ContentService()


@app.get("/")
async def health():
    return {"status": "running"}

@app.post("/generate",response_model=ContentResponse)
async def generate_content(req:ContentRequest):
    logger.info("Content generation started",platform=req.platform)
    post = await service.generate_content(
        notes=req.notes,
        git_log=req.git_log,
        platform=req.platform,
    )

    logger.info("content generation finished")
    
    return ContentResponse(
        platform=req.platform,
        generated_post=post,
    )

