from abc import ABC, abstractmethod
from openai import AsyncOpenAI
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
    
    Any class that inherits from this MUST implement generate().
    This enforces a consistent interface across all providers.
    
    If you want to add a new provider (e.g., Groq, Bedrock, local Ollama),
    just subclass this and implement generate(). Everything else works automatically.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None
        ) -> str:

        temperature = temperature or settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens
        """
        Generate text from the LLM and return it as a plain string.
        Args:
            system prompt: defines WHO the model is and HOW it should behave
            user prompt:   defines WHAT it should do right now
            temperature:   0.4 for summaries (need accuracy), 0.8 for posts (need creativity)
        """
        pass


# =============================================================================
# OPENROUTER PROVIDER
# =============================================================================

class OpenRouterProvider(LLMProvider):
    """
    OpenRouter provider.

    OpenRouter exposes an OpenAI-compatible API endpoint, so we can
    use the OpenAI SDK by simply changing the base_url.

    Docs:
    https://openrouter.ai/docs
    """

    def __init__(self):

        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        # Example:
        # qwen/qwen2.5-7b-instruct
        # deepseek/deepseek-chat
        self.model = settings.openrouter_model

    async def generate(self, system: str, user: str, temperature: float = 0.7) -> str:

        response = await self.client.chat.completions.create(
            model=self.model,

            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],

            temperature=temperature,
            max_tokens=2000,
        )

        return response.choices[0].message.content.strip()


# =============================================================================
# OPENAI PROVIDER (Optional)
# =============================================================================

class OpenAIProvider(LLMProvider):

    def __init__(self):

        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def generate(self, system: str, user: str, temperature: float = 0.7) -> str:

        response = await self.client.chat.completions.create(
            model=self.model,

            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],

            temperature=temperature,
            max_tokens=2000,
        )

        return response.choices[0].message.content.strip()


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_llm() -> LLMProvider:
    """
    Factory function — reads LLM_PROVIDER from settings and returns the
    correct provider instance.
    
    USAGE in other files:
        llm = get_llm()
        result = await llm.generate(system_prompt, user_prompt)
    
    HOW TO ADD A NEW PROVIDER:
        1. Create NewProvider(LLMProvider) class above
        2. Add elif provider == "newname": return NewProvider()
        3. Set LLM_PROVIDER=newname in .env
        → Done. No other files need changing.
    """

    provider = settings.llm_provider.lower()

    if provider == "openrouter":
        return OpenRouterProvider()

    elif provider == "openai":
        return OpenAIProvider()

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. "
            f"Valid options: openrouter, openai"
        )
    

























from abc import ABC, abstractmethod
from openai import AsyncOpenAI

from content_engine.backend.config.settings import get_settings
from content_engine.backend.utils.logger import get_logger


settings = get_settings()
logger = get_logger("llm.provider")


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    Any class that inherits from this MUST implement generate().
    This enforces a consistent interface across all providers.
    
    If you want to add a new provider (e.g., Groq, Bedrock, local Ollama),
    just subclass this and implement generate(). Everything else works automatically.
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate text from the LLM and return it as a plain string.
        Args:
            system prompt: defines WHO the model is and HOW it should behave
            user prompt:   defines WHAT it should do right now
            temperature:   0.4 for summaries (need accuracy), 0.8 for posts (need creativity)
        """



class OpenRouterProvider(LLMProvider):

    def __init__(self):

        logger.info("initializing_openrouter_provider")

        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )

        self.model = settings.llm_model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:

        temperature = temperature or settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens

        logger.info(
            "llm_request",
            model=self.model,
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content.strip()

        logger.info("llm_response_received")

        return content


def get_llm() -> LLMProvider:
    """
    Factory function — reads LLM_PROVIDER from settings and returns the
    correct provider instance.
    
    USAGE in other files:
        llm = get_llm()
        result = await llm.generate(system_prompt, user_prompt)
    
    HOW TO ADD A NEW PROVIDER:
        1. Create NewProvider(LLMProvider) class above
        2. Add elif provider == "newname": return NewProvider()
        3. Set LLM_PROVIDER=newname in .env
        → Done. No other files need changing.
    """

    provider = settings.llm_provider.lower()

    if provider == "openrouter":
        return OpenRouterProvider()

    elif provider == "openai":
        return OpenAIProvider()

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. "
            f"Valid options: openrouter, openai"
        )