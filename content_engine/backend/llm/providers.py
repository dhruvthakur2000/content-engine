from abc import ABC, abstractmethod
from typing import Optional
import httpx

from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger


settings = get_settings()
logger = get_logger("llm.provider")


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