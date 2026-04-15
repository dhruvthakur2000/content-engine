# ============================================================
# backend/api/main.py — FINAL PRODUCTION VERSION
# ============================================================

import os
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any
from functools import partial

from fastapi import FastAPI, HTTPException, status, Query, Depends
from fastapi.middleware.cors import CORSMiddleware

from content_engine.backend.api.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerateFromFileRequest,
)

from content_engine.backend.services.run_pipeline import run_pipeline_service
from content_engine.backend.ingestion.dump_parser import DumpParserService
from content_engine.backend.utils.logger import setup_logging, get_logger
from content_engine.backend.config.settings import get_settings

from content_engine.backend.cache.cache_manager import get_cache
from content_engine.pipeline.graph import get_pipeline

settings = get_settings()
setup_logging(log_level=settings.log_level)
logger = get_logger(__name__)

_cache = get_cache()


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info(
        "server_starting",
        app=settings.app_name,
        version=settings.app_version,
    )

    try:
        get_pipeline()
        logger.info("pipeline_prewarmed")
    except Exception as e:
        logger.warning("pipeline_prewarm_failed", error=str(e))

    for d in [settings.cache_dir, settings.log_dir, "inputs"]:
        os.makedirs(d, exist_ok=True)

    yield

    logger.info("server_shutdown")


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================

def normalize_platforms(platforms):
    """Fix common user mistakes"""
    mapping = {
        "blogs": "blog",
        "linkdin": "linkedin",
        "tweet": "twitter",
    }

    clean = []
    for p in platforms:
        p = p.lower().strip()
        clean.append(mapping.get(p, p))

    return clean


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "app": settings.app_name,
        "version": settings.app_version,
        "time": datetime.utcnow().isoformat(),
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    try:
        cache_stats = _cache.stats()
    except:
        cache_stats = {}

    return {
        "status": "healthy",
        "pipeline_ready": get_pipeline() is not None,
        "cache_files": cache_stats.get("file_count", 0),
    }


# ============================================================
# GENERATE
# ============================================================

@app.post("/generate", response_model=GenerateResponse)
async def generate_content(request: GenerateRequest):

    platforms = normalize_platforms(request.platforms)

    logger.info(
        "generate_called",
        platforms=platforms,
        has_notes=bool(request.raw_notes),
        has_git=bool(request.raw_git_log),
    )

    # Only pass fields that ACTUALLY EXIST
    pipeline_fn = partial(
        run_pipeline_service,
        raw_notes=request.raw_notes,
        raw_git_log=request.raw_git_log,
        platforms=platforms,
        author_name=request.author_name,
        style=request.style,
        extra_material=request.extra_material,
    )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, pipeline_fn)

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Pipeline failed"),
        )

    return GenerateResponse(**result)


# ============================================================
# GENERATE FROM FILE
# ============================================================

@app.post("/generate/file", response_model=GenerateResponse)
async def generate_from_file(request: GenerateFromFileRequest):

    try:
        parser = DumpParserService()
        raw_notes = parser.load_and_parse_dump(request.notes_file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    pipeline_fn = partial(
        run_pipeline_service,
        raw_notes=raw_notes,
        raw_git_log="",
        platforms=normalize_platforms(request.platforms),
        author_name=request.author_name,
        style=request.style,
        extra_material=request.extra_material,
    )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, pipeline_fn)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return GenerateResponse(**result)


# ============================================================
# CACHE
# ============================================================

@app.get("/cache/stats")
async def cache_stats():
    return _cache.stats()


@app.post("/cache/clear")
async def cache_clear():
    deleted = _cache.clear()
    return {"deleted": deleted}


# ============================================================
# PIPELINE INFO
# ============================================================

@app.get("/pipeline/info")
async def pipeline_info():
    return {
        "nodes": [
            "input_detector",
            "parse_notes",
            "parse_git",
            "parse_code",
            "context_builder",
            "angle_generator",
            "style_selector",
            "blog_blueprint",
            "post_generator",
            "humanize",
        ],
        "architecture": "langgraph + ingestion + evaluation-ready",
    }