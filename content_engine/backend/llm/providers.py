from abc import ABC, abstractmethod
from typing import Optional, Type 
import time
from langchain_openai import  ChatOpenAI
from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger


settings = get_settings()
logger = get_logger(__name__)

#Model routing using a dict

Task_model_map=dict[str,str]={
    "parse": settings.parse_model,
    "reason": settings.reason_model,
    "generation": settings.generation_model,
    "blog": settings.blog_model
}

#fallback chain for generation Task

Fallback_model: list[str]=[
    settings.fallback_model_1,
    settings.fallback_model_2
]

# LLM Client Factory

def _create_client(model: str) -> ChatOpenAI:
    """
    Creates a LangChain ChatOpenAI client configured
    to talk to the HuggingFace inference router.
    """

    return ChatOpenAI(
        model=model,
        openai_api_key=settings.hf_api_key,
        openai_api_base=settings.hf_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        request_timeout=settings.llm_request_timeout,
        default_headers={
            "X-App-Name": settings.app_name,
            "X-App-Version": settings.app_version,
        },
    )
    
    
# provider management
class ProviderManager:
    def __init__(self):
        self.settings=settings
        if not self.settings.hf_token_configured:
            raise ValueError(
                "HF TOKEN NOT CONFIGURED"
                "ADD HF_TOKEN to your .env file"
            )
            
        logger.info(
            "llm_provider_initialized",
            provider="huggingface",
            router= self.settings.hf_base_url
        )
        
        
        
    # --------------------------------------------------------
    # model selection
    # --------------------------------------------------------

    def _model_for_task(self, task: str) -> str:

        model = Task_model_map.get(task)

        if model is None:
            model = self.settings.generation_model

        return model

    # --------------------------------------------------------
    # invoke model
    # --------------------------------------------------------

    def invoke(self, messages, task: str = "generation", stream: bool = False):

        primary_model = self._model_for_task(task)

        models_to_try = [primary_model] + Fallback_model

        for model_name in models_to_try:

            client = _create_client(model_name)

            for attempt in range(self.settings.llm_max_retries):

                try:

                    start_time = time.time()

                    if stream:
                        return client.stream(messages)

                    response = client.invoke(messages)

                    latency = round(time.time() - start_time, 3)

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


# ============================================================
# SINGLETON
# ============================================================

_provider_manager: ProviderManager | None = None


def get_llm() -> ProviderManager:
    """
    Global entry point used by the pipeline.
    """

    global _provider_manager

    if _provider_manager is None:
        _provider_manager = ProviderManager()

    return _provider_manager