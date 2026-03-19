from typing import Dict

from langchain_core.messages import HumanMessage

from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node

from content_engine.backend.llm.providers import get_llm
from content_engine.backend.llm.prompts import (
    PLATFORM_PROMPTS,
    LINKEDIN_PSYCHOLOGY,
    TWITTER_PSYCHOLOGY,
    STYLE_INJECTION,
    BLOG_POST_PROMPT,
)
from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)

NODE_NAME = "post_generator"

llm = get_llm()

PLATFORM_PSYCHOLOGY = {
    "linkedin": LINKEDIN_PSYCHOLOGY,
    "twitter": TWITTER_PSYCHOLOGY,
}


@pipeline_node(NODE_NAME)
def post_generator_node(state: PipelineState) -> PipelineState:
    """
    Final pipeline node: generates platform-specific posts.

    Reads:
        context
        narrative_angle
        hook
        key_detail
        style_guide
        blog_blueprint
        memory_context
        platforms

    Writes:
        generated_posts
        metadata
    """

    context = state.get("context", "")
    narrative_angle = state.get("narrative_angle", "ENGINEERING_UPDATE")
    hook = state.get("hook", "Here's what I built today.")
    key_detail = state.get("key_detail", "")
    style_guide = state.get("style_guide", "")
    blog_blueprint = state.get("blog_blueprint", "")
    memory_context = state.get("memory_context", "")
    platforms = state.get("platforms", ["linkedin", "twitter"])

    if not context or len(context.strip()) < 30:
        return {
            "generated_posts": {p: "[No content — insufficient input]" for p in platforms},
            "metadata": {"error": "empty_context"},
        }

    # -----------------------------------------------------
    # STYLE INJECTION
    # -----------------------------------------------------

    style_injection = (
        STYLE_INJECTION.format(style_guide=style_guide)
        if style_guide
        else "Style: Direct, technical, human. Short sentences. Specific over vague."
    )

    # -----------------------------------------------------
    # MEMORY CONTEXT
    # -----------------------------------------------------

    memory_block = ""
    if memory_context and memory_context.strip():
        memory_block = f"\n\n{memory_context}\n"

    generated_posts: Dict[str, str] = {}

    # -----------------------------------------------------
    # PLATFORM LOOP
    # -----------------------------------------------------

    for platform in platforms:

        platform_lower = platform.lower()

        try:

            # BLOG GENERATION
            if platform_lower == "blog":

                effective_blueprint = (
                    blog_blueprint
                    or f"Write a technical blog post about: {context[:500]}"
                )

                prompt = BLOG_POST_PROMPT.format(
                    blueprint=effective_blueprint,
                    context=context,
                    style_guide=style_guide or "Write in authentic developer voice.",
                )

                prompt += memory_block

                response = llm.invoke(
                    [HumanMessage(content=prompt)],
                    task="blog",
                )

                if response and hasattr(response, 'content'):
                    generated_posts[platform] = response.content.strip()
                else:
                    raise ValueError("Empty response from LLM")

                logger.info(
                    "platform_generated",
                    platform=platform,
                    output_chars=len(generated_posts[platform]),
                )
                continue

            # LINKEDIN / TWITTER GENERATION
            prompt_template = PLATFORM_PROMPTS.get(platform_lower)

            if prompt_template is None:
                generated_posts[platform] = f"[Unknown platform: {platform}]"
                continue

            psychology = PLATFORM_PSYCHOLOGY.get(platform_lower, "")

            prompt = prompt_template.format(
                linkedin_psychology=psychology if platform_lower == "linkedin" else "",
                twitter_psychology=psychology if platform_lower == "twitter" else "",
                style_injection=style_injection,
                context=context,
                angle=narrative_angle,
                hook=hook,
                key_detail=key_detail,
            )

            prompt += memory_block

            response = llm.invoke(
                [HumanMessage(content=prompt)],
                task="generation",
            )

            if response and hasattr(response, 'content'):
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

            generated_posts[platform] = f"[Generation failed for {platform}: {str(e)}]"

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    settings = get_settings()

    metadata = {
        "model": settings.generation_model,
        "platforms_generated": list(generated_posts.keys()),
        "narrative_angle": narrative_angle,
        "style_used": state.get("style", "dhruv_default"),
        "two_stage_blog": bool(blog_blueprint),
        "memory_context_used": bool(memory_context),
    }

    return {
        "generated_posts": generated_posts,
        "metadata": metadata,
    }