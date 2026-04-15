from typing import Dict
from langchain_core.messages import HumanMessage

from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node
from content_engine.backend.llm.providers import get_llm
from content_engine.backend.llm.prompts import generate_content_prompt
from content_engine.backend.cache.cache_manager import get_cache
from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

NODE_NAME = "post_generator"
llm = get_llm()
cache = get_cache()

VALID_PLATFORMS = {"linkedin", "twitter", "blog"}
MAX_CONTEXT = 12000


@pipeline_node(NODE_NAME)
def post_generator_node(state: PipelineState) -> PipelineState:

    context = state.get("context", "")
    if not context:
        raise ValueError("context missing — context_builder failed")

    narrative_angle = state.get("narrative_angle", "SYSTEM_INSIGHT")
    blog_blueprint = state.get("blog_blueprint", "")
    platforms = state.get("platforms", [])

    if not platforms:
        raise ValueError("platforms missing")

    style_guide = state.get("style_guide", "")
    if not style_guide:
        logger.warning("style_guide_empty")

    # --- CONTEXT TRUNCATION ---
    if len(context) > MAX_CONTEXT:
        logger.warning("context_truncated", length=len(context))
        context = context[:MAX_CONTEXT] + "\n\n[...truncated...]"

    # --- BLOG BLUEPRINT INJECTION ---
    if blog_blueprint and "blog" in [p.lower() for p in platforms]:
        context = context + f"\n\nBLOG BLUEPRINT:\n{blog_blueprint}"

    if len(context.strip()) < 30:
        return {
            "generated_posts": {p: "[Insufficient context]" for p in platforms},
            "metadata": {"error": "context_too_short"},
        }

    generated_posts: Dict[str, str] = {}

    import os
    debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "debug_output", "generated_posts")
    os.makedirs(debug_dir, exist_ok=True)

    for platform in platforms:
        p = platform.lower()

        if p not in VALID_PLATFORMS:
            generated_posts[platform] = f"[Unknown platform: {platform}]"
            continue

        # --- CACHE ---
        cache_key = f"{p}|{context}|{narrative_angle}|{style_guide}|v2"

        cached = cache.read(input_data=cache_key, node_name=NODE_NAME)
        if cached and "content" in cached:
            generated_posts[platform] = cached["content"]
            # Save cached content for debugging
            try:
                with open(os.path.join(debug_dir, f"{p}_latest.txt"), "w", encoding="utf-8") as f:
                    f.write(cached["content"])
            except Exception as file_exc:
                logger.warning(f"Failed to write cached {p} output: {file_exc}")
            continue

        try:
            system_prompt, user_prompt = generate_content_prompt(
                context=context,
                angle=narrative_angle,
                platform=p,
                style_guide=style_guide,
            )

            full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"

            response = llm.invoke(
                [HumanMessage(content=full_prompt)],
                task="generation",
            )

            if not response or not hasattr(response, "content"):
                raise ValueError("Empty LLM response")

            generated = response.content.strip()

            # --- VALIDATION ---
            if len(generated) < 50:
                raise ValueError("Output too short")

            generated_posts[platform] = generated

            # Save generated content for debugging
            try:
                with open(os.path.join(debug_dir, f"{p}_latest.txt"), "w", encoding="utf-8") as f:
                    f.write(generated)
            except Exception as file_exc:
                logger.warning(f"Failed to write {p} output: {file_exc}")

            cache.write(
                input_data=cache_key,
                result={"content": generated},
                node_name=NODE_NAME,
            )

            logger.info("platform_generated", platform=p, chars=len(generated))

        except Exception as e:
            logger.error("generation_error", platform=p, error=str(e))
            generated_posts[platform] = f"[Generation failed: {str(e)}]"

    return {
        "generated_posts": generated_posts,
        "metadata": {
            "model": settings.generation_model,
            "platforms_generated": list(generated_posts.keys()),
            "narrative_angle": narrative_angle,
            "style_used": state.get("style", "dhruv_default"),
            "style_guide_applied": bool(style_guide),
        },
    }