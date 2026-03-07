from fastapi import FastAPI
from content_engine.backend.api.schemas import ContentRequest, ContentResponse
from content_engine.backend.services.content_service import ContentService
from content_engine.backend.utils.logger import setup_logging
from content_engine.backend.utils.logger import get_logger


setup_logging("INFO")
logger = get_logger("api")


app = FastAPI(
    title="content_engine",
    description = "AI system that converts dev logs into content",
    version = "0.1"
    )


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

