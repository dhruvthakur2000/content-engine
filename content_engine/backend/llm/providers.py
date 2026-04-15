# ============================================================
# backend/llm/providers.py — FINAL
# ============================================================

from typing import Dict
import time
import threading

from langchain_openai import ChatOpenAI

from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


# --------------------------------------------------------
# TASK → MODEL MAP
# --------------------------------------------------------

TASK_MODEL_MAP: Dict[str, str] = {
    "parse": settings.parse_model,
    "reason": settings.reason_model,
    "generation": settings.generation_model,
    "blog": settings.blog_model,
    "eval": settings.eval_model,
}


FALLBACK_MODELS = [
    settings.fallback_model_1,
    settings.fallback_model_2,
]


# --------------------------------------------------------
# CLIENT FACTORY (cached per model)
# --------------------------------------------------------

_client_cache: Dict[str, ChatOpenAI] = {}


def _get_client(model: str) -> ChatOpenAI:
    if model not in _client_cache:
        _client_cache[model] = ChatOpenAI(
            model=model,
            openai_api_key=settings.hf_token,
            openai_api_base=settings.hf_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            request_timeout=settings.llm_request_timeout,
        )
    return _client_cache[model]


# --------------------------------------------------------
# PROVIDER
# --------------------------------------------------------

class ProviderManager:

    def __init__(self):

        if not settings.hf_token_configured:
            raise ValueError("HF_TOKEN missing in .env")

        logger.info(
            "llm_provider_initialized",
            provider="huggingface",
            router=settings.hf_base_url,
        )

    def _model_for_task(self, task: str) -> str:
        return TASK_MODEL_MAP.get(task, settings.generation_model)

    def invoke(self, messages, task: str = "generation", stream: bool = False):

        primary_model = self._model_for_task(task)
        models_to_try = [primary_model] + FALLBACK_MODELS

        for model_name in models_to_try:

            client = _get_client(model_name)

            for attempt in range(settings.llm_max_retries):

                try:
                    start = time.time()

                    if stream:
                        return client.stream(messages)

                    response = client.invoke(messages)

                    latency = round(time.time() - start, 3)

                    logger.info(
                        "llm_success",
                        model=model_name,
                        task=task,
                        latency=latency,
                    )

                    return response

                except Exception as e:

                    logger.warning(
                        "llm_attempt_failed",
                        model=model_name,
                        task=task,
                        attempt=attempt,
                        error=str(e),
                    )

                    time.sleep(2 ** attempt)

            logger.warning(
                "switching_to_fallback_model",
                failed_model=model_name,
            )

        raise RuntimeError("All LLM models failed.")


# --------------------------------------------------------
# SINGLETON
# --------------------------------------------------------

_provider = None
_lock = threading.Lock()


def get_llm() -> ProviderManager:
    global _provider

    if _provider is None:
        with _lock:
            if _provider is None:
                _provider = ProviderManager()

    return _provider