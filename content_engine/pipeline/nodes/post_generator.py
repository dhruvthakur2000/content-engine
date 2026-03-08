# ============================================================
# pipeline/nodes/post_generator.py
# ============================================================

from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.messages import HumanMessage

from pipeline.state import PipelineState
from pipeline.utils.node_wrapper import pipeline_node

from backend.llm.providers import get_llm
from backend.llm.prompts import (
    PLATFORM_PROMPTS,
    LINKEDIN_PSYCHOLOGY,
    TWITTER_PSYCHOLOGY,
    STYLE_INJECTION,
    BLOG_POST_PROMPT,
)

from backend.config.settings import get_settings


# Initialize LLM once
llm = get_llm()


# Platform psychology mapping
PLATFORM_PSYCHOLOGY = {
    "linkedin": LINKEDIN_PSYCHOLOGY,
    "twitter": TWITTER_PSYCHOLOGY,
}


def generate_for_platform(
    platform: str,
    context: str,
    narrative_angle: str,
    hook: str,
    key_detail: str,
    style_injection: str,
    blog_blueprint: str,
    style_guide: str,
) -> tuple[str, str]:
    """
    Generates a post for a single platform.
    This function is executed in parallel threads.
    """

    platform_lower = platform.lower()

    try:

        # BLOG GENERATION (Stage 2)
        if platform_lower == "blog":

            effective_blueprint = blog_blueprint or (
                f"Write a technical blog post about: {context[:500]}"
            )

            prompt = BLOG_POST_PROMPT.format(
                blueprint=effective_blueprint,
                context=context,
                style_guide=style_guide or "Write in authentic developer voice.",
            )

        # LINKEDIN / TWITTER
        else:

            prompt_template = PLATFORM_PROMPTS.get(platform_lower)

            if prompt_template is None:
                return platform, f"[Unknown platform: {platform}]"

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

        response = llm.invoke([HumanMessage(content=prompt)])

        return platform, response.content.strip()

    except Exception as e:

        return platform, f"[Generation failed for {platform}: {str(e)}]"


@pipeline_node("post_generator")
def post_generator_node(state: PipelineState) -> PipelineState:
    """
    Final LangGraph node that generates platform-specific posts.
    Supports parallel generation across platforms.
    """

    context = state.get("context", "")
    narrative_angle = state.get("narrative_angle", "ENGINEERING_UPDATE")
    hook = state.get("hook", "Here's what I built today.")
    key_detail = state.get("key_detail", "")
    style_guide = state.get("style_guide", "")
    blog_blueprint = state.get("blog_blueprint", "")
    extra_material = state.get("extra_material", "")
    platforms = state.get("platforms", ["linkedin", "twitter"])

    if not context or len(context.strip()) < 30:
        return {
            "generated_posts": {p: "[No content — insufficient input]" for p in platforms},
            "metadata": {"error": "empty_context"},
        }

    # Inject style guide
    if style_guide:
        style_injection = STYLE_INJECTION.format(style_guide=style_guide)
    else:
        style_injection = (
            "Style: Direct, technical, human. Short sentences. Specific over vague."
        )

    generated_posts: Dict[str, str] = {}

    # Parallel platform generation
    with ThreadPoolExecutor(max_workers=len(platforms)) as executor:

        futures = [
            executor.submit(
                generate_for_platform,
                platform,
                context,
                narrative_angle,
                hook,
                key_detail,
                style_injection,
                blog_blueprint,
                style_guide,
            )
            for platform in platforms
        ]

        for future in as_completed(futures):

            platform, result = future.result()

            generated_posts[platform] = result

    # Metadata
    settings = get_settings()

    metadata = {
        "model": settings.llm_model,
        "platforms_generated": list(generated_posts.keys()),
        "narrative_angle": narrative_angle,
        "style_used": state.get("style", "dhruv_default"),
        "two_stage_blog": bool(blog_blueprint),
        "nodes_executed": [
            "parse_notes",
            "parse_git",
            "context_builder",
            "angle_generator",
            "style_selector",
            "blog_blueprint",
            "post_generator",
        ],
    }  

    return {
        "generated_posts": generated_posts,
        "metadata": metadata,
    }