from abc import ABC, abstractmethod
from typing import Optional, Type 
import time
from langchain_openai import  ChatOpenAI
from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger


settings = get_settings()
logger = get_logger("llm.providers")

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
        openai_api_key=settings.hf_token,
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
    def init(self):
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
    
    












# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    This layer isolates the rest of the application from the
    underlying model provider implementation.

    Your pipeline nodes interact with this interface only.

    This design makes it easy to switch providers in the future
    without modifying the pipeline logic.

    Example:
        llm = get_llm()

        result = await llm.generate(
            system_prompt="You are a senior backend engineer.",
            user_prompt="Explain the purpose of Redis caching."
        )
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using the LLM.

        Args:
            system_prompt:
                Defines the role, behavior, and constraints of the model.

            user_prompt:
                The instruction or task given to the model.

            temperature:
                Controls randomness.
                Lower = deterministic, higher = more creative.

            max_tokens:
                Maximum number of tokens the model may generate.

        Returns:
            Generated text output from the model.
        """
        pass


# =============================================================================
# HUGGINGFACE PROVIDER
# =============================================================================


class HuggingFaceProvider(LLMProvider):
    """
    HuggingFace Inference API provider.

    This provider uses HuggingFace hosted inference models.

    Advantages:
        - Access to state-of-the-art open models
        - No local GPU required
        - Simple REST API

    Recommended models for this project:
        - meta-llama/Meta-Llama-3-70B-Instruct
        - Qwen/Qwen2.5-72B-Instruct
        - mistralai/Mixtral-8x7B-Instruct
    """

    def __init__(self):

        logger.info("initializing_huggingface_provider")

        self.api_key = settings.hf_api_key
        self.model = settings.llm_model

        self.endpoint = f"https://api-inference.huggingface.co/models/{self.model}"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:

        temperature = temperature or settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens

        logger.info(
            "hf_llm_request",
            model=self.model,
        )

        prompt = f"{system_prompt}\n\n{user_prompt}"

        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
            }
        }

        async with httpx.AsyncClient(timeout=120) as client:

            response = await client.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

        if isinstance(data, list) and len(data) > 0:
            content = data[0]["generated_text"]
        else:
            content = str(data)

        logger.info("hf_llm_response_received")

        return content.strip()


# =============================================================================
# SINGLETON FACTORY
# =============================================================================


_provider_instance: Optional[LLMProvider] = None


def get_llm() -> LLMProvider:
    """
    Returns a singleton instance of the configured LLM provider.

    This ensures the provider client is initialized only once
    during the application lifecycle.

    Configuration is controlled through environment variables.

    Example `.env` configuration:

        LLM_PROVIDER=huggingface
        LLM_MODEL=meta-llama/Meta-Llama-3-70B-Instruct
    """

    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider = settings.llm_provider.lower()

    if provider == "huggingface":
        _provider_instance = HuggingFaceProvider()

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. "
            f"Valid option: huggingface"
        )

    return _provider_instance