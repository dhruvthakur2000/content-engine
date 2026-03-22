from typing import Dict

from langchain_core.messages import HumanMessage

from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node

from content_engine.backend.llm.providers import get_llm
from content_engine.backend.llm.prompts import generate_content_prompt
from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)

NODE_NAME = "post_generator"
llm = get_llm()

VALID_PLATFORMS = ["linkedin", "twitter", "blog"]


@pipeline_node(NODE_NAME)
def post_generator_node(state: PipelineState) -> PipelineState:

    context = state.get("context", "")
    if not context:
        raise ValueError("context missing in pipeline state")
    
    narrative_angle = state.get("narrative_angle", "SYSTEM_INSIGHT")
    
    blog_blueprint = state.get("blog_blueprint", "")
    
    platforms = state.get("platforms")
    if not platforms:
        raise ValueError("Platforms missing in pipeline state")

    # Inject blueprint into context (for blogs)
    if blog_blueprint:
        context += f"\n\nBLOG BLUEPRINT:\n{blog_blueprint}"

    if not context or len(context.strip()) < 30:
        return {
            "generated_posts": {p: "[No content — insufficient input]" for p in platforms},
            "metadata": {"error": "empty_context"},
        }

    generated_posts: Dict[str, str] = {}

    for platform in platforms:

        platform_lower = platform.lower()

        if platform_lower not in VALID_PLATFORMS:
            generated_posts[platform] = f"[Unknown platform: {platform}]"
            continue

        try:
            system_prompt, user_prompt = generate_content_prompt(
                context=context,
                angle=narrative_angle,
                platform=platform_lower,
            )

            response = llm.invoke(
                [HumanMessage(content=system_prompt + "\n\n" + user_prompt)],
                task="generation",
            )

            if response and hasattr(response, "content"):
                generated_posts[platform] = response.content.strip()
            else:
                raise ValueError("Empty response from LLM")

            logger.info(
                "platform_generated",
                platform=platform,
                output_chars=len(generated_posts[platform]),
            )

        except Exception as e:
            logger.error(
                "platform_generation_error",
                platform=platform,
                error=str(e),
            )
            generated_posts[platform] = f"[Generation failed: {str(e)}]"

    settings = get_settings()

    metadata = {
        "model": settings.generation_model,
        "platforms_generated": list(generated_posts.keys()),
        "narrative_angle": narrative_angle,
        "style_used": state.get("style", "dhruv_default"),
    }

    return {
        "generated_posts": generated_posts,
        "metadata": metadata,
    }