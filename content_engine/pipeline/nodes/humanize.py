from content_engine.pipeline.state import PipelineState
from content_engine.pipeline.utils.node_wrapper import pipeline_node as _pn7
from content_engine.backend.llm.providers import get_llm as _get_llm7
from content_engine.backend.cache.cache_manager import get_cache as _get_cache7
from content_engine.backend.llm.prompts import HUMANIZE_PASS_PROMPT
from content_engine.backend.utils.logger import get_logger as _get_logger7

_llm7 = _get_llm7()
_cache7 = _get_cache7()
_logger7 = _get_logger7("humanize")

NODE_NAME = "humanize"


@_pn7(NODE_NAME)
def humanize_node(state: PipelineState) -> PipelineState:

    generated_posts = state.get("generated_posts", {})

    if not generated_posts:
        return {}

    humanized = {}

    for platform, content in generated_posts.items():

        if not content or content.startswith("["):
            humanized[platform] = content
            continue

        cache_key = f"{platform}|{content}|v1"

        cached = _cache7.read(input_data=cache_key, node_name=NODE_NAME)

        if cached and "content" in cached:
            humanized[platform] = cached["content"]
            continue

        prompt = HUMANIZE_PASS_PROMPT.format(generated_content=content)

        try:
            from langchain_core.messages import HumanMessage as HM7
            response = _llm7.invoke([HM7(content=prompt)], task="generation")
            edited = response.content.strip()

            if edited and len(edited) > len(content) * 0.5:
                humanized[platform] = edited

                _cache7.write(
                    input_data=cache_key,
                    result={"content": edited},
                    node_name=NODE_NAME,
                )

            else:
                humanized[platform] = content
                _logger7.warning("humanize_suspicious_output", platform=platform)

        except Exception as e:
            _logger7.error("humanize_error", error=str(e))
            humanized[platform] = content

    return {"generated_posts": humanized}